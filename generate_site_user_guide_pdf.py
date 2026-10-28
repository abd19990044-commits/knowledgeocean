# -*- coding: utf-8 -*-
"""
مولد ملف PDF: دليل استخدام منصة محيط المعرفة الشامل للباحثين
Knowledge Ocean — Comprehensive Platform User Manual
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

class SiteUserGuidePDF(FPDF):
    def __init__(self):
        super().__init__(format="A4", orientation="P", unit="mm")
        self.set_auto_page_break(auto=False)
        self.add_font("Amiri", "", FONT_REG)
        self.add_font("Amiri", "B", FONT_BOLD)
        self.set_font("Amiri", "", 10)
        self.doc_title = "دليل استخدام منصة محيط المعرفة الأكاديمية — KNOWLEDGE OCEAN"

    def header(self):
        if self.page_no() == 1:
            return
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
        self.cell(self.epw / 2, 5, "Knowledge Ocean 2.0 | Complete User Manual", align="L")
        
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
            prefix = "[ ميزة متقدمة ] : "
        elif box_type == "warning":
            bg_col = (254, 252, 232)
            border_col = (234, 179, 8)
            title_col = (161, 98, 7)
            prefix = "[ إرشاد وتوجيه ] : "
        else: # info
            bg_col = (240, 249, 255)
            border_col = (14, 165, 233)
            title_col = (3, 105, 161)
            prefix = "[ معلومة هامة ] : "

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

    def draw_feature_card(self, title: str, subtitle: str, description: str):
        """بطاقة ميزة منظمة وأنيقة."""
        y = self.get_y()
        needed_h = 16.5

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

        self.set_y(y + needed_h + 2.2)


def generate_guide():
    pdf = SiteUserGuidePDF()
    pdf.alias_nb_pages()

    # =========================================================================
    # الصفحة 1: الغلاف، الرؤية، وقواعد البيانات الـ 12 المعتمدة
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
    pdf.cell(pdf.epw, 7, ar("دليل الاستخدام الشامل للمنصة ومحرك البحث الأكاديمي الموحد"), align="C", new_x="LMARGIN", new_y="NEXT")

    pdf.set_font("Amiri", "", 8.5)
    pdf.set_text_color(203, 213, 225) # Slate-300
    pdf.cell(pdf.epw, 5.5, ar("المرجع الكامل للباحثين: الفهرسة الأكاديمية، البحث البولياني، وتوليد استشهادات APA 7th و BibTeX"), align="C", new_x="LMARGIN", new_y="NEXT")

    pdf.set_y(44)

    # شارة التعريف
    pdf.set_fill_color(248, 250, 252)
    pdf.set_draw_color(226, 232, 240)
    pdf.rect(pdf.l_margin, pdf.get_y(), pdf.epw, 12, style="FD")
    pdf.set_xy(pdf.l_margin + 2, pdf.get_y() + 1)
    pdf.set_font("Amiri", "B", 8.5)
    pdf.set_text_color(71, 85, 105)
    meta_1 = "المحرك: الاتحاد الأكاديمي الموحد (12 قاعدة بيانات عالمية)   |   الإصدار: v9.5 الأكاديمي"
    meta_2 = "المخرجات: استشهادات قياسية للوورد + ملفات BibTeX/RIS + نصوص كاملة PDF + حزم ZIP"
    pdf.cell(pdf.epw - 4, 5, ar(meta_1), align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(pdf.epw - 4, 5, ar(meta_2), align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_y(pdf.get_y() + 3)

    # القسم 1
    pdf.draw_section_title("مقدمة ورؤية منصة محيط المعرفة", "1")
    p1 = ("منصة 'محيط المعرفة' هي محرك بحث وفهرسة أكاديمي متقدم، صُمم خصيصاً للباحثين وطلاب الدراسات العليا "
          "والمؤسسات الأكاديمية. على خلاف محركات الويب العامة التي تمزج المقالات التجارية بالإعلانات، يتصل محيط المعرفة "
          "مباشرة بالمستودعات العلمية العالمية والمجلات المحكمة لاسترجاع الأبحاث الموثقة وتوفير نصوصها الكاملة واستشهاداتها القياسية.")
    pdf.write_ar_paragraph(p1, size=9)

    # القسم 2: قواعد البيانات
    pdf.draw_section_title("قواعد البيانات والمستودعات المعرفية المدعومة", "2")

    # جدول قواعد البيانات
    table_y = pdf.get_y()
    col1_w = 48
    col2_w = pdf.epw - col1_w

    pdf.set_fill_color(30, 41, 59)
    pdf.rect(pdf.l_margin, table_y, pdf.epw, 6.2, style="F")

    pdf.set_xy(pdf.l_margin + col2_w, table_y + 0.4)
    pdf.set_font("Amiri", "B", 8.8)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(col1_w, 5.5, ar("المستودع / قاعدة البيانات"), align="C")

    pdf.set_xy(pdf.l_margin, table_y + 0.4)
    pdf.cell(col2_w, 5.5, ar("التخصص والدور في محرك البحث"), align="C")
    pdf.set_y(table_y + 6.4)

    dbs_info = [
        ("Crossref", "المصدر الرئيسي للمعرفات الرقمية (DOI) وتفاصيل المجلدات والسنوات والمجلات."),
        ("Unpaywall", "كشف واسترجاع الروابط المباشرة للنصوص الكاملة المفتوحة (Open Access PDFs) قانونياً."),
        ("OpenAlex", "أضخم فهرس معرفي عالمي للأبحاث الأكاديمية والملخصات وتصنيف المؤسسات والجامعات."),
        ("Europe PMC", "مستودع الأبحاث الطبية والحيوية وعلوم الصحة والأدوية مع ملخصات كاملة."),
        ("PubMed / NCBI", "المرجع العالمي الرائد للطب السريري والعلوم الحيوية والجينات."),
        ("Semantic Scholar", "الذكاء الاصطناعي لتحليل الاستشهادات واكتشاف صلة الأوراق البحثية وأثرها العلمي."),
        ("DataCite", "فهرسة الأوراق البحثية، ومجموعات البيانات العلمية متعددة التخصصات."),
        ("ArXiv", "أحدث المسودات العلمية والأبحاث قيد النشر في الفيزياء والرياضيات والذكاء الاصطناعي."),
        ("Scholarly Registry", "سجل مدمج خاص بالأوراق العلمية التراثية والمؤتمرات غير المسجلة بـ DOI رقمي.")
    ]

    for idx, (dbname, dbdesc) in enumerate(dbs_info):
        row_y = pdf.get_y()
        bg = (248, 250, 252) if idx % 2 == 0 else (255, 255, 255)
        pdf.set_fill_color(*bg)
        pdf.set_draw_color(226, 232, 240)
        pdf.rect(pdf.l_margin, row_y, pdf.epw, 5.8, style="FD")

        pdf.set_xy(pdf.l_margin + col2_w, row_y + 0.3)
        pdf.set_font("Courier", "B", 8)
        pdf.set_text_color(15, 23, 42)
        pdf.cell(col1_w, 5.2, dbname, align="C")

        pdf.set_xy(pdf.l_margin, row_y + 0.3)
        pdf.set_font("Amiri", "", 8.3)
        pdf.set_text_color(51, 65, 85)
        pdf.cell(col2_w - 2, 5.2, ar(dbdesc), align="R")
        pdf.set_y(row_y + 5.8)

    # =========================================================================
    # الصفحة 2: أنماط وتقنيات البحث المتقدمة
    # =========================================================================
    pdf.add_page()
    pdf.draw_section_title("أنماط وتقنيات البحث في المنصة", "3")

    pdf.write_ar_paragraph(
        "تتيح المنصة أربعة أنماط متكاملة للبحث لتلبية كافة احتياجات الباحث، من الاستعلام السريع إلى التدقيق المرجعي المباشر:",
        size=9, bold=True
    )
    pdf.ln(1)

    pdf.draw_feature_card(
        "البحث السريع بالكلمات المفتاحية (Keyword Search)", "النمط الافتراضي",
        "اكتب المصطلحات الأكاديمية بلغتك أو بالإنجليزية، ويقوم المحرك باستعلام القواعد العالمية بالتوازي وترتيب النتائج بالأكثر صلة."
    )

    pdf.draw_feature_card(
        "البحث المباشر بمعرّف DOI (Direct DOI Lookup)", "دقة 100%",
        "ضع معرّف البحث مثل 10.1016/j.chroma.2017.03.059، لجلب بيانات الورقة فوراً وتوليد استشهادها والوصول لنصها الكامل."
    )

    pdf.draw_feature_card(
        "البحث بعنوان الورقة الدقيق (Exact Title Match)", "أولوية العنوان",
        "ابحث بعنوان البحث كاملاً؛ يمنح النظام وزناً فائقاً للتطابق اللفظي التام ويرفع الورقة تلقائياً إلى صدارة النتائج."
    )

    pdf.draw_feature_card(
        "البحث المتقدم بالمعاملات البوليانية (Boolean Search)", "تحليل نحوي صارم",
        "يدعم النظام المعاملات AND و OR و NOT والأقواس المتداخلة وعلامات الاقتباس دون أي قيود."
    )

    pdf.draw_callout_box("دليل المعاملات البوليانية (Boolean Operators Guide)",
        "• المعامل AND: يربط بين مفهومين ويشترط وجودهما معاً (مثال: 'Machine Learning AND Healthcare').\n"
        "• المعامل OR: يوسع البحث ليشمل أحد المفهومين (مثال: 'Cancer OR Neoplasm').\n"
        "• المعامل NOT: يستبعد مصطلحات غير مرغوبة من النتائج (مثال: 'Transformers NOT Electrical').\n"
        "• علامات التنصيص \" \": للبحث عن عبارة متطابقة تماماً (مثال: \"Deep Residual Learning\").\n"
        "• الأقواس ( ): لتحديد أولوية التنفيذ الرياضي (مثال: '(AI OR ML) AND Agriculture').",
        box_type="info")

    pdf.draw_section_title("أدوات الفلترة والتخصيص الأكاديمي", "4")

    pdf.draw_feature_card(
        "التصفية الزمنية (Year Range Filter)", "من سنة إلى سنة",
        "حدد سنة النشر الأولى والأخيرة لحصر نتائج البحث في أحدث ما تم نشره خلال السنوات الأخيرة أو لتغطية فترة تاريخية محددة."
    )

    pdf.draw_feature_card(
        "فلتر المسودات العلمية (Include Preprints)", "أوراق محكمة فقط",
        "خيار لتضمين أو استبعاد المسودات غير المحكمة (مثل arXiv) في حال رغبت في حصر النتائج في المجلات المراجعة بالأقران حصراً."
    )

    pdf.draw_feature_card(
        "البحث بحسب الجامعة أو المؤسسة (Affiliation)", "المراكز العلمية",
        "اكتب اسم الجامعة أو المؤسسة الأكاديمية لحصر الأبحاث الصادرة عن باحثيها ومختبراتها التابعة."
    )

    # =========================================================================
    # الصفحة 3: الاستشهادات والتصدير وإدارة المراجع
    # =========================================================================
    pdf.add_page()
    pdf.draw_section_title("توليد الاستشهادات وإدارة المراجع الأكاديمية", "5")

    pdf.write_ar_paragraph(
        "يوفر محيط المعرفة محرك استشهادات قياسي متطور يلتزم بالدقة الحرفية لمعايير النشر العالمية:",
        size=9, bold=True
    )
    pdf.ln(1)

    pdf.draw_callout_box("قواعد الاستشهاد القياسي الصارم APA 7th Edition",
        "1) خط التوثيق المعتمد: تم ضبط المخرج ليلائم خط Times New Roman بحجم 14pt المعتمد في الجامعات.\n"
        "2) التنسيق البصري: اسم المجلة مائل (Italic) ورقم المجلد عريض (Bold) متبوعاً برقم العدد والصفحات ورابط DOI الحي.\n"
        "3) حالة الجملة الحذرة (Sentence Case): معالجة عناوين الأبحاث مع الحفاظ التام على الأسماء العلمية والمركبات الكيميائية.\n"
        "4) نقاء التوثيق: خالٍ تماماً من النجوم التنسيقية (**) ومن النقاط المزدوجة (..) التي تشوه بحوث الوورد.\n"
        "5) زر 'نسخ للوورد': نقرة واحدة تنسخ النص المنسق والمبني برمجياً ليُلصق في Microsoft Word مباشرة بأعلى دقة.",
        box_type="success")

    pdf.draw_feature_card(
        "تصدير واستيراد بصيغة BibTeX (.bib)", "جاهز لـ LaTeX",
        "توليد ملفات ومقاطع BibTeX منسقة وموثوقة، جاهزة للنسخ أو التحميل المباشر للعمل على Overleaf ومحررات TeX."
    )

    pdf.draw_feature_card(
        "تصدير بصيغة RIS (.ris)", "مديرو المراجع",
        "تصدير متوافق بنقرة واحدة مع برامج إدارة المراجع العالمية: EndNote و Zotero و Mendeley."
    )

    pdf.draw_feature_card(
        "الفهرس الأكاديمي المجمع (Index PDF)", "تقرير مجمع",
        "توليد مستند PDF منسق يضم ملخصات الأبحاث المسترجعة، وأسماء المؤلفين، والمجلات، مع روابط الوصول المفتوح."
    )

    pdf.draw_feature_card(
        "الحزمة الكاملة المضغوطة (Full Research ZIP)", "أرشيف متكامل",
        "تجميع تقارير PDF، وملفات BibTeX و RIS، ومسودات Markdown في حزمة ZIP واحدة للتحميل برابط مباشر."
    )

    pdf.draw_section_title("نظام العضوية والصلاحيات والحصص اليومية", "6")

    pdf.draw_callout_box("أنماط الوصول وحصص الاستخدام",
        "• وضع الباحث الزائر (Guest Mode): متاح مجاناً للجميع بدون تسجيل. يتيح تصفح النتائج والملخصات، وتوليد استشهادات APA 7th، "
        "مع حصة يومية تبلغ 100 فحص DOI تتجدد تلقائياً عند منتصف ليل بغداد (Baghdad Time 00:00).\n"
        "• وضع الباحث المتميز (VIP Mode): يتم تفعيله بإدخال رمز الوصول السري المعتمد (Access Password). يتيح هذا الوضع "
        "استخداماً غير محدود، وإمكانية تنزيل حزم ZIP الشاملة وتقارير النصوص الكاملة.\n"
        "• نظام الحماية من إساءة الاستخدام: عند إدخال رمز غير صحيح 5 مرات متتالية، يُحظر عنوان الـ IP لمدة 24 ساعة لحماية الخادم.",
        box_type="warning")

    # =========================================================================
    # الصفحة 4: واجهة المستخدم، بيئات التشغيل، وأفضل الممارسات
    # =========================================================================
    pdf.add_page()
    pdf.draw_section_title("ميزات واجهة المستخدم والتفاعل الذكي", "7")

    pdf.draw_feature_card(
        "شارة نسبة تطابق العنوان (Title Match %)", "ذكاء اصطناعي",
        "يحلل النظام درجة تطابق عنوان الورقة مع استعلامك ويظهر شارة ملونة توضح نسبة الدقة من 1% إلى 100%."
    )

    pdf.draw_feature_card(
        "شارات الوصول المفتوح (Open Access Badge)", "تحميل مجاني",
        "تظهر شارة خضراء مميزة عند توفر النص الكامل مجاناً مع زر مباشر يفتح ملف الـ PDF الأصلي بنقرة واحدة."
    )

    pdf.draw_feature_card(
        "راصد حالة الاتصال التلقائي (Heartbeat Banner)", "استقرار فوري",
        "يراقب المتصفح حالة الخادم لحظياً؛ وفي حال انقطاع الشبكة يظهر تنبيه ينبض ويستأنف الاتصال تلقائياً فور عودتها."
    )

    pdf.draw_feature_card(
        "دعم الوضع الليلي والنهاري (Dark / Light Theme)", "راحة العين",
        "واجهة متناسقة بألوان مريحة للعين تدعم التبديل السلس بين المظهر الداكن الملكي والمظهر النهاري النقي."
    )

    pdf.draw_section_title("النسخ والبيئات المتاحة لتشغيل محيط المعرفة", "8")

    pdf.draw_callout_box("خيارات التوزيع والتشغيل للمنصة",
        "1) النسخة السحابية العالمية (Hugging Face Spaces): متاحة أونلاين عبر المتصفح على مدار الساعة لكافة الباحثين حول العالم.\n"
        "2) النسخة المحلية المستقلة (Local Web App): خادم محلي يشتغل على جهاز الباحث بنقرة زر عبر ملف run_local.bat.\n"
        "3) النسخة التنفيذية المحمية عتادياً (Media Dongle Locked EXE): تطبيق سطح مكتب مشفر مقيد بـ (CD / DVD / FLASH).",
        box_type="info")

    pdf.draw_section_title("أفضل النصائح للباحثين للحصول على أفضل النتائج", "9")

    tips = [
        ("• استخدم المصطلحات باللغة الإنجليزية للأبحاث العالمية:",
         "معظم قواعد البيانات العالمية (Crossref, PubMed, arXiv) تفهرس العناوين والملخصات بالإنجليزية بشكل أوسع."),
        ("• استفد من ميزة البحث المباشر بـ DOI:",
         "إذا كان لديك رقم الـ DOI لبحث معين، ضعه في شريط البحث لتحصل على استشهاد APA 7th الدقيق مع رابط التحميل المباشر فوراً."),
        ("• راجع الاستشهاد بنقرة واحدة للوورد:",
         "اضغط على زر 'نسخ APA 7th للوورد'، وسيتم حفظه في الحافظة بخط Times New Roman 14pt مائل ومضبوط وجاهز للصق.")
    ]

    for t_head, t_body in tips:
        pdf.write_ar_paragraph(t_head, size=8.8, bold=True, color=(15, 23, 42), line_h=4.8)
        pdf.write_ar_paragraph(t_body, size=8.4, bold=False, color=(71, 85, 105), line_h=4.5)
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
    seal_text = "محيط المعرفة (Knowledge Ocean) — رفيق الباحث العلمي في الفهرسة والتوثيق الأكاديمي المعتمد"
    pdf.cell(pdf.epw - 4, 4.5, ar(seal_text), align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Amiri", "", 8)
    pdf.set_text_color(100, 116, 139)
    pdf.cell(pdf.epw - 4, 4.0, "Knowledge Ocean 2.0 • Official Comprehensive Platform User Guide", align="C")

    output_path = "دليل_استخدام_محيط_المعرفة_للباحثين.pdf"
    pdf.output(output_path)
    print("User guide PDF build successful!")
    return output_path

if __name__ == "__main__":
    generate_guide()
