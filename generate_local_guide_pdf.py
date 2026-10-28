# -*- coding: utf-8 -*-
"""
مولد ملف PDF: دليل استخدام منصة وتطبيق محيط المعرفة مع التركيز على التطبيق المحلي
Knowledge Ocean — Dedicated Local Application & Platform User Manual
تصميم متناسق عالي الاحترافية مكون من 4 صفحات متوازنة ومراجعة بصرياً.
"""
import os
import sys
import re
from fpdf import FPDF
import arabic_reshaper
from bidi.algorithm import get_display

FONT_REG = "fonts/Amiri-Regular.ttf"
FONT_BOLD = "fonts/Amiri-Bold.ttf"

def ar(text: str) -> str:
    """إعادة تشكيل وترتيب النص العربي للعرض السليم من اليمين لليسار."""
    if not text:
        return ""
    clean = re.sub(r'[ \t]+', ' ', str(text)).strip()
    return get_display(arabic_reshaper.reshape(clean))

class LocalGuidePDF(FPDF):
    def __init__(self):
        super().__init__(format="A4", orientation="P", unit="mm")
        self.set_auto_page_break(auto=False) # تحكم دقيق ومتوازن بالصفحات لمنع الطفرات
        self.add_font("Amiri", "", FONT_REG)
        self.add_font("Amiri", "B", FONT_BOLD)
        self.set_font("Amiri", "", 10)
        self.doc_title = "دليل استخدام وتشغيل التطبيق المحلي — محيط المعرفة (Knowledge Ocean)"

    def header(self):
        if self.page_no() == 1:
            return  # الغلاف له ترويسة رئيسية خاصة
        self.set_xy(self.l_margin, 7)
        self.set_font("Amiri", "", 8.5)
        self.set_text_color(100, 116, 139) # Slate-500
        self.cell(self.epw, 5, ar(self.doc_title), align="R", new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(203, 213, 225) # Slate-300
        self.set_line_width(0.3)
        self.line(self.l_margin, 13.5, self.w - self.r_margin, 13.5)
        self.set_y(16)

    def footer(self):
        self.set_y(-13)
        self.set_font("Amiri", "", 8.5)
        self.set_text_color(148, 163, 184) # Slate-400
        self.set_draw_color(226, 232, 240)
        self.set_line_width(0.2)
        self.line(self.l_margin, self.get_y() - 1, self.w - self.r_margin, self.get_y() - 1)
        
        self.set_xy(self.l_margin, -11)
        self.cell(self.epw / 2, 5, "Knowledge Ocean 2.0 | Local & Desktop Manual", align="L")
        
        page_str = f"صفحة {self.page_no()} من {{nb}}"
        self.set_xy(self.l_margin + self.epw / 2, -11)
        self.cell(self.epw / 2, 5, ar(page_str), align="R")

    def draw_section_title(self, title_ar: str, icon_num: str = "1"):
        """رسم عنوان قسم رئيسي أنيق مع شريط لوني جانبي."""
        self.ln(2)
        y = self.get_y()
        self.set_fill_color(14, 116, 144) # Cyan-700
        self.rect(self.w - self.r_margin - 3.5, y, 3.5, 8.5, style="F")
        
        self.set_fill_color(241, 245, 249) # Slate-100
        self.rect(self.l_margin, y, self.epw - 4.5, 8.5, style="F")
        
        self.set_xy(self.l_margin, y + 0.8)
        self.set_font("Amiri", "B", 11.5)
        self.set_text_color(15, 23, 42) # Slate-900
        full_title = f"[ {icon_num} ]  {title_ar}"
        self.cell(self.epw - 6, 7, ar(full_title), align="R")
        self.set_y(y + 11)

    def write_ar_paragraph(self, text: str, size: float = 9.2, bold: bool = False, 
                           color=(30, 41, 59), line_h: float = 5.5, align: str = "R"):
        """كتابة فقرة عربية مع التفاف الكلمات السليم دون انعكاس الأسطر."""
        self.set_font("Amiri", "B" if bold else "", size)
        self.set_text_color(*color)
        max_w = self.epw
        words = text.split()
        current_line = []
        
        for word in words:
            test_line = " ".join(current_line + [word])
            reshaped_test = ar(test_line)
            if self.get_string_width(reshaped_test) <= max_w:
                current_line.append(word)
            else:
                if current_line:
                    line_str = " ".join(current_line)
                    self.cell(max_w, line_h, ar(line_str), align=align, new_x="LMARGIN", new_y="NEXT")
                current_line = [word]
                
        if current_line:
            line_str = " ".join(current_line)
            self.cell(max_w, line_h, ar(line_str), align=align, new_x="LMARGIN", new_y="NEXT")

    def draw_callout_box(self, title: str, text: str, box_type: str = "info"):
        """صندوق تنبيه أو إرشاد ملون."""
        if box_type == "danger":
            bg_col = (254, 242, 242)
            border_col = (239, 68, 68)
            title_col = (185, 28, 28)
            prefix = "[ تنبيه أمني ] : "
        elif box_type == "success":
            bg_col = (240, 253, 244)
            border_col = (34, 197, 94)
            title_col = (21, 128, 61)
            prefix = "[ ميزة حصرية للنسخة المحلية ] : "
        elif box_type == "warning":
            bg_col = (254, 252, 232)
            border_col = (234, 179, 8)
            title_col = (161, 98, 7)
            prefix = "[ إرشاد وتوجيه ] : "
        else: # info
            bg_col = (240, 249, 255)
            border_col = (14, 165, 233)
            title_col = (3, 105, 161)
            prefix = "[ معلومة فنية ] : "

        words = text.split()
        lines = []
        curr = []
        inner_w = self.epw - 10
        self.set_font("Amiri", "", 8.8)
        for w in words:
            t = " ".join(curr + [w])
            if self.get_string_width(ar(t)) <= inner_w:
                curr.append(w)
            else:
                if curr: lines.append(" ".join(curr))
                curr = [w]
        if curr: lines.append(" ".join(curr))
        
        box_h = 7.5 + (len(lines) * 4.9) + 2
        y = self.get_y()

        self.set_fill_color(*bg_col)
        self.set_draw_color(*border_col)
        self.set_line_width(0.35)
        self.rect(self.l_margin, y, self.epw, box_h, style="FD")
        
        self.set_fill_color(*border_col)
        self.rect(self.w - self.r_margin - 2.5, y, 2.5, box_h, style="F")

        self.set_xy(self.l_margin + 3, y + 1.5)
        self.set_font("Amiri", "B", 9.5)
        self.set_text_color(*title_col)
        self.cell(self.epw - 7, 5, ar(prefix + title), align="R", new_x="LMARGIN", new_y="NEXT")

        self.set_font("Amiri", "", 8.8)
        self.set_text_color(30, 41, 59)
        for line in lines:
            self.cell(self.epw - 7, 4.9, ar(line), align="R", new_x="LMARGIN", new_y="NEXT")
        self.set_y(y + box_h + 2.5)

    def draw_feature_card(self, title: str, subtitle: str, description: str, command: str = ""):
        """بطاقة ميزة منظمة وأنيقة مع سطر أوامر اختياري."""
        y = self.get_y()
        needed_h = 16.5 + (6.5 if command else 0)

        self.set_fill_color(248, 250, 252) # Slate-50
        self.set_draw_color(203, 213, 225) # Slate-300
        self.set_line_width(0.3)
        self.rect(self.l_margin, y, self.epw, needed_h, style="FD")

        badge_w = 26
        self.set_fill_color(30, 58, 138) # Blue-900
        self.rect(self.w - self.r_margin - badge_w, y, badge_w, 6.5, style="F")
        self.set_xy(self.w - self.r_margin - badge_w, y + 0.5)
        self.set_font("Amiri", "B", 8.5)
        self.set_text_color(255, 255, 255)
        self.cell(badge_w, 5.5, ar(subtitle), align="C")

        self.set_xy(self.l_margin + 4, y + 0.5)
        self.set_font("Amiri", "B", 9.8)
        self.set_text_color(15, 23, 42)
        self.cell(self.epw - badge_w - 6, 5.5, ar(title), align="R")

        self.set_xy(self.l_margin + 4, y + 6.8)
        self.set_font("Amiri", "", 8.6)
        self.set_text_color(51, 65, 85)
        self.cell(self.epw - 8, 5.5, ar(description), align="R")

        if command:
            self.set_xy(self.l_margin + 3, y + 12.8)
            self.set_fill_color(226, 232, 240)
            self.rect(self.l_margin + 3, y + 12.8, self.epw - 6, 5.5, style="F")
            self.set_font("Courier", "B", 8.5)
            self.set_text_color(15, 23, 42)
            self.cell(self.epw - 8, 5.5, f"  > {command}", align="L")

        self.set_y(y + needed_h + 2.2)


def generate_local_manual_pdf():
    pdf = LocalGuidePDF()
    pdf.alias_nb_pages()

    # =========================================================================
    # الصفحة 1: الغلاف، الرؤية المحلية، ومقارنة النسخة المحلية بالسحابية
    # =========================================================================
    pdf.add_page()

    # الترويسة الرئيسية للموقع
    pdf.set_fill_color(15, 23, 42) # Slate-900
    pdf.rect(0, 0, 210, 38, style="F")
    pdf.set_fill_color(14, 116, 144) # Cyan-600
    pdf.rect(0, 38, 210, 2.5, style="F")

    pdf.set_xy(pdf.l_margin, 7)
    pdf.set_font("Amiri", "B", 16)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(pdf.epw, 8, ar("محيط المعرفة — KNOWLEDGE OCEAN"), align="C", new_x="LMARGIN", new_y="NEXT")

    pdf.set_font("Amiri", "B", 12)
    pdf.set_text_color(125, 211, 252) # Sky-300
    pdf.cell(pdf.epw, 7, ar("دليل استخدام وتشغيل التطبيق والنسخة المحلية (Local & Desktop Edition)"), align="C", new_x="LMARGIN", new_y="NEXT")

    pdf.set_font("Amiri", "", 8.5)
    pdf.set_text_color(203, 213, 225) # Slate-300
    pdf.cell(pdf.epw, 5.5, ar("المرجع الفني والتشغيلي الشامل: الاستقلالية التامة، الخصوصية، غياب القيود، وإدارة السيرفر المحلي"), align="C", new_x="LMARGIN", new_y="NEXT")

    pdf.set_y(44)

    # شارة التعريف الفني للنسخة المحلية
    pdf.set_fill_color(248, 250, 252)
    pdf.set_draw_color(226, 232, 240)
    pdf.rect(pdf.l_margin, pdf.get_y(), pdf.epw, 12, style="FD")
    pdf.set_xy(pdf.l_margin + 2, pdf.get_y() + 1)
    pdf.set_font("Amiri", "B", 8.5)
    pdf.set_text_color(71, 85, 105)
    meta_1 = "البيئة المستهدفة: Windows 10 / Windows 11   |   المحرك المحلي: FastAPI + Uvicorn + SQLite WAL"
    meta_2 = "أنماط التشغيل: ويب محلي (run_local.bat)  •  نافذة سطح مكتب (run_desktop.bat)  •  مثبت مقفل (Setup_Locked.exe)"
    pdf.cell(pdf.epw - 4, 5, ar(meta_1), align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(pdf.epw - 4, 5, ar(meta_2), align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_y(pdf.get_y() + 3)

    # القسم 1
    pdf.draw_section_title("مقدمة: لماذا التطبيق والنسخة المحلية هي الخيار الأمثل للباحث؟", "1")
    p1 = ("تم تصميم النسخة والتطبيق المحلي من 'محيط المعرفة' لتمنح الباحث الأكاديمي بيئة بحثية متكاملة "
          "ومستقلة تماماً تعمل على جهازه الشخصي دون الاعتماد على خوادم سحابية مشتركة. تتيح لك النسخة المحلية "
          "الاستفادة من القوة الكاملة لـ 12 قاعدة بيانات أكاديمية عالمية مع الحفاظ على سرية أبحاثك وبياناتك، وتجاوز "
          "كافة قيود الاستخدام اليومية المفروضة على النسخ العامة عبر الإنترنت.")
    pdf.write_ar_paragraph(p1, size=9)

    # القسم 2: المزايا الحصرية
    pdf.draw_section_title("المزايا الحصرية للتطبيق والنسخة المحلية", "2")

    pdf.draw_callout_box("الخصوصية والأمان المطلق (Complete Privacy)",
        "• لا يتم إرسال استعلامات بحثك أو موضوعات رسالتك العلمية إلى أي خادم وسيط تابع لجهة خارجية.\n"
        "• تتم كافة عمليات المعالجة الببليوغرافية، واستخراج النصوص، وفهرسة الملخصات، وتوليد الاستشهادات داخل حاسوبك محلياً.\n"
        "• تحفظ سجلات المهام وتاريخ التنزيلات في قاعدة بيانات داخلية SQLite مشفرة في مجلد التطبيق.",
        box_type="success")

    pdf.draw_callout_box("غياب القيود والحصص اليومية (Zero Rate-Limits & Quotas)",
        "• على عكس النسخة السحابية المقيدة بـ 100 فحص DOI يومياً للضيوف، تعمل النسخة المحلية بصلاحية غير محدودة.\n"
        "• يمكنك فحص آلاف المعرفات، وتنزيل مئات الأوراق البحثية، وبناء حزم ZIP ضخمة في أي وقت دون انتظار تجديد الحصص.\n"
        "• لا توجد طوابير انتظار مع مستخدمين آخرين؛ فالمعالج وموارد جهازك مخصصة بالكامل لأبحاثك وحدك.",
        box_type="success")

    pdf.draw_callout_box("السرعة الفائقة والحفظ المباشر على القرص الصلب (Local File Storage)",
        "• تحفظ كافة ملفات الـ PDF المفتوحة، وفهارس الاستشهادات، وملفات BibTeX و RIS مباشرة في مجلد downloads داخل جهازك.\n"
        "• سرعة فائقة في استعراض النتائج والملخصات لعدم وجود تأخير شبكي بين المتصفح والخادم.",
        box_type="info")

    # =========================================================================
    # الصفحة 2: طرق تشغيل التطبيق المحلي وشرح ملف الإعدادات
    # =========================================================================
    pdf.add_page()
    pdf.draw_section_title("طرق تشغيل التطبيق المحلي (3 خيارات متكاملة)", "3")

    pdf.write_ar_paragraph(
        "يوفر محيط المعرفة 3 طرق مرنة لتشغيل النسخة المحلية على حاسوبك بحسب طبيعة استخدامك:",
        size=9, bold=True
    )
    pdf.ln(1)

    pdf.draw_feature_card(
        "1. الخادم المحلي عبر المتصفح (Web Mode)", "نقرة واحدة تلقائية",
        "شغل ملف run_local.bat؛ يقوم آلياً بفحص بايثون وتهيئة البيئة الافتراضية وفتح المتصفح على الرابط http://localhost:7860/.",
        command="run_local.bat"
    )

    pdf.draw_feature_card(
        "2. تطبيق سطح المكتب المستقل بنوافذ ويندوز (Desktop App)", "بدون متصفح خارجي",
        "شغل run_desktop.bat لإطلاق التطبيق كنافذة ويندوز مدمجة نقية (Native WebView2) بدون أشرطة متصفح وبإغلاق آلي نظيف.",
        command="run_desktop.bat"
    )

    pdf.draw_feature_card(
        "3. المثبت المقفل والمحمي عتادياً (Hardware Dongle EXE)", "تثبيت رسمي مشفر",
        "الملف التنفيذي KnowledgeOcean_Setup_Locked.exe الذي يُثبت البرنامج ويفك تشفيره حصراً من وسيط الحماية (CD/DVD/FLASH).",
        command="KnowledgeOcean_Setup_Locked.exe"
    )

    pdf.draw_section_title("ملف الإعدادات المحلي (config.txt) وشرح خياراته", "4")

    pdf.write_ar_paragraph(
        "يحتوي مجلد التطبيق على ملف نصي باسم config.txt يمكنك تعديله بالمفكرة لتخصيص بيئة عملك:",
        size=9, bold=True
    )
    pdf.ln(1)

    # جدول الإعدادات
    table_y = pdf.get_y()
    col1_w = 46
    col2_w = pdf.epw - col1_w

    pdf.set_fill_color(30, 41, 59)
    pdf.rect(pdf.l_margin, table_y, pdf.epw, 6.2, style="F")

    pdf.set_xy(pdf.l_margin + col2_w, table_y + 0.4)
    pdf.set_font("Amiri", "B", 8.8)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(col1_w, 5.5, ar("المتغير في config.txt"), align="C")

    pdf.set_xy(pdf.l_margin, table_y + 0.4)
    pdf.cell(col2_w, 5.5, ar("الوظيفة والأثر في تشغيل البرنامج"), align="C")
    pdf.set_y(table_y + 6.4)

    configs_info = [
        ("APP_PASSWORD = 123", "رمز الوصول المحلي. في النسخة المحلية تكون الصلاحيات مفتوحة VIP تلقائياً دون الحاجة لكتابته."),
        ("UNPAYWALL_EMAIL", "بريدك الأكاديمي؛ يُستخدم في بروتوكول Polite Pool لتسريع جلب نصوص Open Access المجانية."),
        ("ELSEVIER_API_KEY", "مفتاح Scopus / Elsevier لمن يملكون اشتراكاً جامعياً لجلب أبحاث دار النشر مباشرة (اختياري)."),
        ("SEMANTIC_SCHOLAR_KEY", "مفتاح API اختياري لرفع حدود وسرعة الاستعلام في قاعدة Semantic Scholar للذكاء الاصطناعي."),
        ("DOWNLOAD_DIR", "المسار المحلي لحفظ ملفات الـ PDF والـ ZIP الناتجة (الافتراضي هو مجلد downloads داخل التطبيق).")
    ]

    for idx, (cname, cdesc) in enumerate(configs_info):
        row_y = pdf.get_y()
        bg = (248, 250, 252) if idx % 2 == 0 else (255, 255, 255)
        pdf.set_fill_color(*bg)
        pdf.set_draw_color(226, 232, 240)
        pdf.rect(pdf.l_margin, row_y, pdf.epw, 5.8, style="FD")

        pdf.set_xy(pdf.l_margin + col2_w, row_y + 0.3)
        pdf.set_font("Courier", "B", 7.6)
        pdf.set_text_color(15, 23, 42)
        pdf.cell(col1_w, 5.2, cname, align="C")

        pdf.set_xy(pdf.l_margin, row_y + 0.3)
        pdf.set_font("Amiri", "", 8.3)
        pdf.set_text_color(51, 65, 85)
        pdf.cell(col2_w - 2, 5.2, ar(cdesc), align="R")
        pdf.set_y(row_y + 5.8)

    pdf.draw_callout_box("الربط مع قواعد بيانات Scopus و Elsevier",
        "إذا كانت جامعتك أو مؤسستك تمتلك اشتراكاً في ScienceDirect / Scopus، ضع مفتاح الـ API الخاص بك في ملف config.txt.\n"
        "سيقوم محيط المعرفة بالاتصال الفوري بدار إلسيفير واسترجاع بيانات الأبحاث المفهرسة المحكمة بكامل تفاصيلها.",
        box_type="warning")

    # =========================================================================
    # الصفحة 3: محركات البحث، الاستشهادات القياسية للوورد، وإدارة المراجع
    # =========================================================================
    pdf.add_page()
    pdf.draw_section_title("محرك البحث الأكاديمي والاتحاد المعرفي (12 قاعدة بيانات)", "5")

    pdf.write_ar_paragraph(
        "يربط التطبيق المحلي محركات البحث العالمية بالتوازي مع قواطع دارة مستقلة لمنع أي تجميد أثناء البحث:",
        size=9, bold=True
    )
    pdf.ln(1)

    pdf.draw_callout_box("أنماط الاستعلام المدعومة في التطبيق المحلي",
        "• استعلام DOI الفوري (Direct DOI Lookup): ضع معرّف البحث مثل 10.1016/j.chroma.2017.03.059، لجلب الورقة فوراً بدقة 100%.\n"
        "• مطابقة العنوان الدقيق (Exact Title Match): خوارزمية ذكية ترفع الورقة المطابقة لفظياً للمرتبة الأولى مع نسبة التطابق.\n"
        "• البحث بالمعاملات البوليانية (Boolean AST Parser): دعم كامل لـ AND و OR و NOT والأقواس ( ) وعلامات الاقتباس \" \".\n"
        "• فلاتر متقدمة: تحديد نطاق سنوات النشر، حظر أو تضمين المسودات غير المحكمة (Preprints)، والبحث حسب الجامعة التابعة.",
        box_type="info")

    pdf.draw_section_title("توليد الاستشهادات القياسية المعتمدة للوورد (Word APA 7th)", "6")

    pdf.write_ar_paragraph(
        "تمت هندسة محرك استشهادات محيط المعرفة ليتوافق بدقة صارمة مع المعايير الجامعية لرسائل الماجستير والدكتوراه:",
        size=9, bold=True
    )
    pdf.ln(1)

    pdf.draw_callout_box("المواصفات الصارمة لاستشهاد APA 7th Edition في التطبيق المحلي",
        "1) خط التوثيق الجامعي: مضبوط ومعتمد لخط Times New Roman بحجم 14pt المعتمد في الجامعات العربية والعالمية.\n"
        "2) التنسيق الببليوغرافي: اسم المجلة مائل (Italic)، ورقم المجلد عريض (Bold)، ورقم العدد بين قوسين مع الصفحات ورابط DOI الحي.\n"
        "3) حالة الجملة الذكية (Smart Sentence Case): صياغة العناوين مع حماية تامة للرموز والمركبات الكيميائية (NaCl, mRNA, DFT).\n"
        "4) النقاء المطلق: خالٍ تماماً من النجوم التنسيقية (**) ومن النقاط المزدوجة (..) التي تظهر كعيوب في برامج أخرى.\n"
        "5) زر 'نسخ للوورد': نقرة واحدة تنسخ التوثيق المنسق إلى الحافظة بصيغة HTML مهيأة للصق المباشر في Microsoft Word.",
        box_type="success")

    pdf.draw_feature_card(
        "تصدير واستيراد بصيغة BibTeX (.bib)", "جاهز لـ LaTeX",
        "توليد ملفات ومقاطع BibTeX قياسية قابلة للنسخ أو التنزيل المباشر للاستخدام مع محررات TeX ورسائل LaTeX الأكاديمية."
    )

    pdf.draw_feature_card(
        "تصدير بصيغة RIS (.ris) المباشر", "مديرو المراجع",
        "تصدير بنقرة واحدة لملفات .ris لدمج المراجع في مكتباتك البحثية الرقمية مع كافة الحقول والمؤلفين والمجلات (Zotero/EndNote)."
    )

    # =========================================================================
    # الصفحة 4: تنزيل الأبحاث، صيانة السيرفر المحلي، واستكشاف الأخطاء
    # =========================================================================
    pdf.add_page()
    pdf.draw_section_title("حزم الأرشيف ZIP وتنزيل تقارير النصوص الكاملة", "7")

    pdf.draw_feature_card(
        "تنزيل تقارير الفهرس المجمعة (Abstract Index PDF)", "تقرير شامل",
        "يقوم التطبيق المحلي بإنشاء مستند PDF موحد يجمع ملخصات الأبحاث المسترجعة، وأسماء الباحثين، وروابط النصوص الكاملة."
    )

    pdf.draw_feature_card(
        "حزمة الأرشيف الكاملة المجمعة (Complete Research ZIP)", "حفظ فوري بضغطة زر",
        "تجميع تقارير PDF، وملفات BibTeX و RIS، ومسودات Markdown في ملف ZIP واحد يُحفظ مباشرة في مجلد downloads داخل جهازك."
    )

    pdf.draw_section_title("إدارة وصيانة السيرفر المحلي (Local Server Maintenance)", "8")

    pdf.draw_callout_box("إرشادات التحكم في الخادم المحلي وإيقافه",
        "• إيقاف الخادم: لإيقاف السيرفر المحلي في أي وقت، اضغط على مفتاحي (Ctrl + C) داخل نافذة سطر الأوامر أو أغلق النافذة ببساطة.\n"
        "• إعادة التشغيل: ما عليك سوى النقر المزدوج على run_local.bat أو run_desktop.bat لإعادة تشغيل السيرفر في أي لحظة.\n"
        "• تعارض المنافذ (Port Conflict): يعمل السيرفر على المنفذ 7860، وفي حال كان المنفذ مشغولاً، يتعامل السكربت مع الأمر تلقائياً.\n"
        "• قاعدة البيانات المحلية (academic.db): تُحفظ إعداداتك ومراجعك في قاعدة بيانات SQLite محلية تدعم نمط السرعة العالية WAL.",
        box_type="warning")

    pdf.draw_section_title("استكشاف الأخطاء الشائعة وحلولها السريعة (Troubleshooting)", "9")

    troubles = [
        ("س: ظهرت رسالة 'Python is not installed' عند تشغيل run_local.bat؟",
         "ج: يتضمن السكربت آلية تنزيل وتثبيت بايثون تلقائياً، أو يمكنك تثبيت Python 3.10+ يدوياً مع تفعيل خيار 'Add to PATH'."),
        ("س: المتصفح يظهر 'لا يمكن الوصول إلى الموقع' بعد تشغيل السكربت؟",
         "ج: انتظر بضع ثوانٍ حتى تكتمل رسالة بدء الخادم، ثم افتح الرابط يدوياً في متصفحك: http://localhost:7860/."),
        ("س: هل تستهلك النسخة المحلية باقة الإنترنت بشكل كبير؟",
         "ج: كلا، النسخة المحلية تطلب فقط النصوص والبيانات الببليوغرافية الخفيفة من قواعد البيانات، مما يوفر استهلاك البيانات."),
        ("س: هل يمكن تشغيل النسخة المحلية على أكثر من جهاز في نفس الشبكة؟",
         "ج: نعم، يمكنك فتح الرابط عبر IP جهازك المحلي متبوعاً بالمنفذ :7860 من أي هاتف أو لابتوب متصل بنفس شبكة الـ Wi-Fi.")
    ]

    for q, a in troubles:
        pdf.write_ar_paragraph(q, size=8.8, bold=True, color=(15, 23, 42), line_h=4.8)
        pdf.write_ar_paragraph(a, size=8.4, bold=False, color=(71, 85, 105), line_h=4.5)
        pdf.ln(0.8)

    # ختم الجودة والاعتماد
    pdf.ln(1.5)
    stamp_y = pdf.get_y()
    pdf.set_fill_color(241, 245, 249)
    pdf.set_draw_color(148, 163, 184)
    pdf.rect(pdf.l_margin, stamp_y, pdf.epw, 11.5, style="FD")
    pdf.set_xy(pdf.l_margin + 2, stamp_y + 1.2)
    pdf.set_font("Amiri", "B", 8.5)
    pdf.set_text_color(30, 41, 59)
    seal_text = "النسخة والتطبيق المحلي لمحيط المعرفة (Knowledge Ocean Local Edition) — خصوصية مطلقة وأداء أكاديمي فائق"
    pdf.cell(pdf.epw - 4, 4.5, ar(seal_text), align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Amiri", "", 8)
    pdf.set_text_color(100, 116, 139)
    pdf.cell(pdf.epw - 4, 4.0, "Knowledge Ocean 2.0 • Dedicated Local Application & Standalone Architecture Manual", align="C")

    output_path = "دليل_استخدام_وتشغيل_التطبيق_المحلي_محيط_المعرفة.pdf"
    pdf.output(output_path)
    print("Local manual PDF build successful!")
    return output_path

if __name__ == "__main__":
    generate_local_manual_pdf()
