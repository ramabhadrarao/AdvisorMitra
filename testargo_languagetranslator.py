from argostranslate import package, translate
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
import os

# ✅ STEP 1: Install all translation models (only once, from local files)
model_files = [
    "en_hi.argosmodel", "en_mr.argosmodel", "en_gu.argosmodel",
    "en_te.argosmodel", "en_bn.argosmodel", "en_kn.argosmodel",
    "en_ta.argosmodel", "en_ml.argosmodel"
]

for file in model_files:
    if os.path.exists(file):
        package.install_from_path(file)

# ✅ STEP 2: Load installed languages
installed_languages = translate.load_installed_languages()
en = next(lang for lang in installed_languages if lang.code == "en")

# Mapping of language names to ISO codes
lang_map = {
    "Hindi": "hi",
    "Marathi": "mr",
    "Gujarati": "gu",
    "Telugu": "te",
    "Bengali": "bn",
    "Kannada": "kn",
    "Tamil": "ta",
    "Malayalam": "ml"
}

# ✅ STEP 3: Translate text to all target languages
source_text = "Hello, how are you?"
translations = []

for lang_name, code in lang_map.items():
    try:
        target_lang = next(lang for lang in installed_languages if lang.code == code)
        translated_text = en.translate(source_text, target_lang)
        translations.append((lang_name, translated_text))
    except StopIteration:
        translations.append((lang_name, "[Model not installed]"))

# ✅ STEP 4: Generate PDF with translations
pdf_file = "translations.pdf"
c = canvas.Canvas(pdf_file, pagesize=A4)
width, height = A4

y = height - 50
c.setFont("Helvetica-Bold", 14)
c.drawString(50, y, "English Source Text:")
y -= 20
c.setFont("Helvetica", 12)
c.drawString(50, y, source_text)

y -= 40
c.setFont("Helvetica-Bold", 14)
c.drawString(50, y, "Translations:")
y -= 20
c.setFont("Helvetica", 12)

for lang, text in translations:
    if y < 50:  # New page if space runs out
        c.showPage()
        y = height - 50
        c.setFont("Helvetica", 12)
    c.drawString(50, y, f"{lang}: {text}")
    y -= 20

c.save()
print(f"✅ PDF saved as {pdf_file}")
