# -*- coding: utf-8 -*-
"""
Knowledge Ocean - Hardware Dongle Protected USB Installer Launcher
Developed for ABDULSALAM S. HASAN

Enforces strict hardware-binding to the authorized physical USB drive:
 - Drive Type: Removable Media (DRIVE_REMOVABLE = 2)
 - Storage Bus Type: USB (BusTypeUsb = 7)
 - Volume Serial Number: 0xB6301249 (3056603721)
 - Volume Storage Size: ~29.11 GB (31,259,066,368 bytes)
 - Physical Disk Hardware Controller Serial: 058F63666438

If copied to any computer hard drive, SSD, network share, or any other USB drive,
execution is strictly blocked with a native hardware security alert modal.
"""

from __future__ import annotations

import os
import sys
import ctypes
from ctypes import wintypes
import shutil
import subprocess
import tempfile

# Authorized Hardware Dongle Profile
AUTHORIZED_CONFIG = {
    "DRIVE_TYPE": 2,                 # DRIVE_REMOVABLE
    "BUS_TYPE": 7,                   # BusTypeUsb
    "VOL_SERIAL_HEX": "B6301249",
    "VOL_SERIAL_DEC": 3056603721,
    "VOL_SIZE_MIN": 31200000000,
    "VOL_SIZE_MAX": 31300000000,
    "HW_SERIAL": "058F63666438",
}

IOCTL_STORAGE_QUERY_PROPERTY = 0x002D1400

class STORAGE_PROPERTY_QUERY(ctypes.Structure):
    _fields_ = [
        ("PropertyId", wintypes.DWORD),
        ("QueryType", wintypes.DWORD),
        ("AdditionalParameters", wintypes.BYTE * 1)
    ]

class STORAGE_DESCRIPTOR_HEADER(ctypes.Structure):
    _fields_ = [
        ("Version", wintypes.DWORD),
        ("Size", wintypes.DWORD)
    ]

def show_native_error(title: str, message: str) -> None:
    """Displays a native modal error dialog with high priority."""
    try:
        # 0x10 = MB_ICONERROR | 0x00040000 = MB_TOPMOST
        ctypes.windll.user32.MessageBoxW(0, message, title, 0x10 | 0x00040000)
    except Exception:
        pass

def query_hardware_storage(drive_letter: str):
    """Queries hardware bus type and manufacturer controller serial via Win32 IOCTL."""
    drive_clean = drive_letter.strip().rstrip("\\").rstrip(":")
    volume_path = f"\\\\.\\{drive_clean}:"
    FILE_SHARE_READ = 0x00000001
    FILE_SHARE_WRITE = 0x00000002
    OPEN_EXISTING = 3

    kernel32 = ctypes.windll.kernel32
    h_device = kernel32.CreateFileW(
        volume_path,
        0,  # Query access
        FILE_SHARE_READ | FILE_SHARE_WRITE,
        None,
        OPEN_EXISTING,
        0,
        None
    )
    if h_device == -1 or h_device == 0xFFFFFFFFFFFFFFFF:
        return None, f"تعذر فتح منفذ قراءة العتاد للقرص ({drive_clean}:)."

    try:
        query = STORAGE_PROPERTY_QUERY()
        query.PropertyId = 0  # StorageDeviceProperty
        query.QueryType = 0   # PropertyStandardQuery

        header = STORAGE_DESCRIPTOR_HEADER()
        bytes_returned = wintypes.DWORD(0)

        ok = kernel32.DeviceIoControl(
            h_device,
            IOCTL_STORAGE_QUERY_PROPERTY,
            ctypes.byref(query),
            ctypes.sizeof(query),
            ctypes.byref(header),
            ctypes.sizeof(header),
            ctypes.byref(bytes_returned),
            None
        )

        out_size = header.Size if header.Size > 0 else 1024
        buf = ctypes.create_string_buffer(out_size)

        ok = kernel32.DeviceIoControl(
            h_device,
            IOCTL_STORAGE_QUERY_PROPERTY,
            ctypes.byref(query),
            ctypes.sizeof(query),
            buf,
            out_size,
            ctypes.byref(bytes_returned),
            None
        )

        if not ok:
            return None, "تعذر استعلام الخصائص العتادية لمنفذ الـ USB."

        raw_bytes = buf.raw
        serial_offset = int.from_bytes(raw_bytes[24:28], byteorder="little")
        bus_type = int.from_bytes(raw_bytes[28:32], byteorder="little")
        removable = bool(raw_bytes[10])

        serial = ""
        if 0 < serial_offset < len(raw_bytes):
            end = raw_bytes.find(b"\x00", serial_offset)
            if end != -1:
                serial = raw_bytes[serial_offset:end].decode("ascii", errors="ignore").strip()
            else:
                serial = raw_bytes[serial_offset:].decode("ascii", errors="ignore").strip()

        return {
            "serial": serial,
            "bus_type": bus_type,
            "removable": removable
        }, None
    finally:
        kernel32.CloseHandle(h_device)

