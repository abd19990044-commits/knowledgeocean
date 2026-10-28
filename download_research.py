import tempfile
# -*- coding: utf-8 -*-
"""
═══════════════════════════════════════════════════════════════════════════
 ⬇️  منزّل ملفات PDF من «ملف 0» — Production Grade (Architecture 13.0)
═══════════════════════════════════════════════════════════════════════════
 نفس الفكرة والآلية الأصلية:
   ملف 0  →  تحليل المداخل  →  Chrome حقيقي ببروفايل الطالب  →
   (رابط Open Access → DOI Checker → Sci-Hub)  →  تنزيل  →  تقرير PDF.

 ما الذي تغيّر في نسخة الإنتاج (إصلاحات فقط، بلا تغيير في المنطق):
   1) [CRITICAL] إيقاف نافذة «تشخيص شبكة Windows» المتكررة:
      كان XPath القديم  contains(translate(text(),'NO','no'),'no')  يطابق
      زر «Diag(no)se network problems» في صفحة خطأ Chrome، فينقره السكربت
      في كل دورة من حلقة الانتظار → تفتح النافذة كلما أغلقتها.
      الحل: مطابقة نصّية تامّة لكلمة "no" + تجاهل صفحات chrome-error نهائياً
      + حارس اختياري يُنهي msdt.exe إن ظهرت لأي سبب آخر.
   2) [CRITICAL] Cloudflare / Turnstile:
      - كانت إحداثيات النقر تُؤخذ من element.rect (إحداثيات المستند) وتُرسل
        إلى CDP الذي يتوقع إحداثيات النافذة (viewport) → النقر يقع في مكان خاطئ.
        الآن تُحسب عبر getBoundingClientRect() بعد scrollIntoView.
      - انتظار الحل التلقائي أولاً (أغلب التحديات المُدارة تمرّ وحدها).
      - أحداث ماوس CDP مكتملة (buttons/clickCount) لتُعتبر موثوقة.
      - إصلاح تسريب تبويبات Z.ai وقفل التزامن.
      - إلغاء تلويث window.chrome (كان بصمة كشف واضحة).
   3) إجبار تنزيل PDF فعلياً: ضبط تفضيلات البروفايل المستنسخ
      (always_open_pdf_externally) بدل الاعتماد على النقر فقط.
   4) التحقق من صحة الملف: رفض أي ملف ليس PDF حقيقياً (%PDF magic) —
      كان يحفظ صفحات Cloudflare/تسجيل الدخول كملفات .pdf فاسدة.
   5) عزل التبويبات بين الخيوط (تبويب home ثابت لكل خيط) + منع سرقة التبويبات.
   6) إصلاح NameError عند قائمة روابط فارغة، وإعادة محاولة ذكية للأخطاء العابرة فقط.
   7) اكتشاف «ملف 0» لم يعد يلتقط الملفات المنزَّلة بالخطأ (0100_xxx.pdf).
   8) دعم pypdf كبديل لـ PyMuPDF، استئناف التشغيل، إيقاف نظيف بـ Ctrl+C.

 إضافات 13.1 (بلا أي تغيير في الهيكلة أو تسلسل العمل):
   9) [CRITICAL] بوابة «هل هذه صفحة بحث؟» قبل حفظ أي صفحة HTML كـ PDF:
      لا تُحفظ الصفحة إلا إذا حوت عنوان Abstract/Summary + Introduction/Background
      + قسماً أكاديمياً واحداً على الأقل (Methods/Results/Discussion/References…)
      + طولاً نصّياً كافياً ونصّاً حقيقياً بعد المقدمة. وإلا فالورقة تُصنَّف
      «غير متاح للتنزيل» وتُدرج في التقرير النهائي بسبب صريح لا كنجاح كاذب.
      (الفحص في looks_like_research_text — دالة نقيّة قابلة للاختبار.)
  10) [CRITICAL] Cloudflare: تمييز الحظر النهائي (1015/1020/«you have been
      blocked») عن التحدي القابل للحل. كان السكربت ينتظر 25 ثانية ثم ينقر ثم
      يُشغّل Z.ai ثلاث دقائق على صفحة حظر لا تحدي فيها أصلاً — ولكل ورقة.
      الآن يُعلَّم النطاق ويُتجاوز فوراً لبقية التشغيل (DomainCooldown).
  11) Turnstile: يُحدَّد مربّع التأشير من داخل الإطار نفسه (إحداثيات مركّبة
      صحيحة) بدل التخمين عند x+30، مع اختيار أكبر إطار تحدٍّ وتفضيل إطارات CF.
  12) اختبار الصور «اختر كل الصور التي…»: تُقرأ تعليمة التحدي وتُرسل إلى Z.ai
      (كانت مفقودة تماماً)، واللقطة تُقصّ على التحدي وحده عبر CDP، ويُطلب
      *أرقام بلاطات* تُحسب مراكزها من DOM بدل إحداثيات مخمَّنة، ثم يُنقر زر
      التحقق. ويُعطَّل Z.ai تلقائياً إن ظهر جدار تسجيل دخول بدل إهدار الوقت.
  13) إزالة لافتات الكوكيز (OneTrust/Cookiebot/…) التي تعترض النقر والتنزيل.
  14) التقرير: تصنيف لكل فشل (غير متاح للتنزيل / حماية / مهلة / بلا مصدر …)
      + ملخّص عددي، في TXT و CSV و PDF.
═══════════════════════════════════════════════════════════════════════════
"""

import os
import re
import sys
import glob
import json
import difflib
import time
import uuid
import base64
import random
import shutil
import signal
import atexit
import logging
import argparse
import threading
import subprocess
import urllib.request
import socket
import requests
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
from dataclasses import dataclass
from pathlib import Path
from functools import wraps
from urllib.parse import urlparse
from typing import List, Tuple, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.common.keys import Keys
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import (
        TimeoutException, WebDriverException, NoSuchWindowException,
        JavascriptException, InvalidSessionIdException,
    )
except ImportError:
    print("Missing deps. Please run:  pip install selenium pymupdf fpdf2")
    sys.exit(1)


# ═════════════════════════ CONFIG ═════════════════════════
@dataclass
class AppConfig:
    # --- المسارات ---
    output_dir: str = "downloaded_pdfs"          # يُحوَّل إلى مسار مطلق داخل main()
    staging_dirname: str = ".staging"            # مجلد تنزيل Chrome الافتراضي (احتياطي)
    file0_glob: str = "*00_*.pdf"
    report_name: str = "download_report.pdf"
    state_name: str = ".download_state.json"
    log_name: str = "agent_production.log"

    # --- المهلات (مُحسّنة لشبكات الإنترنت الضعيفة والمتقطعة) ---
    hard_timeout: int = 240        # أقصى زمن لمحاولة رابط واحد
    entry_budget: int = 600        # أقصى زمن إجمالي لورقة واحدة عبر كل مصادرها
    idle_timeout: int = 120        # زيادة مهلة انتظار تقدم التنزيل لتجنب إجهاض التحميل عند بطء الشبكة
    page_load_timeout: int = 90    # مهلة driver.get
    script_timeout: int = 180      # مهلة execute_async_script (الجلب داخل الصفحة)
    cf_auto_wait: int = 35         # انتظار حلّ Cloudflare تلقائياً قبل التدخّل

    # --- التنفيذ ---
    max_workers: int = 3
    max_retries: int = 3           # زيادة محاولات الإعادة عند التقطع
    skip_existing: bool = True
    per_domain_delay: float = 2.0  # تهذيب: أقل فاصل بين طلبين لنفس النطاق
    min_pdf_bytes: int = 8 * 1024  # أقل حجم مقبول لملف PDF سليم
    max_fetch_bytes: int = 80 * 1024 * 1024
    chunk_size: int = 64 * 1024    # 64 KB chunk size for resumable streaming
    unpaywall_email: str = "contact@example.com"

    # --- الميزات ---
    use_inpage_fetch: bool = True      # جلب البايتات داخل الصفحة (يرث كوكيز/جلسة Cloudflare)
    allow_html_fallback: bool = False  # ملغى: عدم حفظ واجهات HTML كـ PDF نهائياً (PDF حقيقي فقط)
    kill_msdt_watchdog: bool = True    # حارس نافذة تشخيص شبكة Windows
    solve_captcha_with_zai: bool = True
    dismiss_consent: bool = True       # إزالة لافتات الكوكيز التي تعترض النقر والتنزيل

    # --- بوابة «هل هذه صفحة بحث؟» (تُطبَّق قبل حفظ HTML كـ PDF) ---
    require_research_markers: bool = True   # لا تُحفظ صفحة إلا إذا كانت بحثاً فعلياً
    html_min_text_chars: int = 2500         # أقل طول نصّي مقبول لصفحة بحث كامل
    research_min_sections: int = 1          # أقسام أكاديمية إضافية مطلوبة (Methods/Results/…)
    research_min_gap: int = 800             # أقل نثر بين «Introduction» والقسم الذي يليه

    # --- الكابتشا / التحديات ---
    captcha_max_attempts: int = 2      # أقصى عدد محاولات حل تحدٍّ واحد
    zai_answer_timeout: int = 150      # أقصى انتظار لجواب Z.ai
    blocked_domain_cooldown: int = 900 # تجاهل نطاقاً حظرنا صراحةً (1015/1020) لهذه المدة

    # --- المتصفح ---
    chrome_debug_port: int = 9222
    chrome_profile: Optional[str] = None   # فرض بروفايل معيّن بدل السؤال
    z_ai_url: str = "https://z.ai/chat"
    ko_local_url: str = "http://127.0.0.1:7860"

    # يُملأ في main()
    base_dir: str = ""
    staging_dir: str = ""


config = AppConfig()
STOP = threading.Event()          # إيقاف تعاوني نظيف (Ctrl+C)


# ═════════════════════════ LOGGING ═════════════════════════
# ملاحظة: لا نستخدم الإيموجي في السجل — كونسول Windows (cp1256) يرفعه UnicodeEncodeError.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

log = logging.getLogger("downloader")


def setup_logging(base_dir: str) -> None:
    log.setLevel(logging.INFO)
    log.handlers.clear()
    fmt = logging.Formatter("%(asctime)s | %(threadName)-12s | %(levelname)-7s | %(message)s",
                            datefmt="%H:%M:%S")
    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(fmt)
    log.addHandler(sh)
    try:
        fh = logging.FileHandler(os.path.join(base_dir, config.log_name), encoding="utf-8")
        fh.setFormatter(logging.Formatter(
            "%(asctime)s | %(threadName)-12s | %(levelname)-7s | %(message)s"))
        log.addHandler(fh)
    except Exception as e:
        print(f"[!] تعذّر فتح ملف السجل: {e}")
    logging.getLogger("selenium").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)


# ═════════════ WINDOWS NETWORK-DIAGNOSTICS WATCHDOG ═════════════
class MsdtWatchdog(threading.Thread):
    """
    السبب الجذري لنافذة «Windows Network Diagnostics» صار مُصلحاً (انظر _bypass_robot_page).
    هذا الحارس خط دفاع ثانٍ فقط: إن فتحها أي شيء آخر يُنهي msdt.exe فوراً
    بدل أن تظل تعود كلما أغلقتها.
    """
    TARGETS = ("msdt.exe",)

    def __init__(self):
        super().__init__(name="msdt-guard", daemon=True)
        self.kills = 0

    def run(self):
        if sys.platform != "win32":
            return
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        while not STOP.wait(5.0):
            for proc in self.TARGETS:
                try:
                    r = subprocess.run(["taskkill", "/F", "/IM", proc, "/T"],
                                       capture_output=True, text=True, timeout=10,
                                       errors="ignore", creationflags=flags)
                    if r.returncode == 0:
                        self.kills += 1
                        log.warning(f"[Guard] أُغلقت نافذة تشخيص الشبكة ({proc}) تلقائياً.")
                except Exception:
                    pass


# ═════════════════════════ RETRY ═════════════════════════
# لا نعيد المحاولة على المهلة الصلبة (مضيعة للوقت) — فقط على الأخطاء العابرة.
TRANSIENT = ("idle timeout", "webdriver", "timeout waiting", "connection",
             "no such window", "target closed", "chrome not reachable",
             "stale element", "invalid session")


def _is_transient(reason: str) -> bool:
    r = (reason or "").lower()
    return any(t in r for t in TRANSIENT)


def retry_on_failure(max_retries: int = 2):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last = (False, "unknown")
            for attempt in range(max_retries):
                if STOP.is_set():
                    return False, "Aborted"
                try:
                    res = func(*args, **kwargs)
                except Exception as e:
                    res = (False, f"{type(e).__name__}: {e}")
                if isinstance(res, tuple) and res[0]:
                    return res
                last = res if isinstance(res, tuple) else (False, str(res))
                if attempt == max_retries - 1 or not _is_transient(last[1]):
                    return last
                wait = (2 ** attempt) + random.uniform(0, 1)
                log.warning(f"  محاولة {attempt + 1}/{max_retries} فشلت ({last[1]}). انتظار {wait:.1f}s ...")
                if STOP.wait(wait):
                    return False, "Aborted"
            return last
        return wrapper
    return decorator


# ═════════════════════════ FILE 0 PARSER ═════════════════════════
def _clean_url(u: str) -> str:
    return (u or "").strip().strip('"').strip("'").strip("»").strip().rstrip(").,;")


def _read_pdf_text(pdf_path: str) -> str:
    """يقرأ نص ملف 0 عبر PyMuPDF، ويرجع إلى pypdf عند غيابه."""
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(pdf_path)
        try:
            return "\n".join(page.get_text("text") for page in doc)
        finally:
            doc.close()
    except ImportError:
        pass
    except Exception as e:
        log.warning(f"PyMuPDF فشل ({e}) — سيتم تجربة pypdf.")
    try:
        import pypdf
        reader = pypdf.PdfReader(pdf_path)
        return "\n".join((pg.extract_text() or "") for pg in reader.pages)
    except ImportError:
        log.error("لا يوجد قارئ PDF. ثبّت أحدهما:  pip install pymupdf   أو   pip install pypdf")
    except Exception as e:
        log.error(f"تعذّرت قراءة ملف 0: {e}")
    return ""


def parse_entries(pdf_path: str) -> List[dict]:
    text = _read_pdf_text(pdf_path)
    if not text.strip():
        return []

    entries, blocks = [], re.split(r"(?m)^\s*(\d{1,4})\.[ \t]+", text)
    for i in range(1, len(blocks) - 1, 2):
        try:
            idx = int(blocks[i])
        except ValueError:
            continue
        content = blocks[i + 1]

        m = re.match(r"(.*?)(?:\n\s*Year:)", content, re.DOTALL)
        raw_title = m.group(1) if m else content.split("\n")[0]
        title = re.sub(r"(?i)\b(PREPRINT|HAS FULL TEXT|LINK-ONLY)\b", "", raw_title)
        title = re.sub(r"\s+", " ", title).strip()

        ym = re.search(r"Year:\s*(\d{4})", content)
        dm = re.search(r"DOI:\s*(\S+)", content)
        om = re.search(r"Open Access:\s*(\S+)", content)

        def _na(v: str) -> str:
            return "" if v.upper().strip("() ") in ("N/A", "NA", "-", "NONE", "") else v

        doi = _na(_clean_url(dm.group(1)) if dm else "")
        oa = _na(_clean_url(om.group(1)) if om else "")

        # [إصلاح] كانت المداخل بلا DOI وبلا Open Access تُحذف بصمت،
        # فيظهر «25 ورقة» في ملف 0 بينما يعالج السكربت 23 فقط بلا أي تفسير.
        # الآن تُدرج وتظهر في تقرير الفشل بسبب واضح.
        entries.append({
            "idx": idx,
            "title": title[:200] or f"paper_{idx}",
            "year": ym.group(1) if ym else "",
            "doi": doi,
            "oa_url": oa if oa.lower().startswith("http") else "",
        })

    seen, out = set(), []
    for e in entries:
        key = (e["idx"], e["doi"] or e["oa_url"])
        if key not in seen:
            seen.add(key)
            out.append(e)
    return out


def safe_filename(entry: dict) -> str:
    name = re.sub(r'[\\/*?:"<>|\r\n\t]', "_", entry.get("title", "paper")[:70]).strip(" .")
    return f"{entry.get('idx', 0):04d}_{name or 'paper'}.pdf"


def already_downloaded(entry: dict) -> Optional[Path]:
    """يبحث بالفهرس لا بالاسم — حتى لو تغيّر العنوان لا نُعيد التنزيل."""
    for h in glob.glob(os.path.join(config.output_dir, f"{entry['idx']:04d}_*.pdf")):
        p = Path(h)
        if p.is_file() and looks_like_pdf(p):
            return p
    return None


# ═════════════════════════ PDF VALIDATION ═════════════════════════
def looks_like_pdf(path: Path, min_bytes: Optional[int] = None) -> bool:
    """
    حصانة الإنتاج: كثير من «التنزيلات الناجحة» كانت في الحقيقة صفحات Cloudflare
    أو صفحات تسجيل دخول محفوظة بامتداد .pdf. نتحقق من التوقيع الحقيقي.
    """
    min_bytes = config.min_pdf_bytes if min_bytes is None else min_bytes
    try:
        if not path.is_file() or path.stat().st_size < min_bytes:
            return False
        with open(path, "rb") as f:
            head = f.read(2048)
        return b"%PDF" in head[:1024]
    except Exception:
        return False


def _pdf_bytes_ok(data: bytes) -> bool:
    return bool(data) and len(data) >= config.min_pdf_bytes and b"%PDF" in data[:1024]


# ═══════════════ RESEARCH-PAPER GATE (هل هذه صفحة بحث فعلاً؟) ═══════════════
# [إضافة حرِجة] النسخة السابقة كانت تحفظ أي صفحة HTML كـ PDF «ناجح» ما لم تكن
# صفحة خطأ أو حماية — فتنتهي بملفات هي صفحة ناشر أو صفحة اشتراك أو نتائج بحث،
# ويُحسب ذلك نجاحاً كاذباً لا يمكن كشفه إلا بفتح كل ملف يدوياً.
#
# المعيار المستخدم هو ما تتفق عليه الأبحاث المنشورة بالإنجليزية عملياً:
#   (1) عنوان Abstract  (أو Summary/Synopsis في قوالب Cell Press وغيرها)
#   (2) عنوان Introduction (أو Background في القوالب الطبية/BMC)
#   (3) قسم أكاديمي إضافي واحد على الأقل: Methods / Results / Discussion /
#       Conclusion / References / Keywords / Acknowledgements …
#   (4) طول نصّي معقول، ونصّ كافٍ *بعد* عنوان المقدمة — وهذا وحده يفرّق بين
#       صفحة البحث الكامل وصفحة «الملخص فقط» التي تسرد أسماء الأقسام في فهرس.
# ما لا يستوفي ذلك يُعتبر «غير متاح للتنزيل» ويُدرج في التقرير النهائي بسببه.

NOT_AVAILABLE = "غير متاح للتنزيل"   # بادئة موحَّدة تُميّز هذا السبب في التقرير

