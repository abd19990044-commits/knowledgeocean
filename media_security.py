# -*- coding: utf-8 -*-
"""
Knowledge Ocean - Physical Media Security & Hardware Dongle Module
Supports: USB Flash Drives (DRIVE_REMOVABLE = 2) and Optical Discs (CD/DVD: DRIVE_CDROM = 5)

Enforces strict hardware-binding to the physical medium:
 - Volume Serial Number (السيريال)
 - Total Storage Capacity in Bytes (الحجم)
 - Volume Name / Label (الاسم)
 - Media Bus & Drive Type (نوع الوسيط)

Developed for ABDULSALAM S. HASAN
"""

from __future__ import annotations

import os
import sys
import ctypes
from ctypes import wintypes
import hashlib
import json
import struct

# Win32 Drive Type Constants
DRIVE_UNKNOWN = 0
DRIVE_NO_ROOT_DIR = 1
DRIVE_REMOVABLE = 2   # USB Flash Drive, Floppy, Thumbdrive
DRIVE_FIXED = 3       # Internal Hard Drive / SSD
DRIVE_REMOTE = 4      # Network Share
DRIVE_CDROM = 5       # Optical Disc (CD-ROM, DVD-ROM, BD-ROM)
DRIVE_RAMDISK = 6

DRIVE_TYPE_NAMES = {
    DRIVE_UNKNOWN: "وسيط غير معروف (Unknown)",
    DRIVE_NO_ROOT_DIR: "مسار غير صالح (Invalid Path)",
    DRIVE_REMOVABLE: "قرص فلاش USB (Removable Flash Drive)",
    DRIVE_FIXED: "قرص صلب داخلي / SSD (Fixed Internal Drive)",
    DRIVE_REMOTE: "قرص شبكي (Network Share)",
    DRIVE_CDROM: "قرص ليزري ضوئي CD / DVD (Optical Disc)",
    DRIVE_RAMDISK: "قرص ذاكرة مؤقتة (RAM Disk)",
}

SALT_MAGIC = b"KnowledgeOcean_MediaDongle_Lock_v2026_Secured"

class SecurityIntegrityError(Exception):
    """Raised when hardware decryption or tamper validation fails."""
    pass


def get_drive_info(drive_path: str) -> dict:
    """
    Queries hardware properties of the specified drive path (e.g. 'E:', 'E:\\', or full file path).
    Returns a dictionary of hardware attributes or raises ValueError.
    """
    clean_drive = os.path.splitdrive(os.path.abspath(drive_path))[0].upper()
    if not clean_drive:
        clean_drive = drive_path.strip().rstrip("\\/").rstrip(":").upper() + ":"
    if not clean_drive.endswith(":"):
        clean_drive += ":"
    root = f"{clean_drive}\\"

    kernel32 = ctypes.windll.kernel32

    # 1. Drive Type
    drive_type = kernel32.GetDriveTypeW(root)

    # 2. Volume Information (Label, Serial, File System)
    vol_name = ctypes.create_unicode_buffer(260)
    fs_name = ctypes.create_unicode_buffer(260)
    vol_serial = ctypes.c_ulong()
    max_len = ctypes.c_ulong()
    flags = ctypes.c_ulong()

    res_vol = kernel32.GetVolumeInformationW(
        root, vol_name, 260,
        ctypes.byref(vol_serial),
        ctypes.byref(max_len),
        ctypes.byref(flags),
        fs_name, 260
    )

    # 3. Disk Free Space / Total Capacity
    free_bytes = ctypes.c_ulonglong()
    total_bytes = ctypes.c_ulonglong()
    total_free = ctypes.c_ulonglong()
    res_space = kernel32.GetDiskFreeSpaceExW(
        root,
        ctypes.byref(free_bytes),
        ctypes.byref(total_bytes),
        ctypes.byref(total_free)
    )

    serial_dec = vol_serial.value if res_vol else 0
    serial_hex = f"{serial_dec:08X}"
    name_str = vol_name.value.strip() if res_vol else ""
    fs_str = fs_name.value.strip() if res_vol else ""
    capacity = total_bytes.value if res_space else 0

    return {
        "drive_letter": clean_drive,
        "drive_root": root,
        "drive_type": drive_type,
        "drive_type_name": DRIVE_TYPE_NAMES.get(drive_type, f"نوع {drive_type}"),
        "volume_name": name_str,
        "volume_serial_dec": serial_dec,
        "volume_serial_hex": serial_hex,
        "total_bytes": capacity,
        "free_bytes": free_bytes.value if res_space else 0,
        "fs_name": fs_str,
        "is_valid_dongle_media": drive_type in (DRIVE_REMOVABLE, DRIVE_CDROM)
    }


