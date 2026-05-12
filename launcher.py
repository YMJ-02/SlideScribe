"""launcher.py — entry point for the bundled SlideScribe.exe.

Run from source:
    python launcher.py

When frozen by PyInstaller, this becomes SlideScribe.exe and the bundled
files live next to it (one-dir layout) or inside sys._MEIPASS (one-file).
The launcher:
  1. Picks a per-user writable directory for config / outputs / tmp.
  2. Copies the bundled default config.yaml there on first run.
  3. Prepends the bundle's `bin/` (ffmpeg.exe etc.) to PATH.
  4. Starts the FastAPI app on localhost:7860.
  5. Auto-opens the user's default browser.
  6. Closes everything when the console window is closed.
"""

from __future__ import annotations

import os
import shutil
import sys
import threading
import time
import webbrowser
from pathlib import Path


HOST = "127.0.0.1"
PORT = 7860


def _bundle_dir() -> Path:
    """Directory containing the running exe / launcher.py."""
    if getattr(sys, "frozen", False):
        # PyInstaller one-dir: sys.executable is the exe.
        # PyInstaller one-file: sys._MEIPASS is the temp extract dir.
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            return Path(meipass)
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent


def _user_data_dir() -> Path:
    """Per-user writable directory for config / outputs / tmp."""
    if sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA") or str(Path.home())
    elif sys.platform == "darwin":
        base = str(Path.home() / "Library" / "Application Support")
    else:
        base = os.environ.get("XDG_DATA_HOME") or str(Path.home() / ".local" / "share")
    return Path(base) / "SlideScribe"


def _setup_runtime() -> tuple[Path, Path]:
    bundle = _bundle_dir()
    user_dir = _user_data_dir()
    user_dir.mkdir(parents=True, exist_ok=True)

    # First-run: copy default config.yaml from bundle so user can edit it.
    user_cfg = user_dir / "config.yaml"
    if not user_cfg.exists():
        bundled_cfg = bundle / "config.yaml"
        if bundled_cfg.is_file():
            try:
                shutil.copy2(bundled_cfg, user_cfg)
            except OSError:
                pass

    # Make bundled ffmpeg (if shipped at bundle/bin/ffmpeg.exe) discoverable.
    bundled_bin = bundle / "bin"
    if bundled_bin.is_dir():
        os.environ["PATH"] = str(bundled_bin) + os.pathsep + os.environ.get("PATH", "")

    # Run the app from user_dir so config's relative paths (.tmp, output)
    # resolve under user_dir instead of Program Files.
    os.chdir(user_dir)
    return bundle, user_dir


def _open_browser_when_ready(url: str, delay: float = 1.8) -> None:
    time.sleep(delay)
    try:
        webbrowser.open(url)
    except Exception:
        pass


def main() -> None:
    bundle, user_dir = _setup_runtime()
    url = f"http://localhost:{PORT}"

    print("=" * 60)
    print("  SlideScribe")
    print("=" * 60)
    print(f"  Open in browser : {url}")
    print(f"  Data folder     : {user_dir}")
    print(f"  Config file     : {user_dir / 'config.yaml'}")
    print()
    print("  Close this window or press Ctrl+C to stop the app.")
    print("=" * 60)
    print()

    threading.Thread(
        target=_open_browser_when_ready, args=(url,), daemon=True,
    ).start()

    # Import AFTER cwd / PATH are set up so the FastAPI app sees the right env.
    import uvicorn  # noqa: WPS433
    from app import app as fastapi_app  # noqa: WPS433

    try:
        uvicorn.run(
            fastapi_app,
            host=HOST,
            port=PORT,
            log_level="info",
            access_log=False,
        )
    except KeyboardInterrupt:
        print("\nShutting down…")


if __name__ == "__main__":
    main()