# كلمات الأقسام تُبحث كـ«عناوين» لا كأي ورود في النص: بداية سطر قصير، مع
# سماحٍ بترقيم عربي أو روماني. هذا وحده يمنع الخلط بين عنوان «Introduction»
# وجملةٍ داخل الملخص مثل «Introduction of chloride accelerated decay».
_HEAD_PREFIX = (r"(?m)^[\s•·\-–—>|*#]{0,6}(?=[^\n]{0,90}$)"
                r"(?:\d{1,2}(?:\.\d{1,2})*[.)]?\s*|[ivx]{1,4}[.)]\s*)?")


def _head(body: str) -> "re.Pattern":
    return re.compile(_HEAD_PREFIX + body + r"\b")


_ABSTRACT_RE = _head(r"(?:abstract|summary|synopsis)")
_INTRO_RE = _head(r"(?:introduction|background)")

# أقسام البحث البنيوية — تُحتسب كعناوين فقط
_SECTION_RES = (
    ("methods", _head(r"(?:materials?\s+and\s+methods|methodolog(?:y|ies)|methods?|"
                      r"experimental(?:\s+(?:section|procedures?))?|study\s+design|"
                      r"patients?\s+and\s+methods)")),
    ("results", _head(r"(?:results?|findings)")),
    ("discussion", _head(r"discussions?")),
    ("conclusion", _head(r"(?:conclusions?|concluding\s+remarks)")),
    ("references", _head(r"(?:references|bibliography|literature\s+cited|works\s+cited)")),
)

# قرائن علمية إضافية (أي موضع في النص) — للتسجيل والتشخيص لا للقبول وحدها
_HINT_RES = (
    ("keywords", re.compile(r"\bkey\s?words?\s*[:：]")),
    ("citation", re.compile(r"(?:\bet\s+al\b|\bdoi\s*:|doi\.org/10\.|"
                            r"\bcite\s+this\s+article\b|\bhow\s+to\s+cite\b)")),
    ("front", re.compile(r"\b(?:acknowledge?ments?|conflicts?\s+of\s+interest|"
                         r"author\s+contributions|data\s+availability|"
                         r"received\s+\d|accepted\s+\d|supplementary\s+material)\b")),
)

# سلبيات قاطعة: لا يمكن أن تكون صفحة بحث بحال
_HARD_NEGATIVE_RES = (
    (re.compile(r"\b(?:access\s+denied|403\s+forbidden|not\s+authori[sz]ed|"
                r"you\s+do\s+not\s+have\s+access)\b"), "صفحة ممنوعة (403/Access denied)"),
    (re.compile(r"\b(?:page\s+not\s+found|404\s+(?:error|not\s+found)|error\s+404|"
                r"the\s+requested\s+(?:page|url)\s+(?:was\s+)?(?:not\s+found|"
                r"could\s+not\s+be\s+found))\b"), "صفحة غير موجودة (404)"),
    (re.compile(r"\b(?:just\s+a\s+moment|enable\s+javascript\s+and\s+cookies|"
                r"verify\s+you\s+are\s+human|are\s+you\s+a\s+robot|"
                r"cloudflare\s+ray\s+id|checking\s+your\s+browser)\b"), "صفحة تحقق/حماية"),
    (re.compile(r"\b(?:this\s+site\s+can[’']?t\s+be\s+reached|err_)"), "صفحة خطأ شبكة"),
)

# سلبيات مرجَّحة: تُرفض بها الصفحة فقط إذا كانت الأدلة الإيجابية ناقصة،
# لأن كلمات مثل «Sign in» و«Purchase PDF» تظهر في ترويسة صفحات الوصول المفتوح أيضاً.
_SOFT_NEGATIVE_RES = (
    (re.compile(r"\b(?:purchase\s+(?:access|pdf|article)|buy\s+(?:this\s+)?article|"
                r"rent\s+this\s+article|add\s+to\s+cart|"
                r"subscribe\s+to\s+(?:this|the)\s+journal|"
                r"immediate\s+online\s+access|institutional\s+(?:login|access))\b"),
     "صفحة اشتراك/دفع"),
    (re.compile(r"\b(?:sign\s?in|log\s?in|create\s+an\s+account)\b[^.\n]{0,80}"
                r"\b(?:to\s+(?:continue|read|view|download|access)|is\s+required)\b"),
     "بوابة تسجيل دخول"),
    (re.compile(r"\b(?:search\s+results?|showing\s+\d+\s*(?:-|–|to)\s*\d+\s+of)\b"),
     "صفحة نتائج بحث"),
)


def _normalize_page_text(txt: str) -> Tuple[str, str]:
    """
    يرجع (نص مطبَّع، نص مطبَّع بحروف مفكوكة مضمومة).
    الثاني ضروري لأن قوالب Elsevier وSpringer تكتب العناوين متباعدة الحروف
    («A B S T R A C T») فلا يطابقها أي تعبير نمطي عادي.
    """
    low = (txt or "").lower().replace(" ", " ").replace("‏", " ")
    low = re.sub(r"[^\S\n]+", " ", low)
    despaced = re.sub(r"\b(?:[a-z] ){2,}[a-z]\b",
                      lambda m: m.group(0).replace(" ", ""), low)
    return low, despaced


def research_markers(txt: str) -> dict:
    """يحسب علامات البحث في نصّ صفحة — دالة نقيّة قابلة للاختبار وحدةً."""
    flat, despaced = _normalize_page_text(txt)
    both = (flat, despaced)

    def hit(rx) -> bool:
        return any(rx.search(s) for s in both)

    sections = [name for name, rx in _SECTION_RES if hit(rx)]
    hints = [name for name, rx in _HINT_RES if hit(rx)]

    # نصّ ما بعد عنوان المقدمة: يفرّق بين بحث كامل وصفحة تنتهي عند الملخص
    tail = 0
    # وأهمّ منه: مقدار النثر بين عنوان «المقدمة» وأول عنوان قسم بعده.
    # في البحث الكامل آلاف الحروف؛ وفي «فهرس الأقسام» على صفحة الاشتراك
    # يكون العنوانان متجاورين ببضع عشرات من الحروف — وهذا هو الفارق القاطع.
    gap = 0
    for s in both:
        starts = [m.end() for m in _INTRO_RE.finditer(s)]
        if not starts:
            continue
        tail = max(tail, len(s) - starts[-1])
        heads = sorted(m.start() for _, rx in _SECTION_RES for m in rx.finditer(s))
        for pos in starts:
            nxt = next((h for h in heads if h > pos), None)
            gap = max(gap, (nxt - pos) if nxt is not None else (len(s) - pos))

    hard = next((why for rx, why in _HARD_NEGATIVE_RES if hit(rx)), "")
    soft = next((why for rx, why in _SOFT_NEGATIVE_RES if hit(rx)), "")

    return {
        "chars": len(flat.strip()),
        "abstract": hit(_ABSTRACT_RE),
        "intro": hit(_INTRO_RE),
        "sections": sections,
        "hints": hints,
        "tail": tail,
        "gap": gap,
        "hard_negative": hard,
        "soft_negative": soft,
    }


