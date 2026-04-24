"""
SENTINEL - Face Recognition Module
Uses OpenCV for detection + DeepFace for recognition.
No dlib, no C++ compiler, no face_recognition package.
Fully compatible with Python 3.14+.
"""

import cv2
import numpy as np
import threading
import time
from pathlib import Path
from datetime import datetime
from typing import Callable

from utils.config import Config
from utils.logger import get_logger, event_logger

logger = get_logger("face_recognition")


class FaceDetector:
    """
    Lightweight face detector using OpenCV Haar Cascades.
    Runs natively via OpenCV with pre-packaged models.
    """

    def __init__(self) -> None:
        self._detector = None
        self._init_detector()

    def _init_detector(self) -> None:
        try:
            cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
            self._detector = cv2.CascadeClassifier(cascade_path)
            logger.info("OpenCV Haar Cascade Face Detection initialized.")
        except Exception as e:
            logger.error(f"OpenCV Face Detection init failed: {e}")

    def detect(self, frame: np.ndarray) -> list[dict]:
        """
        Detect faces in a BGR frame.
        Returns list of dicts: {bbox: (x,y,w,h), confidence: float}
        """
        if self._detector is None:
            return []
        try:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            # Detect faces using standard Haar Cascade with strict matching to reduce false positives
            rects = self._detector.detectMultiScale(
                gray, scaleFactor=1.1, minNeighbors=8, minSize=(60, 60)
            )
            faces = []
            for (x, y, w, h) in rects:
                faces.append({
                    "bbox": (int(x), int(y), int(w), int(h)),
                    "confidence": 1.0,  # Haar Cascades don't expose simple 0-1 confidence natively
                })
            return faces
        except Exception as e:
            logger.warning(f"Face detection error: {e}")
            return []


