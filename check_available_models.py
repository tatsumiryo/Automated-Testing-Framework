#!/usr/bin/env python3
"""
Check what Gemini models are available with your API key
"""

import os
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()

try:
    api_key = os.getenv("GEMINI_API_KEY")
    
    if not api_key:
        print("❌ No API key found in .env file")
        exit(1)
    
    print(f"✅ API Key found: {api_key[:10]}...\n")
    
    genai.configure(api_key=api_key)
    
    print("📋 Available Gemini Models:")
    print("=" * 60)
    
    for model in genai.list_models():
        if 'generateContent' in model.supported_generation_methods:
            print(f"\n✅ Model: {model.name}")
            print(f"   Display Name: {model.display_name}")
            print(f"   Description: {model.description[:100]}...")
    
    print("\n" + "=" * 60)
    print("\nℹ️  Use one of these model names in your code!")
    print("   Common working names:")
    print("   - gemini-pro")
    print("   - gemini-1.5-flash")
    print("   - gemini-1.5-flash-latest")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()