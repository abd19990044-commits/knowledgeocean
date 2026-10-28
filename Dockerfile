FROM python:3.10-slim

# متغيرات بيئة مفيدة
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    DOWNLOAD_DIR=/app/downloads \
    FONT_DIR=/app/fonts

WORKDIR /app

# خطوط النظام (عربي Amiri + رموز DejaVu) + أدوات OCR ومعالجة الصور + curl لفحص الصحة
RUN apt-get update && apt-get install -y --no-install-recommends \
        fonts-hosny-amiri \
        fonts-dejavu-core \
        poppler-utils \
        tesseract-ocr \
        tesseract-ocr-eng \
        tesseract-ocr-ara \
        curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# مجلدات قابلة للكتابة (HF Spaces قد يشغّل بمستخدم غير root)
RUN mkdir -p /app/downloads /app/fonts && chmod -R 777 /app/downloads /app/fonts

EXPOSE 7860

# فحص صحة داخلي (اختياري لكنه مفيد)
HEALTHCHECK --interval=60s --timeout=10s --start-period=20s --retries=3 \
    CMD curl -fsS http://localhost:7860/health || exit 1

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "7860"]
