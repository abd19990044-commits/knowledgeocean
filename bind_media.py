# -*- coding: utf-8 -*-
"""
Knowledge Ocean - Media Dongle Injection & Lock Script (أداة قفل وحقن الوسيط العتادي)
Binds the installer and application exclusively to a CD, DVD, or USB Flash Drive.

When copied to a CD, DVD, or Flash Drive, this script:
 1. Detects the physical drive's volume serial number (السيريال).
 2. Detects the total storage capacity in bytes (حجم القرص).
 3. Detects the volume label / name (اسم القرص).
 4. Derives an AES-256-GCM hardware key from these values.
 5. Encrypts the installer payload into 'KnowledgeOcean_Payload.bin'.
 6. Generates 'media_dongle.lic' and prepares 'KnowledgeOcean_Setup_Locked.exe'.

If the installer is moved/copied to any computer hard drive or another USB/CD,
it will NOT work and cannot be decrypted!

Developed for ABDULSALAM S. HASAN
"""

from __future__ import annotations

import os
import sys
import shutil
import json
import argparse
from pathlib import Path

# Import core security logic
try:
    import media_security
except ImportError:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import media_security


def print_banner():
    print("=" * 72)
    print("  🌊 محيط المعرفة — أداة قفل وحقن مفاتيح التشفير العتادية (Media Locker)")
    print("  تأمين وتقييد الحزمة التنصيبية بأقراص CD / DVD ووحدات الـ USB Flash")
    print("  Developed for ABDULSALAM S. HASAN")
    print("=" * 72)


def select_target_drive(requested_arg: str | None = None) -> dict:
    """Detects or interactively prompts for the target CD/DVD or USB Flash drive."""
    script_drive = os.path.splitdrive(os.path.abspath(__file__))[0].upper()
    if not script_drive.endswith(":"):
        script_drive += ":"

    # Case 1: Drive specified via argument
    if requested_arg:
        drv_clean = requested_arg.strip().rstrip("\\/").rstrip(":").upper() + ":"
        try:
            return media_security.get_drive_info(drv_clean)
        except Exception as e:
            print(f"[!] خطأ في فحص القرص المحدد ({drv_clean}): {e}")
            sys.exit(1)

    # Case 2: Running directly from a removable or optical media drive
    try:
        current_info = media_security.get_drive_info(script_drive)
        if current_info["drive_type"] in (media_security.DRIVE_REMOVABLE, media_security.DRIVE_CDROM):
            print(f"[*] تم اكتشاف تشغيل الأداة مباشرة من الوسيط المحمول ({script_drive})...")
            return current_info
    except Exception:
        pass

    # Case 3: Running from fixed hard drive -> list candidate drives
    all_drives = media_security.get_all_connected_drives()
    candidates = [d for d in all_drives if d["drive_type"] in (media_security.DRIVE_REMOVABLE, media_security.DRIVE_CDROM)]

    print("\n🔍 الأقراص ووحدات التخزين المحمولة المتصلة بالجهاز حالياً:")
    if candidates:
        for idx, c in enumerate(candidates, start=1):
            gb = c["total_bytes"] / (1024**3)
            print(f"  [{idx}] محرك الأقراص {c['drive_letter']} — {c['drive_type_name']} | الاسم: '{c['volume_name']}' | السيريال: 0x{c['volume_serial_hex']} | السعة: {gb:.2f} GB")
    else:
        print("  [!] لم يتم العثور على فلاشة USB أو قرص CD/DVD متصل حالياً.")
        print("      (يمكنك إدخال فلاشة أو قرص ليزري الآن ثم إعادة المحاولة، أو إدخال الحرف يدوياً)")

    print("-" * 72)
    choice = input("👉 أدخل حرف محرك الأقراص المستهدف للحقن (مثال: E أو F أو H) أو رقم الخيار [1]: ").strip().upper()

    if not choice and candidates:
        return candidates[0]

    if choice.isdigit() and 1 <= int(choice) <= len(candidates):
        return candidates[int(choice) - 1]

    target_letter = choice.rstrip("\\/").rstrip(":") + ":"
    try:
        return media_security.get_drive_info(target_letter)
    except Exception as e:
        print(f"[X] تعذر فحص محرك الأقراص ({target_letter}): {e}")
        sys.exit(1)


