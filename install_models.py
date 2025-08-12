#!/usr/bin/env python3
"""
IndicTrans2 Setup and Translation System
Supports all major Indian languages with state-of-the-art translation quality
"""

import os
import sys
import torch
from typing import List, Dict, Optional
import subprocess

# Language configurations
INDIC_LANGUAGES = {
    "en": "English",
    "hi": "Hindi",
    "mr": "Marathi", 
    "gu": "Gujarati",
    "te": "Telugu",
    "bn": "Bengali",
    "kn": "Kannada",
    "ta": "Tamil",
    "ml": "Malayalam",
    "pa": "Punjabi",
    "or": "Odia",
    "as": "Assamese",
    "ur": "Urdu"
}

# Your preferred languages
PREFERRED_LANGUAGES = ["en", "hi", "mr", "gu", "te", "bn", "kn", "ta", "ml"]

class IndicTrans2Setup:
    """Setup IndicTrans2 environment"""
    
    def __init__(self):
        self.base_dir = os.path.expanduser("~/IndicTrans2")
        self.venv_path = os.path.join(self.base_dir, "venv")
    
    def clone_repository(self):
        """Clone IndicTrans2 repository"""
        print("=== Cloning IndicTrans2 Repository ===\n")
        
        if os.path.exists(self.base_dir):
            print(f"✓ Repository already exists at {self.base_dir}")
            return
        
        try:
            subprocess.run([
                "git", "clone", 
                "https://github.com/AI4Bharat/IndicTrans2.git",
                self.base_dir
            ], check=True)
            print(f"✓ Repository cloned to {self.base_dir}")
        except subprocess.CalledProcessError as e:
            print(f"✗ Failed to clone repository: {e}")
            sys.exit(1)
    
    def setup_environment(self):
        """Setup Python environment and install dependencies"""
        print("\n=== Setting up Python Environment ===\n")
        
        # Create virtual environment if it doesn't exist
        if not os.path.exists(self.venv_path):
            print("Creating virtual environment...")
            subprocess.run([sys.executable, "-m", "venv", self.venv_path], check=True)
            print("✓ Virtual environment created")
        
        # Get pip path in virtual environment
        pip_path = os.path.join(self.venv_path, "bin", "pip") if os.name != "nt" else os.path.join(self.venv_path, "Scripts", "pip.exe")
        
        # Install requirements
        print("\nInstalling dependencies...")
        requirements_file = os.path.join(self.base_dir, "requirements.txt")
        
        if os.path.exists(requirements_file):
            subprocess.run([pip_path, "install", "-r", requirements_file], check=True)
            print("✓ Dependencies installed")
        else:
            # Install core dependencies manually
            dependencies = [
                "torch>=1.10.0",
                "transformers>=4.20.0",
                "sentencepiece>=0.1.96",
                "sacremoses>=0.0.53",
                "pandas>=1.3.0",
                "numpy>=1.21.0",
                "mosestokenizer>=1.0.0",
                "indic-nlp-library>=0.91"
            ]
            
            for dep in dependencies:
                print(f"Installing {dep}...")
                subprocess.run([pip_path, "install", dep], check=True)
            
            print("✓ Core dependencies installed")
    
    def download_models(self):
        """Download IndicTrans2 models"""
        print("\n=== Downloading IndicTrans2 Models ===\n")
        
        models_dir = os.path.join(self.base_dir, "models")
        os.makedirs(models_dir, exist_ok=True)
        
        # Model URLs (you'll need to get actual URLs from AI4Bharat)
        model_urls = {
            "en-indic": "https://storage.googleapis.com/indictrans2-public/it2_en_indic_model.zip",
            "indic-en": "https://storage.googleapis.com/indictrans2-public/it2_indic_en_model.zip",
            "indic-indic": "https://storage.googleapis.com/indictrans2-public/it2_indic_indic_model.zip"
        }
        
        print("Note: You need to download models from AI4Bharat")
        print("Visit: https://github.com/AI4Bharat/IndicTrans2#download-models")
        print("\nModels to download:")
        for model_name in model_urls:
            print(f"  - {model_name}")
        
        # Create download script
        download_script = os.path.join(self.base_dir, "download_models.sh")
        with open(download_script, "w") as f:
            f.write("#!/bin/bash\n\n")
            f.write("# IndicTrans2 Model Download Script\n")
            f.write(f"cd {models_dir}\n\n")
            
            for model_name, url in model_urls.items():
                f.write(f"# Download {model_name} model\n")
                f.write(f"wget -c {url} -O {model_name}.zip\n")
                f.write(f"unzip {model_name}.zip\n\n")
        
        os.chmod(download_script, 0o755)
        print(f"\n✓ Download script created: {download_script}")
        print("Run this script to download models")