def looks_like_research_text(txt: str) -> Tuple[bool, str]:
    """
    (مقبولة؟، السبب). أسباب الرفض تبدأ دائماً بـ NOT_AVAILABLE
    حتى يتعرّف عليها _download_attempt ويرفعها إلى التقرير النهائي كما هي.
    """
    m = research_markers(txt)
    min_tail = max(1000, config.html_min_text_chars // 2)

    def no(detail: str) -> Tuple[bool, str]:
        return False, f"{NOT_AVAILABLE} — {detail}"

    if m["hard_negative"]:
        return no(m["hard_negative"])
    if m["chars"] < config.html_min_text_chars:
        return no(f"محتوى الصفحة قصير ({m['chars']} حرف < {config.html_min_text_chars})")
    if not m["abstract"] and not m["intro"]:
        return no("الصفحة ليست بحثاً: لا Abstract ولا Introduction")
    if not m["abstract"]:
        return no("لا يوجد عنوان Abstract/Summary في الصفحة")
    if not m["intro"]:
        return no("لا يوجد عنوان Introduction/Background في الصفحة")
    if len(m["sections"]) < config.research_min_sections:
        return no("لا توجد عناوين أقسام أكاديمية "
                  "(Methods/Results/Discussion/Conclusions/References)")
    if m["tail"] < min_tail:
        return no(f"نصّ ما بعد المقدمة قصير ({m['tail']} حرف) — صفحة ملخص لا بحث كامل")
    if m["gap"] < config.research_min_gap:
        return no(f"لا نصّ بين «Introduction» والقسم التالي ({m['gap']} حرف) — "
                  f"فهرس أقسام على صفحة الناشر لا بحث كامل")

    # السلبيات المرجَّحة تُرفض بها الصفحة إلا إذا كانت أدلة النص الكامل قاطعة:
    # صفحة الاشتراك النموذجية تحتوي ملخصاً وفهرس أقسام ثم دعوة للشراء، لكنها
    # لا تحتوي أبداً نصاً كاملاً بعدة أقسام وبهذا الحجم.
    strong_full_text = (len(m["sections"]) >= 3
                        and m["chars"] >= config.html_min_text_chars * 3
                        and m["gap"] >= config.research_min_gap * 2)
    if m["soft_negative"] and not strong_full_text:
        return no(f"{m['soft_negative']} — نصّ البحث الكامل غير معروض")

    return True, (f"صفحة بحث (chars={m['chars']}, gap={m['gap']}, "
                  f"sections={'+'.join(m['sections'][:4]) or '-'}"
                  f"{', hints=' + '+'.join(m['hints']) if m['hints'] else ''})")


# ═════════════════════════ DOMAIN THROTTLE ═════════════════════════
class DomainThrottle:
    """فاصل زمني بسيط لكل نطاق — يقلّل حظر المعدّل ويبدو أقرب لسلوك بشري."""
    def __init__(self):
        self._last, self._lock = {}, threading.Lock()

    def wait(self, url: str):
        try:
            host = urlparse(url).netloc.lower()
        except Exception:
            return
        if not host:
            return
        with self._lock:
            prev = self._last.get(host, 0.0)
            delta = time.time() - prev
            sleep_for = max(0.0, config.per_domain_delay - delta)
            self._last[host] = time.time() + sleep_for
        if sleep_for > 0:
            STOP.wait(sleep_for)


throttle = DomainThrottle()


class DomainCooldown:
    """
    [إضافة إنتاجية] عندما يردّ Cloudflare بحظر نهائي (Error 1015 تجاوز معدّل،
    1020 قاعدة وصول، «Sorry, you have been blocked») فلا يوجد تحدٍّ يُحل أصلاً.
    النسخة السابقة كانت تنتظر 25 ثانية ثم تنقر ثم تُشغّل Z.ai لثلاث دقائق لكل
    ورقة على نفس النطاق المحظور. هنا نُعلّم النطاق ونتجاوزه فوراً لبقية التشغيل.
    """
    def __init__(self):
        self._until, self._lock = {}, threading.Lock()

    @staticmethod
    def _host(url: str) -> str:
        try:
            return urlparse(url).netloc.lower()
        except Exception:
            return ""

    def block(self, url: str, seconds: Optional[int] = None) -> None:
        host = self._host(url)
        if not host:
            return
        secs = config.blocked_domain_cooldown if seconds is None else seconds
        with self._lock:
            fresh = self._until.get(host, 0.0) < time.time()
            self._until[host] = time.time() + secs
        if fresh:
            log.warning(f"  [CF] النطاق {host} يحظرنا صراحةً — تجاهله لـ {secs // 60} دقيقة.")

    def blocked(self, url: str) -> bool:
        host = self._host(url)
        if not host:
            return False
        with self._lock:
            return self._until.get(host, 0.0) > time.time()


cooldown = DomainCooldown()


# ═════════════════════════ STAGING CLAIMER ═════════════════════════
class StagingClaimer:
    """
    بعض التنزيلات (خصوصاً الانتقال المباشر لرابط .pdf) ينسبها Chrome للمتصفح
    لا للصفحة، فتهبط في مجلد التنزيل الافتراضي بدل مجلد التبويب المؤقت.

    [سلامة البيانات] لا يمكن نسب ملف في هذا المجلد إلى محاولة بعينها بيقين.
    لذلك لا نلتقط منه إلا إذا كانت هناك محاولة واحدة نشطة فقط — وإلا فقد
    تُحفظ ورقة تحت اسم ورقة أخرى عند التشغيل المتوازي. هذا أخطر من فشل التنزيل.
    """
    def __init__(self):
        self._claimed = set()
        self._lock = threading.Lock()
        self._inflight = 0

    def enter(self):
        with self._lock:
            self._inflight += 1

    def leave(self):
        with self._lock:
            self._inflight = max(0, self._inflight - 1)

    def claim(self, since_ts: float, entry: Optional[dict] = None) -> Optional[Path]:
        d = Path(config.staging_dir)
        if not d.is_dir():
            return None
        with self._lock:
            try:
                cands = [f for f in d.iterdir()
                         if f.is_file()
                         and not f.name.endswith((".crdownload", ".tmp", ".partial"))
                         and str(f) not in self._claimed
                         and f.stat().st_mtime >= since_ts - 2
                         and looks_like_pdf(f)]
            except Exception:
                return None
            if not cands:
                return None

            if self._inflight > 1:
                # عند التوازي: نتحقق من مطابقة معرّف DOI أو كلمات العنوان لنسب الملف بدقة
                if not entry:
                    return None
                doi_tail = (entry.get("doi") or "").split("/")[-1].lower()
                doi_clean = re.sub(r"[^a-zA-Z0-9_-]", "", doi_tail)
                title_words = [w.lower() for w in re.split(r"\W+", entry.get("title", "")) if len(w) >= 4]
                matched = []
                for c in cands:
                    c_low = c.name.lower()
                    if doi_clean and len(doi_clean) >= 4 and doi_clean in c_low:
                        matched.append(c)
                    elif title_words and sum(1 for w in title_words[:4] if w in c_low) >= 2:
                        matched.append(c)
                if matched:
                    best = max(matched, key=lambda f: f.stat().st_mtime)
                    self._claimed.add(str(best))
                    log.info(f"  [Staging] تم التقاط ملف مطابق لمعرف البحث: {best.name}")
                    return best
                return None      # لم يتطابق اسم الملف يقيناً مع هذه المهمة

            best = max(cands, key=lambda f: f.stat().st_mtime)
            self._claimed.add(str(best))
            return best

    def has_activity(self, since_ts: float) -> bool:
        d = Path(config.staging_dir)
        try:
            return any(f.name.endswith(".crdownload") and f.stat().st_mtime >= since_ts - 2
                       for f in d.iterdir() if f.is_file())
        except Exception:
            return False


staging = StagingClaimer()


# ═════════════════════════ BROWSER MANAGER ═════════════════════════
class BrowserManager:
    def __init__(self):
        self._local = threading.local()
        self.drivers = []
        self._iso_dirs = []
        self.lock = threading.Lock()

    # ---------- اكتشاف Chrome ----------
    @staticmethod
    def _find_chrome() -> Optional[str]:
        paths = [
            os.environ.get("CHROME_PATH", ""),
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            os.path.join(os.environ.get("LOCALAPPDATA", ""), r"Google\Chrome\Application\chrome.exe"),
            r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
            r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
            os.path.join(os.environ.get("LOCALAPPDATA", ""), r"Microsoft\Edge\Application\msedge.exe"),
            "/usr/bin/google-chrome", "/usr/bin/google-chrome-stable", "/usr/bin/chromium",
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        ]
        return next((p for p in paths if p and os.path.exists(p)), None)

    # ---------- الحصول على driver لكل خيط ----------
    def get_driver(self, base_dir: str = "") -> Optional[webdriver.Chrome]:
        drv = getattr(self._local, "driver", None)
        if drv is not None:
            try:
                _ = drv.current_window_handle
                return drv
            except Exception:
                self._local.driver = None
                self._local.home = None

        with self.lock:
            try:
                opts = Options()
                cp = self._find_chrome()
                if cp and os.path.exists(cp):
                    opts.binary_location = cp

                opts.add_argument("--headless=new")
                opts.add_argument("--disable-gpu")
                opts.add_argument("--mute-audio")
                opts.add_argument("--no-sandbox")
                opts.add_argument("--disable-dev-shm-usage")
                opts.add_argument("--disable-blink-features=AutomationControlled")
                opts.add_argument("--no-first-run")
                opts.add_argument("--no-default-browser-check")
                opts.add_argument("--disable-extensions")
                opts.add_argument("--disable-popup-blocking")

                iso_dir = os.path.join(tempfile.gettempdir(), f".ko_chr_{os.getpid()}_{threading.get_ident()}_{random.randint(1000, 9999)}")
                os.makedirs(iso_dir, exist_ok=True)
                self._iso_dirs.append(iso_dir)
                opts.add_argument(f"--user-data-dir={iso_dir}")

                opts.add_experimental_option("prefs", {
                    "download.default_directory": config.staging_dir,
                    "download.prompt_for_download": False,
                    "download.directory_upgrade": True,
                    "plugins.always_open_pdf_externally": True,
                    "profile.default_content_settings.popups": 0,
                    "profile.content_settings.exceptions.automatic_downloads.*.setting": 1
                })

                driver = webdriver.Chrome(options=opts)
                driver.set_page_load_timeout(config.page_load_timeout)
                driver.set_script_timeout(config.script_timeout)

                try:
                    driver.execute_cdp_cmd("Page.setDownloadBehavior", {
                        "behavior": "allow",
                        "downloadPath": config.staging_dir
                    })
                except Exception:
                    pass

                driver.get("about:blank")
                self._local.home = driver.current_window_handle
                self._local.driver = driver
                self.drivers.append(driver)
                log.info(f"[Chrome] تم تشغيل متصفح خفي نظيف وآمن بنجاح.")
                return driver
            except Exception as e:
                log.warning(f"تعذر تهيئة WebDriver الخلفي: {e}")
                return None

    def home_handle(self) -> Optional[str]:
        return getattr(self._local, "home", None)

    def quit_all(self) -> None:
        with self.lock:
            for driver in self.drivers:
                try:
                    driver.quit()
                except Exception:
                    pass
            self.drivers.clear()
            if hasattr(self._local, "driver"):
                self._local.driver = None
            if hasattr(self._local, "home"):
                self._local.home = None
            for p in self._iso_dirs:
                try:
                    shutil.rmtree(p, ignore_errors=True)
                except Exception:
                    pass
            self._iso_dirs.clear()


browser_manager = BrowserManager()
atexit.register(browser_manager.quit_all)


# ═════════════════════════ HUMAN MOUSE ═════════════════════════
class HumanMouse:
    """
    مهم: Input.dispatchMouseEvent يتوقّع إحداثيات CSS بالنسبة لإطار العرض (viewport).
    النسخة القديمة كانت تمرّر element.rect (إحداثيات المستند مع التمرير) فيقع النقر
    في مكان خاطئ تماماً على الصفحات الطويلة — وهو أحد أسباب فشل تجاوز Cloudflare.
    """
    @staticmethod
    def viewport_rect(driver, element) -> Optional[dict]:
        try:
            driver.execute_script(
                "arguments[0].scrollIntoView({block:'center', inline:'center'});", element)
            time.sleep(0.25)
            return driver.execute_script("""
                const r = arguments[0].getBoundingClientRect();
                return {x:r.left, y:r.top, w:r.width, h:r.height};
            """, element)
        except Exception:
            return None

    @staticmethod
    def move_and_click(driver, x: float, y: float) -> bool:
        try:
            sx, sy = x + random.uniform(-160, 160), y + random.uniform(-120, 120)
            steps = random.randint(14, 22)
            for i in range(1, steps + 1):
                t = i / steps
                ease = t * t * (3 - 2 * t)                       # منحنى تسارع/تباطؤ
                cx = sx + (x - sx) * ease + random.uniform(-2.5, 2.5)
                cy = sy + (y - sy) * ease + random.uniform(-2.5, 2.5)
                driver.execute_cdp_cmd("Input.dispatchMouseEvent", {
                    "type": "mouseMoved", "x": cx, "y": cy,
                    "button": "none", "buttons": 0, "modifiers": 0,
                    "pointerType": "mouse",
                })
                time.sleep(random.uniform(0.008, 0.03))
            time.sleep(random.uniform(0.10, 0.25))
            for evt, buttons in (("mousePressed", 1), ("mouseReleased", 0)):
                driver.execute_cdp_cmd("Input.dispatchMouseEvent", {
                    "type": evt, "x": x, "y": y, "button": "left",
                    "buttons": buttons, "clickCount": 1, "modifiers": 0,
                    "pointerType": "mouse",
                })
                if evt == "mousePressed":
                    time.sleep(random.uniform(0.06, 0.15))
            return True
        except Exception as e:
            log.debug(f"[Mouse] {e}")
            return False

    @classmethod
    def click_element(cls, driver, element, dx: Optional[float] = None,
                      dy: Optional[float] = None) -> bool:
        r = cls.viewport_rect(driver, element)
        if not r or r["w"] <= 0 or r["h"] <= 0:
            return False
        x = r["x"] + (dx if dx is not None else r["w"] / 2)
        y = r["y"] + (dy if dy is not None else r["h"] / 2)
        return cls.move_and_click(driver, x, y)


# ═════════════════════════ PAGE STATE ═════════════════════════
CF_MARKERS = (
    "just a moment", "checking your browser", "performing security verification",
    "verify you are human", "لحظة من فضلك", "cf-chl", "challenge-platform",
    "attention required", "enable javascript and cookies",
)
CF_IFRAME_XPATH = (
    "//iframe[contains(@src,'challenges.cloudflare.com')]"
    " | //iframe[contains(@title,'Cloudflare')]"
    " | //iframe[contains(@title,'challenge')]"
    " | //iframe[contains(@src,'recaptcha')]"
    " | //iframe[contains(@src,'hcaptcha')]"
    " | //iframe[contains(@src,'turnstile')]"
    " | //iframe[contains(@src,'geo.captcha-delivery.com')]"
)

# زرّ «Verify you are human» يظهر أحياناً في المستند نفسه لا داخل إطار
CF_VERIFY_XPATH = (
    "//input[@type='checkbox' and (contains(@id,'challenge') or contains(@name,'cf'))]"
    " | //button[contains(translate(.,'VERIFYHUMAN','verifyhuman'),'verify')]"
    " | //a[contains(translate(.,'VERIFYHUMAN','verifyhuman'),'verify you are human')]"
)

# حظر نهائي من Cloudflare — لا يوجد تحدٍّ يُحل، فالانتظار والنقر مضيعة كاملة
CF_BLOCKED_MARKERS = (
    "sorry, you have been blocked", "you have been blocked",
    "you are unable to access", "error 1015", "error 1020", "error 1006",
    "error 1010", "error 1012", "access denied | ", "rate limited",
    "banned from accessing", "this website is using a security service to protect",
)


def is_error_page(driver) -> bool:
    """
    صفحات أخطاء Chrome الحقيقية مع تخطٍّ تلقائي لتحذيرات شهادات SSL (NET::ERR_CERT).
    """
    try:
        # 1. فحص شاشة التحذير الأمني "الاتصال ليس خاصاً" (Your connection is not private) وتجاوزها فوراً
        try:
            interstitial = driver.execute_script("""
                const p = document.getElementById('proceed-link');
                if (p) { p.click(); return 'proceed'; }
                const d = document.getElementById('details-button');
                if (d) {
                    d.click();
                    const p2 = document.getElementById('proceed-link');
                    if (p2) { p2.click(); return 'proceed'; }
                    return 'details';
                }
                return null;
            """)
            if interstitial:
                log.info("  [SSL Security] تم تجاوز شاشة تحذير الشهادة الأمنية (NET::ERR_CERT) تلقائياً.")
                time.sleep(1.5)
                return False
        except Exception:
            pass

        u = (driver.current_url or "").lower()
        if u.startswith(("chrome-error://", "chrome://network-error", "edge-error://")):
            return True
        return bool(driver.execute_script("""
            // إذا كانت صفحة تحذير شهادة تحتوي على زر الإعدادات المتقدمة فلا نعتبرها خطأ شبكة قاتلاً
            if (document.getElementById('details-button') || document.getElementById('proceed-link')) {
                return false;
            }
            return !!(document.querySelector('#main-frame-error, #diagnose-button, .neterror')
                   || document.documentElement.classList.contains('neterror'));
        """))
    except Exception:
        return False


def is_cloudflare(driver) -> bool:
    # الحظر النهائي ليس تحدياً: لو عاملناه كتحدٍّ لأهدرنا كل ميزانية الورقة
    if is_blocked_page(driver):
        return False
    try:
        title = (driver.title or "").lower()
        if any(m in title for m in CF_MARKERS):
            return True
        return bool(driver.execute_script("""
            const t = (document.body ? document.body.innerText : '').slice(0, 4000).toLowerCase();
            const m = ['just a moment','verify you are human','checking your browser',
                       'performing security verification','enable javascript and cookies',
                       'needs to review the security of your connection'];
            if (m.some(s => t.includes(s))) return true;
            return !!document.querySelector(
              '#challenge-running, #challenge-stage, #cf-challenge-running, .cf-turnstile, ' +
              '[id^="cf-chl-widget"], iframe[src*="challenges.cloudflare.com"], ' +
              'iframe[src*="turnstile"], #captcha-container, #px-captcha');
        """))
    except Exception:
        return False


def is_blocked_page(driver) -> bool:
    """
    [إضافة] حظر Cloudflare/WAF النهائي: 1015 (تجاوز معدّل)، 1020 (قاعدة وصول)،
    «Sorry, you have been blocked». لا يوجد مربّع تحقق ولا كابتشا — فقط رفض.
    """
    try:
        blob = driver.execute_script("""
            const t = ((document.body ? document.body.innerText : '') || '').slice(0, 3000);
            const code = document.querySelector('.cf-error-code, #cf-error-details .cf-error-code');
            return ((document.title || '') + ' \\n ' + t + ' \\n ' +
                    (code ? code.innerText : '')).toLowerCase();
        """) or ""
    except Exception:
        return False
    if not blob:
        return False
    if any(m in blob for m in CF_BLOCKED_MARKERS):
        # «attention required» وحدها لا تكفي: صفحة التحدي تستعملها أيضاً
        return not any(m in blob for m in ("just a moment", "checking your browser",
                                           "verify you are human"))
    return False


# ═════════════════════════ Z.AI CAPTCHA SOLVER ═════════════════════════
# الفكرة نفسها (لقطة للتحدي → Z.ai → إحداثيات → نقر بشري) لكن بثلاث إضافات
# تصنع الفرق بين «يعمل أحياناً» و«جاهز للإنتاج»:
#   1) اللقطة تُقصّ على إطار التحدي فقط عبر CDP، والإحداثيات الراجعة تُحوّل
#      بمعامل محسوب فعلياً (لا افتراض ×1) — النسخة السابقة كانت تُرسل لقطة
#      الصفحة كاملة، فيصف Z.ai نقاطاً في نصف الصفحة الخطأ.
#   2) تُقرأ *تعليمة* التحدي («Select all images with …» / «اختر كل الصور التي …»)
#      وتُرسل إلى Z.ai. بدونها لا يعرف النموذج ما المطلوب اختياره أصلاً،
#      وهذا كان السبب الجذري لفشل اختبارات الصور المتعددة.
#   3) لتحديات الشبكة نطلب *أرقام بلاطات* لا إحداثيات بكسل، ونحسب مراكز
#      البلاطات من DOM بأنفسنا — فتصبح دقة النقر مضمونة لا تخميناً — ثم
#      نضغط زر التحقق داخل الإطار.

# نمنع إهدار 3 دقائق لكل ورقة إذا كان Z.ai نفسه غير متاح (جدار تسجيل دخول مثلاً)
_ZAI_STATE = {"disabled": False, "reason": ""}
_ZAI_LOCK = threading.Lock()


def _zai_disable(reason: str) -> None:
    with _ZAI_LOCK:
        if not _ZAI_STATE["disabled"]:
            _ZAI_STATE["disabled"] = True
            _ZAI_STATE["reason"] = reason
            log.warning(f"  [Z.ai] تعطيل حلّ الكابتشا لبقية التشغيل: {reason}")


def _zai_ready() -> bool:
    return config.solve_captcha_with_zai and not _ZAI_STATE["disabled"]


# محدِّدات شبكات الصور وتعليماتها وأزرار التحقق (Cloudflare / reCAPTCHA / hCaptcha)
TILE_SELECTORS = [
    "td.rc-imageselect-tile", ".rc-imageselect-tile",
    ".task-image", ".challenge-grid > div", ".image-grid > div",
    "[class*='task-image']", ".captcha-grid > *", ".challenge-container .task",
    "table td img", ".grid-cell",
]
INSTRUCTION_SELECTORS = [
    ".rc-imageselect-desc-wrapper", ".rc-imageselect-desc", ".rc-imageselect-desc-no-canonical",
    ".prompt-text", "[class*='prompt']", ".challenge-prompt", ".task-text",
    "h1", "h2", "legend", "label",
]
SUBMIT_SELECTORS = [
    "#recaptcha-verify-button", "button.rc-button-default", ".button-submit",
    "#checkbox-submit", "button[type='submit']", "input[type='submit']",
    ".challenge-verify", "button",
]
CHECKBOX_SELECTORS = [
    "input[type='checkbox']", "#challenge-stage input", ".cb-lb", ".cb-i",
    ".ctp-checkbox-label", "label", "#checkbox",
]
# كلمات تدل على أنّ التحدي «اختيار صور» لا مجرّد مربّع تأشير
CHOICE_WORDS = ("select all", "select each", "choose all", "click on all", "click each",
                "pick all", "click verify once", "اختر", "اختيار", "انقر على", "حدد",
                "выберите", "seleccione", "sélectionnez", "wählen")


def _png_size(data: bytes) -> Tuple[int, int]:
    """أبعاد PNG من ترويسة IHDR — بلا أي اعتماد على Pillow."""
    try:
        if data[:8] == b"\x89PNG\r\n\x1a\n":
            return (int.from_bytes(data[16:20], "big"), int.from_bytes(data[20:24], "big"))
    except Exception:
        pass
    return (0, 0)


def _clip_screenshot(driver, rect: dict) -> Tuple[Optional[bytes], float]:
    """
    لقطة مقصوصة على منطقة التحدي وحدها + معامل التحويل الحقيقي
    (بكسلات الصورة ÷ بكسلات CSS). clip في CDP بإحداثيات المستند، لذا نضيف التمرير.
    """
    try:
        scroll = driver.execute_script(
            "return [window.scrollX || 0, window.scrollY || 0];") or [0, 0]
        pad = 6.0
        w = max(20.0, rect["w"] + pad * 2)
        h = max(20.0, rect["h"] + pad * 2)
        res = driver.execute_cdp_cmd("Page.captureScreenshot", {
            "format": "png",
            "captureBeyondViewport": False,
            "clip": {"x": max(0.0, rect["x"] - pad + float(scroll[0])),
                     "y": max(0.0, rect["y"] - pad + float(scroll[1])),
                     "width": w, "height": h, "scale": 1},
        })
        data = base64.b64decode(res["data"])
        img_w, _ = _png_size(data)
        ratio = (img_w / w) if (img_w and w) else 1.0
        if not (0.2 < ratio < 6):
            ratio = 1.0
        # الأصل الذي تُحسب منه إحداثيات الصورة (بإحداثيات إطار العرض)
        return data, ratio
    except Exception as e:
        log.debug(f"  [Captcha] فشلت اللقطة المقصوصة: {type(e).__name__}: {e}")
        return None, 1.0


def _frame_probe(driver, iframe, base: dict) -> dict:
    """
    يفحص داخل إطار التحدي: بلاطات الصور + نصّ التعليمة، ويُرجع الإحداثيات
    محوّلةً إلى إطار العرض العلوي (وهو ما يتوقّعه Input.dispatchMouseEvent).
    """
    out = {"rects": [], "instr": "", "cols": 0}
    try:
        driver.switch_to.default_content()
        driver.switch_to.frame(iframe)
        data = driver.execute_script(r"""
            const tsel = arguments[0], isel = arguments[1];
            let tiles = [];
            for (const s of tsel) {
              try {
                const els = Array.from(document.querySelectorAll(s));
                const vis = els.filter(e => { const r = e.getBoundingClientRect();
                                              return r.width > 24 && r.height > 24; });
                if (vis.length >= 4) { tiles = vis; break; }
              } catch (e) {}
            }
            const rects = tiles.map(e => { const r = e.getBoundingClientRect();
                                           return {x:r.left, y:r.top, w:r.width, h:r.height}; });
            let instr = '';
            for (const s of isel) {
              try {
                const e = document.querySelector(s);
                const t = e && e.innerText ? e.innerText.trim() : '';
                if (t.length > 5 && t.length < 300) { instr = t; break; }
              } catch (e) {}
            }
            const body = (document.body ? document.body.innerText : '') || '';
            return {rects: rects, instr: instr || body.slice(0, 300)};
        """, TILE_SELECTORS, INSTRUCTION_SELECTORS) or {}
        rects = [r for r in (data.get("rects") or [])
                 if isinstance(r, dict) and r.get("w", 0) > 24 and r.get("h", 0) > 24]
        # تحويل من إحداثيات الإطار إلى إحداثيات النافذة
        out["rects"] = [{"x": r["x"] + base["x"], "y": r["y"] + base["y"],
                         "w": r["w"], "h": r["h"]} for r in rects]
        out["instr"] = (data.get("instr") or "").strip()
    except Exception as e:
        log.debug(f"  [Captcha] فحص الإطار: {type(e).__name__}: {e}")
    finally:
        try:
            driver.switch_to.default_content()
        except Exception:
            pass
    out["rects"], out["cols"] = _order_tiles(out["rects"])
    return out


def _order_tiles(rects: List[dict]) -> Tuple[List[dict], int]:
    """ترتيب البلاطات من اليسار لليمين ثم من الأعلى للأسفل + عدد الأعمدة."""
    if not rects:
        return [], 0
    tol = max(8.0, min(r["h"] for r in rects) * 0.5)
    rows: List[List[dict]] = []
    for r in sorted(rects, key=lambda q: q["y"]):
        for row in rows:
            if abs(row[0]["y"] - r["y"]) <= tol:
                row.append(r)
                break
        else:
            rows.append([r])
    ordered, cols = [], 0
    for row in rows:
        row.sort(key=lambda q: q["x"])
        cols = max(cols, len(row))
        ordered.extend(row)
    return ordered, cols


def _frame_click(driver, iframe, base: dict, selectors: List[str],
                 texts: Tuple[str, ...] = ()) -> bool:
    """
    نقرة بشرية على عنصر داخل إطار — بإحداثيات النافذة الصحيحة.
    iframe=None يعني أنّ التحدي في المستند نفسه، فالإحداثيات جاهزة بلا إزاحة.
    """
    off = {"x": 0.0, "y": 0.0} if iframe is None else base
    try:
        driver.switch_to.default_content()
        if iframe is not None:
            driver.switch_to.frame(iframe)
        r = driver.execute_script(r"""
            const sels = arguments[0], words = arguments[1];
            const vis = (e) => { const b = e.getBoundingClientRect();
                                 return b.width > 8 && b.height > 8 &&
                                        getComputedStyle(e).visibility !== 'hidden'; };
            for (const s of sels) {
              let els = [];
              try { els = Array.from(document.querySelectorAll(s)); } catch (e) { continue; }
              for (const e of els) {
                if (!vis(e)) continue;
                if (words.length) {
                  const t = ((e.innerText || '') + ' ' + (e.value || '')).toLowerCase();
                  if (!words.some(w => t.includes(w))) continue;
                }
                const b = e.getBoundingClientRect();
                return {x: b.left, y: b.top, w: b.width, h: b.height};
              }
            }
            return null;
        """, selectors, [t.lower() for t in texts])
    except Exception:
        r = None
    finally:
        try:
            driver.switch_to.default_content()
        except Exception:
            pass
    if not r:
        return False
    return HumanMouse.move_and_click(driver,
                                    off["x"] + r["x"] + r["w"] / 2,
                                    off["y"] + r["y"] + r["h"] / 2)


def _parse_json_answer(ans: str):
    """Z.ai قد يردّ بسياج ```json أو بكائن {"tiles":[…]} — نقبل كل الصيغ."""
    if not ans:
        return None
    txt = re.sub(r"```[a-z]*", "", ans).replace("```", "")
    for pat in (r"\{[\s\S]*\}", r"\[[\s\S]*\]"):
        m = re.search(pat, txt)
        if not m:
            continue
        try:
            obj = json.loads(m.group())
        except Exception:
            continue
        if isinstance(obj, dict):
            for k in ("tiles", "points", "indices", "cells", "answer", "result"):
                if isinstance(obj.get(k), list):
                    return obj[k]
            continue
        return obj
    nums = re.findall(r"\b\d{1,2}\b", txt)
    return [int(n) for n in nums[:12]] if nums else None


class CaptchaSolver:
    """يبقى كما هو فكرةً: لقطة للتحدي → Z.ai → إحداثيات نقر → نقر بشري."""
    z_ai_lock = threading.Lock()

    def _ask_z_ai(self, drv, prompt: str, image_path: str) -> str:
        if not _zai_ready():
            return ""
        with self.z_ai_lock:
            original = drv.current_window_handle
            zai_handle = None
            try:
                drv.switch_to.new_window("tab")
                zai_handle = drv.current_window_handle
                try:
                    drv.get(config.z_ai_url)
                except TimeoutException:
                    pass

                # جدار تسجيل دخول أو صفحة غير متاحة → تعطيل نهائي بدل الانتظار
                gate = (drv.execute_script(
                    "return ((document.body?document.body.innerText:'')||'')"
                    ".slice(0,600).toLowerCase();") or "")
                if not drv.find_elements(By.XPATH, "//input[@type='file']") and any(
                        k in gate for k in ("sign in", "log in", "sign up", "unavailable",
                                            "not available in your", "تسجيل الدخول")):
                    _zai_disable("Z.ai يطلب تسجيل دخول أو غير متاح")
                    return ""

                file_input = WebDriverWait(drv, 25).until(
                    EC.presence_of_element_located((By.XPATH, "//input[@type='file']")))
                drv.execute_script(
                    "arguments[0].style.display='block';arguments[0].style.visibility='visible';",
                    file_input)
                file_input.send_keys(image_path)
                time.sleep(2.5)

                box = WebDriverWait(drv, 25).until(EC.presence_of_element_located(
                    (By.XPATH, "//textarea | //div[@contenteditable='true']")))
                box.send_keys(prompt)
                time.sleep(0.6)
                box.send_keys(Keys.ENTER)

                prev, stable = "", 0
                deadline = time.time() + config.zai_answer_timeout
                while time.time() < deadline and not STOP.is_set():
                    time.sleep(1.0)
                    msgs = drv.find_elements(
                        By.XPATH, "//div[contains(@class,'message') or contains(@class,'markdown')]"
                                  " | //pre")
                    if not msgs:
                        continue
                    cur = msgs[-1].text
                    # لا نقبل ثباتاً على نصّ بلا أرقام: الجواب المطلوب رقمي دائماً
                    if cur == prev and len(cur) > 5 and re.search(r"\d", cur):
                        stable += 1
                        if stable >= 4:
                            return cur
                    else:
                        stable, prev = 0, cur
                return prev
            except TimeoutException:
                _zai_disable("لم تُعثر على حقل الرفع/الإدخال في Z.ai")
                return ""
            except Exception as e:
                log.warning(f"  [Z.ai] {type(e).__name__}: {e}")
                return ""
            finally:
                # [إصلاح] النسخة القديمة كانت تعود للتبويب الأصلي قبل finally
                # فلا يتحقق شرط الإغلاق → تتراكم تبويبات Z.ai بلا نهاية.
                try:
                    if zai_handle and zai_handle in drv.window_handles:
                        drv.switch_to.window(zai_handle)
                        drv.close()
                except Exception:
                    pass
                try:
                    if original in drv.window_handles:
                        drv.switch_to.window(original)
                except Exception:
                    pass

    @staticmethod
    def _png_width(data: bytes) -> int:
        return _png_size(data)[0]

    # ---------- تحدي شبكة الصور: «اختر كل الصور التي …» ----------
    def _solve_grid(self, driver, iframe, base: dict, probe: dict, temp_dir: str) -> bool:
        rects, cols = probe["rects"], max(1, probe["cols"])
        rows = (len(rects) + cols - 1) // cols
        png, ratio = _clip_screenshot(driver, base)
        if not png:
            return False
        img_path = os.path.join(temp_dir, f"grid_{uuid.uuid4().hex[:6]}.png")
        with open(img_path, "wb") as f:
            f.write(png)

        instr = re.sub(r"\s+", " ", probe["instr"])[:220]
        prompt = (
            "This image is an image-selection bot check. "
            f"The tiles form a {rows}x{cols} grid, numbered 1..{len(rects)} "
            "left-to-right then top-to-bottom. "
            f"The instruction shown to the user is: \"{instr}\". "
            "Decide which tiles satisfy that instruction. "
            "Return ONLY a JSON array of the matching tile numbers, e.g. [1,4,7]. "
            "No prose, no markdown, no explanation. "
            "If none match, return []."
        )
        ans = self._ask_z_ai(driver, prompt, img_path)
        picks = _parse_json_answer(ans)
        if not isinstance(picks, list):
            log.warning("  [Captcha] جواب Z.ai غير قابل للتحليل.")
            return False

        idxs, seen = [], set()
        for p in picks:
            try:
                n = int(p if not isinstance(p, dict) else p.get("index", 0))
            except Exception:
                continue
            if 1 <= n <= len(rects) and n not in seen:
                seen.add(n)
                idxs.append(n)
        if not idxs:
            log.info("  [Captcha] لم يُرشَّح أي بلاطة — سنجرّب زر التحقق مباشرة.")
        else:
            log.info(f"  [Captcha] بلاطات مختارة: {idxs}")

        for n in idxs[:12]:
            r = rects[n - 1]
            HumanMouse.move_and_click(driver, r["x"] + r["w"] / 2, r["y"] + r["h"] / 2)
            STOP.wait(random.uniform(0.35, 0.9))

        STOP.wait(1.0)
        _frame_click(driver, iframe, base, SUBMIT_SELECTORS,
                     ("verify", "submit", "next", "skip", "continue", "تحقق", "تأكيد"))
        return True

    # ---------- تحدٍّ حرّ: إحداثيات بكسل داخل منطقة التحدي ----------
    def _solve_points(self, driver, iframe, base: dict, probe: dict, temp_dir: str) -> bool:
        png, ratio = _clip_screenshot(driver, base)
        if not png:
            png = driver.get_screenshot_as_png()
            iw = float(driver.execute_script("return window.innerWidth;") or 0)
            img_w = _png_size(png)[0]
            ratio = (img_w / iw) if (img_w and iw) else 1.0
            origin = {"x": 0.0, "y": 0.0}
        else:
            origin = {"x": base["x"] - 6.0, "y": base["y"] - 6.0}
        img_path = os.path.join(temp_dir, f"captcha_{uuid.uuid4().hex[:6]}.png")
        with open(img_path, "wb") as f:
            f.write(png)

        instr = re.sub(r"\s+", " ", probe.get("instr", ""))[:220]
        prompt = (
            "This image is a bot-verification challenge (the image is cropped to the "
            "challenge itself; its top-left pixel is the challenge's top-left corner). "
            + (f"The instruction shown to the user is: \"{instr}\". " if instr else "")
            + "Return ONLY a valid JSON array of the click points needed to pass it, "
              "in pixel coordinates of THIS image, e.g. [{\"x\":142,\"y\":87}]. "
              "No prose, no markdown."
        )
        ans = self._ask_z_ai(driver, prompt, img_path)
        pts = _parse_json_answer(ans)
        if not isinstance(pts, list):
            return False

        clicked = False
        for c in pts[:8]:
            if not (isinstance(c, dict) and "x" in c and "y" in c):
                continue
            try:
                vx = origin["x"] + float(c["x"]) / ratio
                vy = origin["y"] + float(c["y"]) / ratio
            except Exception:
                continue
            # حاجز أمان: نقطة خارج منطقة التحدي تعني خطأ في التقدير — لا تُنقر
            if not (base["x"] - 12 <= vx <= base["x"] + base["w"] + 12
                    and base["y"] - 12 <= vy <= base["y"] + base["h"] + 12):
                log.debug(f"  [Captcha] نقطة خارج منطقة التحدي ({vx:.0f},{vy:.0f}) — تجاهُلها.")
                continue
            if HumanMouse.move_and_click(driver, vx, vy):
                clicked = True
            STOP.wait(random.uniform(0.7, 1.5))
        STOP.wait(2.0)
        return clicked

    def solve(self, driver, iframe, temp_dir: str) -> bool:
        if not _zai_ready():
            return False
        try:
            base = HumanMouse.viewport_rect(driver, iframe)
            if not base or base["w"] < 10 or base["h"] < 10:
                return False

            probe = _frame_probe(driver, iframe, base)
            instr_low = (probe.get("instr") or "").lower()
            is_grid = len(probe["rects"]) >= 4 or any(w in instr_low for w in CHOICE_WORDS)
            if is_grid and probe["rects"]:
                log.info(f"  [Captcha] اختبار صور ({len(probe['rects'])} بلاطة) — "
                         f"التعليمة: {instr_low[:70]!r}")
                return self._solve_grid(driver, iframe, base, probe, temp_dir)
            if is_grid:
                log.info("  [Captcha] تعليمة اختيار صور بلا بلاطات مقروءة — وضع الإحداثيات.")
            return self._solve_points(driver, iframe, base, probe, temp_dir)
        except Exception as e:
            log.warning(f"  [Captcha] {type(e).__name__}: {e}")
            return False
        finally:
            try:
                driver.switch_to.default_content()
            except Exception:
                pass


def _best_challenge_frame(driver):
    """أكبر إطار تحدٍّ ظاهر، مع تفضيل إطارات Cloudflare على غيرها."""
    try:
        frames = driver.find_elements(By.XPATH, CF_IFRAME_XPATH)
    except Exception:
        return None, None
    scored = []
    for f in frames:
        try:
            if not f.is_displayed():
                continue
            r = driver.execute_script("""
                const b = arguments[0].getBoundingClientRect();
                return {x:b.left, y:b.top, w:b.width, h:b.height};
            """, f)
            if not r or r["w"] < 20 or r["h"] < 20:
                continue
            src = (f.get_attribute("src") or "").lower()
            bonus = 1e6 if ("challenges.cloudflare.com" in src or "turnstile" in src) else 0.0
            scored.append((bonus + r["w"] * r["h"], f))
        except Exception:
            continue
    if not scored:
        return None, None
    scored.sort(key=lambda t: t[0], reverse=True)
    return scored[0][1], None


def handle_cloudflare(driver, temp_dir: str) -> bool:
    """
    الترتيب: انتظار الحل التلقائي (أغلب التحديات المُدارة تمرّ وحدها في نافذة
    حقيقية ببروفايل حقيقي) → نقرة بشرية على مربّع Turnstile → Z.ai.
    """
    if is_blocked_page(driver):
        cooldown.block(driver.current_url or "")
        return False
    if not is_cloudflare(driver):
        return False
    log.info("  [CF] رُصد تحدي Cloudflare — انتظار الحل التلقائي …")

    deadline = time.time() + config.cf_auto_wait
    while time.time() < deadline and not STOP.is_set():
        STOP.wait(2.0)
        if is_blocked_page(driver):
            cooldown.block(driver.current_url or "")
            return False
        if not is_cloudflare(driver):
            log.info("  [CF] تم التجاوز تلقائياً.")
            return True

    def passed(tries: int = 8) -> bool:
        for _ in range(tries):
            STOP.wait(1.5)
            if STOP.is_set():
                return False
            if not is_cloudflare(driver):
                return True
        return False

    # إطار Turnstile يُركَّب بعد تحميل الصفحة، فقد لا يكون موجوداً في أول لحظة
    frame = None
    for _ in range(6):
        frame, _ = _best_challenge_frame(driver)
        if frame is not None:
            break
        STOP.wait(1.5)

    if frame is not None:
        r = HumanMouse.viewport_rect(driver, frame)
        if r and r["w"] > 20 and r["h"] > 20:
            # الأدقّ: تحديد مربّع التأشير من داخل الإطار نفسه. وإن تعذّر
            # (Shadow DOM/تعارض أصول) نرجع إلى النقاط التقريبية المعتادة.
            log.info("  [CF] نقرة بشرية على مربّع التحقق …")
            if _frame_click(driver, frame, r, CHECKBOX_SELECTORS) and passed(6):
                log.info("  [CF] نجح التجاوز بعد النقر على المربّع.")
                return True
            for dx, dy in ((min(30.0, r["w"] / 2), r["h"] / 2),
                           (r["w"] * 0.08, r["h"] * 0.5),
                           (r["w"] / 2, r["h"] / 2)):
                if STOP.is_set():
                    return False
                HumanMouse.move_and_click(driver, r["x"] + dx, r["y"] + dy)
                if passed(4):
                    log.info("  [CF] نجح التجاوز بعد النقر.")
                    return True

        for attempt in range(1, max(1, config.captcha_max_attempts) + 1):
            if STOP.is_set() or not _zai_ready():
                break
            log.info(f"  [CF] محاولة حلّ التحدي عبر Z.ai ({attempt}/{config.captcha_max_attempts}) …")
            if not CaptchaSolver().solve(driver, frame, temp_dir):
                break
            if passed(10):
                log.info("  [CF] نجح التجاوز عبر Z.ai.")
                return True
            frame, _ = _best_challenge_frame(driver)
            if frame is None:
                break

    # بعض التحديات تعرض زر تحقق في المستند نفسه لا داخل إطار
    try:
        for el in driver.find_elements(By.XPATH, CF_VERIFY_XPATH):
            if el.is_displayed() and HumanMouse.click_element(driver, el) and passed(6):
                log.info("  [CF] نجح التجاوز بعد النقر على زر التحقق.")
                return True
    except Exception:
        pass

    log.warning("  [CF] لم يُتجاوز التحدي.")
    return False


# ═════════════════════════ ROBOT PAGE (SCI-HUB) ═════════════════════════
# [إصلاح حرِج] المطابقة صارت تامّة لكلمة "no" بدل contains(...,'no'):
#   القديم كان يطابق "Diag(no)se network problems" في صفحة خطأ Chrome
#   فينقره في كل دورة → نافذة «تشخيص شبكة Windows» تعود كلما أغلقتها.
_ROBOT_XPATH = (
    "//button[normalize-space(translate(., 'NO', 'no'))='no']"
    " | //a[normalize-space(translate(., 'NO', 'no'))='no']"
    " | //div[@role='button'][normalize-space(translate(., 'NO', 'no'))='no']"
    " | //input[(@type='button' or @type='submit') and translate(@value,'NO','no')='no']"
    " | //button[normalize-space(text())='لا']"
    " | //button[normalize-space(translate(., 'НЕТ', 'нет'))='нет']"
)
_FORBIDDEN_IDS = ("diagnose-button", "reload-button", "download-link", "details-button",
                  "error-information-button", "control-buttons")


def _page_signature(driver) -> str:
    """بصمة مختصرة للصفحة — للتحقق من أن النقرة أحدثت تغييراً فعلياً."""
    try:
        return driver.execute_script(
            "return location.href + '|' + (document.body ? document.body.innerText.length : 0);"
        ) or ""
    except Exception:
        return ""


def _bypass_robot_page(driver) -> bool:
    """
    صفحة Sci-Hub «Are you a robot? / Вы робот?» والتحديات الشبيهة:
    تتعامل مع كل من النص الإنجليزي، الروسي (Altcha)، والعربي.
    """
    try:
        if is_error_page(driver):
            return False   # حاجز الأمان الأول: لا نلمس صفحات خطأ Chrome إطلاقاً
        body = (driver.execute_script(
            "return (document.body ? document.body.innerText : '').slice(0,3000).toLowerCase();"
        ) or "")
        is_robot_page = any(w in body for w in ("robot", "робот", "روبوت", "вы робот", "are you a robot"))
        has_altcha = driver.execute_script(
            "return !!(document.querySelector('altcha-widget') || document.querySelector('.question .answer'));"
        )
        if not is_robot_page and not has_altcha:
            return False   # حاجز الأمان الثاني: لا بد أن تذكر الصفحة فحص الروبوت أو تحتوي عنصر التحقق

        log.info("  [Anti-Bot] رصد صفحة فحص الروبوت (Sci-Hub / Altcha)... جاري التحقق التلقائي.")
        clicked = driver.execute_script(r"""
            try {
                if (typeof check === 'function') {
                    check();
                    return true;
                }
                const ans = document.querySelector('.answer, .question .answer, [translate="ru:nope"]');
                if (ans) {
                    ans.click();
                    return true;
                }
                const widget = document.querySelector('altcha-widget');
                if (widget && typeof widget.verify === 'function') {
                    widget.verify();
                    return true;
                }
            } catch(e) {}
            return false;
        """)
        if clicked:
            time.sleep(3.0)
            return True

        for el in driver.find_elements(By.XPATH, _ROBOT_XPATH + " | //div[contains(@class,'answer')] | //*[normalize-space(text())='Нет']"):
            try:
                if not el.is_displayed():
                    continue
                eid = (el.get_attribute("id") or "").lower()
                if any(bad in eid for bad in _FORBIDDEN_IDS):
                    continue
                log.info("  [Anti-Bot] صفحة 'Are you a robot?' — النقر على زر 'No' / 'Нет'.")
                before = _page_signature(driver)
                if not HumanMouse.click_element(driver, el):
                    continue
                STOP.wait(2.0)
                return _page_signature(driver) != before
            except Exception:
                continue
    except Exception:
        pass
    return False


def handle_image_challenge(driver, temp_dir: str) -> bool:
    """
    [إضافة] اختبار الصور الذي يبدأ بـ «اختر …» / «Select all images with …»
    قد يظهر في المستند نفسه (مواقع المرايا وSci-Hub) لا داخل إطار Cloudflare.
    نمرّره لنفس محرّك الحل بعد التأكد أنّ الصفحة تطلب فعلاً اختيار صور.
    """
    if not _zai_ready() or is_error_page(driver):
        return False
    try:
        info = driver.execute_script(r"""
            const words = arguments[0], tsel = arguments[1];
            const t = ((document.body ? document.body.innerText : '') || '')
                        .slice(0, 1500).toLowerCase();
            if (!words.some(w => t.includes(w))) return null;
            for (const s of tsel) {
              try {
                const els = Array.from(document.querySelectorAll(s))
                  .filter(e => { const r = e.getBoundingClientRect();
                                 return r.width > 24 && r.height > 24; });
                if (els.length >= 4) return {sel: s, n: els.length};
              } catch (e) {}
            }
            return null;
        """, list(CHOICE_WORDS), TILE_SELECTORS)
    except Exception:
        return False
    if not info:
        return False

    log.info(f"  [Captcha] اختبار صور في الصفحة نفسها ({info.get('n')} بلاطة).")
    try:
        rects = driver.execute_script(r"""
            return Array.from(document.querySelectorAll(arguments[0])).map(e => {
              const r = e.getBoundingClientRect();
              return {x:r.left, y:r.top, w:r.width, h:r.height};
            }).filter(r => r.w > 24 && r.h > 24);
        """, info["sel"]) or []
        rects, cols = _order_tiles([r for r in rects if isinstance(r, dict)])
        if not rects:
            return False
        xs = [r["x"] for r in rects] + [r["x"] + r["w"] for r in rects]
        ys = [r["y"] for r in rects] + [r["y"] + r["h"] for r in rects]
        base = {"x": min(xs), "y": min(ys), "w": max(xs) - min(xs), "h": max(ys) - min(ys)}
        instr = driver.execute_script(
            "return ((document.body?document.body.innerText:'')||'').slice(0,300);") or ""
        probe = {"rects": rects, "cols": cols, "instr": instr}
        return CaptchaSolver()._solve_grid(driver, None, base, probe, temp_dir)
    except Exception as e:
        log.debug(f"  [Captcha] اختبار الصفحة: {type(e).__name__}: {e}")
        return False


# ═════════════════════════ COOKIE / CONSENT BANNERS ═════════════════════════
# [إضافة إنتاجية] لافتة الموافقة عند Elsevier/Springer/Wiley تغطّي الصفحة بطبقة
# شفافة تعترض كل نقرة (ومنها زر تنزيل الـPDF)، فيبدو الأمر كأن الموقع لا يستجيب.
# نُخفيها بمحدِّدات معروفة فقط — لا نقر على نصوص عشوائية.
CONSENT_SELECTORS = (
    "#onetrust-accept-btn-handler", "#onetrust-reject-all-handler",
    "button#truste-consent-button", ".fc-cta-consent", ".fc-button.fc-cta-consent",
    "button[aria-label='Accept cookies']", "button[aria-label='Accept all cookies']",
    "button[data-testid='cookie-accept']", "#CybotCookiebotDialogBodyButtonAccept",
    ".cc-btn.cc-dismiss", ".cookie-consent-accept", "#accept-cookies",
    "button.osano-cm-accept-all", "#gdpr-consent-accept",
)
CONSENT_OVERLAYS = (
    "#onetrust-consent-sdk", ".onetrust-pc-dark-filter", "#CybotCookiebotDialog",
    ".fc-consent-root", ".osano-cm-window", "#cookie-banner", ".cookie-notice",
    "#truste-consent-track", ".privacy-banner",
)
_consent_done = {}
_consent_lock = threading.Lock()


def dismiss_consent(driver) -> bool:
    """
    زر الموافقة إن وُجد، وإلا إخفاء الطبقة. اللافتة تُركَّب بعد التحميل بثانية
    أو أكثر، لذا لا نكتفي بمحاولة واحدة — لكننا نحدّها بثلاث لكل نطاق حتى لا
    نُنفّق وقتاً على مواقع بلا لافتة أصلاً، ونتوقف نهائياً عند أول نجاح.
    """
    if not config.dismiss_consent:
        return False
    try:
        host = urlparse(driver.current_url or "").netloc.lower()
    except Exception:
        host = ""
    with _consent_lock:
        tries = _consent_done.get(host, 0)
        if host and tries >= 3:
            return False
        if host:
            _consent_done[host] = tries + 1
    try:
        acted = bool(driver.execute_script(r"""
            const btns = arguments[0], overlays = arguments[1];
            let acted = false;
            for (const s of btns) {
              try {
                const e = document.querySelector(s);
                if (e && e.offsetParent !== null) { e.click(); acted = true; break; }
              } catch (err) {}
            }
            for (const s of overlays) {
              try {
                document.querySelectorAll(s).forEach(e => {
                  e.style.setProperty('display', 'none', 'important');
                  acted = true;
                });
              } catch (err) {}
            }
            try {
              document.documentElement.style.overflow = 'auto';
              document.body.style.overflow = 'auto';
              document.body.classList.remove('modal-open', 'no-scroll', 'ot-overflow-hidden');
            } catch (err) {}
            return acted;
        """, list(CONSENT_SELECTORS), list(CONSENT_OVERLAYS)))
    except Exception:
        return False
    if acted and host:
        with _consent_lock:
            _consent_done[host] = 99      # نجحت — لا نعيدها لهذا النطاق
    return acted


# ═════════════════════════ PDF URL HARVESTER ═════════════════════════
JS_HARVEST = r"""
const abs = (u) => { try { return new URL(u, document.baseURI).href; } catch(e) { return null; } };
const out = [];

const isCitationOrRef = (u, t) => {
  const lowU = (u || '').toLowerCase();
  const lowT = (t || '').toLowerCase();
  return (
    lowU.includes('citation-needed') || lowU.includes('format=refman') ||
    lowU.includes('format=citation') || lowU.includes('download-citation') ||
    lowU.includes('.ris') || lowU.includes('.enw') || lowU.includes('.bib') ||
    lowU.includes('export-citation') || lowU.includes('/cite/') ||
    lowT.includes('download citation') || lowT.includes('download references') ||
    lowT.includes('export citation') || lowT.includes('cite this')
  );
};

const push = (u, t) => {
  const a = abs(u);
  if (a && /^https?:/i.test(a) && !isCitationOrRef(a, t)) {
    out.push(a);
  }
};

// 1) الوسم المعياري للناشرين
const meta = document.querySelector('meta[name="citation_pdf_url"], meta[name="citation_pdf"]');
if (meta && meta.content) push(meta.content, 'meta');

// 2) Sci-Hub: زر الحفظ / الإطار المضمّن
document.querySelectorAll('#buttons button, #buttons a, .button, button').forEach(b => {
  const oc = (b.getAttribute('onclick') || '') + ' ' + (b.getAttribute('href') || '');
  const m = oc.match(/location\.href\s*=\s*['"]([^'"]+)['"]/) || oc.match(/(\/\/[^'"\s]+\.pdf[^'"\s]*)/);
  if (m) push(m[1], 'scihub');
});
['#pdf', 'embed[type="application/pdf"]', 'iframe#pdf', 'object[type="application/pdf"]',
 'embed[src*=".pdf"]', 'iframe[src*=".pdf"]', 'object[data*=".pdf"]'].forEach(sel => {
  document.querySelectorAll(sel).forEach(e => push(e.src || e.data || '', 'embed'));
});

// 3) روابط PDF صريحة (مع استبعاد روابط الاستشهادات والمراجع النصية)
document.querySelectorAll('a[href]').forEach(a => {
  const h = a.getAttribute('href') || '';
  const txt = ((a.innerText || '') + ' ' + (a.title || '') + ' ' + (a.className || '')).toLowerCase();
  if (isCitationOrRef(h, txt)) return;
  if (/\.pdf(\?|#|$)/i.test(h) || /\/pdf\//i.test(h) || /blobtype=pdf/i.test(h) || /content\/pdf/i.test(h)) {
    push(h, txt);
  } else if ((txt.includes('download pdf') || txt.includes('full text pdf') || txt.includes('view pdf')) &&
             (h.includes('pdf') || h.includes('download') || h.includes('content'))) {
    push(h, txt);
  }
});

// 4) الصفحة نفسها ملف PDF
if (/\.pdf(\?|#|$)/i.test(location.href) && !isCitationOrRef(location.href, '')) {
  push(location.href, 'self');
}

return Array.from(new Set(out)).slice(0, 12);
"""


def harvest_pdf_urls(driver) -> List[str]:
    try:
        urls = driver.execute_script(JS_HARVEST) or []
    except (JavascriptException, WebDriverException):
        return []
    clean = []
    for u in urls:
        if not isinstance(u, str):
            continue
        u = u.strip()
        if u.startswith("//"):
            u = "https:" + u
        if u.lower().startswith("http") and u not in clean:
            clean.append(u)
    return clean


# ═════════════════════════ IN-PAGE FETCH (يرث جلسة Cloudflare) ═════════════════════════
JS_FETCH = r"""
const url = arguments[0], cap = arguments[1], done = arguments[arguments.length - 1];
(async () => {
  try {
    const r = await fetch(url, {credentials: 'include', redirect: 'follow'});
    if (!r.ok) { done({ok:false, err:'HTTP ' + r.status}); return; }
    const buf = new Uint8Array(await r.arrayBuffer());
    if (buf.length < 1024) { done({ok:false, err:'too small (' + buf.length + ')'}); return; }
    if (buf.length > cap)  { done({ok:false, err:'too large'}); return; }
    const sig = String.fromCharCode(buf[0], buf[1], buf[2], buf[3]);
    let bin = '', CH = 0x8000;
    for (let i = 0; i < buf.length; i += CH) {
      bin += String.fromCharCode.apply(null, buf.subarray(i, i + CH));
    }
    done({ok:true, sig: sig, size: buf.length, b64: btoa(bin)});
  } catch (e) { done({ok:false, err: String(e)}); }
})();
"""


def fetch_pdf_in_page(driver, url: str, dest: Path) -> bool:
    """
    يجلب بايتات الملف من داخل الصفحة نفسها، فيرث كوكيز الجلسة و cf_clearance
    وترويسات الأصل — أوثق بكثير من انتظار مجلد التنزيل، وبنفس آلية العمل
    (كل شيء يمرّ عبر متصفح الطالب الحقيقي).
    """
    if not config.use_inpage_fetch:
        return False
    try:
        res = driver.execute_async_script(JS_FETCH, url, config.max_fetch_bytes)
    except Exception as e:
        log.debug(f"  [Fetch] {type(e).__name__}: {e}")
        return False
    if not isinstance(res, dict) or not res.get("ok"):
        log.debug(f"  [Fetch] فشل: {(res or {}).get('err') if isinstance(res, dict) else res}")
        return False
    if res.get("sig") != "%PDF":
        log.debug(f"  [Fetch] المحتوى ليس PDF (sig={res.get('sig')!r}).")
        return False
    try:
        data = base64.b64decode(res["b64"])
        if not _pdf_bytes_ok(data):
            return False
        tmp = dest.with_suffix(".part")
        with open(tmp, "wb") as f:
            f.write(data)
        os.replace(tmp, dest)
        log.info(f"  [Fetch] تم الجلب داخل الصفحة ({len(data) / 1024:.0f} KB).")
        return True
    except Exception as e:
        log.debug(f"  [Fetch] كتابة فاشلة: {e}")
        return False


# ═════════════════════════ RESILIENT STREAM DOWNLOADER ═════════════════════════
def download_stream_with_resume(
    url: str,
    dest: Path,
    headers: Optional[dict] = None,
    max_retries: int = 4,
    timeout: int = 35
) -> Tuple[bool, str]:
    """
    تنزيل بايتات مباشر فائق الصمود لشبكات الإنترنت الضعيفة والمتقطعة.
    يدعم استئناف التنزيل من نقطة الانقطاع عبر ترويسة Range: bytes=X-
    ويعيد المحاولة آلياً بفواصل متصاعدة عند تقطع الشبكة دون إعادة البدء من الصفر.
    """
    if STOP.is_set():
        return False, "Aborted"

    tmp = dest.with_suffix(".part")
    default_headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/pdf,application/octet-stream,*/*;q=0.8",
        "Accept-Encoding": "identity",
    }
    if headers:
        default_headers.update(headers)

    s = requests.Session()
    s.verify = False  # مرايا المقالات قد تحوي شهادات ذاتية التوقيع

    retries = 0
    backoff = 1.5

    while retries < max_retries and not STOP.is_set():
        existing_bytes = tmp.stat().st_size if tmp.exists() else 0
        req_headers = dict(default_headers)
        if existing_bytes > 0:
            req_headers["Range"] = f"bytes={existing_bytes}-"

        try:
            with s.get(url, headers=req_headers, stream=True, timeout=timeout, allow_redirects=True) as resp:
                if resp.status_code not in (200, 206):
                    if resp.status_code == 416 and existing_bytes > config.min_pdf_bytes:
                        if looks_like_pdf(tmp):
                            os.replace(str(tmp), str(dest))
                            return True, f"Success (stream resume complete, {existing_bytes // 1024} KB)"
                        tmp.unlink(missing_ok=True)
                        existing_bytes = 0
                    return False, f"HTTP {resp.status_code}"

                mode = "ab" if (resp.status_code == 206 and existing_bytes > 0) else "wb"
                if mode == "wb":
                    existing_bytes = 0

                with open(tmp, mode) as f:
                    for chunk in resp.iter_content(chunk_size=config.chunk_size):
                        if STOP.is_set():
                            return False, "Aborted"
                        if chunk:
                            f.write(chunk)
                            existing_bytes += len(chunk)

                if looks_like_pdf(tmp):
                    os.replace(str(tmp), str(dest))
                    log.info(f"  [Stream] تم التنزيل المباشر بنجاح ({dest.stat().st_size // 1024} KB)")
                    return True, "Success (stream)"
                else:
                    tmp.unlink(missing_ok=True)
                    return False, "Streamed content is not a valid PDF"

        except (requests.exceptions.RequestException, ConnectionError, TimeoutError, socket.timeout) as e:
            retries += 1
            log.debug(f"  [Stream Retry {retries}/{max_retries}] تقطع اتصال ({type(e).__name__}): استئناف بعد {backoff:.1f} ثانية...")
            STOP.wait(backoff)
            backoff *= 2
        except Exception as e:
            log.debug(f"  [Stream Err] {e}")
            break

    if tmp.exists() and looks_like_pdf(tmp):
        os.replace(str(tmp), str(dest))
        return True, f"Success (stream recovery, {dest.stat().st_size // 1024} KB)"

    return False, "Stream download failed after retries"


# ═════════════════════════ FALLBACK PROVIDER ═════════════════════════
class FallbackProvider:
    """نفس ترتيب المصادر الأصلي: Open Access → Unpaywall → Direct Publisher → DOI Checker → Sci-Hub."""
    SCIHUB_MIRRORS = ("https://sci-hub.ru", "https://sci-hub.ren", "https://sci-hub.st")

    @staticmethod
    def normalize_doi(doi: str) -> str:
        d = (doi or "").strip()
        if d.upper() in ("N/A", "NA", "-", "NONE"):
            return ""
        for pref in ("https://doi.org/", "http://doi.org/", "https://dx.doi.org/",
                     "http://dx.doi.org/", "doi:", "DOI:"):
            if d.lower().startswith(pref.lower()):
                d = d[len(pref):]
        d = d.strip().strip("/")
        # لا نبني روابط من قيمة ليست DOI أصلاً (تفادي https://sci-hub.st/N/A)
        return d if re.match(r"^10\.\d{4,9}/\S+$", d) else ""

    @classmethod
    def resolve_unpaywall(cls, doi: str) -> List[str]:
        """فحص شبكة Unpaywall للأبحاث المفتوحة في مستودعات الجامعات ومستودع PubMed Central."""
        if not doi:
            return []
        urls = []
        try:
            email = getattr(config, "unpaywall_email", "contact@example.com")
            upw_url = f"https://api.unpaywall.org/v2/{doi}?email={email}"
            with requests.get(upw_url, timeout=5) as resp:
                if resp.status_code == 200:
                    data = resp.json()
                    best = data.get("best_oa_location") or {}
                    pdf_url = best.get("url_for_pdf") or best.get("url")
                    if pdf_url:
                        urls.append(pdf_url)
                    for loc in data.get("oa_locations") or []:
                        loc_pdf = loc.get("url_for_pdf") or loc.get("url")
                        if loc_pdf and loc_pdf not in urls:
                            urls.append(loc_pdf)
        except Exception:
            pass
        return urls

    @classmethod
    def resolve_researchgate(cls, doi: str = "", title: str = "") -> List[str]:
        """فحص منصة ResearchGate للتحقق مما إذا كان الباحثون قد أتاحوا نسخة PDF قابلة للتنزيل المباشر."""
        urls = []
        clean_doi = cls.normalize_doi(doi) if doi else ""
        clean_t = (title or "").strip()
        if not clean_doi and not clean_t:
            return urls
        try:
            if clean_doi.startswith("10.13140/"):
                urls.append(f"https://doi.org/{clean_doi}")
                return urls

            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
            }
            q = f'"{clean_t}" site:researchgate.net' if clean_t else f'"{clean_doi}" site:researchgate.net'
            scholar_url = f"https://scholar.google.com/scholar?q={urllib.parse.quote(q)}"
            with requests.get(scholar_url, headers=headers, timeout=3.5) as r:
                if r.status_code == 200 and "researchgate.net" in r.text:
                    rg_pdfs = re.findall(r'href="(https?://(?:www\.)?researchgate\.net/[^"]+\.pdf[^"]*)"', r.text)
                    for p in rg_pdfs:
                        if p not in urls:
                            urls.append(p)
        except Exception:
            pass
        return urls

    @staticmethod
    def normalize_paper_title(title: str) -> str:
        """توحيد وتنظيف عنوان البحث للمطابقة الدقيقة وحذف الكلمات الشائعة والرموز."""
        if not title:
            return ""
        t = re.sub(r"<[^>]+>", " ", title)
        t = re.sub(r"(?i)\b(preprint|has full text|link-only|pdf|full text)\b", " ", t)
        t = re.sub(r"[^\w\s]", " ", t.lower())
        return re.sub(r"\s+", " ", t).strip()

    @classmethod
    def calculate_title_similarity(cls, title1: str, title2: str) -> float:
        """
        حساب نسبة التشابه الدقيقة بين عنوانين بعد المعايرة والتنظيف.
        تُرجع قيمة بين 0.0 و 1.0 (مثلاً 0.96 تعني 96%).
        """
        c1 = cls.normalize_paper_title(title1)
        c2 = cls.normalize_paper_title(title2)
        if not c1 or not c2:
            return 0.0
        if c1 == c2:
            return 1.0
        return difflib.SequenceMatcher(None, c1, c2).ratio()

    @classmethod
    def resolve_by_title_knowledge_ocean(cls, title: str, min_similarity: float = 0.95) -> Optional[dict]:
        """
        البحث عن الورقة البحثية واستخراج الـ DOI والروابط باستخدام محرك محيط المعرفة:
        1. الاستعلام من خادم محيط المعرفة المحلي إن كان يعمل (/api/find-doi).
        2. كاحتياطي مدمج: الاستعلام المباشر من محركات Crossref و OpenAlex.
        شرط المطابقة الحازم: لا تُقبل أي نتيجة إلا إذا كانت نسبة تطابق العنوان أعلى من أو تساوي 95% (>= 95%).
        """
        clean_t = title.strip()
        if not clean_t:
            return None

        headers = {"User-Agent": "KnowledgeOcean/9.5 (mailto:contact@knowledgeocean.org)"}

        # 1. فحص خادم محيط المعرفة المحلي (Local Knowledge Ocean Server)
        try:
            local_api = f"{config.ko_local_url}/api/find-doi?title={urllib.parse.quote(clean_t)}&limit=6"
            with requests.get(local_api, headers=headers, timeout=2.5) as r:
                if r.status_code == 200:
                    data = r.json() or {}
                    for cand in data.get("results") or []:
                        cand_title = cand.get("title") or ""
                        sim = cls.calculate_title_similarity(clean_t, cand_title)
                        if sim >= min_similarity:
                            cand_doi = cls.normalize_doi(cand.get("doi", ""))
                            urls = []
                            if cand.get("oa_url"):
                                urls.append(cand["oa_url"])
                            if cand.get("pdf_url"):
                                urls.append(cand["pdf_url"])
                            if cand_doi:
                                for u in cls.resolve_unpaywall(cand_doi):
                                    if u not in urls:
                                        urls.append(u)
                            return {
                                "matched": True,
                                "doi": cand_doi,
                                "title": cand_title,
                                "similarity": sim,
                                "urls": urls,
                                "source": "knowledge_ocean_local"
                            }
        except Exception:
            pass

        # 2. استعلام Crossref مباشرة كنسخة احتياطية مدمجة
        try:
            cr_url = f"https://api.crossref.org/works?query.title={urllib.parse.quote(clean_t)}&rows=5"
            with requests.get(cr_url, headers=headers, timeout=6) as r:
                if r.status_code == 200:
                    items = (r.json().get("message") or {}).get("items") or []
                    for it in items:
                        t_list = it.get("title") or []
                        cand_title = t_list[0] if t_list else ""
                        sim = cls.calculate_title_similarity(clean_t, cand_title)
                        if sim >= min_similarity:
                            cand_doi = cls.normalize_doi(it.get("DOI", ""))
                            urls = []
                            for link in it.get("link") or []:
                                if "pdf" in (link.get("content-type") or "").lower() and link.get("URL"):
                                    urls.append(link["URL"])
                            if cand_doi:
                                for u in cls.resolve_unpaywall(cand_doi):
                                    if u not in urls:
                                        urls.append(u)
                            return {
                                "matched": True,
                                "doi": cand_doi,
                                "title": cand_title,
                                "similarity": sim,
                                "urls": urls,
                                "source": "crossref"
                            }
        except Exception:
            pass

        # 3. استعلام OpenAlex مباشرة كنسخة احتياطية مدمجة
        try:
            oa_url = f"https://api.openalex.org/works?filter=title.search:{urllib.parse.quote(clean_t)}&per_page=5"
            with requests.get(oa_url, headers=headers, timeout=6) as r:
                if r.status_code == 200:
                    results = r.json().get("results") or []
                    for res in results:
                        cand_title = res.get("title") or ""
                        sim = cls.calculate_title_similarity(clean_t, cand_title)
                        if sim >= min_similarity:
                            raw_doi = res.get("doi") or ""
                            cand_doi = cls.normalize_doi(raw_doi.replace("https://doi.org/", "").strip())
                            urls = []
                            oa = (res.get("open_access") or {}).get("oa_url")
                            if oa:
                                urls.append(oa)
                            loc = (res.get("primary_location") or {}).get("pdf_url")
                            if loc and loc not in urls:
                                urls.append(loc)
                            if cand_doi:
                                for u in cls.resolve_unpaywall(cand_doi):
                                    if u not in urls:
                                        urls.append(u)
                            return {
                                "matched": True,
                                "doi": cand_doi,
                                "title": cand_title,
                                "similarity": sim,
                                "urls": urls,
                                "source": "openalex"
                            }
        except Exception:
            pass

        return None

    @classmethod
    def resolve_knowledge_ocean_doi(cls, doi: str) -> List[str]:
        """
        استعلام محرك محيط المعرفة لجلب روابط الوصول المفتوح (OA) والملفات المباشرة لمعرف DOI معين.
        """
        if not doi:
            return []
        clean_doi = cls.normalize_doi(doi)
        if not clean_doi:
            return []
        urls = []
        headers = {"User-Agent": "KnowledgeOcean/9.5 (mailto:contact@knowledgeocean.org)"}

        # 1. فحص خادم محيط المعرفة المحلي
        try:
            local_api = f"{config.ko_local_url}/api/doi-lookup?doi={urllib.parse.quote(clean_doi)}"
            with requests.get(local_api, headers=headers, timeout=2.5) as r:
                if r.status_code == 200:
                    data = r.json() or {}
                    paper = data.get("paper") or {}
                    pdf_u = paper.get("pdf_url")
                    oa_u = paper.get("oa_url")
                    if pdf_u and not pdf_u.startswith(("https://doi.org/", "http://doi.org/")):
                        urls.append(pdf_u)
                    if oa_u and not oa_u.startswith(("https://doi.org/", "http://doi.org/")) and oa_u not in urls:
                        urls.append(oa_u)
        except Exception:
            pass

        # 2. استعلام OpenAlex لجلب روابط OA إضافية
        try:
            oa_url = f"https://api.openalex.org/works/https://doi.org/{urllib.parse.quote(clean_doi)}"
            with requests.get(oa_url, headers=headers, timeout=5) as r:
                if r.status_code == 200:
                    oa_data = r.json() or {}
                    oa_u = (oa_data.get("open_access") or {}).get("oa_url")
                    pdf_u = (oa_data.get("primary_location") or {}).get("pdf_url")
                    if pdf_u and not pdf_u.startswith(("https://doi.org/", "http://doi.org/")):
                        if pdf_u not in urls:
                            urls.append(pdf_u)
                    if oa_u and not oa_u.startswith(("https://doi.org/", "http://doi.org/")):
                        if oa_u not in urls:
                            urls.append(oa_u)
        except Exception:
            pass

        return urls

    @classmethod
    def get_urls(cls, entry: dict) -> List[str]:
        urls = []
        if entry.get("oa_url"):
            urls.append(entry["oa_url"])
        
        doi = cls.normalize_doi(entry.get("doi", ""))
        title = (entry.get("title") or "").strip()

        # 1. إذا كان معرّف الـ DOI مفقوداً أو غير صالح، يتم استخدام محرك محيط المعرفة للبحث بالعنوان ومطابقة العنوان (>= 95%)
        if not doi and title:
            log.info(f"[{entry.get('idx', 0):04d}] معرّف DOI مفقود — البحث في محيط المعرفة بالعنوان ومطابقة العنوان (>= 95%): {title[:60]}…")
            ko_match = cls.resolve_by_title_knowledge_ocean(title, min_similarity=0.95)
            if ko_match and ko_match.get("doi"):
                doi = ko_match["doi"]
                entry["doi"] = doi
                log.info(f"[{entry.get('idx', 0):04d}] تم تأكيد البحث وتطابق العنوان بنسبة {ko_match['similarity']*100:.1f}% >= 95% | DOI: {doi}")
                for u in ko_match.get("urls", []):
                    if u not in urls:
                        urls.append(u)

        if doi:
            # 2. روابط مستودعات الوصول المفتوح (PMC, Repositories) عبر Unpaywall
            for u in cls.resolve_unpaywall(doi):
                if u not in urls:
                    urls.append(u)

            # 3. استعلام محرك محيط المعرفة المدمج لجلب روابط OA إضافية
            for u in cls.resolve_knowledge_ocean_doi(doi):
                if u not in urls:
                    urls.append(u)

            # 3.5. فحص منصة ResearchGate للتحقق من وجود نسخة PDF متاحة للتنزيل
            for u in cls.resolve_researchgate(doi=doi, title=title):
                if u not in urls:
                    urls.append(u)

            # 4. مرايا Sci-Hub المباشرة (فحص HTTP سريع وتنزيل تدفقي فوري دون استهلاك المتصفح)
            urls.extend(f"{m}/{doi}" for m in cls.SCIHUB_MIRRORS)

            # 5. روابط دور النشر المباشرة (Springer Nature / BMC)
            if doi.startswith(("10.1007/", "10.1186/", "10.1038/")):
                springer_pdf = f"https://link.springer.com/content/pdf/{doi}.pdf"
                if springer_pdf not in urls:
                    urls.append(springer_pdf)

            # 6. الرابط الرسمي للـ DOI
            resolved = f"https://doi.org/{doi}"
            if resolved not in urls:
                urls.append(resolved)

        # 7. محاولة أخيرة بالعنوان إذا لم تتوفر أي روابط وكان العنوان متوفراً
        if not urls and title:
            ko_match = cls.resolve_by_title_knowledge_ocean(title, min_similarity=0.95)
            if ko_match and ko_match.get("doi"):
                doi = ko_match["doi"]
                entry["doi"] = doi
                for u in ko_match.get("urls", []):
                    if u not in urls:
                        urls.append(u)
                for u in cls.resolve_researchgate(doi=doi, title=title):
                    if u not in urls:
                        urls.append(u)
                urls.extend(f"{m}/{doi}" for m in cls.SCIHUB_MIRRORS)

        seen, out = set(), []
        for u in urls:
            if u not in seen:
                seen.add(u)
                out.append(u)

        # نضع روابط PDF المباشرة في الصدارة دائماً لتنزيلها فوراً وبسرعة فائقة دون الحاجة للمتصفح
        pdf_direct = [
            u for u in out
            if any(u.lower().endswith(ext) for ext in (".pdf", ".pdf/", "blobtype=pdf"))
            or "/content/pdf/" in u.lower()
            or "/pdf/" in u.lower()
        ]
        non_pdf = [u for u in out if u not in pdf_direct]
        return pdf_direct + non_pdf


def trigger_download(driver, url: str) -> None:
    """محفّز التنزيل القسري (نفس فكرة النسخة الأصلية) لكن بتمرير آمن للرابط."""
    try:
        driver.execute_script("""
            const u = arguments[0];
            const a = document.createElement('a');
            a.href = u; a.download = ''; a.rel = 'noopener';
            a.style.display = 'none';
            document.body.appendChild(a); a.click();
            setTimeout(() => a.remove(), 1500);
        """, url)
    except Exception:
        pass


# ═════════════════════════ DOWNLOAD CORE ═════════════════════════
@retry_on_failure(max_retries=config.max_retries)
def _download_attempt(url: str, entry: dict, final_path: Path, base_dir: str) -> Tuple[bool, str]:
    if STOP.is_set():
        return False, "Aborted"

    # نطاق حظرنا صراحةً في هذه الجلسة: لا معنى لإعادة الطرق عليه لكل ورقة
    if cooldown.blocked(url):
        return False, "Cloudflare block (domain on cooldown)"

    driver = browser_manager.get_driver(base_dir)
    if driver is None:
        return False, "Browser automation unavailable (fallback to direct sources)"
    home = browser_manager.home_handle()
    temp_dir = Path(config.output_dir) / f".tmp_{entry['idx']:04d}_{uuid.uuid4().hex[:8]}"
    temp_dir.mkdir(parents=True, exist_ok=True)

    started = time.time()
    deadline = started + config.hard_timeout
    last_activity = started
    last_size = 0
    my_handle = None
    tried_fetch = set()
    cf_attempts = 0
    robot_clicks = 0
    img_attempts = 0
    junk_logged = False
    staging.enter()

    try:
        driver.switch_to.new_window("tab")
        my_handle = driver.current_window_handle

        # مسار تنزيل مستقل لهذا التبويب (Page-scoped حتى لا تتضارب الخيوط)
        try:
            driver.execute_cdp_cmd("Browser.setDownloadBehavior",
                                   {"behavior": "allow", "downloadPath": str(temp_dir.resolve()), "eventsEnabled": True})
        except Exception:
            pass
        try:
            driver.execute_cdp_cmd("Page.setDownloadBehavior",
                                   {"behavior": "allow", "downloadPath": str(temp_dir.resolve())})
        except Exception as e:
            log.debug(f"  [CDP] setDownloadBehavior: {e}")

        # ---------- فتح المصدر ----------
        throttle.wait(url)
        try:
            driver.get(url)
        except TimeoutException:
            pass          # طبيعي: الانتقال إلى ملف ينتهي بتنزيل لا بتحميل صفحة
        except WebDriverException as e:
            msg = str(e)
            # [مهم] عند فرض تنزيل PDF يُجهض Chrome الانتقال ويرفع ERR_ABORTED —
            # وهذا يعني أن التنزيل *بدأ*، لا أنه فشل. النسخة القديمة كانت
            # ستعتبره فشلاً وتنتقل للمصدر التالي.
            if "ERR_ABORTED" in msg or "ERR_BLOCKED_BY_RESPONSE" in msg:
                log.debug("  [Nav] ERR_ABORTED — غالباً بدأ التنزيل.")
            else:
                return False, f"Navigation: {msg.splitlines()[0][:100]}"
        STOP.wait(1.5)

        if is_error_page(driver):
            return False, "Site unreachable (network error)"

        # حظر نهائي (1015/1020): لا تحدي يُحل — نُعلّم النطاق ونخرج فوراً
        if is_blocked_page(driver):
            cooldown.block(url)
            return False, "Cloudflare block (1015/1020) — الموقع يرفض الوصول"

        if is_cloudflare(driver):
            cf_attempts += 1
            handle_cloudflare(driver, str(temp_dir))
            last_activity = time.time()

        # لافتة الكوكيز تعترض النقر وزرّ التنزيل — نُزيلها مرة واحدة لكل نطاق
        if dismiss_consent(driver):
            log.debug("  [Consent] أُزيلت لافتة الموافقة.")
            STOP.wait(0.6)

        # محفّز التنزيل الذكي (نفس آلية الأصل)
        for cand in harvest_pdf_urls(driver)[:2]:
            if cand.rstrip("/") != url.rstrip("/"):
                trigger_download(driver, cand)
                last_activity = time.time()
                break

        # ---------- حلقة المراقبة ----------
        while time.time() < deadline and not STOP.is_set():
            # 1) اكتمال التنزيل في مجلد التبويب
            try:
                files = list(temp_dir.iterdir())
            except Exception:
                files = []

            in_prog = [f for f in files if f.name.endswith((".crdownload", ".tmp", ".partial"))]
            if in_prog:
                size = sum(f.stat().st_size for f in in_prog if f.exists())
                if size > last_size:
                    last_size, last_activity = size, time.time()
                elif time.time() - last_activity > 15:
                    # تفقد تنزيلات المتصفح ومحاولة استئناف التنزيل إذا توقف مؤقتاً بسبب ضعف الشبكة
                    try:
                        driver.execute_script("""
                            if (window.chrome && window.chrome.downloads) {
                                chrome.downloads.search({state: 'interrupted'}, (items) => {
                                    items.forEach(i => { if (i.canResume) chrome.downloads.resume(i.id); });
                                });
                            }
                        """)
                    except Exception:
                        pass

            done = [f for f in files
                    if f.is_file() and not f.name.endswith((".crdownload", ".tmp", ".partial"))]
            good = [f for f in done if looks_like_pdf(f)]
            if good:
                best = max(good, key=lambda f: f.stat().st_size)
                os.replace(str(best), str(final_path))
                return True, "Success"
            if done and not in_prog:
                # نزل شيء لكنه ليس PDF (صفحة HTML/حظر/تسجيل دخول) — لا نُبقيه
                for f in done:
                    if not junk_logged:
                        junk_logged = True
                        log.info(f"  [!] الملف النازل ليس PDF صالحاً "
                                 f"({f.name}, {f.stat().st_size // 1024} KB) — تجاهُله.")
                    try:
                        f.unlink()
                    except Exception:
                        pass

            # 2) مجلد التنزيل الافتراضي (تنزيلات ينسبها Chrome للمتصفح لا للصفحة)
            claimed = staging.claim(started, entry)
            if claimed:
                try:
                    os.replace(str(claimed), str(final_path))
                    return True, "Success (staging)"
                except Exception:
                    pass
            if staging.has_activity(started):
                last_activity = time.time()

            # 3) صفحات الحماية
            if is_error_page(driver):
                return False, "Site unreachable (network error)"

            if is_blocked_page(driver):
                cooldown.block(url)
                return False, "Cloudflare block (1015/1020) — الموقع يرفض الوصول"

            # تفقد ما إذا كانت صفحة Sci-Hub تؤكد عدم توفر البحث في خوادمها
            if any(m in url for m in FallbackProvider.SCIHUB_MIRRORS):
                try:
                    title = (driver.title or "").lower()
                    if "article is not available" in title:
                        log.info("  [Sci-Hub] البحث غير متوفر في هذه المرآة — الانتقال للمصدر التالي.")
                        return False, "Not available on this Sci-Hub mirror"
                except Exception:
                    pass

            # حدّ أقصى للنقرات: صفحة عنيدة فيها زر "No" دائماً لا يجوز أن
            # تحبس الخيط في حلقة نقر لا تنتهي حتى المهلة الصلبة.
            if robot_clicks < 3 and _bypass_robot_page(driver):
                robot_clicks += 1
                last_activity = time.time()
                STOP.wait(2.0)
                continue

            if is_cloudflare(driver):
                if cf_attempts < 2:
                    cf_attempts += 1
                    handle_cloudflare(driver, str(temp_dir))
                    last_activity = time.time()
                    continue
                return False, "Cloudflare challenge unsolved"

            # اختبار الصور «اختر …» المعروض في الصفحة نفسها لا داخل إطار
            if img_attempts < config.captcha_max_attempts and handle_image_challenge(
                    driver, str(temp_dir)):
                img_attempts += 1
                last_activity = time.time()
                STOP.wait(2.0)
                continue

            # 4) الجلب داخل الصفحة (بعد تجاوز الحماية، يرث الجلسة)
            if config.use_inpage_fetch and time.time() - started > 8:
                for cand in harvest_pdf_urls(driver):
                    if cand in tried_fetch:
                        continue
                    tried_fetch.add(cand)
                    # مهلة السكربت لا يجوز أن تتجاوز ما تبقّى من المهلة الصلبة،
                    # وإلا حجب الجلب حلقة المراقبة إلى ما بعد الموعد النهائي.
                    remaining = max(15, min(90, int(deadline - time.time())))
                    try:
                        driver.set_script_timeout(remaining)
                    except Exception:
                        pass
                    if fetch_pdf_in_page(driver, cand, final_path):
                        return True, "Success (in-page fetch)"
                    last_activity = time.time()
                    break

            # 5) خمول
            idle_limit = config.idle_timeout if in_prog else 25
            if time.time() - last_activity > idle_limit:
                break

            STOP.wait(1.5)

        if STOP.is_set():
            return False, "Aborted"

        # ---------- محاولة أخيرة: حفظ الصفحة كـ PDF (بشروط صارمة) ----------
        reason = "Idle timeout" if time.time() < deadline else "Hard timeout"
        if config.allow_html_fallback:
            ok, why = _save_page_as_pdf(driver, final_path)
            if ok:
                return True, "Saved from HTML"
            log.debug(f"  [HTML] تخطّي الحفظ: {why}")
            # سبب «غير متاح للتنزيل» أدقّ وأنفع في التقرير من «Idle timeout»،
            # وهو كذلك غير عابر فلا تُهدر عليه محاولات إعادة.
            if why.startswith(NOT_AVAILABLE):
                reason = why

        return False, reason

    except (NoSuchWindowException, InvalidSessionIdException) as e:
        return False, f"No such window: {type(e).__name__}"
    except WebDriverException as e:
        return False, f"WebDriver: {str(e).splitlines()[0][:120]}"
    except Exception as e:
        return False, f"{type(e).__name__}: {str(e)[:120]}"
    finally:
        staging.leave()
        # تنظيف آمن: نغلق تبويبنا فقط ونعود لتبويب home الخاص بهذا الخيط
        try:
            handles = driver.window_handles
            if my_handle and my_handle in handles:
                driver.switch_to.window(my_handle)
                driver.close()
            handles = driver.window_handles
            target = home if home in handles else (handles[0] if handles else None)
            if target:
                driver.switch_to.window(target)
        except Exception:
            pass
        shutil.rmtree(temp_dir, ignore_errors=True)


# نجمع نصّ الصفحة كاملاً + الأطر المضمّنة من نفس الأصل (بعض الناشرين يعرضون
# النص الكامل داخل إطار) + وسوم citation_* التي تدل على صفحة ورقة علمية.
JS_PAGE_TEXT = r"""
const cap = 400000;
let t = (document.body ? document.body.innerText : '') || '';
if (t.length < 20000) {
  document.querySelectorAll('iframe, frame').forEach(fr => {
    try {
      const d = fr.contentDocument;
      if (d && d.body && d.body.innerText) t += '\n' + d.body.innerText;
    } catch (e) {}
  });
}
const meta = (n) => {
  const e = document.querySelector('meta[name="' + n + '"]');
  return e ? (e.content || '') : '';
};
return {
  text: t.slice(0, cap),
  len: t.length,
  title: document.title || '',
  url: location.href,
  doi: meta('citation_doi'),
  citation_title: meta('citation_title'),
  pdf_meta: meta('citation_pdf_url')
};
"""


def _save_page_as_pdf(driver, final_path: Path) -> Tuple[bool, str]:
    if not config.allow_html_fallback:
        return False, "HTML fallback is completely disabled"
    try:
        if is_error_page(driver) or is_cloudflare(driver):
            return False, "صفحة حماية/خطأ"
        info = driver.execute_script(JS_PAGE_TEXT) or {}
        text = info.get("text") or ""

        if config.require_research_markers:
            ok, why = looks_like_research_text(text)
            if not ok:
                log.info(f"  [Gate] رُفضت الصفحة: {why}")
                return False, why
            log.info(f"  [Gate] {why}")
        elif int(info.get("len", 0)) < config.html_min_text_chars:
            return False, f"{NOT_AVAILABLE} — محتوى الصفحة قصير جداً"

        res = driver.execute_cdp_cmd("Page.printToPDF", {
            "printBackground": True, "preferCSSPageSize": True,
            "marginTop": 0.4, "marginBottom": 0.4})
        data = base64.b64decode(res["data"])
        if not _pdf_bytes_ok(data):
            return False, "ناتج غير صالح"
        with open(final_path, "wb") as f:
            f.write(data)
        return True, "ok"
    except Exception as e:
        return False, f"{type(e).__name__}"


def download_one(entry: dict, base_dir: str) -> Tuple[bool, str]:
    if STOP.is_set():
        return False, "Aborted"

    threading.current_thread().name = f"w{threading.get_ident() % 100:02d}"
    final_path = Path(config.output_dir) / safe_filename(entry)

    if config.skip_existing:
        existing = already_downloaded(entry)
        if existing:
            return True, "Skipped (exists)"

    urls = FallbackProvider.get_urls(entry)
    if not urls:
        # [إصلاح] كان NameError على المتغيّر reason عند قائمة روابط فارغة
        return False, "لا يوجد مصدر (DOI و Open Access كلاهما N/A في ملف 0)"

    reason = "No source URL"
    best = ""          # أنفع سبب رأيناه: «غير متاح للتنزيل» أدقّ من مهلة عامة
    entry_deadline = time.time() + config.entry_budget
    for i, url in enumerate(urls, 1):
        if STOP.is_set():
            return False, "Aborted"
        if time.time() > entry_deadline:
            return False, f"{best or reason} (انتهت ميزانية الورقة الزمنية)"
        short = url if len(url) < 78 else url[:75] + "…"
        log.info(f"[{entry['idx']:04d}] مصدر {i}/{len(urls)}: {short}")

        # محاولة تنزيل تدفقي مباشر فائق السرعة إذا كان الرابط مباشراً لملف PDF أو رابط Unpaywall أو Springer PDF
        # يدعم استئناف التنزيل (Range Header) ومقاومة ضعف الشبكة دون استهلاك المتصفح
        is_direct_pdf = (
            any(url.lower().endswith(ext) for ext in (".pdf", ".pdf/", "blobtype=pdf"))
            or "/content/pdf/" in url.lower()
            or "arxiv.org/pdf" in url.lower()
            or "/pdf/" in url.lower()
        )
        if is_direct_pdf:
            ok, s_reason = download_stream_with_resume(url, final_path)
            if ok and looks_like_pdf(final_path):
                return True, s_reason

        # محاولة مباشرة سريعة لروابط Sci-Hub لاستخراج رابط PDF الحقيقي دون تشغيل المتصفح
        if any(m in url for m in FallbackProvider.SCIHUB_MIRRORS):
            try:
                scihub_headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                }
                with requests.get(url, headers=scihub_headers, verify=False, timeout=7) as r:
                    if r.status_code == 200 and len(r.text) > 100:
                        low_text = r.text.lower()
                        if "article is not available through sci-hub" in low_text or "article not found" in low_text:
                            log.info(f"  [Sci-Hub Direct] البحث غير متوفر في هذه المرآة ({url}) — الانتقال للرابط التالي مباشرة.")
                            continue
                        m_pdf = re.search(r'(?:src|href|location\.href)\s*=\s*["\']([^"\']+\.pdf[^"\']*)["\']', r.text, re.IGNORECASE)
                        if m_pdf:
                            p_url = m_pdf.group(1)
                            if p_url.startswith("//"):
                                direct_pdf = "https:" + p_url
                            elif p_url.startswith("/"):
                                u_parsed = urlparse(url)
                                direct_pdf = f"{u_parsed.scheme}://{u_parsed.netloc}{p_url}"
                            else:
                                direct_pdf = p_url
                            log.info(f"  [Sci-Hub Direct] تم رصد ملف PDF مباشر: {direct_pdf}")
                            ok, s_reason = download_stream_with_resume(direct_pdf, final_path)
                            if ok and looks_like_pdf(final_path):
                                return True, f"Success (Sci-Hub Direct, {s_reason})"
                    elif r.status_code in (404, 403, 444, 500, 502, 503, 504):
                        log.info(f"  [Sci-Hub Direct] المرآة {url} غير متاحة (HTTP {r.status_code}) — الانتقال للرابط التالي مباشرة.")
                        continue
            except (requests.exceptions.RequestException, socket.timeout, ConnectionError) as e:
                log.info(f"  [Sci-Hub Direct] تعذّر الاتصال بمرآة {url} ({type(e).__name__}) — تخطي.")
                continue
            except Exception as e:
                log.debug(f"  [Sci-Hub Direct Err] {e}")

        # محاولة فحص الصفحة المصدرية مباشرة عبر HTTP واستخراج روابط PDF منها دون الحاجة للمتصفح
        try:
            direct_headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,application/pdf;q=0.8,*/*;q=0.7"
            }
            with requests.get(url, headers=direct_headers, timeout=7, allow_redirects=True, stream=True) as resp:
                c_type = resp.headers.get("Content-Type", "").lower()
                if "application/pdf" in c_type:
                    ok, s_reason = download_stream_with_resume(resp.url, final_path)
                    if ok and looks_like_pdf(final_path):
                        return True, f"Success (Direct Stream PDF, {s_reason})"
                elif "text/html" in c_type and resp.status_code == 200:
                    sample = resp.raw.read(80000).decode("utf-8", errors="ignore")
                    m_pdf = None
                    for term in ["citation_pdf_url", "bepress_citation_pdf_url", "eprints.document_url"]:
                        pat = rf'name="{term}"[^>]+content="([^"]+)"'
                        m = re.search(pat, sample, re.IGNORECASE)
                        if not m:
                            pat2 = rf'content="([^"]+)"[^>]+name="{term}"'
                            m = re.search(pat2, sample, re.IGNORECASE)
                        if m:
                            m_pdf = m
                            break
                    if m_pdf:
                        found_pdf_url = m_pdf.group(1).strip()
                        if found_pdf_url.startswith("/"):
                            u_p = urlparse(resp.url)
                            found_pdf_url = f"{u_p.scheme}://{u_p.netloc}{found_pdf_url}"
                        log.info(f"  [Direct Meta PDF] تم رصد رابط PDF مباشر: {found_pdf_url}")
                        ok, s_reason = download_stream_with_resume(found_pdf_url, final_path)
                        if ok and looks_like_pdf(final_path):
                            return True, f"Success (Direct Meta PDF, {s_reason})"
        except Exception as e:
            log.debug(f"  [Direct Meta Harvest] {e}")

        ok, reason = _download_attempt(url, entry, final_path, base_dir)
        if ok:
            if looks_like_pdf(final_path):
                return True, reason
            try:
                final_path.unlink()
            except Exception:
                pass
            reason = "Downloaded file is not a valid PDF"
        if reason.startswith(NOT_AVAILABLE) and not best:
            best = reason
    return False, best or reason


