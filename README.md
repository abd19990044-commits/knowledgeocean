---
title: محيط المعرفة — Knowledge Ocean
emoji: 🌊
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 7860
pinned: false
---

# 🌊 محيط المعرفة (Knowledge Ocean) — الإصدار الأكاديمي الموحد v9.5

محرك استرجاع وفهرسة أكاديمي متقدم ومتعدد المصادر، يجمع بين **12 قاعدة بيانات أكاديمية ومستودعاً معرفياً**:
(PubMed · CrossRef · OpenAlex · Europe PMC · Semantic Scholar · Scopus/Elsevier · DOAJ · arXiv · CORE · Zenodo · Google Books · Open Library)

يُنتج حزماً مهيكلة وشاملة بصيغة **PDF** جاهزة ومحسنة للاستخدام المباشر مع أدوات التحليل والأرشفة الأكاديمية.

---

## 🌟 الميزات الهندسية الأساسية

1. **كشف وتوجيه فوري لمعرفات الـ DOI بدقة 100% (Exact DOI Routing):**
   - توجيه مباشر لمعرفات DOI نحو نقاط النهاية المرجعية (`/works/{doi}`) في CrossRef وOpenAlex وEurope PMC وPubMed دون إهدار الموارد في بحث نصي واسع.
   - تنميط صارم لمعرفات DOI وإزالة كافة الشوائب وبوادئ الروابط وترميز الـ URL.

2. **محلل استعلامات بولياني آمن (Boolean AST Parser):**
   - يدعم المعاملات البوليانية المتقدمة: `AND`، `OR`، `NOT`، والأقواس المتداخلة `(...)`، والعبارات الدقيقة داخل علامات اقتباس `"..."`.
   - مبني بالكامل عبر شجرة تحليل نحوي عودية (Recursive-Descent AST) بدون استخدام `eval()` نهائياً.
   - حساسية للأحرف الكبيرة تميز المعاملات البوليانية الصريحة مع الحفاظ على كلمات الربط في العناوين واللغة الطبيعية.

3. **نموذج بيانات قياسي ودمج وصفي غير فاقد (CanonicalPaper & Lossless Record Linkage):**
   - دمج وصفي ذكي يختار الملخص الأكثر اكتمالاً وجودة ويراعي موثوقية المصدر.
   - حفظ مرجعية الاستشهادات المرجعية مفصلة حسب كل مزود (`citations_by_source: OpenAlex, Semantic Scholar, CrossRef`) وتتبع منشأ الحقول (`field_provenance`).
   - توثيق العلاقات بين المسودات (Preprints) والنسخ المحكّمة المنشورة كرابطين متصلين بدلاً من الدمج الأعمى.
   - اشتراط التطابق الببليوغرافي (المؤلف والسنة والمجلة) لمنع دمج أبحاث مختلفة تشترك في عناوين متطابقة.

4. **فصل تام بين صلة المحتوى وإتاحة الوصول (Decoupled Relevance Ranking):**
   - قياس صلة البحث الموضوعية بدقة بالغة (Relevance Score: 0–1000).
   - احتساب درجة الوصول الحر (Accessibility / OA Score) بصورة منفصلة لمنع تفوق ورقة ضعيفة الصلة على ورقة بالغة الأهمية.

5. **استقرار شبكي وقاطع دارة تفصيلي لكل مزود (Granular Circuit Breaker):**
   - قواطع دارة مستقلة لكل مزود تميز بدقة بين حالات `HTTP 429` (تجاوز معدل الطلب)، `401/403` (مشاكل التوثيق والصلاحيات)، `5xx` (أعطال خوادم المزود)، وحالات `Timeout`.
   - منع تجميد مسارات المعالجة وضمان استمرار باقي المحركات عند تعطل أحدها.

6. **أمان معزز والتحقق من ملكية الملفات (Strict Ownership & Safe Defaults):**
   - إزالة أي كلمات سر افتراضية غير آمنة؛ يعمل النظام تلقائياً في وضع الضيف الآمن المحمي بحصص يومية عند عدم ضبط كلمة السر.
   - مقارنة كلمات السر في زمن ثابت `hmac.compare_digest` للوقاية من هجمات التوقيت.
   - التحقق الصارم من مسارات الملفات ومنع اجتياز الأدلة (Path Traversal Protection) والتحقق من ملكية المستخدم للتحميل والحذف واسترجاع السجل.

