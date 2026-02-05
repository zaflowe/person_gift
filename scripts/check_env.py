
import sys
import os

# Add project root to path
sys.path.append(os.getcwd())

try:
    import google.generativeai as genai
    print("SUCCESS: google.generativeai is installed.")
except ImportError:
    print("FAILURE: google.generativeai is NOT installed.")

try:
    from app.config import settings
    print(f"Mock Mode: {settings.gemini_mock_mode}")
    print(f"Provider: {settings.ai_provider}")
    print(f"Gemini Key Present: {bool(settings.gemini_api_key)}")
    if settings.gemini_api_key:
        print(f"Gemini Key Prefix: {settings.gemini_api_key[:5]}...")
    print(f"Qwen Key Present: {bool(settings.qwen_api_key)}")
except Exception as e:
    print(f"FAILURE loading settings: {e}")