class IndicTrans2Translator:
    """Main translator class using IndicTrans2"""
    
    def __init__(self, model_dir: str):
        self.model_dir = model_dir
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"Using device: {self.device}")
        
        # These will be loaded when models are available
        self.en_indic_model = None
        self.en_indic_tokenizer = None
        self.indic_en_model = None
        self.indic_en_tokenizer = None
    
    def load_models(self):
        """Load translation models"""
        print("\n=== Loading IndicTrans2 Models ===\n")
        
        try:
            from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
            
            # Load En-Indic model
            en_indic_path = os.path.join(self.model_dir, "en-indic")
            if os.path.exists(en_indic_path):
                print("Loading En-Indic model...")
                self.en_indic_tokenizer = AutoTokenizer.from_pretrained(en_indic_path)
                self.en_indic_model = AutoModelForSeq2SeqLM.from_pretrained(en_indic_path)
                self.en_indic_model.to(self.device)
                print("✓ En-Indic model loaded")
            else:
                print(f"✗ En-Indic model not found at {en_indic_path}")
            
            # Load Indic-En model
            indic_en_path = os.path.join(self.model_dir, "indic-en")
            if os.path.exists(indic_en_path):
                print("Loading Indic-En model...")
                self.indic_en_tokenizer = AutoTokenizer.from_pretrained(indic_en_path)
                self.indic_en_model = AutoModelForSeq2SeqLM.from_pretrained(indic_en_path)
                self.indic_en_model.to(self.device)
                print("✓ Indic-En model loaded")
            else:
                print(f"✗ Indic-En model not found at {indic_en_path}")
                
        except Exception as e:
            print(f"Error loading models: {e}")
    
    def translate(self, text: str, src_lang: str, tgt_lang: str) -> Optional[str]:
        """Translate text from source to target language"""
        try:
            # Determine which model to use
            if src_lang == "en" and tgt_lang in INDIC_LANGUAGES:
                model = self.en_indic_model
                tokenizer = self.en_indic_tokenizer
            elif src_lang in INDIC_LANGUAGES and tgt_lang == "en":
                model = self.indic_en_model
                tokenizer = self.indic_en_tokenizer
            else:
                print(f"Translation from {src_lang} to {tgt_lang} not supported")
                return None
            
            if not model or not tokenizer:
                print("Required model not loaded")
                return None
            
            # Tokenize
            inputs = tokenizer(text, return_tensors="pt", padding=True).to(self.device)
            
            # Generate translation
            with torch.no_grad():
                outputs = model.generate(**inputs, max_length=256)
            
            # Decode
            translation = tokenizer.decode(outputs[0], skip_special_tokens=True)
            return translation
            
        except Exception as e:
            print(f"Translation error: {e}")
            return None
    
    def translate_to_all(self, text: str, target_langs: List[str] = None) -> Dict[str, str]:
        """Translate to multiple target languages"""
        if target_langs is None:
            target_langs = [lang for lang in PREFERRED_LANGUAGES if lang != "en"]
        
        translations = {"en": text}
        
        print(f"\nTranslating: '{text}'")
        print("-" * 60)
        
        for tgt_lang in target_langs:
            if tgt_lang == "en":
                continue
            
            result = self.translate(text, "en", tgt_lang)
            if result:
                translations[tgt_lang] = result
                lang_name = INDIC_LANGUAGES.get(tgt_lang, tgt_lang)
                print(f"{lang_name} ({tgt_lang}): {result}")
            else:
                print(f"✗ Failed to translate to {INDIC_LANGUAGES.get(tgt_lang, tgt_lang)}")
        
        return translations

def create_simple_translator():
    """Create a simple wrapper script for easy translation"""
    script_content = '''#!/usr/bin/env python3
"""Simple IndicTrans2 Translator"""

import sys
from indictrans2_translator import IndicTrans2Translator, INDIC_LANGUAGES

def main():
    if len(sys.argv) < 2:
        print("Usage: translate.py <text> [target_language]")
        print("\\nSupported languages:")
        for code, name in INDIC_LANGUAGES.items():
            print(f"  {code}: {name}")
        sys.exit(1)
    
    text = sys.argv[1]
    target_lang = sys.argv[2] if len(sys.argv) > 2 else None
    
    translator = IndicTrans2Translator("./models")
    translator.load_models()
    
    if target_lang:
        result = translator.translate(text, "en", target_lang)
        if result:
            print(f"{INDIC_LANGUAGES.get(target_lang, target_lang)}: {result}")
    else:
        translator.translate_to_all(text)

if __name__ == "__main__":
    main()
'''
    
    with open("translate.py", "w") as f:
        f.write(script_content)
    os.chmod("translate.py", 0o755)
    print("\n✓ Created simple translator script: translate.py")

def main():
    """Main setup and demo function"""
    print("=== IndicTrans2 Setup for Indian Languages ===\n")
    print("This will set up offline translation for:")
    for lang in PREFERRED_LANGUAGES:
        print(f"  • {INDIC_LANGUAGES[lang]}")
    
    # Setup
    setup = IndicTrans2Setup()
    
    # Step 1: Clone repository
    setup.clone_repository()
    
    # Step 2: Setup environment
    setup.setup_environment()
    
    # Step 3: Download models
    setup.download_models()
    
    print("\n=== Setup Complete ===\n")
    print("Next steps:")
    print("1. Run the download script to get models")
    print("2. Use the translator class for translations")
    
    # Create simple translator script
    create_simple_translator()
    
    # Demo (will only work after models are downloaded)
    print("\n=== Demo Code ===")
    print("""
# After downloading models, use like this:
from indictrans2_translator import IndicTrans2Translator

translator = IndicTrans2Translator("./models")
translator.load_models()

# Translate to all languages
translations = translator.translate_to_all("Hello, how are you?")

# Translate to specific language
hindi = translator.translate("Welcome to India", "en", "hi")
""")

if __name__ == "__main__":
    main()