7. **استمرارية المهام وإدارة الحصص (SQLite Persistence):**
   - حفظ حالات المهام وسجلات الاستخدام اليومي في قاعدة بيانات SQLite محلية خفيفة تدعم نمط WAL.

---

## 🔐 إعداد متغيرات البيئة والأسرار (Secrets)

| المفتاح | مطلوب؟ | الافتراضي | الوصف |
|---|---|---|---|
| `APP_PASSWORD` | اختياري | 123 (فقط عند عدم تعيين سيكرت) | رمز الدخول لوضع كبار الباحثين (VIP). عند تعيين رمز مخصص في Settings -> Variables and secrets، يتم إبطال الرمز 123 نهائياً. يستلم المستخدمون بدون رمز تقرير PDF أكاديمي مباشر مع الملخصات الكاملة وإمكانية التصفح وقراءة الملخصات داخل الموقع. |
| `UNPAYWALL_EMAIL` | اختياري | `contact@example.com` | بريد للمهذبين الأكاديميين لتسريع الوصول واسترجاع الـ Open Access. |
| `ELSEVIER_API_KEY` | اختياري | فارغ | مفتاح API لبيانات Scopus / Elsevier. |
| `SEMANTIC_SCHOLAR_API_KEY` | اختياري | فارغ | مفتاح اختياري لرفع حدود معدل Semantic Scholar. |
| `CORE_API_KEY` | اختياري | فارغ | مفتاح اختياري لمستودع CORE للأبحاث المفتوحة. |

---

## 🧪 حزمة الاختبارات المؤتمتة (Test Suite)

يحتوي المشروع على حزمة اختبارات شاملة في مجلد `tests/`:

```bash
# تشغيل كامل حزمة الاختبارات
python -m unittest discover -s tests -p "test_*.py"

# تشغيل اختبارات مرحلة محددة
python -m unittest tests/test_p0_critical.py
python -m unittest tests/test_p1_canonical.py
python -m unittest tests/test_p2_boolean.py
python -m unittest tests/test_p3_ranking.py
python -m unittest tests/test_p4_network_circuit.py
python -m unittest tests/test_p5_security_ownership.py
python -m unittest tests/test_database.py
python -m unittest tests/test_pipeline.py
```

---

## 🚀 التشغيل المحلي

```bash
# تثبيت الاعتماديات الأساسية
pip install -r requirements.txt

# (اختياري) تثبيت مكتبات معالجة النصوص الكاملة و OCR
pip install -r requirements-fulltext.txt

# تشغيل الخادم
uvicorn app:app --host 0.0.0.0 --port 7860
```
افتح المتصفح على: `http://localhost:7860`

---

## 📁 هيكلية النظام المعمارية

```
├── app.py                      # نقطة الدخول وخادم FastAPI وخط المعالجة المتوازي
├── identifiers.py              # تنميط وكشف معرفات DOI و PMCID و arXiv
├── models.py                   # السجل القياسي CanonicalPaper وإثراء البيانات الوصفية
├── dedup.py                    # الربط الوصفي وفلتر المقالات المسحوبة
├── query_parser.py             # محلل الاستعلامات البوليانية (AST)
├── ranking.py                  # خوارزمية الترتيب والفرز الهجينة المنفصلة
├── network.py                  # العميل الشبكي وقواطع الدارة المستقلة
├── providers.py                # مزودو البيانات الـ 12 ونقاط النهاية المعيارية
├── database.py                 # استمرارية المهام والحصص اليومية (SQLite)
├── requirements.txt            # الاعتماديات الأساسية
├── requirements-fulltext.txt   # الاعتماديات الاختيارية للنصوص الكاملة
├── templates/index.html        # واجهة المستخدم التفاعلية (React + Tailwind)
└── tests/                      # حزمة الاختبارات والتأكيد المعياري
```
