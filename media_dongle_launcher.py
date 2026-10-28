# -*- coding: utf-8 -*-
"""
Knowledge Ocean - Media Dongle Protected Installer Launcher
Guarantees execution exclusively from the authorized physical medium (CD / DVD / USB Flash).

If copied to any internal hard drive, SSD, another USB, or another optical disc,
decryption is mathematically impossible and execution is immediately blocked.

Developed for ABDULSALAM S. HASAN
"""

from __future__ import annotations

import os
import sys
import ctypes
import shutil
import subprocess
import tempfile
import json
from pathlib import Path

# Import internal security logic
try:
    import media_security
except ImportError:
    # Development / bundle directory fallback
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import media_security


def show_error_dialog(title: str, message: str) -> None:
    """Shows a native Win32 modal message box with high priority."""
    try:
        # 0x10 = MB_ICONERROR | 0x00040000 = MB_TOPMOST
        ctypes.windll.user32.MessageBoxW(0, message, title, 0x10 | 0x00040000)
    except Exception:
        pass


def main():
    # 1. Resolve executable location
    current_exe = sys.executable if getattr(sys, "frozen", False) else os.path.abspath(__file__)
    exe_dir = os.path.dirname(os.path.abspath(current_exe))
    current_drive = os.path.splitdrive(exe_dir)[0].upper()
    if not current_drive:
        show_error_dialog(
            "حظر أمني - محيط المعرفة",
            "تعذر تحديد مسار وحدة التخزين (Unable to resolve current drive path)."
        )
        sys.exit(1)

    # 2. Check for media license file
    license_file = os.path.join(exe_dir, "media_dongle.lic")
    bundle_dir = getattr(sys, "_MEIPASS", exe_dir)
    if not os.path.exists(license_file):
        license_file = os.path.join(bundle_dir, "media_dongle.lic")

    if not os.path.exists(license_file):
        show_error_dialog(
            "حظر أمني - محيط المعرفة",
            "⚠️ تعذر العثور على ملف ترخيص الوسيط العتادي (media_dongle.lic).\n\n"
            "يرجى التأكد من تشغيل أداة حقن وترخيص القرص (bind_media.py) أولاً."
        )
        sys.exit(1)

    try:
        with open(license_file, "r", encoding="utf-8") as f:
            license_data = json.load(f)
    except Exception as e:
        show_error_dialog(
            "حظر أمني - محيط المعرفة",
            f"⚠️ ملف ترخيص الوسيط تالف أو غير صالح:\n{e}"
        )
        sys.exit(1)

    # 3. Hardware media validation
    is_valid, reason = media_security.verify_media_against_license(current_drive, license_data)
    if not is_valid:
        error_title = "حظر أمني - وسيط تخزين غير مصرح به (Hardware Lock Violation)"
        error_msg = (
            "⛔ تعذر تشغيل برنامج التثبيت!\n\n"
            "هذا الملف التنصيبي محمي ومقيد عتادياً بالقرص الأصلي المعتمد (CD / DVD / FLASH).\n\n"
            f"{reason}\n\n"
            "• لا يمكن تشغيل هذا الملف بعد نسخه للكمبيوتر أو نقله إلى أي وسيط آخر.\n"
            "• يرجى تشغيل الملف مباشرة وحصراً من القرص أو الفلاشة الأصلية المعتمدة."
        )
        show_error_dialog(error_title, error_msg)
        sys.exit(1)

    # 4. Locate encrypted payload
    payload_file = os.path.join(exe_dir, "KnowledgeOcean_Payload.bin")
    if not os.path.exists(payload_file):
        payload_file = os.path.join(bundle_dir, "KnowledgeOcean_Payload.bin")

    if not os.path.exists(payload_file):
        show_error_dialog(
            "حظر أمني - محيط المعرفة",
            "⚠️ تعذر العثور على حزمة التثبيت المشفرة (KnowledgeOcean_Payload.bin)."
        )
        sys.exit(1)

    # 5. Derive decryption key from current verified hardware
    cur_info = media_security.get_drive_info(current_drive)
    key = media_security.derive_media_key(
        cur_info["volume_serial_dec"],
        cur_info["total_bytes"],
        cur_info["volume_name"],
        cur_info["drive_type"]
    )

    # 6. Read and decrypt installation payload
    try:
        with open(payload_file, "rb") as f:
            encrypted_payload = f.read()
        decrypted_setup = media_security.decrypt_payload_aes(
            encrypted_payload, key, b"KO_SETUP_PAYLOAD_V2"
        )
    except Exception as e:
        show_error_dialog(
            "حظر أمني - فشل فك التشفير",
            "⛔ فشل فك تشفير حزمة التثبيت!\n\n"
            "المفتاح العتادي المشتق من وسيط التخزين الحالي غير مطابق لمفتاح فك التشفير.\n"
            f"التفاصيل: {e}\n\n"
            "تم حظر التثبيت لمنع تشغيل الملف بعد نسخه."
        )
        sys.exit(1)

    # 7. Extract decrypted installer into secure volatile temp directory
    temp_dir = tempfile.mkdtemp(prefix="ko_secure_setup_")
    temp_setup_exe = os.path.join(temp_dir, "KnowledgeOcean_Setup.exe")
    temp_sig_file = os.path.join(temp_dir, "media_dongle.sig")

    try:
        with open(temp_setup_exe, "wb") as f:
            f.write(decrypted_setup)

        # Write hardware signature file so Inno Setup / Desktop App can verify dongle after installation
        sig_data = {
            "version": "2.0",
            "drive_type": cur_info["drive_type"],
            "drive_type_name": cur_info["drive_type_name"],
            "volume_name": cur_info["volume_name"],
            "volume_serial_hex": cur_info["volume_serial_hex"],
            "volume_serial_dec": cur_info["volume_serial_dec"],
            "total_bytes": cur_info["total_bytes"],
            "probe_encrypted_hex": license_data.get("probe_encrypted_hex", "")
        }
        with open(temp_sig_file, "w", encoding="utf-8") as f:
            json.dump(sig_data, f, indent=2)

        # Also register media signature in Windows Registry (HKCU\Software\KnowledgeOcean)
        try:
            import winreg
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"Software\KnowledgeOcean") as rk:
                winreg.SetValueEx(rk, "MediaDongleSig", 0, winreg.REG_SZ, json.dumps(sig_data))
                winreg.SetValueEx(rk, "MediaSerial", 0, winreg.REG_SZ, cur_info["volume_serial_hex"])
                winreg.SetValueEx(rk, "MediaSize", 0, winreg.REG_QWORD, cur_info["total_bytes"])
                winreg.SetValueEx(rk, "MediaLabel", 0, winreg.REG_SZ, cur_info["volume_name"])
        except Exception:
            pass

        # 8. Launch the official Inno Setup installer
        cmd = [temp_setup_exe] + sys.argv[1:]
        proc = subprocess.Popen(cmd)
        proc.wait()

        # After installer finishes, if installed directory exists, copy media_dongle.sig there
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\KnowledgeOcean") as rk:
                install_dir, _ = winreg.QueryValueEx(rk, "InstallPath")
                if install_dir and os.path.isdir(install_dir):
                    dest_sig = os.path.join(install_dir, "media_dongle.sig")
                    shutil.copy2(temp_sig_file, dest_sig)
        except Exception:
            pass

        sys.exit(proc.returncode)

    finally:
        # Secure cleanup: shred volatile payload from temp directory
        try:
            if os.path.exists(temp_setup_exe):
                os.remove(temp_setup_exe)
            if os.path.exists(temp_sig_file):
                os.remove(temp_sig_file)
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)
        except Exception:
            pass


if __name__ == "__main__":
    main()