# ═════════════════════════ STATE (استئناف) ═════════════════════════
class StateStore:
    def __init__(self, path: str):
        self.path, self._lock = path, threading.Lock()
        self.data = {}
        try:
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    self.data = json.load(f)
        except Exception:
            self.data = {}

    def get(self, idx: int) -> dict:
        return self.data.get(str(idx), {})

    def set(self, idx: int, **kw):
        with self._lock:
            self.data[str(idx)] = {**self.data.get(str(idx), {}), **kw,
                                   "ts": time.strftime("%Y-%m-%d %H:%M:%S")}
            try:
                tmp = self.path + ".tmp"
                with open(tmp, "w", encoding="utf-8") as f:
                    json.dump(self.data, f, ensure_ascii=False, indent=1)
                os.replace(tmp, self.path)
            except Exception:
                pass


# ═════════════════════════ REPORTS ═════════════════════════
_RESHAPE_WARNED = False


def _shape_arabic(txt: str) -> str:
    """fpdf لا يدعم تشكيل/اتجاه العربية — نستعمل arabic_reshaper+bidi إن توفّرا."""
    global _RESHAPE_WARNED
    try:
        import arabic_reshaper
        from bidi.algorithm import get_display
        return get_display(arabic_reshaper.reshape(txt))
    except ImportError:
        if not _RESHAPE_WARNED:
            _RESHAPE_WARNED = True
            log.info("[i] لعرض العربية متصلة في تقرير PDF:  "
                     "pip install arabic-reshaper python-bidi")
        return txt
    except Exception:
        return txt


