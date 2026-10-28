# -*- coding: utf-8 -*-
"""
Knowledge Ocean - Dedicated Native Desktop Application
Runs the FastAPI / Uvicorn server in a background daemon thread and presents
the full application inside a dedicated native desktop window powered by
Microsoft Edge WebView2 (pywebview).

Features:
 - Pure browser-independent desktop application
 - Clean startup without flashing console windows
 - Automatic port allocation and ghost process cleanup
 - Full research search, abstract view, PDF viewer, and direct downloads
 - Automatic clean exit on window closure
"""
from __future__ import annotations

import os
import sys
import time
import socket
import logging
import threading
from pathlib import Path
import urllib.request
import urllib.error

# Determine paths for both frozen executable and script mode
if getattr(sys, "frozen", False):
    APP_DIR = Path(sys.executable).resolve().parent
    BUNDLE_DIR = Path(getattr(sys, "_MEIPASS", APP_DIR))
else:
    APP_DIR = Path(__file__).resolve().parent
    BUNDLE_DIR = APP_DIR

# Set working directory to application root
os.chdir(str(APP_DIR))

# Safe stream redirection for windowed GUI mode with isatty support
class SafeLogWriter:
    def __init__(self, filepath):
        try:
            self.file = open(filepath, "a", encoding="utf-8")
        except Exception:
            self.file = None

    def write(self, text):
        if self.file and text:
            try:
                self.file.write(text)
                self.file.flush()
            except Exception:
                pass

    def flush(self):
        if self.file:
            try:
                self.file.flush()
            except Exception:
                pass

    def isatty(self):
        return False

log_path = APP_DIR / "desktop_app.log"
writer = SafeLogWriter(log_path)
sys.stdout = writer
sys.stderr = writer

# Ensure local standalone execution flags
os.environ["IS_LOCAL"] = "1"
os.environ["LOCAL_INSTANCE"] = "1"
os.environ["NO_BROWSER"] = "1"  # Do not launch external browser tabs

# Add directories to sys.path
for p in [str(APP_DIR), str(BUNDLE_DIR)]:
    if p not in sys.path:
        sys.path.insert(0, p)

# Logging configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stderr)]
)
log = logging.getLogger("KnowledgeOceanDesktop")

# Helper: Load config and Free port if occupied
try:
    from config_loader import kill_port_occupants, load_local_config
    for cfg_path in [APP_DIR / "config.txt", BUNDLE_DIR / "config.txt", Path("config.txt")]:
        if cfg_path.exists():
            load_local_config(str(cfg_path))
            break
    kill_port_occupants(7860)
except Exception as e:
    log.warning(f"Config/Port non-critical notice: {e}")

# ---------------------------------------------------------------------------
# GPU & Energy Optimization for Edge WebView2 (Chromium)
# ---------------------------------------------------------------------------
low_gpu = os.environ.get("LOW_GPU_MODE", "true").strip().lower() in ("1", "true", "yes", "on")
if low_gpu:
    gpu_flags = [
        "--disable-gpu",
        "--disable-gpu-compositing",
        "--disable-gpu-rasterization",
        "--disable-accelerated-2d-canvas",
        "--disable-d3d11",
        "--gpu-preference=low-power",
        "--enable-low-end-device-mode"
    ]
    cur_args = os.environ.get("WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS", "")
    os.environ["WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS"] = f"{cur_args} {' '.join(gpu_flags)}".strip()
    os.environ["SHIM_MCCOMPAT"] = "0x800000001"
    log.info("⚡ Low-GPU Energy Saver Mode active (GPU offloaded to lightweight CPU software rasterization)")

PORT = 7860