class FaceRecognizer:
    """
    Recognizes faces against enrolled known-faces database.
    Uses DeepFace with VGG-Face / Facenet512 backend (pure Python).
    Falls back to OpenCV histogram comparison if DeepFace unavailable.
    """

    def __init__(self) -> None:
        self._known_faces_dir = Config.KNOWN_FACES_DIR
        self._known_embeddings: list[dict] = []  # [{name, embedding}]
        self._deepface_available = False
        self._mode = Config.FACE_RECOGNITION_MODE
        self._init_recognizer()
        self.load_known_faces()

    def _init_recognizer(self) -> None:
        if self._mode == "deepface":
            try:
                import deepface  # noqa: F401
                self._deepface_available = True
                logger.info("DeepFace backend initialized.")
            except ImportError:
                logger.warning("DeepFace not available. Falling back to histogram.")
        elif self._mode == "opencv_only":
            logger.info("Running in detection-only mode (no recognition).")

    # ─── Enrollment ───────────────────────────────────────────

    def enroll_face(self, frame: np.ndarray, name: str, reload: bool = True) -> bool:
        """Save a face image for a known person."""
        save_dir = self._known_faces_dir / name
        save_dir.mkdir(parents=True, exist_ok=True)
        # Add microsecond to avoid filename collisions during rapid burst capture
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        path = save_dir / f"{timestamp}.jpg"
        cv2.imwrite(str(path), frame)
        logger.info(f"Enrolled face for '{name}': {path.name}")
        if reload:
            event_logger.log_event("ENROLLMENT", f"Enrolled: {name}", "INFO")
            self.load_known_faces()
        return True

    def load_known_faces(self) -> None:
        """Scan known_faces directory and cache embeddings AND histograms as backup."""
        self._known_embeddings = []
        logger.info("Loading face database...")
        
        for person_dir in self._known_faces_dir.iterdir():
            if not person_dir.is_dir(): continue
            name = person_dir.name
            for img_path in person_dir.glob("*.jpg"):
                entry = {"name": name, "path": img_path}
                
                # Always cache histogram as a bulletproof backup
                try:
                    img = cv2.imread(str(img_path))
                    if img is not None:
                        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                        hist = cv2.equalizeHist(cv2.resize(gray, (100, 100)))
                        entry["hist"] = cv2.calcHist([hist], [0], None, [256], [0, 256])
                        cv2.normalize(entry["hist"], entry["hist"])
                except Exception:
                    pass

                # Try to cache DeepFace embedding if available
                if self._deepface_available and self._mode == "deepface":
                    try:
                        from deepface import DeepFace
                        objs = DeepFace.represent(
                            img_path=str(img_path),
                            model_name="Facenet512",
                            detector_backend="skip",
                            enforce_detection=False,
                        )
                        if objs:
                            entry["embedding"] = objs[0]["embedding"]
                    except Exception:
                        pass # Will use histogram fallback during recognize()
                
                self._known_embeddings.append(entry)
                
        logger.info(f"Loaded {len(self._known_embeddings)} face samples.")

    # ─── Recognition ──────────────────────────────────────────

    def recognize(self, face_crop: np.ndarray) -> tuple[str, float]:
        """
        Identify a face crop.
        Returns (name, confidence) — name is 'UNKNOWN' if not matched.
        """
        if not self._known_embeddings:
            return "UNKNOWN", 0.0

        if self._deepface_available and self._mode == "deepface":
            return self._recognize_deepface(face_crop)
        else:
            return self._recognize_histogram(face_crop)

    def _recognize_deepface(self, face_crop: np.ndarray) -> tuple[str, float]:
        try:
            from deepface import DeepFace
            objs = DeepFace.represent(
                img_path=face_crop,
                model_name="Facenet512",
                detector_backend="skip",
                enforce_detection=False,
            )
            if not objs: return "UNKNOWN", 0.0
            
            probe_vec = np.array(objs[0]["embedding"])
            best_name, best_dist = "UNKNOWN", float("inf")
            max_dist = 1.0 - Config.FACE_CONFIDENCE_THRESHOLD

            for entry in self._known_embeddings:
                if "embedding" not in entry: continue
                target_vec = np.array(entry["embedding"])
                
                # Cosine distance
                dist = 1.0 - (np.dot(probe_vec, target_vec) / (np.linalg.norm(probe_vec) * np.linalg.norm(target_vec)))
                
                if dist < max_dist and dist < best_dist:
                    best_dist = dist
                    best_name = entry["name"]

            confidence = max(0.0, 1.0 - best_dist) if best_name != "UNKNOWN" else 0.0
            return best_name, round(confidence, 3)
        except Exception as e:
            logger.warning(f"DeepFace failed: {e}. Using histogram fallback.")
            return self._recognize_histogram(face_crop)

    def _recognize_histogram(self, face_crop: np.ndarray) -> tuple[str, float]:
        """Improved histogram-based recognizer with lighting normalization."""
        try:
            # Normalize lighting using Histogram Equalization
            gray_probe = cv2.cvtColor(face_crop, cv2.COLOR_BGR2GRAY)
            equalized_probe = cv2.equalizeHist(cv2.resize(gray_probe, (100, 100)))
            
            probe_hist = cv2.calcHist([equalized_probe], [0], None, [256], [0, 256])
            cv2.normalize(probe_hist, probe_hist)

            best_name = "UNKNOWN"
            best_score = 0.0

            for entry in self._known_embeddings:
                # Use cached histogram if available
                if "hist" in entry:
                    sample_hist = entry["hist"]
                else:
                    img = cv2.imread(str(entry["path"]))
                    if img is None: continue
                    gray_sample = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                    equalized_sample = cv2.equalizeHist(cv2.resize(gray_sample, (100, 100)))
                    sample_hist = cv2.calcHist([equalized_sample], [0], None, [256], [0, 256])
                    cv2.normalize(sample_hist, sample_hist)
                
                score = cv2.compareHist(probe_hist, sample_hist, cv2.HISTCMP_CORREL)
                if score > best_score:
                    best_score = score
                    best_name = entry["name"]

            if best_score < 0.75:
                return "UNKNOWN", 0.0
            return best_name, round(best_score, 3)

        except Exception as e:
            logger.warning(f"Histogram recognition error: {e}")
            return "UNKNOWN", 0.0


