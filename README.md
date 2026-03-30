# 🛡️ SENTINEL Security System

> Advanced real-time security monitoring with face recognition, intrusion detection, and multi-channel alerts. Python 3.14+ compatible with zero compilation required.

[![Python 3.14+](https://img.shields.io/badge/python-3.14+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey.svg)](https://github.com/abhilash15498/Sentinel_security.git)

---

## 📋 Overview

SENTINEL is a comprehensive Python-based security system that monitors your computer through multiple detection layers. Built without dlib dependency for easy installation across all platforms and Python versions.

### ✨ Key Features

- 🎥 **Face Recognition** - Real-time detection using OpenCV + DeepFace (Facenet512)
- 🔍 **Intrusion Detection** - Keyboard, mouse, and process monitoring
- 💾 **USB Monitoring** - Instant alerts on device insertion/removal
- 🖥️ **Screen Watching** - Detects significant screen content changes
- 🌐 **Network Surveillance** - Monitors suspicious connections
- 📧 **Multi-Channel Alerts** - Email, Telegram, desktop notifications, audio alarms
- 🎨 **Modern GUI** - CustomTkinter dashboard with live camera feed
- 🔐 **Privacy-First** - All data stored locally, no cloud uploads

---

## 🚀 Quick Start

### Prerequisites

- Python 3.10+ (3.14+ recommended)
- Webcam (built-in or USB)
- Windows, Linux, or macOS

### Installation

```bash
# Clone the repository
git clone https://github.com/abhilash15498/Sentinel_security.git
cd sentinel

# Create virtual environment
python -m venv .venv

# Activate virtual environment
# Windows:
.venv\Scripts\activate
# Linux/Mac:
source .venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

### Configuration

```bash
# Copy example configuration
cp .env.example .env

# Edit .env with your credentials (optional)
# - Email (Gmail App Password)
# - Telegram Bot Token & Chat ID
# - Feature toggles
```

### Run

```bash
python main.py
```
## 🎯 How It Works

### Face Recognition Pipeline

```
Camera → OpenCV Haar Cascade → Face Detection
                                      ↓
                           DeepFace Facenet512 → 512-D Embedding
                                      ↓
                              Compare with Database
                                      ↓
                           KNOWN ✓ or UNKNOWN ⚠️
                                      ↓
                              Fire Alert (if unknown)
```

### Detection Layers

1. **Visual Layer** - Camera-based face recognition
2. **Physical Layer** - USB device monitoring
3. **System Layer** - Process and activity tracking
4. **Screen Layer** - Content change detection
5. **Network Layer** - Connection monitoring

---

## 🛠️ Tech Stack

### Core Computer Vision
- **OpenCV** - Face detection (Haar Cascade)
- **DeepFace** - Face recognition (Facenet512)
- **Pillow** - Image processing

### System Monitoring
- **psutil** - Process & network monitoring
- **pynput** - Keyboard/mouse activity
- **pyudev** (Linux) - USB event monitoring
- **mss** - Screen capture

### Alerts & Notifications
- **plyer** - Desktop notifications
- **pyttsx3** - Text-to-speech
- **pygame** - Audio alarm synthesis
- **smtplib** - Email alerts
- **python-telegram-bot** - Telegram messages

### User Interface
- **CustomTkinter** - Modern dark-themed GUI
- **tkinter** - Base GUI framework

### Utilities
- **colorlog** - Colored console logging
- **python-dotenv** - Configuration management
- **numpy** - Numerical operations

---

## 📁 Project Structure

```
sentinel/
├── main.py                      # Application entry point
├── requirements.txt             # Dependencies
├── .env.example                 # Configuration template
│
├── core/                        # Detection engines
│   ├── face_recognition.py      # Camera + face detection/recognition
│   ├── intrusion_detection.py   # Activity & process monitoring
│   ├── usb_watcher.py          # USB device monitoring
│   ├── screen_watcher.py       # Screen change detection
│   └── network_monitor.py      # Network activity monitoring
│
├── services/                    # Alert systems
│   ├── alarm.py                # Audio alarms + TTS
│   ├── notifier.py             # Email, Telegram, desktop popups
│   └── screenshot.py           # Evidence capture
│
├── ui/                         # User interface
│   └── dashboard.py            # GUI dashboard
│
├── utils/                      # Shared utilities
│   ├── config.py               # Configuration manager
│   └── logger.py               # Logging system
│
├── models/                     # Face recognition data
│   └── known_faces/            # Enrolled face images
│       └── <PersonName>/
│           └── *.jpg
│
└── logs/                       # System logs
    ├── sentinel_YYYYMMDD.log   # Daily logs
    ├── events.log              # Security events
    └── screenshots/            # Evidence captures
```

---

## ⚙️ Configuration

### Email Alerts (Gmail)

1. Enable [Gmail App Passwords](https://myaccount.google.com/apppasswords)
2. Configure in `.env`:
   ```env
   EMAIL_SENDER=your@gmail.com
   EMAIL_PASSWORD=your_app_password_here
   EMAIL_RECEIVER=alerts@email.com
   ```

### Telegram Bot

1. Create bot with [@BotFather](https://t.me/BotFather) → `/newbot`
2. Get your Chat ID from [@userinfobot](https://t.me/userinfobot)
3. Configure in `.env`:
   ```env
   TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
   TELEGRAM_CHAT_ID=987654321
   ```

### Feature Toggles

```env
FACE_RECOGNITION_MODE=deepface    # or opencv_only
SCREENSHOT_ON_INTRUSION=true
TTS_ENABLED=true
SOUND_ALARM_ENABLED=true
USB_MONITOR_ENABLED=true
ALERT_COOLDOWN_SECONDS=30
```

---

## 🎓 Usage Guide

### First-Time Setup

1. **Start the application**
   ```bash
   python main.py
   ```

2. **Start camera monitoring**
   - Click "📷 Start Camera" in sidebar

3. **Enroll yourself**
   - Go to "👤 Enrollment" tab
   - Enter your name
   - Click "📷 Capture from Camera" (burst captures 15 frames)
   - OR click "🖼 Load from File" to upload a photo

4. **System arms automatically**
   - Unknown faces trigger alerts
   - All detection layers active

### Daily Operation

- **Armed Mode** - Full monitoring + alerts
- **Disarmed Mode** - Monitoring continues, no alerts fired
- Toggle via "🔓 ARM/DISARM SYSTEM" button

---

## 🐛 Troubleshooting

### Camera not opening
```bash
# Test camera separately
python -c "import cv2; cap=cv2.VideoCapture(0); print(cap.isOpened()); cap.release()"
```

### DeepFace slow on first run
First run downloads model weights (~250 MB). Cached afterwards - subsequent runs are fast.

### TTS not working (Linux)
```bash
sudo apt-get install espeak
pip install pyttsx3
```

### USB monitoring on macOS
Uses disk partition polling via psutil. Fires when USB drives mount/unmount.

---

## 🔒 Privacy & Security

- ✅ All face data stored **locally** in `models/known_faces/`
- ✅ No cloud uploads or external API calls (except optional email/Telegram)
- ✅ DeepFace models download once from official sources
- ✅ Logs rotate every 5 MB, keep 7 days
- ✅ Screenshots stored locally with timestamps
- ✅ Full control over all data

---

## 🏗️ Architecture Highlights

### Why No dlib?

**Problem:** dlib requires C++ compiler, CMake, 15-30 min compilation, breaks on Python 3.14+

**Solution:**
- **Detection:** OpenCV Haar Cascades (built into opencv-python)
- **Recognition:** DeepFace with Facenet512 (pure Python + ONNX)
- **Fallback:** Histogram matching (pure OpenCV)

**Result:** Zero compilation, pip-only install, Python 3.14+ compatible

### Async Recognition

**Problem:** DeepFace takes 100-500ms per face. Running in camera loop drops FPS to 2-10.

**Solution:**
- Main camera loop runs at 30 FPS
- Recognition runs in background thread
- UI displays cached result (smooth, no stuttering)
- Background updates cache when complete

**Result:** Smooth 30 FPS display + accurate recognition

---

## 📊 System Requirements

### Minimum
- Python 3.10+
- 4 GB RAM
- Webcam (any resolution)
- 500 MB disk space

### Recommended
- Python 3.14+
- 8 GB RAM
- 720p+ webcam
- 1 GB disk space
- SSD for faster model loading

---

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

```
MIT License

Copyright (c) 2024 Abhi

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

---

## 🙏 Acknowledgments

- OpenCV team for computer vision tools
- DeepFace developers for face recognition framework
- CustomTkinter for modern UI components
- All open-source contributors

---

## 📧 Contact

**Developer:** Abhi

**Project Link:** [https://github.com/abhilash15498/Sentinel_security.git](https://github.com/abhilash15498/Sentinel_security.git)
**Email:** [hmabhilash15@gmail.com]
---

## ⭐ Star History

If you find this project useful, please consider giving it a star! ⭐

---

**Built with ❤️ for security and privacy**