def _safe_idx(val: Any) -> int:
    try:
        return int(val)
    except (ValueError, TypeError):
        return 0


def _clean_field(val: Any, default: str = "") -> str:
    if val is None:
        return default
    s = str(val).replace("\r", " ").replace("\n", " ").strip()
    return s if s else default


def _has_arabic_text(text: str) -> bool:
    return bool(re.search(r'[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]', str(text)))


def _failure_kind(reason: str, lang: str = "ar") -> str:
    """تصنيف سبب الفشل بدقة — يُظهره التقرير في عمود مستقل قابل للفرز."""
    r = (reason or "").strip()
    if r.startswith(NOT_AVAILABLE):
        return "غير متاح للتنزيل"
    low = r.lower()
    if "html fallback" in low or "saved from html" in low:
        return "غير متاح كـ PDF أصلي"
    if "cloudflare" in low or "captcha" in low or "turnstile" in low or "blocked" in low:
        return "حماية Cloudflare/كابتشا"
    if "لا يوجد مصدر" in r or "no source" in low:
        return "بلا مصدر في ملف 0"
    if "timeout" in low or "ميزانية" in r or "deadline" in low:
        return "مهلة زمنية"
    if "abort" in low or "إلغاء" in r or "توقفت" in r or "مقاطعة" in r:
        return "تم الإلغاء / مقاطعة التشغيل"
    if "doi checker" in low:
        return "فشل فاحص الـ DOI"
    if "network" in low or "navigation" in low or "unreachable" in low or "connection" in low:
        return "تعذّر الوصول للموقع"
    if "not a valid pdf" in low or "غير صالح" in r:
        return "ملف غير صالح"
    return "Other" if lang == "en" else "أخرى"


