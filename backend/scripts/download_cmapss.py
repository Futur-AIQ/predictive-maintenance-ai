#!/usr/bin/env python
"""
Download the NASA CMAPSS Turbofan Engine Degradation Dataset from Kaggle.

Usage:
    python scripts/download_cmapss.py

Prerequisites:
    1. Create a Kaggle account at https://www.kaggle.com
    2. Go to Account -> API -> Create New API Token
    3. Place kaggle.json at ~/.kaggle/kaggle.json (Linux/Mac)
       or C:\\Users\\<username>\\.kaggle\\kaggle.json (Windows)
    4. Run: pip install kaggle
"""

import os
import sys
import subprocess
import zipfile
import shutil


KAGGLE_DATASET = "behrad3d/nasa-cmaps"
OUTPUT_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data", "raw", "nasa_cmapss"
)


def check_and_install_kaggle() -> bool:
    """Check if kaggle package is installed; install it if not."""
    try:
        import kaggle  # noqa: F401
        print("[OK] kaggle package is already installed.")
        return True
    except ImportError:
        print("[INFO] kaggle package not found. Installing...")
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "kaggle"],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            print("[OK] kaggle installed successfully.")
            return True
        else:
            print(f"[ERROR] Failed to install kaggle:\n{result.stderr}")
            return False


def check_credentials() -> bool:
    """Check that kaggle.json credentials exist at the expected path."""
    home = os.path.expanduser("~")
    kaggle_json = os.path.join(home, ".kaggle", "kaggle.json")

    if os.path.exists(kaggle_json):
        print(f"[OK] Kaggle credentials found at: {kaggle_json}")
        return True

    print("\n" + "=" * 60)
    print("ERROR: Kaggle credentials not found!")
    print("=" * 60)
    print("\nTo download the NASA CMAPSS dataset you need a Kaggle API key.")
    print("\nSteps to set up credentials:")
    print("  1. Go to https://www.kaggle.com and sign in (or create an account).")
    print("  2. Click your profile picture -> 'Settings'.")
    print("  3. Scroll to the 'API' section and click 'Create New API Token'.")
    print("  4. A file named 'kaggle.json' will be downloaded.")
    print("  5. Place it at one of these locations:")
    print(f"       Linux/Mac : ~/.kaggle/kaggle.json")
    print(f"       Windows   : C:\\Users\\<YourUsername>\\.kaggle\\kaggle.json")
    print(f"       Expected  : {kaggle_json}")
    print("\nAlternatively, set environment variables:")
    print("       KAGGLE_USERNAME=<your_username>")
    print("       KAGGLE_KEY=<your_api_key>")
    print("\nAfter placing the file, re-run this script.")
    print("=" * 60 + "\n")
    return False


def download_dataset() -> bool:
    """Download the dataset from Kaggle into a temp directory."""
    import kaggle  # noqa: F401 — imported after install check

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    tmp_dir = os.path.join(OUTPUT_DIR, "_tmp_download")
    os.makedirs(tmp_dir, exist_ok=True)

    print(f"\n[INFO] Downloading dataset '{KAGGLE_DATASET}' from Kaggle...")
    print(f"[INFO] Destination: {OUTPUT_DIR}\n")

    try:
        # kaggle datasets download -d <dataset> -p <path> --unzip
        result = subprocess.run(
            [
                sys.executable, "-m", "kaggle",
                "datasets", "download",
                "-d", KAGGLE_DATASET,
                "-p", tmp_dir,
                "--unzip",
            ],
            capture_output=False,  # show live output
        )
        if result.returncode != 0:
            print(f"[ERROR] Kaggle download command failed (exit code {result.returncode}).")
            return False
    except Exception as exc:
        print(f"[ERROR] Exception during download: {exc}")
        return False

    # Move extracted files into OUTPUT_DIR
    for fname in os.listdir(tmp_dir):
        src = os.path.join(tmp_dir, fname)
        dst = os.path.join(OUTPUT_DIR, fname)
        if os.path.exists(dst):
            if os.path.isdir(dst):
                shutil.rmtree(dst)
            else:
                os.remove(dst)
        shutil.move(src, dst)

    shutil.rmtree(tmp_dir, ignore_errors=True)
    print(f"\n[OK] Dataset extracted to: {OUTPUT_DIR}")
    return True


def verify_files() -> None:
    """Print a summary of files in the output directory."""
    print("\n[INFO] Files in output directory:")
    if not os.path.isdir(OUTPUT_DIR):
        print("  (directory does not exist)")
        return
    files = sorted(os.listdir(OUTPUT_DIR))
    if not files:
        print("  (no files found)")
        return
    for fname in files:
        fpath = os.path.join(OUTPUT_DIR, fname)
        size = os.path.getsize(fpath)
        print(f"  {fname:40s}  {size:>10,} bytes")


def main() -> None:
    print("NASA CMAPSS Dataset Downloader")
    print("=" * 60)

    # Step 1: ensure kaggle is installed
    if not check_and_install_kaggle():
        sys.exit(1)

    # Step 2: check credentials
    if not check_credentials():
        sys.exit(1)

    # Step 3: download
    if not download_dataset():
        sys.exit(1)

    # Step 4: report
    verify_files()
    print("\n[DONE] NASA CMAPSS data is ready.")


if __name__ == "__main__":
    main()