def is_port_free(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex(("127.0.0.1", port)) != 0

if not is_port_free(PORT):
    for alt_port in range(7861, 7899):
        if is_port_free(alt_port):
            PORT = alt_port
            break

SERVER_HOST = "127.0.0.1"
SERVER_URL = f"http://{SERVER_HOST}:{PORT}"

def start_backend_server():
    """Run FastAPI through Uvicorn in background thread"""
    try:
        import uvicorn
        from app import app as fastapi_app

        config = uvicorn.Config(
            app=fastapi_app,
            host=SERVER_HOST,
            port=PORT,
            log_level="warning",
            access_log=False,
            loop="asyncio",
            log_config=None  # Standard logging without terminal color isatty check
        )
        server = uvicorn.Server(config)
        server.run()
    except Exception as e:
        log.error(f"Fatal error in backend server: {e}", exc_info=True)

def wait_for_backend(timeout: float = 25.0) -> bool:
    """Wait until /health returns HTTP 200"""
    start_time = time.time()
    health_url = f"{SERVER_URL}/health"
    while time.time() - start_time < timeout:
        try:
            req = urllib.request.Request(health_url, headers={"User-Agent": "KnowledgeOceanDesktop-Probe"})
            with urllib.request.urlopen(req, timeout=1.0) as resp:
                if resp.status == 200:
                    return True
        except Exception:
            pass
        time.sleep(0.3)
    return False

def verify_installation_integrity():
    """
    تحقق نظامي صارم لمنع تشغيل البرنامج عبر النسخ اليدوي:
    البرنامج لن يعمل إلا إذا تم تثبيته رسمياً على نفس الحاسوب عبر ملف التنصيب (KnowledgeOcean_Setup.exe).
    في حال تم نسخ المجلد لجهاز آخر أو نقله لمسار آخر دون تثبيت، يُمنع التشغيل وتظهر رسالة تنبيه نظامية.
    """
    if not getattr(sys, "frozen", False):
        return True

    if sys.platform != "win32":
        return True

    import winreg
    import ctypes

    error_title = "تنبيه نظامي - محيط المعرفة"
    error_msg = (
        "تعذر تشغيل البرنامج!\n\n"
        "لم يتم تثبيت هذا البرنامج بشكل نظامي على هذا الجهاز من خلال ملف التنصيب المعتمد.\n"
        "لا يمكن تشغيل البرنامج عبر نسخ المجلد يدوياً بين الأجهزة أو المسارات.\n\n"
        "يرجى تشغيل ملف التثبيت الرسمي (KnowledgeOcean_Setup.exe) لتنصيب البرنامج والملحقات بشكل صحيح على حاسوبك."
    )

    try:
        current_exe_dir = os.path.abspath(str(APP_DIR)).rstrip("\\/").lower()

        # 1. فحص مفتاح التسجيل المخصص في HKCU
        reg_path = None
        comp_name = None
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\KnowledgeOcean") as key:
                reg_path, _ = winreg.QueryValueEx(key, "InstallPath")
                try:
                    comp_name, _ = winreg.QueryValueEx(key, "ComputerName")
                except Exception:
                    pass
        except Exception:
            pass

        # 2. فحص مفتاح إلغاء التثبيت المسجل من Inno Setup
        uninst_path = None
        for root in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
            for sub in (
                r"Software\Microsoft\Windows\CurrentVersion\Uninstall\{D5E8C941-8F32-4740-9E39-F024BB1797DA}_is1",
                r"Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\{D5E8C941-8F32-4740-9E39-F024BB1797DA}_is1",
            ):
                try:
                    with winreg.OpenKey(root, sub) as key:
                        uninst_path, _ = winreg.QueryValueEx(key, "InstallLocation")
                        if uninst_path:
                            break
                except Exception:
                    continue
            if uninst_path:
                break

        # إذا لم يكن هناك أي سجل تثبيت
        installed_dir = reg_path or uninst_path
        if not installed_dir:
            ctypes.windll.user32.MessageBoxW(0, error_msg, error_title, 0x10 | 0x00040000)
            sys.exit(1)

        # التحقق من أن المسار الحالي يطابق المسار المثبت
        norm_installed_dir = os.path.abspath(installed_dir).rstrip("\\/").lower()
        if current_exe_dir != norm_installed_dir:
            ctypes.windll.user32.MessageBoxW(0, error_msg, error_title, 0x10 | 0x00040000)
            sys.exit(1)

        # التحقق من اسم الحاسوب
        if comp_name:
            current_comp = os.environ.get("COMPUTERNAME", "").strip().lower()
            if comp_name.strip().lower() != current_comp:
                ctypes.windll.user32.MessageBoxW(0, error_msg, error_title, 0x10 | 0x00040000)
                sys.exit(1)

        # التحقق من وجود ملف إلغاء التثبيت unins000.exe
        uninstaller_exe = APP_DIR / "unins000.exe"
        if not uninstaller_exe.exists():
            ctypes.windll.user32.MessageBoxW(0, error_msg, error_title, 0x10 | 0x00040000)
            sys.exit(1)

        # 5. التحقق من وسيط التخزين العتادي الأصلي (CD / DVD / FLASH Dongle Check)
        sig_candidates = [
            APP_DIR / "media_dongle.sig",
            BUNDLE_DIR / "media_dongle.sig",
            Path("media_dongle.sig")
        ]
        sig_data = None
        for sc in sig_candidates:
            if sc.exists():
                try:
                    import json
                    with open(sc, "r", encoding="utf-8") as sf:
                        sig_data = json.load(sf)
                    break
                except Exception:
                    pass

        if not sig_data:
            try:
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\KnowledgeOcean") as key:
                    sig_str, _ = winreg.QueryValueEx(key, "MediaDongleSig")
                    if sig_str:
                        import json
                        sig_data = json.loads(sig_str)
            except Exception:
                pass

        if sig_data:
            import media_security
            is_present, reason, _ = media_security.find_inserted_authorized_media(sig_data)
            if not is_present:
                dongle_title = "تنبيه أمني - القرص الأصلي غير متصل"
                dongle_msg = (
                    "⚠️ تعذر تشغيل برنامج محيط المعرفة!\n\n"
                    "هذا البرنامج مرخص ومقيد عتادياً بالقرص الأصلي (CD / DVD / FLASH).\n"
                    "لم يتم العثور على قرص أو فلاشة التوثيق المعتمدة متصلة بهذا الجهاز.\n\n"
                    "• يرجى إدخال قرص أو فلاشة التوثيق المعتمدة لتشغيل البرنامج.\n"
                    "• تم حظر التشغيل لمنع استخدام البرنامج بعد نقله دون القرص الأصلي."
                )
                ctypes.windll.user32.MessageBoxW(0, dongle_msg, dongle_title, 0x10 | 0x00040000)
                sys.exit(1)

        return True

    except Exception:
        ctypes.windll.user32.MessageBoxW(0, error_msg, error_title, 0x10 | 0x00040000)
        sys.exit(1)

def main():
    verify_installation_integrity()
    log.info(f"Initializing Knowledge Ocean Desktop on {SERVER_URL}...")

    # Launch backend server thread
    backend_thread = threading.Thread(target=start_backend_server, daemon=True)
    backend_thread.start()

    # Wait for server ready
    ready = wait_for_backend(timeout=20.0)
    if ready:
        log.info(f"Backend successfully verified online at {SERVER_URL}")
    else:
        log.warning("Backend health probe timed out; attempting window launch anyway...")

    import webview

    # Configure webview settings
    webview.settings['ALLOW_DOWNLOADS'] = True
    webview.settings['OPEN_EXTERNAL_LINKS_IN_BROWSER'] = True

    # Identify application icon
    icon_candidate = None
    for cand in [
        APP_DIR / "static" / "app_icon.ico",
        BUNDLE_DIR / "static" / "app_icon.ico",
        APP_DIR / "static" / "icon.png",
        BUNDLE_DIR / "static" / "icon.png"
    ]:
        if cand.exists():
            icon_candidate = str(cand)
            break

    window = webview.create_window(
        title="Knowledge Ocean",
        url=SERVER_URL,
        width=1320,
        height=860,
        min_size=(980, 660),
        resizable=True,
        fullscreen=False,
        confirm_close=False,
        background_color="#0b132b"
    )

    def handle_window_closed():
        log.info("Desktop window closed. Exiting Knowledge Ocean cleanly...")
        os._exit(0)

    window.events.closed += handle_window_closed

    try:
        # Start native window UI
        webview.start(icon=icon_candidate, private_mode=False)
    except Exception as e:
        log.warning(f"Native WebView window encountered an issue: {e}")
        try:
            import webbrowser
            log.info(f"Opening fallback browser at {SERVER_URL}...")
            webbrowser.open(SERVER_URL)
            while True:
                time.sleep(1)
        except Exception:
            os._exit(1)

if __name__ == "__main__":
    main()