class CameraMonitor:
    """
    Real-time camera loop that:
    1. Detects faces in each frame
    2. Recognizes each detected face
    3. Fires callbacks on KNOWN / UNKNOWN events
    """

    def __init__(
        self,
        on_unknown: Callable[[np.ndarray, dict], None] | None = None,
        on_known: Callable[[str, np.ndarray], None] | None = None,
        on_frame: Callable[[np.ndarray], None] | None = None,
    ) -> None:
        self._detector = FaceDetector()
        self._recognizer = FaceRecognizer()
        self._on_unknown = on_unknown
        self._on_known = on_known
        self._on_frame = on_frame
        self._running = False
        self._thread: threading.Thread | None = None
        self._cap: cv2.VideoCapture | None = None
        self._last_alert_time: float = 0.0

        # Async recognition state
        self._recognizing_lock = threading.Lock()
        self._is_recognizing = False
        self._last_face_info = ("UNKNOWN", 0.0)
        self._unknown_start_time: float = 0.0
        self._last_log_time: dict[str, float] = {}  # Per-person log throttling
        self._latest_raw_frame: np.ndarray | None = None
        self._frame_lock = threading.Lock()

    @property
    def recognizer(self) -> FaceRecognizer:
        return self._recognizer

    def get_latest_frame(self) -> np.ndarray | None:
        with self._frame_lock:
            return self._latest_raw_frame.copy() if self._latest_raw_frame is not None else None

    def start(self, camera_index: int = 0) -> bool:
        if self._running:
            return True
        self._cap = cv2.VideoCapture(camera_index)
        if not self._cap.isOpened():
            logger.error("Cannot open camera.")
            return False
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        logger.info("Camera monitoring started.")
        event_logger.log_event("CAMERA", "Camera monitoring started", "INFO")
        return True

    def stop(self) -> None:
        self._running = False
        if self._thread:
            self._thread.join(timeout=3)
        if self._cap:
            self._cap.release()
        logger.info("Camera monitoring stopped.")
        event_logger.log_event("CAMERA", "Camera monitoring stopped", "INFO")

    def _async_recognize(self, crop: np.ndarray, face: dict) -> None:
        try:
            name, conf = self._recognizer.recognize(crop)
            with self._recognizing_lock:
                self._last_face_info = (name, conf)
                self._is_recognizing = False
                
            now = time.time()
            if name == "UNKNOWN":
                if self._unknown_start_time == 0:
                    self._unknown_start_time = now
                
                # Only alert if seen unknown for at least 3.0 seconds (grace period)
                if (now - self._unknown_start_time) >= 3.0:
                    if now - self._last_alert_time >= Config.ALERT_COOLDOWN_SECONDS:
                        self._last_alert_time = now
                        if self._on_unknown:
                            self._on_unknown(crop, face)
                        event_logger.log_event("INTRUSION_FACE", "Unknown face detected", "CRITICAL")
            else:
                self._unknown_start_time = 0  # Reset on successful identification
                
                # Throttle logging: only log "identified" once every 5 seconds
                if now - self._last_log_time.get(name, 0) >= 5.0:
                    self._last_log_time[name] = now
                    if self._on_known:
                        self._on_known(name, crop)
                    event_logger.log_event("FACE_KNOWN", f"Identified: {name}", "INFO")
        except Exception as e:
            logger.warning(f"Async recognition error: {e}")
            with self._recognizing_lock:
                self._is_recognizing = False

    def _loop(self) -> None:
        while self._running:
            ret, frame = self._cap.read()
            if not ret:
                time.sleep(0.1)
                continue

            with self._frame_lock:
                self._latest_raw_frame = frame.copy()

            faces = self._detector.detect(frame)
            annotated = frame.copy()

            if faces:
                # Process the largest face to avoid overwhelming the recognizer
                faces.sort(key=lambda f: f["bbox"][2] * f["bbox"][3], reverse=True)
                face = faces[0]
                
                x, y, w, h = face["bbox"]
                # Clamp crop to frame
                y1, y2 = max(0, y), min(frame.shape[0], y + h)
                x1, x2 = max(0, x), min(frame.shape[1], x + w)
                crop = frame[y1:y2, x1:x2]

                if crop.size > 0:
                    with self._recognizing_lock:
                        if not self._is_recognizing:
                            self._is_recognizing = True
                            threading.Thread(
                                target=self._async_recognize,
                                args=(crop.copy(), face),
                                daemon=True
                            ).start()
                            
                        # Use last known information for smooth UI tracking
                        name, conf = self._last_face_info

                    color = (0, 220, 80) if name != "UNKNOWN" else (30, 30, 220)
                    label = f"{name} ({conf:.0%})" if name != "UNKNOWN" else "UNKNOWN"

                    cv2.rectangle(annotated, (x, y), (x + w, y + h), color, 2)
                    cv2.putText(
                        annotated, label, (x, y - 8),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 2,
                    )

            if self._on_frame:
                self._on_frame(annotated)
