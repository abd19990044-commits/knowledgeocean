# -*- coding: utf-8 -*-
"""
Build script for Knowledge Ocean Desktop
Packages the application into a standalone Windows executable directory using PyInstaller.
"""
from __future__ import annotations

import os
import sys
import subprocess
import shutil
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

def run():
    print("===============================================================")
    print("      Knowledge Ocean Desktop - PyInstaller Compilation       ")
    print("===============================================================")

    pyinstaller_exe = r"C:\Users\ahmed\AppData\Roaming\Python\Python314\Scripts\pyinstaller.exe"
    if not os.path.exists(pyinstaller_exe):
        pyinstaller_exe = "pyinstaller"

    cmd = [
        pyinstaller_exe,
        "--noconfirm",
        "--onedir",
        "--windowed",
        "--name=KnowledgeOcean",
        f"--icon={BASE_DIR / 'static' / 'app_icon.ico'}",
        f"--add-data={BASE_DIR / 'templates'}{os.pathsep}templates",
        f"--add-data={BASE_DIR / 'static'}{os.pathsep}static",
        f"--add-data={BASE_DIR / 'fonts'}{os.pathsep}fonts",
        f"--add-data={BASE_DIR / 'config.txt'}{os.pathsep}.",
        f"--add-data={BASE_DIR / 'hero.jpg'}{os.pathsep}.",
        f"--add-data={BASE_DIR / 'media_security.py'}{os.pathsep}.",
        "--hidden-import=media_security",
        "--hidden-import=cryptography",
        "--hidden-import=cryptography.hazmat.primitives.ciphers.aead",
        "--hidden-import=uvicorn.logging",
        "--hidden-import=uvicorn.loops",
        "--hidden-import=uvicorn.loops.auto",
        "--hidden-import=uvicorn.protocols",
        "--hidden-import=uvicorn.protocols.http",
        "--hidden-import=uvicorn.protocols.http.auto",
        "--hidden-import=webview.platforms.winforms",
        "--hidden-import=webview.platforms.edgechromium",
        "--hidden-import=fitz",
        "--hidden-import=arabic_reshaper",
        "--hidden-import=bidi",
        "--hidden-import=bidi.algorithm",
        "--hidden-import=fpdf",
        "--hidden-import=multipart",
        "--hidden-import=selenium",
        "--hidden-import=selenium.webdriver",
        "--hidden-import=selenium.webdriver.chrome.webdriver",
        "--hidden-import=selenium.webdriver.chrome.service",
        "--hidden-import=selenium.webdriver.chrome.options",
        "--hidden-import=selenium.webdriver.common.by",
        "--hidden-import=selenium.webdriver.common.keys",
        "--hidden-import=selenium.webdriver.support.ui",
        "--hidden-import=selenium.webdriver.support.expected_conditions",
        "--collect-all=webview",
        "--collect-all=fitz",
        "--collect-all=fpdf",
        "--collect-all=arabic_reshaper",
        "--collect-all=bidi",
        "--collect-all=selenium",
        str(BASE_DIR / "desktop_app.py")
    ]

    print("Running PyInstaller...")
    ret = subprocess.run(cmd, cwd=str(BASE_DIR))
    if ret.returncode != 0:
        print(f"[X] PyInstaller failed with code {ret.returncode}")
        sys.exit(ret.returncode)

    dist_dir = BASE_DIR / "dist" / "KnowledgeOcean"
    print("[+] Application built successfully in dist/KnowledgeOcean")

    # Ensure config.txt, hero.jpg, templates, static, fonts are in dist root as well
    shutil.copy2(BASE_DIR / "config.txt", dist_dir / "config.txt")
    shutil.copy2(BASE_DIR / "hero.jpg", dist_dir / "hero.jpg")
    shutil.copy2(BASE_DIR / "media_security.py", dist_dir / "media_security.py")
    for fldr in ["templates", "static", "fonts"]:
        shutil.copytree(BASE_DIR / fldr, dist_dir / fldr, dirs_exist_ok=True)
    print("[+] Prepared root assets (templates, static, fonts, config) in distribution directory.")

    # Apply self-signed Authenticode signature
    try:
        from sign_tool import sign_file
        print("[*] Signing KnowledgeOcean.exe with Authenticode Digital Certificate...")
        sign_file(dist_dir / "KnowledgeOcean.exe")
    except Exception as e:
        print(f"[!] Warning: Code signing step encountered an issue: {e}")

if __name__ == "__main__":
    run()
