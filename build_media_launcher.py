# -*- coding: utf-8 -*-
"""
Builds the standalone KnowledgeOcean_Setup_Locked.exe using PyInstaller.
"""
from __future__ import annotations

import os
import sys
import subprocess
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

def build():
    print("==================================================================")
    print("  Building KnowledgeOcean_Setup_Locked.exe (Media Dongle Launcher)  ")
    print("==================================================================")

    pyinstaller_exe = r"C:\Users\ahmed\AppData\Roaming\Python\Python314\Scripts\pyinstaller.exe"
    if not os.path.exists(pyinstaller_exe):
        pyinstaller_exe = "pyinstaller"

    icon_path = BASE_DIR / "static" / "app_icon.ico"

    cmd = [
        pyinstaller_exe,
        "--noconfirm",
        "--onefile",
        "--windowed",
        "--name=KnowledgeOcean_Setup_Locked",
        f"--icon={icon_path}",
        "--hidden-import=media_security",
        "--hidden-import=cryptography",
        "--hidden-import=cryptography.hazmat.primitives.ciphers.aead",
        str(BASE_DIR / "media_dongle_launcher.py")
    ]

    print("Running PyInstaller...")
    ret = subprocess.run(cmd, cwd=str(BASE_DIR))
    if ret.returncode != 0:
        print(f"[X] Compilation failed with code {ret.returncode}")
        sys.exit(ret.returncode)

    built_exe = BASE_DIR / "dist" / "KnowledgeOcean_Setup_Locked.exe"
    target_dist = BASE_DIR / "installer_dist" / "KnowledgeOcean_Setup_Locked.exe"
    if built_exe.exists():
        import shutil
        target_dist.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(built_exe, target_dist)
        print(f"[✔] Successfully compiled and copied to: {target_dist}")
        print(f"    Size: {target_dist.stat().st_size / (1024**2):.2f} MB")
    else:
        print("[X] Error: Built executable not found!")
        sys.exit(1)

if __name__ == "__main__":
    build()
