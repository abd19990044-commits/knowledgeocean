"""Build the public, bilingual Knowledge Ocean handbooks.

Install requirements.txt and requirements-guides.txt, then run this script.
Arabic is wrapped in logical order before each line is shaped and displayed RTL.
No account credentials or deployment secrets are included in these documents.
"""
import json
from pathlib import Path
from tempfile import TemporaryDirectory

import arabic_reshaper
from bidi.algorithm import get_display
from pypdf import PdfReader, PdfWriter
from pypdf.generic import DictionaryObject, NameObject, TextStringObject
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "static" / "guides"
SITE = "https://salam1234561-knowledgeocean.hf.space/"
NAVY = colors.HexColor("#102B43")
TEAL = colors.HexColor("#007E80")
INK = colors.HexColor("#253C4B")
MUTED = colors.HexColor("#607785")
PALE = colors.HexColor("#EDF7F6")
WIDTH, HEIGHT = A4
MARGIN = 49
TEXT_WIDTH = WIDTH - 2 * MARGIN

PAGES = json.loads((ROOT / "scripts" / "user_guides.json").read_text(encoding="utf-8"))


def visual(text, language):
    if language == "ar":
        return get_display(arabic_reshaper.reshape(text), base_dir="R")
    return text


def wrapped(text, font, size, width, language):
    lines, current = [], ""
    for word in text.split():
        candidate = (current + " " + word).strip()
        if current and pdfmetrics.stringWidth(visual(candidate, language), font, size) > width:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    return lines


def text_at(pdf, text, y, language, size=12, bold=False, color=INK, x=None):
    font = ("AmiriBold" if bold else "Amiri") if language == "ar" else ("SansBold" if bold else "Sans")
    pdf.setFont(font, size)
    pdf.setFillColor(color)
    display = visual(text, language)
    if language == "ar":
        pdf.drawRightString(x if x is not None else WIDTH - MARGIN, y, display)
    else:
        pdf.drawString(x if x is not None else MARGIN, y, display)


def make_guide(language):
    OUTPUT.mkdir(parents=True, exist_ok=True)
    filename = OUTPUT / ("KnowledgeOcean_User_Guide_" + language.upper() + ".pdf")
    with TemporaryDirectory() as temp:
        raw = Path(temp, "guide.pdf")
        pdf = canvas.Canvas(str(raw), pagesize=A4, pageCompression=1)
        pdf.setTitle("دليل استخدام محيط المعرفة" if language == "ar" else "Knowledge Ocean User Guide")
        pdf.setAuthor("Knowledge Ocean")
        for page_no, (eyebrow, title, subtitle, blocks) in enumerate(PAGES[language], 1):
            pdf.setFillColor(NAVY)
            pdf.rect(0, HEIGHT - 35, WIDTH, 35, stroke=0, fill=1)
            pdf.setFont("SansBold", 9)
            pdf.setFillColor(colors.white)
            pdf.drawString(MARGIN, HEIGHT - 23, "KNOWLEDGE OCEAN")
            pdf.drawRightString(WIDTH - MARGIN, HEIGHT - 23, "USER HANDBOOK / " + language.upper())
            text_at(pdf, eyebrow, HEIGHT - 70, language, 10.5, True, TEAL)
            title_font = "AmiriBold" if language == "ar" else "SansBold"
            title_size = 27 if language == "ar" else 23
            while pdfmetrics.stringWidth(visual(title, language), title_font, title_size) > TEXT_WIDTH:
                title_size -= 0.5
            text_at(pdf, title, HEIGHT - 108, language, title_size, True, NAVY)
            text_at(pdf, subtitle, HEIGHT - 136, language, 12.2 if language == "ar" else 10.1, color=MUTED)
            pdf.setStrokeColor(colors.HexColor("#C4DCDB"))
            pdf.line(MARGIN, HEIGHT - 155, WIDTH - MARGIN, HEIGHT - 155)
            y = HEIGHT - 184
            for block in blocks:
                heading, body = block[:2]
                code = len(block) == 3 and block[2] == "code"
                text_at(pdf, heading, y, language, 14 if language == "ar" else 11.7, True, TEAL)
                y -= 25 if language == "ar" else 22
                if code:
                    pdf.setFillColor(PALE)
                    pdf.roundRect(MARGIN, y - 15, TEXT_WIDTH, 33, 6, stroke=0, fill=1)
                    pdf.setFont("Sans", 10.4)
                    pdf.setFillColor(NAVY)
                    pdf.drawString(MARGIN + 13, y - 3, body)
                    y -= 38
                else:
                    font = "Amiri" if language == "ar" else "Sans"
                    size = 12.1 if language == "ar" else 10.4
                    leading = 19.8 if language == "ar" else 16.6
                    for line in wrapped(body, font, size, TEXT_WIDTH, language):
                        text_at(pdf, line, y, language, size)
                        y -= leading
                    y -= 17 if language == "ar" else 19
            if y < 72:
                raise ValueError(f"Page {page_no} in {language} overflows: {y:.1f}")
            key = language + str(page_no)
            pdf.bookmarkPage(key)
            pdf.addOutlineEntry(title, key, level=0)
            pdf.setStrokeColor(colors.HexColor("#DCE5EA"))
            pdf.line(MARGIN, 49, WIDTH - MARGIN, 49)
            pdf.setFont("Sans", 8)
            pdf.setFillColor(MUTED)
            pdf.drawString(MARGIN, 32, "Knowledge Ocean | October 2026")
            pdf.drawRightString(WIDTH - MARGIN, 32, str(page_no) + " / " + str(len(PAGES[language])))
            pdf.linkURL(SITE, (MARGIN, 21, MARGIN + 190, 43), relative=0)
            pdf.showPage()
        pdf.save()
        reader = PdfReader(raw)
        writer = PdfWriter()
        writer.clone_document_from_reader(reader)
        writer._root_object[NameObject("/Lang")] = TextStringObject("ar-IQ" if language == "ar" else "en-US")
        writer._root_object[NameObject("/ViewerPreferences")] = DictionaryObject({
            NameObject("/Direction"): NameObject("/R2L" if language == "ar" else "/L2R")
        })
        with filename.open("wb") as target:
            writer.write(target)
    print(f"{filename.relative_to(ROOT)}: {len(reader.pages)} pages, {filename.stat().st_size} bytes")


if __name__ == "__main__":
    for name, filename in (("Amiri", "Amiri-Regular.ttf"), ("AmiriBold", "Amiri-Bold.ttf"), ("Sans", "DejaVuSans.ttf"), ("SansBold", "DejaVuSans-Bold.ttf")):
        pdfmetrics.registerFont(TTFont(name, str(ROOT / "fonts" / filename)))
    for lang in ("ar", "en"):
        make_guide(lang)