def find_setup_payload() -> Path:
    """Finds the official compiled Inno Setup installer."""
    base_dir = Path(__file__).resolve().parent
    candidates = [
        base_dir / "installer_dist" / "KnowledgeOcean_Setup.exe",
        base_dir / "محلي" / "installer_dist" / "KnowledgeOcean_Setup.exe",
        base_dir / "KnowledgeOcean_Setup.exe",
        Path(r"g:\محيط المعرفة\installer_dist\KnowledgeOcean_Setup.exe")
    ]
    for c in candidates:
        if c.exists() and c.stat().st_size > 10 * 1024 * 1024:
            return c

    print("[X] خطأ: تعذر العثور على ملف التثبيت الأصلي (KnowledgeOcean_Setup.exe).")
    print("    يرجى التأكد من وجوده في مجلد installer_dist أو بجانب هذا السكربت.")
    sys.exit(1)


def inject_and_bind(target_info: dict, output_dir: Path | None = None):
    """Performs cryptographic binding and payload encryption for the target drive."""
    drive_root = target_info["drive_root"]
    drive_letter = target_info["drive_letter"]
    serial_dec = target_info["volume_serial_dec"]
    serial_hex = target_info["volume_serial_hex"]
    size_bytes = target_info["total_bytes"]
    vol_name = target_info["volume_name"]
    drive_type = target_info["drive_type"]
    drive_type_name = target_info["drive_type_name"]

    print("\n" + "=" * 72)
    print("📋 تقرير مواصفات الوسيط العتادي المكتشف:")
    print("=" * 72)
    print(f" • مسار القرص:              {drive_letter} ({drive_root})")
    print(f" • نوع الوسيط:              {drive_type_name}")
    print(f" • اسم وحدة التخزين (Label): '{vol_name}'")
    print(f" • الرقم التسلسلي (Serial):  0x{serial_hex} ({serial_dec})")
    print(f" • السعة الإجمالية (Size):    {size_bytes:,} بايت ({size_bytes / (1024**3):.2f} GB)")
    print(f" • نظام الملفات:             {target_info['fs_name']}")
    print("=" * 72)

    # Warning if running on fixed hard drive
    if drive_type == media_security.DRIVE_FIXED:
        print("\n⚠️ تنبيه شديد:")
        print(f"محرك الأقراص {drive_letter} هو قرص صلب داخلي (Hard Drive / SSD) وليس فلاشة أو CD/DVD!")
        confirm = input("هل أنت متأكد من رغبتك بالربط بهذا القرص الداخلي؟ (y/N): ").strip().lower()
        if confirm != "y":
            print("[!] تم إلغاء العملية بناءً على رغبتك.")
            sys.exit(0)

    # 1. Locate setup executable payload
    setup_exe = find_setup_payload()
    print(f"\n[*] جاري قراءة حزمة التثبيت الأصلية ({setup_exe.name} — {setup_exe.stat().st_size / (1024**2):.2f} MB)...")
    with open(setup_exe, "rb") as f:
        payload_data = f.read()

    # 2. Derive media hardware key
    print("[*] جاري اشتقاق مفتاح التشفير العتادي PBKDF2-HMAC-SHA256 (120,000 دورة)...")
    hw_key = media_security.derive_media_key(serial_dec, size_bytes, vol_name, drive_type)

    # 3. Encrypt payload with AES-256-GCM
    print("[*] جاري تشفير الحزمة التنصيبية بنظام AES-256-GCM العتادي الموثق...")
    encrypted_payload = media_security.encrypt_payload_aes(payload_data, hw_key, b"KO_SETUP_PAYLOAD_V2")

    # 4. Create media license
    license_dict = media_security.create_media_license(target_info)

    # Determine destination folder
    dest_dir = output_dir if output_dir else Path(drive_root)
    # If destination drive is read-only (like finalized CD) or not writable, fallback to local locked_dist folder
    try:
        test_file = dest_dir / ".ko_write_test"
        with open(test_file, "w") as f:
            f.write("test")
        test_file.unlink()
        write_to_target = True
    except Exception:
        write_to_target = False
        fallback_dir = Path(__file__).resolve().parent / "locked_media_package"
        fallback_dir.mkdir(parents=True, exist_ok=True)
        print(f"[!] تنبيه: لا يمكن الكتابة المباشرة على {dest_dir} (قد يكون قرص CD/DVD جاهز للحرق).")
        print(f"    سيتم حفظ الملفات المحمية في المجلد: {fallback_dir}")
        dest_dir = fallback_dir

    # 5. Write encrypted payload and license
    payload_dest = dest_dir / "KnowledgeOcean_Payload.bin"
    lic_dest = dest_dir / "media_dongle.lic"
    sig_dest = dest_dir / "media_dongle.sig"

    print(f"[*] جاري حفظ الحزمة المشفرة في: {payload_dest}...")
    with open(payload_dest, "wb") as f:
        f.write(encrypted_payload)

    print(f"[*] جاري حفظ ترخيص البصمة العتادية في: {lic_dest}...")
    with open(lic_dest, "w", encoding="utf-8") as f:
        json.dump(license_dict, f, indent=2)

    with open(sig_dest, "w", encoding="utf-8") as f:
        json.dump(license_dict, f, indent=2)

    # 6. Copy or compile launcher executable
    base_dir = Path(__file__).resolve().parent
    launcher_src = base_dir / "installer_dist" / "KnowledgeOcean_Setup_Locked.exe"
    if not launcher_src.exists():
        launcher_src = base_dir / "KnowledgeOcean_Setup_Locked.exe"
    if not launcher_src.exists():
        launcher_src = base_dir / "KnowledgeOcean_Launcher.exe"

    launcher_dest = dest_dir / "KnowledgeOcean_Setup_Locked.exe"
    if launcher_src.exists():
        shutil.copy2(launcher_src, launcher_dest)
        print(f"[+] تم نسخ الملف التنصيبي المحمي: {launcher_dest.name}")
    else:
        print("[!] ملاحظة: ملف المشغل المترجم KnowledgeOcean_Setup_Locked.exe غير موجود في مجلد التطوير،")
        print("    يرجى ترجمته عبر build_media_launcher.py أو تشغيل حزمة البايثون المرفقة.")

    # 7. Write run_installer.bat for instant launching
    bat_dest = dest_dir / "run_installer.bat"
    with open(bat_dest, "w", encoding="utf-8") as f:
        f.write("@echo off\r\n")
        f.write("title Knowledge Ocean - Media Protected Installer\r\n")
        f.write("if exist \"KnowledgeOcean_Setup_Locked.exe\" (\r\n")
        f.write("    start \"\" \"KnowledgeOcean_Setup_Locked.exe\"\r\n")
        f.write(") else (\r\n")
        f.write("    python media_dongle_launcher.py\r\n")
        f.write(")\r\n")

    print("\n" + "=" * 72)
    print("🎉 تم بنجاح حقن بصمة القرص وتأمين الحزمة التنصيبية عتادياً!")
    print("=" * 72)
    print("الملفات الناتجة والمجهزة في الوسيط:")
    print(f" 1. {launcher_dest.name if launcher_dest.exists() else 'media_dongle_launcher.py'} (الملف التنصيبي المشفر)")
    print(f" 2. {payload_dest.name} (حزمة التثبيت المشفرة بـ AES-256-GCM)")
    print(f" 3. {lic_dest.name} (ملف البصمة والترخيص العتادي)")
    print(f" 4. {bat_dest.name} (ملف التشغيل السريع)")
    print("\n🛡️ الحماية المفروضة:")
    print(" • عند تشغيل الملف التنصيبي، سيقوم بمطابقة السيريال والحجم والاسم تلقائياً وفك التشفير.")
    print(" • إذا قام أي شخص بنسخ الملف التنصيبي إلى جهاز حاسوب أو أي فلاشة أو قرص آخر،")
    print("   فلن يتمكن من فك التشفير نهائياً وستظهر له رسالة الحظر الأمني!")
    print("=" * 72)


def main():
    parser = argparse.ArgumentParser(description="Knowledge Ocean Media Dongle Binder")
    parser.add_argument("drive", nargs="?", help="Target drive letter (e.g. E: or H:)")
    parser.add_argument("--out", "-o", help="Output directory to place locked package")
    args = parser.parse_args()

    print_banner()
    target_info = select_target_drive(args.drive)
    out_dir = Path(args.out) if args.out else None
    inject_and_bind(target_info, out_dir)


if __name__ == "__main__":
    main()
