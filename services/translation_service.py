# services/translation_service.py
# ENHANCED - Offline translation with Argos Translate

import argostranslate.package
import argostranslate.translate
import redis
import json
import logging
from flask import current_app
import time
import os

class TranslationService:
    def __init__(self):
        self.redis_client = None
        self.logger = logging.getLogger(__name__)
        self._initialized = False
        self._argos_initialized = False
        
        # Language mapping
        self.supported_languages = {
            'en': 'English',
            'hi': 'Hindi',
            'mr': 'Marathi', 
            'gu': 'Gujarati',
            'te': 'Telugu',
            'bn': 'Bengali',
            'kn': 'Kannada',
            'ta': 'Tamil',
            'ml': 'Malayalam'
        }
        
        # Argos language codes mapping
        self.argos_language_map = {
            'en': 'en',
            'hi': 'hi',
            'mr': 'mr',  # Marathi might not be available
            'gu': 'gu',  # Gujarati might not be available
            'te': 'te',  # Telugu might not be available
            'bn': 'bn',
            'kn': 'kn',  # Kannada might not be available
            'ta': 'ta',
            'ml': 'ml'   # Malayalam might not be available
        }
        
        # Initialize with your existing pre-translations
        self._static_translations = {
            # ... (keep all your existing pre-translations)
        }
    
    def _init_argos(self):
        """Initialize Argos Translate with required language packages"""
        if self._argos_initialized:
            return
            
        try:
            self.logger.info("🔄 Initializing Argos Translate...")
            
            # Update package index
            argostranslate.package.update_package_index()
            
            # Download and install required language packages
            available_packages = argostranslate.package.get_available_packages()
            
            # Language pairs we need (English to/from each language)
            required_pairs = [
                ('en', 'hi'),  # English to Hindi
                ('hi', 'en'),  # Hindi to English
                ('en', 'bn'),  # English to Bengali
                ('bn', 'en'),  # Bengali to English
                ('en', 'ta'),  # English to Tamil
                ('ta', 'en'),  # Tamil to English
                # Add more pairs as they become available
            ]
            
            installed_count = 0
            for from_code, to_code in required_pairs:
                # Check if package exists
                package = next(
                    (pkg for pkg in available_packages 
                     if pkg.from_code == from_code and pkg.to_code == to_code),
                    None
                )
                
                if package and not argostranslate.package.is_installed(package):
                    self.logger.info(f"📦 Installing {from_code} -> {to_code} translation package...")
                    argostranslate.package.install_from_path(package.download())
                    installed_count += 1
                elif package:
                    self.logger.info(f"✅ Package {from_code} -> {to_code} already installed")
                else:
                    self.logger.warning(f"⚠️ Package {from_code} -> {to_code} not available")
            
            self._argos_initialized = True
            self.logger.info(f"✅ Argos Translate initialized with {installed_count} new packages")
            
        except Exception as e:
            self.logger.error(f"❌ Failed to initialize Argos Translate: {e}")
            self._argos_initialized = False
    
    def _translate_with_argos(self, text, target_lang='en', source_lang='auto'):
        """Translate text using Argos Translate (offline)"""
        try:
            # Initialize Argos if needed
            if not self._argos_initialized:
                self._init_argos()
            
            # Detect source language if auto
            if source_lang == 'auto':
                source_lang = 'en'  # Default to English
            
            # Map to Argos language codes
            from_code = self.argos_language_map.get(source_lang, 'en')
            to_code = self.argos_language_map.get(target_lang, 'en')
            
            # Get installed languages
            installed_languages = argostranslate.translate.get_installed_languages()
            
            # Find source and target languages
            from_lang = next((lang for lang in installed_languages if lang.code == from_code), None)
            to_lang = next((lang for lang in installed_languages if lang.code == to_code), None)
            
            if not from_lang or not to_lang:
                self.logger.warning(f"Language pair {from_code}->{to_code} not available in Argos")
                return None
            
            # Get translation
            translation = from_lang.get_translation(to_lang)
            if translation:
                result = translation.translate(text)
                self.logger.debug(f"✅ Argos translated: '{text[:50]}...' to '{result[:50]}...'")
                return result
            
            return None
            
        except Exception as e:
            self.logger.error(f"Argos translation error: {e}")
            return None
    
    def translate_text(self, text, target_lang='en', source_lang='auto'):
        """Translate text with fallback strategy: Static -> Cache -> Argos -> Original"""
        # OPTIMIZATION 1: Return immediately for English
        if not text or target_lang == 'en':
            return text
        
        # OPTIMIZATION 2: Check static translations first
        if target_lang in self._static_translations:
            # Check in root level
            if text in self._static_translations[target_lang]:
                return self._static_translations[target_lang][text]
            # Check in fields
            if 'fields' in self._static_translations[target_lang] and text in self._static_translations[target_lang]['fields']:
                return self._static_translations[target_lang]['fields'][text]
            # Check in other nested dictionaries
            for key in ['options', 'values', 'recommendations', 'success']:
                if key in self._static_translations[target_lang] and text in self._static_translations[target_lang][key]:
                    return self._static_translations[target_lang][key][text]
        
        # OPTIMIZATION 3: Check cache
        cached = self.get_cached_translation(text, target_lang)
        if cached:
            return cached
        
        # OPTIMIZATION 4: Try Argos Translate (offline)
        argos_result = self._translate_with_argos(text, target_lang, source_lang)
        if argos_result:
            # Cache the translation
            self.cache_translation(text, target_lang, argos_result)
            return argos_result
        
        # OPTIMIZATION 5: Fallback to original text
        self.logger.warning(f"No translation available for '{text[:50]}...' in {target_lang}")
        return text
    
    def get_form_translations(self, target_lang='en'):
        """Get all form field translations with Argos fallback"""
        # First try to return pre-translated content
        if target_lang in self._static_translations:
            return self._static_translations[target_lang]
        
        # If not available, translate dynamically with Argos
        base_content = self._static_translations['en']
        
        # For unsupported languages, try Argos translation
        if self._argos_initialized or not self._argos_initialized:
            self._init_argos()
        
        # Translate the base content
        translated_content = self._translate_dict_with_argos(base_content, target_lang)
        
        # Cache the full translation for future use
        self._static_translations[target_lang] = translated_content
        
        return translated_content
    
    def _translate_dict_with_argos(self, content_dict, target_lang):
        """Recursively translate dictionary content using Argos"""
        translated = {}
        
        for key, value in content_dict.items():
            if isinstance(value, str):
                # Translate string
                translated[key] = self.translate_text(value, target_lang)
            elif isinstance(value, list):
                # Translate list items
                translated[key] = [self.translate_text(item, target_lang) if isinstance(item, str) else item for item in value]
            elif isinstance(value, dict):
                # Recursively translate nested dictionary
                translated[key] = self._translate_dict_with_argos(value, target_lang)
            else:
                # Keep non-string values as is
                translated[key] = value
        
        return translated