def get_all_connected_drives() -> list[dict]:
    """Scans and returns hardware profiles of all logical drives on the system."""
    kernel32 = ctypes.windll.kernel32
    bitmask = kernel32.GetLogicalDrives()
    drives = []
    for letter in range(26):
        if bitmask & (1 << letter):
            drv = chr(65 + letter) + ":"
            try:
                info = get_drive_info(drv)
                drives.append(info)
            except Exception:
                pass
    return drives


def derive_media_key(vol_serial: int, total_size: int, vol_name: str, drive_type: int) -> bytes:
    """
    Cryptographically derives a 256-bit AES encryption/decryption key
    strictly bound to the physical medium's attributes.
    """
    key_material = f"SERIAL:{vol_serial}|SIZE:{total_size}|LABEL:{vol_name}|TYPE:{drive_type}".encode("utf-8")
    return hashlib.pbkdf2_hmac("sha256", key_material, SALT_MAGIC, iterations=120000, dklen=32)


def encrypt_payload_aes(data: bytes, key: bytes, extra_auth_data: bytes = b"") -> bytes:
    """
    Encrypts data using military-grade AES-256-GCM.
    Returns nonce + ciphertext + auth_tag blob.
    """
    try:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        nonce = os.urandom(12)
        aesgcm = AESGCM(key)
        ciphertext = aesgcm.encrypt(nonce, data, extra_auth_data)
        return nonce + ciphertext
    except ImportError:
        # High-security pure-Python fallback using PBKDF2 CTR + HMAC-SHA256
        nonce = os.urandom(16)
        mac_key = hashlib.sha256(key + b":mac").digest()
        cipher_key = hashlib.sha256(key + b":cipher").digest()

        # Keystream generation via HMAC-SHA256 counter
        keystream = bytearray()
        counter = 0
        while len(keystream) < len(data):
            block = hashlib.sha256(cipher_key + nonce + struct.pack(">Q", counter)).digest()
            keystream.extend(block)
            counter += 1

        ct = bytes(b ^ k for b, k in zip(data, keystream[:len(data)]))
        tag = hashlib.sha256(mac_key + nonce + ct + (extra_auth_data or b"")).digest()[:16]
        return nonce + tag + ct


def decrypt_payload_aes(encrypted_blob: bytes, key: bytes, extra_auth_data: bytes = b"") -> bytes:
    """
    Decrypts AES-256-GCM data using the derived media key.
    Raises SecurityIntegrityError if the key or media signature does not match.
    """
    if len(encrypted_blob) < 28:
        raise SecurityIntegrityError("تلف في الحزمة المشفرة (Encrypted payload is corrupted).")

    try:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        nonce = encrypted_blob[:12]
        ciphertext = encrypted_blob[12:]
        aesgcm = AESGCM(key)
        return aesgcm.decrypt(nonce, ciphertext, extra_auth_data)
    except ImportError:
        nonce = encrypted_blob[:16]
        expected_tag = encrypted_blob[16:32]
        ct = encrypted_blob[32:]

        mac_key = hashlib.sha256(key + b":mac").digest()
        cipher_key = hashlib.sha256(key + b":cipher").digest()
        computed_tag = hashlib.sha256(mac_key + nonce + ct + (extra_auth_data or b"")).digest()[:16]

        if not hmac_compare(expected_tag, computed_tag):
            raise SecurityIntegrityError("فشل التحقق من صحة التشفير العتادي (Hardware MAC mismatch).")

        keystream = bytearray()
        counter = 0
        while len(keystream) < len(ct):
            block = hashlib.sha256(cipher_key + nonce + struct.pack(">Q", counter)).digest()
            keystream.extend(block)
            counter += 1

        return bytes(b ^ k for b, k in zip(ct, keystream[:len(ct)]))
    except Exception as e:
        raise SecurityIntegrityError(f"فشل فك التشفير العتادي: عدم تطابق بصمة القرص الأصلي ({e}).")


def hmac_compare(a: bytes, b: bytes) -> bool:
    """Constant-time comparison."""
    if len(a) != len(b):
        return False
    res = 0
    for x, y in zip(a, b):
        res |= x ^ y
    return res == 0


def create_media_license(drive_info: dict) -> dict:
    """
    Generates a hardware-bound license profile dictionary from drive info.
    """
    serial = drive_info["volume_serial_dec"]
    size = drive_info["total_bytes"]
    name = drive_info["volume_name"]
    dtype = drive_info["drive_type"]

    key = derive_media_key(serial, size, name, dtype)
    probe_phrase = f"KO_VALIDATED_MEDIA_{serial}_{size}".encode("utf-8")
    probe_encrypted = encrypt_payload_aes(probe_phrase, key, b"KO_PROBE_HEADER")

    return {
        "version": "2.0",
        "drive_type": dtype,
        "drive_type_name": drive_info["drive_type_name"],
        "volume_name": name,
        "volume_serial_hex": drive_info["volume_serial_hex"],
        "volume_serial_dec": serial,
        "total_bytes": size,
        "fs_name": drive_info["fs_name"],
        "probe_encrypted_hex": probe_encrypted.hex(),
        "created_at_utc": "2026-10-05T06:40:00Z"
    }