def verify_dongle() -> tuple[bool, str]:
    """
    Verifies that the current executable resides directly on the authorized physical USB drive.
    Returns (True, details) or (False, error_reason).
    """
    current_exe = sys.executable
    drive = os.path.splitdrive(os.path.abspath(current_exe))[0].upper()
    if not drive:
        return False, "تعذر تحديد حرف محرك الأقراص (Unable to resolve drive letter)."
    if not drive.endswith(":"):
        drive += ":"
    root = f"{drive}\\"

    kernel32 = ctypes.windll.kernel32

    # 1. Drive Type Check: Must be REMOVABLE (USB), not FIXED (Hard Disk / SSD)
    drive_type = kernel32.GetDriveTypeW(root)
    if drive_type != AUTHORIZED_CONFIG["DRIVE_TYPE"]:
        drive_names = {
            0: "Unknown Media",
            1: "Invalid Root",
            2: "Removable USB Drive",
            3: "Fixed Hard Drive / SSD (القرص الصلب)",
            4: "Network Drive / Share",
            5: "Optical Disc (CD/DVD)",
            6: "RAM Disk"
        }
        current_name = drive_names.get(drive_type, f"Type {drive_type}")
        return False, (
            f"نوع الوسيط غير مصرح به:\n"
            f"تم تشغيل الملف من «{current_name}» ({drive})، بينما الملف مصرح له بالعمل من وحدة الـ USB الأصلية فقط.\n\n"
            f"⛔ لا يمكن تشغيل البرنامج بعد نسخه إلى القرص الصلب للحاسوب."
        )

    # 2. Volume Serial Number Check
    vol_name = ctypes.create_unicode_buffer(260)
    fs_name = ctypes.create_unicode_buffer(260)
    vol_serial = ctypes.c_ulong()
    max_comp_len = ctypes.c_ulong()
    fs_flags = ctypes.c_ulong()

    res_vol = kernel32.GetVolumeInformationW(
        root, vol_name, 260,
        ctypes.byref(vol_serial),
        ctypes.byref(max_comp_len),
        ctypes.byref(fs_flags),
        fs_name, 260
    )
    if not res_vol:
        return False, f"تعذر قراءة بيانات وحدة التخزين ({drive})."

    cur_serial_hex = f"{vol_serial.value:08X}"
    if vol_serial.value != AUTHORIZED_CONFIG["VOL_SERIAL_DEC"] and cur_serial_hex != AUTHORIZED_CONFIG["VOL_SERIAL_HEX"]:
        return False, (
            f"عدم تطابق رقم تسلسل وحدة الـ USB (Volume Serial Mismatch):\n"
            f"• الرقم المكتشف: {cur_serial_hex}\n"
            f"• الرقم المصرح به: {AUTHORIZED_CONFIG['VOL_SERIAL_HEX']}\n\n"
            f"⛔ تم حظر التشغيل لأن الملف التنصيبي تم نسخه إلى وحدة USB أخرى غير مصرح بها."
        )

    # 3. Volume Capacity Check
    free_avail = ctypes.c_ulonglong()
    total_bytes = ctypes.c_ulonglong()
    total_free = ctypes.c_ulonglong()
    res_space = kernel32.GetDiskFreeSpaceExW(root, ctypes.byref(free_avail), ctypes.byref(total_bytes), ctypes.byref(total_free))
    if not res_space or not (AUTHORIZED_CONFIG["VOL_SIZE_MIN"] <= total_bytes.value <= AUTHORIZED_CONFIG["VOL_SIZE_MAX"]):
        detected_gb = total_bytes.value / (1024**3)
        return False, (
            f"عدم تطابق سعة وحدة الـ USB (Storage Capacity Mismatch):\n"
            f"• السعة المكتشفة: {detected_gb:.2f} GB ({total_bytes.value:,} bytes)\n"
            f"• السعة المصرح بها: ~29.11 GB (31,259,066,368 bytes)\n\n"
            f"⛔ وحدة الـ USB الحالية لا تطابق السعة الأصلية لوحدة التوثيق المعتمدة."
        )

    # 4. Hardware Controller Serial and Bus Type Check
    hw_info, err = query_hardware_storage(drive)
    if err:
        return False, err

    if hw_info["bus_type"] != AUTHORIZED_CONFIG["BUS_TYPE"]:
        return False, f"ناقل وحدة التخزين ليس USB حقيقي (BusType: {hw_info['bus_type']})."

    if hw_info["serial"] != AUTHORIZED_CONFIG["HW_SERIAL"]:
        return False, (
            f"عدم تطابق السيريال العتادي للمصنع (Hardware Serial Mismatch):\n"
            f"• السيريال المكتشف: {hw_info['serial']}\n"
            f"• السيريال المصرح به: {AUTHORIZED_CONFIG['HW_SERIAL']}\n\n"
            f"⛔ تم حظر التثبيت: وحدة الـ USB الحالية ليست وحدة الدونجل الأصلية المعتمدة."
        )

    return True, "Authorized Hardware Dongle Verified"

