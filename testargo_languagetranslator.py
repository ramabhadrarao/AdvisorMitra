from argostranslate import package, translate

# 1. Install language packages (run only once)
# Example: English to Hindi
# You can find available packages with package.get_available_packages()
available_packages = package.get_available_packages()
installed_languages = translate.get_installed_languages()

# Function to install a translation model if not already installed
def install_lang_pair(from_code, to_code):
    for pkg in available_packages:
        if pkg.from_code == from_code and pkg.to_code == to_code:
            print(f"Installing {from_code} → {to_code}...")
            package.install_from_path(pkg.download())
            break

# List of target languages
target_langs = [
    ("hi", "Hindi"),
    ("mr", "Marathi"),
    ("gu", "Gujarati"),
    ("te", "Telugu"),
    ("bn", "Bengali"),
    ("kn", "Kannada"),
    ("ta", "Tamil"),
    ("ml", "Malayalam"),
]

# Install missing packages
for code, _ in target_langs:
    install_lang_pair("en", code)

# 2. Translate text
text = "Hello, how are you? Welcome to India"

installed_languages = translate.get_installed_languages()
from_lang = None
for lang in installed_languages:
    if lang.code == "en":
        from_lang = lang
        break

if from_lang:
    for code, name in target_langs:
        to_lang = None
        for lang in installed_languages:
            if lang.code == code:
                to_lang = lang
                break
        if to_lang:
            translation = from_lang.get_translation(to_lang)
            result = translation.translate(text)
            print(f"{name} ({code}): {result}")