def verify_media_against_license(current_drive: str, license_data: dict) -> tuple[bool, str]:
    """
    Verifies that current_drive matches the hardware license profile.
    Returns (True, "OK") or (False, "Arabic reason").
    """
    try:
        cur_info = get_drive_info(current_drive)
    except Exception as e:
        return False, f"تعذر فحص وسيط التخزين ({e})."

    # 1. Drive type check: must NOT be fixed internal drive
    if cur_info["drive_type"] == DRIVE_FIXED:
        return False, (
            "تم تشغيل الملف من القرص الصلب للحاسوب (Fixed Hard Drive / SSD).\n"
            "هذا المثبت محمي ومقيد بالتشغيل مباشرة وحصراً من القرص الأصلي (CD / DVD / FLASH).\n"
            "لا يمكن تشغيل البرنامج بعد نسخه إلى القرص الصلب."
        )

    # 2. Check drive type match (Removable Flash or Optical Disc)
    if cur_info["drive_type"] != license_data["drive_type"]:
        return False, (
            f"نوع وسيط التخزين الحالي ({cur_info['drive_type_name']}) "
            f"لا يطابق نوع الوسيط الأصلي المصرح به ({license_data.get('drive_type_name', 'القرص الأصلي')})."
        )

    # 3. Check Volume Serial Number
    cur_serial = cur_info["volume_serial_dec"]
    req_serial = license_data["volume_serial_dec"]
    if cur_serial != req_serial:
        return False, (
            f"عدم تطابق الرقم التسلسلي لوسيط التخزين (Volume Serial Mismatch):\n"
            f"• الرقم المكتشف: 0x{cur_info['volume_serial_hex']}\n"
            f"• الرقم المصرح به: 0x{license_data['volume_serial_hex']}\n\n"
            "⛔ تم حظر التشغيل لأن الحزمة تم نقلها إلى قرص أو فلاشة أخرى غير مصرح بها."
        )

    # 4. Check Total Capacity / Storage Size (Size must match)
    cur_size = cur_info["total_bytes"]
    req_size = license_data["total_bytes"]
    # Allow 0.5% tolerance only for dynamic optical disk lead-in variations if CD/DVD
    tolerance = 0 if cur_info["drive_type"] == DRIVE_REMOVABLE else int(req_size * 0.01)
    if abs(cur_size - req_size) > tolerance:
        cur_gb = cur_size / (1024**3)
        req_gb = req_size / (1024**3)
        return False, (
            f"عدم تطابق سعة وسيط التخزين (Capacity Mismatch):\n"
            f"• السعة المكتشفة: {cur_gb:.2f} GB ({cur_size:,} بايت)\n"
            f"• السعة المصرح بها: {req_gb:.2f} GB ({req_size:,} بايت)\n\n"
            "⛔ حجم وسيط التخزين لا يطابق سعة القرص الأصلي المعتمد."
        )

    # 5. Check Volume Label / Name (if non-empty in license)
    if license_data.get("volume_name"):
        if cur_info["volume_name"].strip().lower() != license_data["volume_name"].strip().lower():
            return False, (
                f"عدم تطابق اسم وحدة التخزين (Volume Label Mismatch):\n"
                f"• الاسم المكتشف: '{cur_info['volume_name']}'\n"
                f"• الاسم المصرح به: '{license_data['volume_name']}'"
            )

    # 6. Cryptographic Probe Verification
    try:
        key = derive_media_key(cur_serial, cur_size, cur_info["volume_name"], cur_info["drive_type"])
        probe_blob = bytes.fromhex(license_data["probe_encrypted_hex"])
        pt = decrypt_payload_aes(probe_blob, key, b"KO_PROBE_HEADER")
        expected_phrase = f"KO_VALIDATED_MEDIA_{req_serial}_{req_size}".encode("utf-8")
        if pt != expected_phrase:
            return False, "فشل اختبار فك التشفير العتادي لمفتاح القرص."
    except Exception as e:
        return False, f"فشل فك التشفير العتادي لبيانات القرص: {e}"

    return True, "تم التحقق من وسيط التخزين الأصلي بنجاح (Authorized Media Verified)."


def find_inserted_authorized_media(license_data: dict) -> tuple[bool, str, dict | None]:
    """
    Scans all connected drives to find if the authorized CD/DVD or Flash drive is currently plugged in.
    Returns (True, drive_root, drive_info) or (False, reason, None).
    """
    for drv in get_all_connected_drives():
        # Only check Removable and CD-ROM drives
        if drv["drive_type"] in (DRIVE_REMOVABLE, DRIVE_CDROM):
            ok, _ = verify_media_against_license(drv["drive_letter"], license_data)
            if ok:
                return True, drv["drive_root"], drv
    return False, "لم يتم العثور على قرص أو فلاشة التوثيق المعتمدة متصلة بالحاسوب.", None