def build_reports(report_path: str, meta: dict, failed_entries: List[dict], lang: str = "ar") -> None:
    base = os.path.dirname(report_path)
    for it in failed_entries:
        it["kind"] = _failure_kind(it.get("reason", ""), lang=lang)

    # Safe sorting by classification then numeric idx without TypeError
    sorted_failed = sorted(failed_entries, key=lambda x: (str(x.get("kind", "")), _safe_idx(x.get("idx"))))
    n_na = sum(1 for it in sorted_failed if it["kind"] in ("غير متاح للتنزيل", "Not Available for Download"))
    total_failed = len(sorted_failed)
    total_count = meta.get("total", total_failed)
    total_ok = meta.get("ok", max(0, total_count - total_failed))

    if lang == "en":
        head = f"Total: {total_count} | Success: {total_ok} | Failed/Incomplete: {total_failed} | Not Available: {n_na}"
    else:
        head = f"إجمالي: {total_count} | نجح: {total_ok} | فشل / غير مكتمل: {total_failed} | منها غير متاح للتنزيل: {n_na}"

    # 1) TXT report
    try:
        txt_path = report_path.replace(".pdf", ".txt")
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(f"{head}\n{'='*70}\n\n")
            for it in sorted_failed:
                idx_num = _safe_idx(it.get("idx"))
                idx_disp = f"#{idx_num:04d}" if idx_num > 0 else "#----"
                title = _clean_field(it.get("title"), "N/A")
                year = _clean_field(it.get("year"), "N/A")
                doi = _clean_field(it.get("doi"), "N/A")
                oa = _clean_field(it.get("oa_url"), "")
                kind = _clean_field(it.get("kind"), "Other" if lang == "en" else "أخرى")
                reason = _clean_field(it.get("reason"), "N/A")
                f.write(f"{idx_disp} - {title} ({year})\n"
                        f"DOI: {doi}\n"
                        f"OA : {oa}\n"
                        f"التصنيف: {kind}\n"
                        f"سبب الفشل: {reason}\n\n")
    except Exception as e:
        log.warning(f"تعذّر كتابة تقرير TXT: {e}")

    # 2) CSV report
    try:
        import csv
        csv_path = report_path.replace(".pdf", ".csv")
        with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
            w = csv.writer(f)
            w.writerow(["idx", "title", "year", "doi", "open_access", "kind", "reason"])
            for it in sorted_failed:
                w.writerow([
                    _safe_idx(it.get("idx")),
                    _clean_field(it.get("title"), "N/A"),
                    _clean_field(it.get("year"), "N/A"),
                    _clean_field(it.get("doi"), ""),
                    _clean_field(it.get("oa_url"), ""),
                    _clean_field(it.get("kind"), "أخرى"),
                    _clean_field(it.get("reason"), "N/A")
                ])
    except Exception as e:
        log.warning(f"تعذّر كتابة تقرير CSV: {e}")

    # 3) PDF report
    try:
        from fpdf import FPDF

        # Discover fonts from local project directories first
        search_dirs = [
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts"),
            os.path.join(base, "fonts"),
            os.path.join(config.base_dir, "fonts"),
            "C:/Windows/Fonts",
            "/usr/share/fonts/truetype/dejavu"
        ]
        reg_font, bold_font = None, None
        for sdir in search_dirs:
            if not os.path.isdir(sdir):
                continue
            amiri_r = os.path.join(sdir, "Amiri-Regular.ttf")
            amiri_b = os.path.join(sdir, "Amiri-Bold.ttf")
            if os.path.exists(amiri_r):
                reg_font = amiri_r
                bold_font = amiri_b if os.path.exists(amiri_b) else amiri_r
                break
            deja_r = os.path.join(sdir, "DejaVuSans.ttf")
            deja_b = os.path.join(sdir, "DejaVuSans-Bold.ttf")
            if os.path.exists(deja_r):
                reg_font = deja_r
                bold_font = deja_b if os.path.exists(deja_b) else deja_r
                break
            arial_p = os.path.join(sdir, "arial.ttf")
            if os.path.exists(arial_p):
                reg_font = arial_p
                bold_p = os.path.join(sdir, "arialbd.ttf")
                bold_font = bold_p if os.path.exists(bold_p) else arial_p
                break

        pdf = FPDF(format="A4")
        pdf.set_auto_page_break(auto=True, margin=16)

        font_family = "Ar"
        if reg_font and os.path.exists(reg_font):
            pdf.add_font(font_family, "", reg_font)
            pdf.add_font(font_family, "B", bold_font or reg_font)
        else:
            font_family = "helvetica"

        pdf.add_page()

        def line(txt, h=6, align="R", wrap="WORD"):
            try:
                pdf.set_x(pdf.l_margin)
                pdf.multi_cell(pdf.epw, h, txt, align=align,
                               new_x="LMARGIN", new_y="NEXT", wrapmode=wrap)
            except Exception:
                try:
                    sanitized = "".join(c if ord(c) < 256 else "?" for c in str(txt))
                    pdf.set_x(pdf.l_margin)
                    pdf.multi_cell(pdf.epw, h, sanitized, align=align,
                                   new_x="LMARGIN", new_y="NEXT", wrapmode=wrap)
                except Exception as e:
                    log.debug(f"[Report] تخطّي سطر: {e}")
                    try:
                        pdf.set_x(pdf.l_margin)
                    except Exception:
                        pass

        pdf.set_font(font_family, "B", 20)
        pdf.set_text_color(20, 20, 90)
        line(_shape_arabic("تقرير تنزيل ملفات PDF والأبحاث المتعذّرة"), h=14, align="C")

        pdf.set_font(font_family, "", 11)
        pdf.set_text_color(0, 0, 0)
        line(_shape_arabic(head), h=7, align="C")
        line(f"Total: {total_count}   |   Downloaded: {total_ok}   |   "
             f"Failed/Incomplete: {total_failed}   |   Not available: {n_na}   |   "
             f"{time.strftime('%Y-%m-%d %H:%M')}", h=6, align="C")
        pdf.ln(3)

        if sorted_failed:
            kinds = {}
            for it in sorted_failed:
                k_name = it.get("kind") or "أخرى"
                kinds[k_name] = kinds.get(k_name, 0) + 1

            pdf.set_text_color(0, 0, 0)
            pdf.set_font(font_family, "B", 12)
            line(_shape_arabic("ملخّص أسباب التعذّر:"), h=8, align="R")
            pdf.set_font(font_family, "", 10)
            for k, n in sorted(kinds.items(), key=lambda t: -t[1]):
                line(_shape_arabic(f"— {k}: {n}"), h=5.5, align="R")
            pdf.ln(4)

            pdf.set_text_color(160, 20, 20)
            pdf.set_font(font_family, "B", 13)
            line(_shape_arabic("الأوراق التي تعذّر تنزيلها (تفاصيل كاملة):"), h=9, align="R")
            pdf.ln(2)

            for it in sorted_failed:
                if pdf.get_y() > (pdf.h - 45):
                    pdf.add_page()

                idx_num = _safe_idx(it.get("idx"))
                idx_disp = f"#{idx_num:04d}" if idx_num > 0 else "#----"
                title_val = _clean_field(it.get("title"), "Unknown Title")
                year_val = _clean_field(it.get("year"), "N/A")
                kind_val = _clean_field(it.get("kind"), "أخرى")
                reason_val = _clean_field(it.get("reason"), "N/A")
                doi_val = _clean_field(it.get("doi"), "")
                oa_val = _clean_field(it.get("oa_url"), "")

                is_ar_title = _has_arabic_text(title_val)
                title_line = f"{idx_disp} - {title_val}"
                pdf.set_text_color(160, 20, 20)
                pdf.set_font(font_family, "B", 11)
                if is_ar_title:
                    line(_shape_arabic(title_line), align="R")
                else:
                    line(title_line, align="L")

                pdf.set_text_color(60, 60, 60)
                pdf.set_font(font_family, "", 10)
                line(_shape_arabic(f"السنة: {year_val}  |  التصنيف: {kind_val}"), align="R")

                if doi_val:
                    pdf.set_text_color(0, 90, 190)
                    line(f"DOI: {doi_val}", align="L", wrap="CHAR")
                if oa_val:
                    pdf.set_text_color(0, 120, 60)
                    line(f"OA : {oa_val}", align="L", wrap="CHAR")

                pdf.set_text_color(180, 50, 50)
                is_ar_reason = _has_arabic_text(reason_val)
                if is_ar_reason:
                    line(_shape_arabic(f"سبب الفشل: {reason_val}"), align="R")
                else:
                    line(f"Reason: {reason_val}", align="L")

                pdf.set_draw_color(220, 220, 220)
                pdf.line(pdf.l_margin, pdf.get_y() + 1, pdf.w - pdf.r_margin, pdf.get_y() + 1)
                pdf.ln(3)
        else:
            pdf.set_text_color(20, 120, 40)
            pdf.set_font(font_family, "B", 14)
            if lang == "en": line("All papers downloaded successfully.", h=10, align="C")
            else: line(_shape_arabic("تم تنزيل جميع الأوراق بنجاح."), h=10, align="C")

        pdf.output(report_path)
        log.info(f"[+] تقرير PDF: {os.path.basename(report_path)}")
    except Exception as e:
        log.warning(f"تعذّر توليد تقرير PDF ({e}) — التقريران TXT و CSV جاهزان.")