def main():
    # 1. Strict Hardware Dongle Verification
    is_valid, reason = verify_dongle()
    if not is_valid:
        error_title = "حظر أمني - Knowledge Ocean Hardware Dongle"
        error_msg = (
            "⚠️ تعذر تشغيل برنامج التثبيت!\n\n"
            "هذا الملف التنصيبي محمي ومقيد عتادياً بوحدة الـ USB الأصلية المعتمدة (Hardware Dongle Lock).\n\n"
            f"{reason}\n\n"
            "• لا يمكن تشغيل هذا الملف بعد نسخه للكمبيوتر أو نقله إلى أي فلاشة أخرى.\n"
            "• يرجى تشغيل الملف مباشرة من وحدة الـ USB الأصلية المصرح بها حصراً."
        )
        show_native_error(error_title, error_msg)
        sys.exit(1)

    # 2. Locate Embedded Payload
    bundle_dir = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    payload_name = "ko_setup_payload.bin"
    payload_source = os.path.join(bundle_dir, payload_name)

    # Development mode fallbacks
    if not os.path.exists(payload_source):
        payload_source = os.path.join(bundle_dir, "installer_dist", "KnowledgeOcean_Setup.exe")
    if not os.path.exists(payload_source):
        payload_source = r"g:\محيط المعرفة\installer_dist\KnowledgeOcean_Setup.exe"

    if not os.path.exists(payload_source):
        show_native_error("Knowledge Ocean", "تعذر العثور على حزمة التثبيت الداخلية المرفقة.")
        sys.exit(1)

    # 3. Extract payload to volatile secure temporary directory
    temp_dir = tempfile.mkdtemp(prefix="ko_setup_")
    temp_setup = os.path.join(temp_dir, "KnowledgeOcean_Setup.exe")

    try:
        shutil.copy2(payload_source, temp_setup)

        # Launch the official Inno Setup installer payload
        cmd = [temp_setup] + sys.argv[1:]
        proc = subprocess.Popen(cmd)
        proc.wait()
        sys.exit(proc.returncode)

    finally:
        # Secure cleanup: shred and wipe temporary unpacked files
        try:
            if os.path.exists(temp_setup):
                os.remove(temp_setup)
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)
        except Exception:
            pass

if __name__ == "__main__":
    main()
