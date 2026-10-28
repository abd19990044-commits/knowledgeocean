"""Build the public, bilingual Knowledge Ocean handbooks.

Install requirements.txt and requirements-guides.txt, then run this script.
Arabic is wrapped in logical order before each line is shaped and displayed RTL.
No account credentials or deployment secrets are included in these documents.
"""
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

PAGES = {
    "ar": [
        ("ابدأ من هنا", "دليل استخدام محيط المعرفة", "البحث الأكاديمي، المعرّفات، والتوثيق في مكان واحد.", [
            ("1. افتح الموقع واختر لغة الواجهة", "يمكن استخدام المنصة بالعربية أو الإنكليزية. لغة ملف الدليل مستقلة عن لغة الواجهة؛ اخترها من قائمة دليل الاستخدام ثم اضغط زر تنزيل الدليل بصيغة PDF."),
            ("2. ابدأ بموضوع محدد", "اكتب مصطلحاً علمياً واضحاً، مثل اسم مركب أو تقنية تحليل. ابدأ بخمس أو عشر نتائج، ثم وسّع البحث بعد مراجعة صلة النتائج بالموضوع."),
            ("3. اضبط البحث ثم شغّله", "اختر المصادر والسنوات ونوع الوثائق، وحدد إن كنت تحتاج الملخصات. اضغط زر بدء البحث، وانتظر اكتمال جمع البيانات وتجهيز ملف التنزيل."),
            ("الحصص اليومية", "للضيف 50 رصيداً، وللرمز الثانوي 250 رصيداً. تُحجز وحدة لكل سجل مطلوب، أو وحدتان عند طلب الملخصات؛ لذلك قد يستهلك بحث واحد عدة وحدات. يتجدد الرصيد عند منتصف الليل بتوقيت بغداد. حساب VIP لا يخضع لهذه الحصة اليومية."),
            ("خريطة هذا الدليل", "الصفحة 2: إعداد البحث. الصفحة 3: الدخول ومفتاح Elsevier. الصفحة 4: النتائج والتقارير. الصفحة 5: البحث عن DOI والاستشهادات. الصفحة 6: السجل والخصوصية وحل المشكلات."),
        ]),
        ("البحث الأكاديمي", "صمّم استعلاماً أكثر دقة", "ابدأ واسعاً، ثم ضيّق النتائج باستخدام المرشحات.", [
            ("اختر وضع البحث", "الكلمات المفتاحية مناسبة للموضوعات والمصطلحات، ووضع المؤلف مناسب لأسماء الباحثين بالأحرف الإنكليزية. وضع العبارة التامة يبحث عن صياغة محددة. يمكن الانتقال إلى مركز المعرّفات للبحث بمعرّف DOI أو بعنوان الدراسة."),
            ("استخدم العلاقات المنطقية", "يجمع AND بين موضوعين، ويوسّع OR البحث بمرادفات، ويستبعد NOT مصطلحاً. تجمع الأقواس العبارات المتصلة، وتحفظ علامات الاقتباس الكلمات كعبارة واحدة. تجنّب شروط الاستبعاد الكثيرة عند أول محاولة."),
            ("مثال قابل للتجربة", "naproxen AND (HPLC OR spectrophotometry)", "code"),
            ("اضبط السنوات والمصادر", "حدّد سنة البداية والنهاية بالترتيب الصحيح. استخدم البحث الشامل لتجميع بيانات من مصادر متعددة، أو اختر قاعدة واحدة للمقارنة. يتطلب Scopus حساب VIP؛ وقد تخضع المصادر لحدود استخدام أو صلاحيات إضافية."),
            ("ميّز النطاق من نوع الوثيقة", "النطاق يحدد الأبحاث أو الكتب أو كليهما. مرشح النوع يختار المراجعات أو التحليل التلوي أو الأبحاث الأصلية أو الكتب أو المؤتمرات. فعّل المسودات فقط إذا كنت تريد إدراج منشورات ما قبل التحكيم."),
            ("الملخصات ومرشح العنوان", "طلب الملخصات يعرض ما تتيحه بيانات المصدر، ولا يضمن وجود ملخص لكل سجل. مرشح العنوان أكثر تقييداً؛ أوقفه عند نقص النتائج. العدد المطلوب هدف للبحث؛ قد يعود عدد أقل بسبب القيود أو انتهاء المهلة."),
        ]),
        ("الدخول والمفاتيح", "حسابك ومفتاح Elsevier الشخصي", "مفتاح قاعدة البيانات مستقل عن رمز الدخول إلى المنصة.", [
            ("سجّل الدخول بالرمز الصحيح", "افتح نافذة تسجيل الدخول من أعلى الصفحة، وأدخل رمز VIP أو الرمز الثانوي الذي حصلت عليه. لا يوجد رمز افتراضي منشور في هذا الدليل. تجنّب التخمين؛ خمس محاولات خاطئة متتالية تؤدي إلى حظر مؤقت لمدة 24 ساعة."),
            ("أدخل مفتاح Elsevier اختيارياً", "في نافذة الدخول، الصق مفتاح Elsevier API الخاص بك في الحقل الاختياري. اضغط حفظ المفتاح في المتصفح، أو احفظه مع نجاح تسجيل الدخول. يمكنك حفظ المفتاح أو تعديله دون إدخال رمز الدخول مجدداً إذا كانت جلستك ما زالت فعالة."),
            ("متى يستخدم المفتاح؟", "في حساب VIP، يُرسل المفتاح المحفوظ مع طلب البحث ويُستخدم بدلاً من مفتاح المنصة عند استعلام Scopus. يُضمّن Scopus أيضاً في البحث الشامل عند توفر المفتاح. إدخال مفتاح Elsevier لا يمنح الضيف أو الرمز الثانوي صلاحية VIP."),
            ("الحفظ والحذف", "يبقى المفتاح محفوظاً في المتصفح نفسه بعد إعادة فتح الصفحة. لا ينتقل تلقائياً إلى جهاز أو متصفح آخر. زر حذف المفتاح يمسحه من المتصفح؛ تسجيل الخروج وحده لا يحذفه. إذا منع المتصفح التخزين، يظهر تنبيه بأن المفتاح متاح للجلسة فقط."),
            ("حماية المفتاح", "يُنقل المفتاح إلى الخادم عبر الاتصال المشفر ثم إلى Elsevier لتنفيذ البحث. لا يُحفظ في سجلات المهام أو قاعدة بيانات البحث أو التقارير، ولا يغيّر مفتاح مستخدم آخر. لا تنشر رموز الدخول أو مفاتيح API في GitHub أو الصور العامة."),
            ("إذا رفض Scopus الطلب", "تحقق من صلاحية المفتاح وتفعيل واجهة Scopus وحدود الاستخدام. قد يتطلب حساب Elsevier ترخيصاً أو وصولاً مؤسسياً؛ امتلاك المفتاح وحده لا يضمن كل البيانات أو النصوص الكاملة."),
        ]),
        ("النتائج والتقارير", "راجع النتائج قبل استخدامها", "المنصة تجمع البيانات الوصفية وتنسّقها لتسهيل المراجعة.", [
            ("اقرأ حالة البحث", "توضح الحالة بدء البحث وجمع البيانات وتجهيز التقرير. قد تنتهي العملية بعدد أقل من المطلوب إذا لم تتوفر سجلات كافية. عند الإيقاف، يمكن تجهيز ما جُمع بالفعل؛ إذا لم توجد نتائج بعد، تُلغى العملية دون تقرير."),
            ("استخدم مستكشف النتائج", "راجع العنوان والمؤلفين والسنة والمجلة والمصدر. صفِّ النتائج إلى المسودات أو الكتب أو المراجعات أو الوصول الحر، أو ابحث داخل القائمة بالعنوان والمؤلف والمجلة."),
            ("تحقق من التصنيف", "التصنيفات مشتقة آلياً من بيانات المصادر. غياب وسم المسودة لا يثبت التحكيم، ووسم الوصول الحر لا يضمن أن الرابط ملف PDF مباشر. تحقّق من الناشر ونوع المنشور قبل إدراجه في مراجعة علمية."),
            ("نزّل ملف النتائج", "بعد الاكتمال، اضغط زر تنزيل التقرير. يحصل الضيف عادة على تقرير PDF، بينما قد يحصل VIP على حزمة ZIP تحتوي التقارير وملفات التوثيق. افتح الملف للتحقق من المحتوى، ولا تعتمد على نجاح التنزيل وحده."),
            ("افهم محتوى التقرير", "تتضمن التقارير بيانات الأبحاث وروابطها والملخصات المتاحة إذا طُلبت. التقرير ليس نسخة من مقالات الناشر الكاملة. افتح DOI أو رابط المصدر للاطلاع على المقال وفق صلاحيات الوصول المتاحة لك."),
            ("الحصة والطلبات المتكررة", "الطلبات غير الصالحة تُرفض قبل خصم الحصة. عند نقص النتائج يُعاد الرصيد غير المستخدم، وعند فشل التصدير يُرد الرصيد المحجوز. إعادة إرسال الطلب أثناء وجود مهمة نشطة تستأنف المهمة نفسها بدلاً من إنشاء مهمة مكررة."),
        ]),
        ("المعرّفات والتوثيق", "من العنوان إلى DOI والاستشهاد", "طابق السجل العلمي، لا نسبة التشابه وحدها.", [
            ("استعلام DOI مباشر", "انتقل إلى مركز DOI، ثم أدخل المعرّف أو رابطه الكامل. راجع بيانات الدراسة والمجلة والمؤلفين والسنة والروابط التي تُرجعها المصادر. قد لا تتوفر بعض الحقول في المصدر الأصلي."),
            ("ابحث بعنوان الدراسة", "اختر مطابقة العنوان إلى DOI، والصق عنواناً كاملاً قدر الإمكان. راجع أعلى النتائج، ثم قارن العنوان والمؤلفين والسنة والمجلة قبل اعتماد المعرّف. قد تكون النتيجة المشابهة دراسة أخرى أو نسخة مسودة."),
            ("الاقتباس والتصدير", "تتيح بطاقات النتائج نسخ استشهاد APA أو بيانات BibTeX عند توفرها. يمكن استخدام BibTeX مع برامج إدارة المراجع أو LaTeX. راجع ترتيب الأسماء والعنوان والعدد والصفحات وDOI قبل التسليم الأكاديمي."),
            ("تعامل مع البيانات الناقصة", "قد يظهر مؤلف غير معروف أو سنة غير متاحة أو سجل بلا DOI. افتح صفحة الناشر للتحقق من الحقول الناقصة؛ لا تضف معرفاً تخمينياً ولا تستنتج بيانات غير موجودة في المصدر."),
            ("الوصول إلى النص الكامل", "قد تقود الروابط إلى صفحة الناشر أو مستودع مفتوح. بعض الأوراق تتطلب اشتراكاً أو دخولاً مؤسسياً. وجود DOI أو مفتاح Elsevier لا يمنح تلقائياً حق تنزيل مقال مدفوع."),
            ("مسار عملي للبحث التحليلي", "ابدأ باسم المادة وتقنية التحليل، ثم صفِّ السنوات ونوع الوثيقة. راجع العنوان والملخص والناشر، وطابق DOI، ثم صدّر المرجع. احفظ نسخة من التقرير والمراجع التي راجعتها على جهازك."),
        ]),
        ("السجل والمساعدة", "استرجع عملك وحل المشكلات", "احتفظ بنسخة محلية من الملفات التي تحتاجها لاحقاً.", [
            ("سجل الحزم", "استخدم تحديث السجل لإظهار ملفاتك، ثم افتح النتائج أو نزّل التقرير. ترتبط صلاحية الوصول بجلسة المتصفح؛ حذف بيانات الموقع أو انتهاء الجلسة قد يؤثر في الوصول إلى ملفات الضيف. تُحذف ملفات التقارير تلقائياً بعد 48 ساعة."),
            ("بيانات الخدمة", "تُحفظ استعلامات البحث والنتائج وبيانات المهام على الخادم لتوفير السجل. تُستخدم بيانات الحصة وعناوين IP لإدارة الاستخدام وحماية الدخول. حذف ملفات التقارير لا يعني بالضرورة حذف جميع سجلات قاعدة البيانات في اللحظة نفسها."),
            ("لا توجد نتائج أو البحث بطيء", "قلل شروط AND والاستبعاد، وأوقف مرشح العنوان، ووسّع السنوات أو نوع الوثيقة. جرّب مصدراً آخر أو DOI مباشراً. قد تحدّ قواعد البيانات معدل الطلبات أو تتوقف مؤقتاً؛ جرّب لاحقاً عند ظهور رسالة مزود أو مهلة انتظار."),
            ("انتهت الحصة أو مُنع التنزيل", "راجع الرصيد الظاهر وعدد السجلات المطلوبة وخيار الملخصات. يتجدد الرصيد عند منتصف الليل بتوقيت بغداد. إذا مُنع ملف قديم، استخدم المتصفح والجلسة اللذين أنشآه؛ وإن حُذف الملف بعد مدة الاحتفاظ، أعد البحث."),
            ("المفتاح لا يبقى محفوظاً", "تحقق من استخدام المتصفح نفسه ومن السماح بتخزين بيانات الموقع. التصفح الخاص أو مسح بيانات الموقع قد يزيل المفتاح. افتح نافذة الدخول، وأعد الحفظ عند الحاجة، ثم استخدم زر الحذف لإزالته من جهاز مشترك."),
            ("قبل إنهاء جلستك", "نزّل التقارير المهمة، وراجع الاستشهادات، واحذف المفتاح الشخصي إن كنت لا تريد بقاءه. اضغط زر تسجيل الخروج في أعلى الموقع لإنهاء الجلسة والعودة لوضع الضيف. يمكنك تنزيل الدليل باللغة الأخرى من القائمة نفسها."),
        ]),
    ],
    "en": [
        ("START HERE", "Knowledge Ocean User Guide", "Academic search, identifiers, and citation tools in one place.", [
            ("1. Open the site and choose a language", "Use the interface in Arabic or English. The handbook language is independent of the interface language: select it in the user-guide menu and click Download User Guide (PDF)."),
            ("2. Start with a focused topic", "Enter a compound, method, or research topic. Begin with five or ten results, review their relevance, and then expand the search."),
            ("3. Set options and launch", "Choose sources, publication years, and document types. Decide whether you need abstracts. Start the search and wait for collection and report preparation to finish."),
            ("Daily credits", "Guests receive 50 daily credits; secondary-code users receive 250. Each requested record reserves one credit, or two when abstracts are requested. One search can therefore consume several credits. Credits renew at midnight in Baghdad. VIP access has no daily credit cap."),
            ("Inside this handbook", "Page 2: search settings. Page 3: sign-in and personal Elsevier keys. Page 4: results and reports. Page 5: DOI matching and citations. Page 6: history, privacy, and troubleshooting."),
        ]),
        ("ACADEMIC SEARCH", "Build a better query", "Start broadly, then narrow the results with filters.", [
            ("Choose a search mode", "Use keywords for topics and terms, author mode for names written in Latin characters, and exact-phrase mode for a specific wording. Use the DOI hub for identifier lookup or title-to-DOI matching."),
            ("Combine terms with Boolean operators", "AND combines topics, OR adds alternatives, and NOT excludes a term. Parentheses group related terms; quotation marks keep words together as a phrase. Avoid adding too many exclusions at the start."),
            ("Try this query", "naproxen AND (HPLC OR spectrophotometry)", "code"),
            ("Set years and sources", "Enter a valid starting and ending year. Choose comprehensive search to aggregate sources or a single database for comparison. Scopus requires VIP access. Providers can impose their own request limits and access conditions."),
            ("Separate scope from document type", "Scope chooses papers, books, or both. Document type selects reviews, meta-analyses, original research, books, or conference papers. Enable preprints only when you intend to include manuscripts before peer review."),
            ("Abstracts and title filtering", "Abstract mode includes abstracts supplied by source metadata; some records have none. Strict title filtering can exclude relevant studies, so turn it off if results are sparse. The requested count is a target; time limits and provider restrictions may produce fewer results."),
        ]),
        ("ACCESS & KEYS", "Sign in and use your Elsevier key", "Your database API key is separate from your platform access code.", [
            ("Sign in with your access code", "Open Sign In at the top of the page and enter your VIP or secondary code. This handbook contains no default or personal access codes. Avoid guessing: five consecutive invalid attempts cause a temporary 24-hour IP ban."),
            ("Optionally enter an Elsevier API key", "Paste your own key into the optional field in the sign-in dialog. Choose Save Key in Browser, or save it when sign-in succeeds. You can update or save the key without re-entering your access code while your signed-in session remains active."),
            ("When the key is used", "For VIP searches, the saved personal key replaces the platform key for Scopus requests. Scopus is also included in comprehensive searches when a key is available. Supplying an Elsevier key does not give a guest or secondary-code user VIP privileges."),
            ("Saving and removing the key", "The key stays in the same browser after reopening the page. It does not automatically sync to another device or browser. Remove Key clears it; signing out alone does not. If browser storage is blocked, the interface explains that the key is available only for the current session."),
            ("How the key is handled", "The browser sends the key to the application over HTTPS, and the server forwards it to Elsevier for the search. It is not saved in search-task records, the search database, or reports, and it does not replace another user's key. Never publish credentials in GitHub or public screenshots."),
            ("If Scopus rejects the request", "Check that the key is valid, Scopus access is enabled, and its usage allowance is available. Elsevier access may require a subscription or institutional entitlement. An API key alone does not guarantee every record or full-text article."),
        ]),
        ("RESULTS & REPORTS", "Review before you reuse", "The application collects metadata and formats it for inspection.", [
            ("Read the task status", "Status messages show collection and report preparation. A search may finish below the requested count if too few eligible records are available. Stopping a task can preserve records already collected; stopping before any result is found produces no report."),
            ("Explore the results", "Check the title, authors, year, journal, and source. Filter the list to preprints, books, reviews, or open-access records, or search within the results by title, author, or journal."),
            ("Verify the classifications", "Labels are derived automatically from provider metadata. The absence of a preprint label is not proof of peer review, and an open-access label does not guarantee a direct PDF link. Verify the publisher and publication type before relying on a record."),
            ("Download your results", "After completion, select the download control. Guests normally receive a PDF report; VIP users may receive a ZIP package containing reports and citation exports. Open the downloaded file to check its contents."),
            ("Understand what is included", "Reports contain record metadata, links, and available abstracts when requested. They are not copies of the publisher's full-text articles. Follow the DOI or source link to read an article under the access rights available to you."),
            ("Credits and repeated requests", "Invalid requests are rejected before charging credits. Unused credits are refunded when fewer records are returned, and a failed export refunds the reservation. Resubmitting while your task is active resumes that task rather than starting a duplicate."),
        ]),
        ("IDENTIFIERS & CITATIONS", "From a title to a verified DOI", "Match the bibliographic record, not only its similarity score.", [
            ("Look up a DOI directly", "Open the DOI hub and enter an identifier or its full link. Review the returned title, authors, journal, year, and links. Some fields may be missing from the original source."),
            ("Match a paper title", "Choose title-to-DOI matching and paste the full title where possible. Compare the highest results with the expected authors, year, and journal before accepting a DOI. A similar title can belong to a different paper or a preprint version."),
            ("Copy and export citations", "Result cards offer APA citation copying or BibTeX data when available. Use BibTeX with a reference manager or LaTeX. Verify names, title, issue, pages, and DOI before submitting academic work."),
            ("Handle incomplete metadata", "A record can have unknown authors, an unavailable year, or no DOI. Check the publisher page for missing details. Do not invent an identifier or infer facts absent from the source."),
            ("Follow full-text links", "Links may lead to a publisher page or an open repository. Some articles require a subscription or institutional sign-in. A DOI or Elsevier key does not automatically grant permission to download a paywalled article."),
            ("A practical analytical-search workflow", "Start with the analyte and analytical technique. Refine years and document type. Review the title, abstract, and publisher, verify the DOI, and export the reference. Save local copies of the reviewed report and citations."),
        ]),
        ("HISTORY & HELP", "Recover your work and troubleshoot", "Keep local copies of files you will need later.", [
            ("Use package history", "Refresh history to see your files, then reopen results or download a report. Access is tied to your browser session; clearing site data or losing a session can affect guest-file access. Report files are deleted automatically after 48 hours."),
            ("Service data", "Search queries, results, and task data are stored on the server for history. Quota and IP data support usage limits and sign-in protection. Deleting report files does not necessarily delete every database record at the same moment."),
            ("No results or slow searches", "Reduce AND conditions and exclusions, turn off strict title filtering, and widen years or document type. Try another source or a direct DOI. Providers can throttle requests or become temporarily unavailable; retry later after a provider or timeout message."),
            ("Credits exhausted or a download denied", "Check your remaining balance, requested record count, and abstract option. Credits renew at midnight in Baghdad. For old files, use the browser and session that created them. If retention has expired, repeat the search."),
            ("A key is not retained", "Use the same browser and allow site storage. Private browsing or clearing site data can remove the key. Reopen Sign In and save it again when needed. Use Remove Key when you do not want a key to remain on a shared device."),
            ("Before you finish", "Download important reports and verify your citations. Remove the personal key if it should not remain in the browser. Select Log Out at the top of the site to end the session and return to guest mode. Download the handbook in the other language from the same menu."),
        ]),
    ],
}


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
            text_at(pdf, title, HEIGHT - 108, language, 27 if language == "ar" else 23, True, NAVY)
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