# ═════════════════════════ FILE 0 DISCOVERY ═════════════════════════
def find_file0(base_dir: str) -> Optional[str]:
    """
    [إصلاح] القديم كان يلتقط الملفات المنزَّلة نفسها (مثل 0100_xxx.pdf تطابق *00_*.pdf)
    ويرتّب بالأحدث → في التشغيل الثاني قد يعتبر ورقة منزَّلة هي «ملف 0».
    """
    out_abs = os.path.abspath(config.output_dir) if config.output_dir else ""
    cands = []
    for p in glob.glob(os.path.join(base_dir, "**", "*.pdf"), recursive=True):
        ap = os.path.abspath(p)
        if out_abs and (ap.startswith(out_abs + os.sep) or ap == out_abs):
            continue
        name = os.path.basename(ap)
        if re.match(r"^\d{4}_", name):          # نمط الملفات المنزَّلة
            continue
        if name == config.report_name:
            continue
        cands.append(ap)

    exact = [p for p in cands if os.path.basename(p).lower().startswith("00_")]
    pool = exact or [p for p in cands
                     if re.search(r"00[_\- ]", os.path.basename(p))
                     or "openaccess" in os.path.basename(p).lower().replace(" ", "")]
    if not pool:
        return None
    return sorted(pool, key=os.path.getmtime, reverse=True)[0]


