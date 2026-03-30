"""
SENTINEL - Automated Setup Script
Run once: python setup.py
Installs dependencies, validates environment, creates dirs.
"""

import subprocess
import sys
import os
import shutil
from pathlib import Path

BOLD = "\033[1m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
CYAN = "\033[96m"
RESET = "\033[0m"


def banner():
    print(f"""
{CYAN}{BOLD}
  ███████╗███████╗███╗   ██╗████████╗██╗███╗   ██╗███████╗██╗
  ██╔════╝██╔════╝████╗  ██║╚══██╔══╝██║████╗  ██║██╔════╝██║
  ███████╗█████╗  ██╔██╗ ██║   ██║   ██║██╔██╗ ██║█████╗  ██║
  ╚════██║██╔══╝  ██║╚██╗██║   ██║   ██║██║╚██╗██║██╔══╝  ██║
  ███████║███████╗██║ ╚████║   ██║   ██║██║ ╚████║███████╗███████╗
  ╚══════╝╚══════╝╚═╝  ╚═══╝   ╚═╝   ╚═╝╚═╝  ╚═══╝╚══════╝╚══════╝
  Security System v1.0  —  Setup Script
{RESET}""")


def check(label: str, ok: bool, hint: str = "") -> bool:
    mark = f"{GREEN}✓{RESET}" if ok else f"{RED}✗{RESET}"
    print(f"  {mark}  {label}")
    if not ok and hint:
        print(f"      {YELLOW}→ {hint}{RESET}")
    return ok


def step(title: str):
    print(f"\n{BOLD}{CYAN}── {title}{RESET}")


def main():
    banner()

    # ── Python version check ──────────────────────────────────
    step("Checking Python version")
    v = sys.version_info
    ok = check(
        f"Python {v.major}.{v.minor}.{v.micro}",
        v >= (3, 10),
        "Sentinel requires Python 3.10 or higher.",
    )
    if not ok:
        sys.exit(1)

    # ── pip upgrade ───────────────────────────────────────────
    step("Upgrading pip")
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "--upgrade", "pip"],
        check=False, capture_output=True,
    )
    print(f"  {GREEN}✓{RESET}  pip upgraded")

    # ── Install requirements ───────────────────────────────────
    step("Installing dependencies")
    req_path = Path(__file__).parent / "requirements.txt"
    if not req_path.exists():
        print(f"  {RED}✗  requirements.txt not found{RESET}")
        sys.exit(1)

    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", "-r", str(req_path)],
        capture_output=False,
    )
    if result.returncode != 0:
        print(f"\n  {RED}✗  Some packages failed to install.{RESET}")
        print(f"  {YELLOW}Try running manually: pip install -r requirements.txt{RESET}")
    else:
        print(f"\n  {GREEN}✓  All packages installed successfully{RESET}")

    # ── Validate key imports ───────────────────────────────────
    step("Validating key imports")

    imports = [
        ("customtkinter", "CustomTkinter GUI"),
        ("cv2", "OpenCV"),
        ("deepface", "DeepFace (face recognition)"),
        ("psutil", "psutil (system monitoring)"),
        ("pynput", "pynput (activity monitoring)"),
        ("plyer", "plyer (desktop notifications)"),
        ("pyttsx3", "pyttsx3 (text-to-speech)"),
        ("pygame", "pygame (sound alarm)"),
        ("mss", "mss (screen capture)"),
        ("PIL", "Pillow (image processing)"),
        ("colorlog", "colorlog (logging)"),
        ("dotenv", "python-dotenv"),
    ]

    failures = []
    for mod, label in imports:
        try:
            __import__(mod)
            check(label, True)
        except ImportError as e:
            check(label, False, str(e))
            failures.append(label)

    # ── Create directories ─────────────────────────────────────
    step("Creating project directories")
    dirs = [
        "logs",
        "logs/screenshots",
        "models/known_faces",
        "assets",
    ]
    for d in dirs:
        Path(d).mkdir(parents=True, exist_ok=True)
        print(f"  {GREEN}✓{RESET}  {d}/")

    # ── .env setup ────────────────────────────────────────────
    step("Configuration")
    env_example = Path(".env.example")
    env_file = Path(".env")
    if not env_file.exists() and env_example.exists():
        shutil.copy(env_example, env_file)
        print(f"  {GREEN}✓{RESET}  .env created from .env.example")
        print(f"  {YELLOW}→  Edit .env to set email/Telegram credentials{RESET}")
    elif env_file.exists():
        print(f"  {GREEN}✓{RESET}  .env already exists")
    else:
        print(f"  {YELLOW}!  No .env.example found — skipping{RESET}")

    # ── Summary ───────────────────────────────────────────────
    print(f"\n{'═'*55}")
    if failures:
        print(f"{YELLOW}  Setup completed with warnings:{RESET}")
        for f in failures:
            print(f"    {YELLOW}• {f} — install manually if needed{RESET}")
    else:
        print(f"{GREEN}{BOLD}  ✓  Setup complete! All systems go.{RESET}")

    print(f"""
{BOLD}  Next steps:{RESET}
  1. Edit {CYAN}.env{RESET} with your alert credentials (optional)
  2. Run:  {CYAN}{BOLD}python main.py{RESET}
  3. Click "📷 Start Camera" in the GUI
  4. Go to "👤 Enrollment" to register your face
{'═'*55}
""")


if __name__ == "__main__":
    main()