# ═════════════════════════ MAIN ═════════════════════════
def _install_signal_handlers():
    def handler(signum, frame):
        if STOP.is_set():
            log.warning("إيقاف قسري.")
            os._exit(1)
        log.warning("طلب إيقاف — إنهاء المهام الجارية بأمان (اضغط Ctrl+C ثانية للإيقاف الفوري) …")
        STOP.set()
    for sig in (signal.SIGINT, getattr(signal, "SIGTERM", signal.SIGINT)):
        try:
            signal.signal(sig, handler)
        except Exception:
            pass


def main() -> int:
    ap = argparse.ArgumentParser(description="منزّل أبحاث — Production Grade 13.1")
    ap.add_argument("--dir", default=None, help="مجلد العمل (افتراضياً مجلد السكربت)")
    ap.add_argument("--file0", default=None, help="مسار ملف 0 صراحةً")
    ap.add_argument("--out", default=None, help="مجلد الحفظ")
    ap.add_argument("--workers", type=int, default=None, help="عدد الخيوط المتوازية")
    ap.add_argument("--profile", default=None, help="اسم/مجلد بروفايل Chrome (بلا سؤال)")
    ap.add_argument("--limit", type=int, default=0, help="حدّ عدد الأوراق (للاختبار)")
    ap.add_argument("--only", default="", help="فهارس محددة، مثال: 1,5,9-12")
    ap.add_argument("--retry-failed", action="store_true", help="إعادة محاولة الفاشلة فقط")
    ap.add_argument("--no-watchdog", action="store_true", help="تعطيل حارس msdt.exe")
    ap.add_argument("--no-zai", action="store_true", help="تعطيل حل الكابتشا عبر Z.ai")
    ap.add_argument("--no-html-fallback", action="store_true", help="عدم حفظ الصفحة كـ PDF")
    ap.add_argument("--no-research-check", action="store_true",
                    help="إلغاء بوابة «هل الصفحة بحث؟» (Abstract + Introduction) قبل حفظ HTML")
    ap.add_argument("--min-chars", type=int, default=None,
                    help=f"أقل طول نصّي لصفحة بحث مقبولة (افتراضياً {config.html_min_text_chars})")
    ap.add_argument("--sections", type=int, default=None,
                    help="عدد الأقسام الأكاديمية الإضافية المطلوبة (Methods/Results/…)")
    ap.add_argument("--min-gap", type=int, default=None,
                    help=f"أقل نثر بين Introduction والقسم التالي "
                         f"(افتراضياً {config.research_min_gap})")
    ap.add_argument("--no-consent", action="store_true", help="عدم إزالة لافتات الكوكيز")
    ap.add_argument("--timeout", type=int, default=None, help="المهلة الصلبة لكل رابط (ثوانٍ)")
    args = ap.parse_args()

    base_dir = os.path.abspath(args.dir or os.path.dirname(os.path.abspath(__file__)))
    config.base_dir = base_dir
    config.output_dir = os.path.abspath(args.out or os.path.join(base_dir, "downloaded_pdfs"))
    config.staging_dir = os.path.join(config.output_dir, config.staging_dirname)
    if args.workers:
        config.max_workers = max(1, min(8, args.workers))
    if args.timeout:
        config.hard_timeout = max(30, args.timeout)
    if args.profile:
        config.chrome_profile = args.profile
    if args.no_watchdog:
        config.kill_msdt_watchdog = False
    if args.no_zai:
        config.solve_captcha_with_zai = False
    if args.no_html_fallback:
        config.allow_html_fallback = False
    if args.no_research_check:
        config.require_research_markers = False
    if args.no_consent:
        config.dismiss_consent = False
    if args.min_chars:
        config.html_min_text_chars = max(500, args.min_chars)
    if args.sections is not None:
        config.research_min_sections = max(0, args.sections)
    if args.min_gap is not None:
        config.research_min_gap = max(0, args.min_gap)

    Path(config.output_dir).mkdir(parents=True, exist_ok=True)
    Path(config.staging_dir).mkdir(parents=True, exist_ok=True)
    setup_logging(base_dir)
    _install_signal_handlers()

    log.info("=" * 66)
    log.info("  منزّل ملفات PDF — Production Grade 13.1")
    log.info(f"  مجلد العمل : {base_dir}")
    log.info(f"  مجلد الحفظ : {config.output_dir}")
    log.info(f"  بوابة «صفحة بحث» : "
             f"{'مُفعَّلة' if config.require_research_markers else 'مُعطَّلة'}"
             f" (Abstract + Introduction + {config.research_min_sections} قسم، "
             f"≥ {config.html_min_text_chars} حرف)")
    log.info("=" * 66)

    f0 = args.file0 or find_file0(base_dir)
    if not f0 or not os.path.exists(f0):
        log.error(f"[X] لم يُعثر على «ملف 0» في: {base_dir}")
        log.error("    ضع ملفاً باسم يبدأ بـ 00_ (مثل 00_OpenAccessLinks.pdf) أو استخدم --file0")
        return 1
    log.info(f"[i] ملف 0: {os.path.basename(f0)}")

    entries = parse_entries(f0)
    if not entries:
        log.error("[X] لم يُستخرج أي مدخل من ملف 0.")
        log.error("    تأكد من تثبيت قارئ PDF:  pip install pymupdf")
        return 1

    # فلترة اختيارية
    if args.only:
        wanted = set()
        for part in args.only.split(","):
            part = part.strip()
            if "-" in part:
                a, b = part.split("-", 1)
                if a.strip().isdigit() and b.strip().isdigit():
                    wanted.update(range(int(a), int(b) + 1))
            elif part.isdigit():
                wanted.add(int(part))
        entries = [e for e in entries if e["idx"] in wanted]

    state = StateStore(os.path.join(config.output_dir, config.state_name))
    if args.retry_failed:
        entries = [e for e in entries if state.get(e["idx"]).get("status") != "ok"]
    if args.limit:
        entries = entries[:args.limit]

    total = len(entries)
    if total == 0:
        log.warning("لا توجد أوراق للمعالجة.")
        return 0
    log.info(f"[i] عدد الأوراق: {total} | خيوط: {config.max_workers} | "
             f"مهلة الرابط: {config.hard_timeout}s")

    watchdog = None
    if config.kill_msdt_watchdog and sys.platform == "win32":
        watchdog = MsdtWatchdog()
        watchdog.start()

    no_src = sum(1 for e in entries if not FallbackProvider.get_urls(e))
    if no_src:
        log.warning(f"[!] {no_src} ورقة بلا أي رابط (DOI و Open Access = N/A) — "
                    f"ستظهر في تقرير الفشل بسبب واضح.")

    counters = {"ok": 0, "failed": 0, "skipped": 0}
    failed_entries, lock = [], threading.Lock()
    t0 = time.time()

    try:
        with ThreadPoolExecutor(max_workers=config.max_workers,
                                thread_name_prefix="w") as executor:
            futures = {executor.submit(download_one, e, base_dir): e for e in entries}
            for n, future in enumerate(as_completed(futures), 1):
                entry = futures[future]
                try:
                    success, msg = future.result()
                except Exception as e:
                    success, msg = False, f"{type(e).__name__}: {e}"

                if success:
                    if "Skipped" in msg:
                        counters["skipped"] += 1
                    counters["ok"] += 1
                    state.set(entry["idx"], status="ok", note=msg,
                              file=safe_filename(entry))
                    log.info(f"[OK]   ({n}/{total}) #{entry['idx']:04d} — {msg}")
                else:
                    counters["failed"] += 1
                    state.set(entry["idx"], status="failed", note=msg)
                    with lock:
                        failed_entries.append({**entry, "reason": msg})
                    log.error(f"[FAIL] ({n}/{total}) #{entry['idx']:04d} — {msg}")
    except KeyboardInterrupt:
        STOP.set()
        log.warning("تم الإيقاف بواسطة المستخدم.")
    finally:
        STOP.set()
        browser_manager.quit_all()
        if watchdog and watchdog.kills:
            log.info(f"[Guard] عدد مرات إغلاق نافذة التشخيص: {watchdog.kills}")
        shutil.rmtree(config.staging_dir, ignore_errors=True)

    # Reconcile all entries to ensure every undownloaded paper is in failed_entries
    successful_indices = set()
    for e in entries:
        target_f = Path(config.output_dir) / safe_filename(e)
        if looks_like_pdf(target_f):
            successful_indices.add(e.get("idx"))

    failed_dict = {}
    for it in failed_entries:
        idx_val = it.get("idx")
        if idx_val not in successful_indices:
            failed_dict[idx_val] = it

    for e in entries:
        idx_val = e.get("idx")
        if idx_val not in successful_indices and idx_val not in failed_dict:
            st = state.get(idx_val) if state else {}
            reason = st.get("note") or ("تم الإلغاء قبل المعالجة" if STOP.is_set() else "لم يكتمل التنزيل")
            failed_dict[idx_val] = {**e, "reason": reason}

    failed_entries = list(failed_dict.values())
    counters["ok"] = len(successful_indices)
    counters["failed"] = len(failed_entries)

    meta = {"total": total, "out": config.output_dir, **counters}
    build_reports(os.path.join(base_dir, config.report_name), meta, failed_entries)

    n_na = sum(1 for it in failed_entries
               if str(it.get("reason", "")).startswith(NOT_AVAILABLE))
    mins = (time.time() - t0) / 60
    log.info("=" * 66)
    log.info(f"[+] اكتمل خلال {mins:.1f} دقيقة | نجح: {counters['ok']} "
             f"(منها {counters['skipped']} موجودة مسبقاً) | فشل: {counters['failed']}")
    if n_na:
        log.info(f"[i] {n_na} ورقة صُنِّفت «غير متاحة للتنزيل» (الصفحة ليست بحثاً كاملاً) "
                 f"— التفاصيل في التقرير.")
    if _ZAI_STATE["disabled"]:
        log.info(f"[i] حلّ الكابتشا عبر Z.ai كان مُعطَّلاً: {_ZAI_STATE['reason']}")
    log.info(f"[+] الملفات في: {config.output_dir}")
    log.info("=" * 66)
    return 0 if counters["failed"] == 0 else 2


def run_fulltext_scraper(
    file0_or_entries: Union[str, List[dict]],
    output_dir: str,
    base_dir: Optional[str] = None,
    max_workers: int = 2,
    hard_timeout: int = 90,
    progress_callback: Optional[Callable[[int, int, str], None]] = None,
    stop_check: Optional[Callable[[], bool]] = None,
    lang: str = "ar"
) -> dict:
    """
    الدالة البرمجية المدمجة في موقع محيط المعرفة لتنزيل الأبحاث الكاملة (Full-Text Scraper).
    - تلغي حفظ واجهات HTML كـ PDF نهائياً (allow_html_fallback = False).
    - تنزّل فقط ملفات الـ PDF الحقيقية المعتمدة وتتحقق من تواقيعها.
    - تصدر تقريراً تفصيلياً بالحالات الناجحة والفاشلة وسبب كل منها.
    """
    STOP.clear()
    base_dir = os.path.abspath(base_dir or os.path.dirname(os.path.abspath(__file__)))
    config.base_dir = base_dir
    config.output_dir = os.path.abspath(output_dir)
    config.staging_dir = os.path.join(config.output_dir, config.staging_dirname)
    config.max_workers = max(1, min(4, max_workers))
    config.hard_timeout = max(30, hard_timeout)
    config.allow_html_fallback = False  # ضمان حازم لإلغاء حفظ واجهات HTML
    config.kill_msdt_watchdog = True

    Path(config.output_dir).mkdir(parents=True, exist_ok=True)
    Path(config.staging_dir).mkdir(parents=True, exist_ok=True)
    setup_logging(base_dir)

    log.info("=" * 66)
    log.info("  [Knowledge Ocean] بدء تشغيل سكرابر تنزيل الأبحاث الكاملة...")
    log.info(f"  مجلد الحفظ: {config.output_dir}")
    log.info("  تنزيل واجهات HTML: مُعطَّل تماماً (PDF حقيقي فقط)")
    log.info("=" * 66)

    entries = []
    if isinstance(file0_or_entries, str):
        if os.path.exists(file0_or_entries):
            entries = parse_entries(file0_or_entries)
    elif isinstance(file0_or_entries, list):
        for idx, p in enumerate(file0_or_entries, 1):
            if isinstance(p, dict):
                entries.append({
                    "idx": p.get("idx", idx),
                    "title": (p.get("title") or f"paper_{idx}")[:200],
                    "year": str(p.get("year") or ""),
                    "doi": (p.get("doi") or "").strip(),
                    "oa_url": (p.get("oa_url") or "").strip()
                })

    if not entries:
        log.warning("لم يتم تمرير أو استخراج أي أوراق بحثية للتنزيل.")
        return {
            "total": 0, "ok": 0, "failed": 0, "skipped": 0,
            "files": [], "report_path": None
        }

    total = len(entries)
    log.info(f"[i] عدد الأوراق المستهدفة للتنزيل: {total} | خيوط: {config.max_workers} | مهلة: {config.hard_timeout}s")

    watchdog = None
    if config.kill_msdt_watchdog and sys.platform == "win32":
        try:
            watchdog = MsdtWatchdog()
            watchdog.start()
        except Exception:
            pass

    counters = {"ok": 0, "failed": 0, "skipped": 0}
    failed_entries, lock = [], threading.Lock()
    state = StateStore(os.path.join(config.output_dir, config.state_name))
    t0 = time.time()

    try:
        with ThreadPoolExecutor(max_workers=config.max_workers, thread_name_prefix="w") as executor:
            futures = {executor.submit(download_one, e, base_dir): e for e in entries}
            for n, future in enumerate(as_completed(futures), 1):
                if stop_check and stop_check():
                    STOP.set()
                    break

                entry = futures[future]
                try:
                    success, msg = future.result()
                except Exception as e:
                    success, msg = False, f"{type(e).__name__}: {e}"

                if success:
                    if "Skipped" in msg:
                        counters["skipped"] += 1
                    counters["ok"] += 1
                    state.set(entry["idx"], status="ok", note=msg, file=safe_filename(entry))
                    log.info(f"[OK]   ({n}/{total}) #{entry['idx']:04d} — {msg}")
                else:
                    counters["failed"] += 1
                    state.set(entry["idx"], status="failed", note=msg)
                    with lock:
                        failed_entries.append({**entry, "reason": msg})
                    log.error(f"[FAIL] ({n}/{total}) #{entry['idx']:04d} — {msg}")

                if progress_callback:
                    try:
                        status_str = ("Downloaded" if success else "Unavailable") if lang == "en" else ("تم التنزيل" if success else "تعذّر")
                        progress_callback(n, total, f"#{entry['idx']:04d} {status_str}: {entry.get('title','')[:40]}")
                    except Exception:
                        pass
    except Exception as e:
        log.error(f"خطأ أثناء حلقة تنزيل الأبحاث: {e}")
        STOP.set()
    finally:
        STOP.set()
        browser_manager.quit_all()
        if watchdog and watchdog.kills:
            log.info(f"[Guard] عدد مرات إغلاق نافذة التشخيص: {watchdog.kills}")
        shutil.rmtree(config.staging_dir, ignore_errors=True)

    # Reconcile all entries to ensure every undownloaded paper is in failed_entries
    successful_indices = set()
    for e in entries:
        target_f = Path(config.output_dir) / safe_filename(e)
        if looks_like_pdf(target_f):
            successful_indices.add(e.get("idx"))

    failed_dict = {}
    for it in failed_entries:
        idx_val = it.get("idx")
        if idx_val not in successful_indices:
            failed_dict[idx_val] = it

    for e in entries:
        idx_val = e.get("idx")
        if idx_val not in successful_indices and idx_val not in failed_dict:
            st = state.get(idx_val) if state else {}
            reason = st.get("note") or ("تم الإلغاء قبل المعالجة" if STOP.is_set() else "لم يكتمل التنزيل")
            failed_dict[idx_val] = {**e, "reason": reason}

    failed_entries = list(failed_dict.values())
    counters["ok"] = len(successful_indices)
    counters["failed"] = len(failed_entries)

    meta = {"total": total, "out": config.output_dir, **counters}
    rep_path = os.path.join(config.output_dir, config.report_name)
    try:
        build_reports(rep_path, meta, failed_entries)
    except Exception as e:
        log.warning(f"تعذّر إنشاء تقارير التنزيل: {e}")

    downloaded = []
    for p in Path(config.output_dir).glob("*.pdf"):
        if p.name != config.report_name and looks_like_pdf(p):
            downloaded.append(str(p))
    downloaded.sort()

    mins = (time.time() - t0) / 60
    log.info(f"[+] اكتمل سكرابر الأبحاث الكاملة خلال {mins:.1f} دقيقة | ناجح: {counters['ok']} | فشل: {counters['failed']}")

    return {
        "total": total,
        "ok": counters["ok"],
        "failed": counters["failed"],
        "skipped": counters["skipped"],
        "files": downloaded,
        "report_path": rep_path if os.path.exists(rep_path) else None
    }


if __name__ == "__main__":
    try:
        sys.exit(main() or 0)
    except KeyboardInterrupt:
        sys.exit(130)
