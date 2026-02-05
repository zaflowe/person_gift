"""Test script to list available Gemini models and test API key."""
import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv()

# Configure API
api_key = os.getenv('GEMINI_API_KEY')
print(f"Using API Key: {api_key[:10]}...")
genai.configure(api_key=api_key)

print("\n🔍 Listing all available models:\n")
print("-" * 60)

for model in genai.list_models():
    if 'generateContent' in model.supported_generation_methods:
        print(f"✅ {model.name}")
        print(f"   Display Name: {model.display_name}")
        print(f"   Description: {model.description[:80]}...")
        print()

print("-" * 60)
print("\n💡 Try using one of the model names above in your code!")
print("\nTesting a simple text prompt with the first available model...")

try:
    # Find first available model
    available_models = [m for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
    if available_models:
        test_model_name = available_models[0].name
        print(f"\n🧪 Testing with: {test_model_name}")
        
        model = genai.GenerativeModel(test_model_name)
        response = model.generate_content("Say hello in Chinese")
        print(f"✅ Response: {response.text}")
    else:
        print("❌ No models support generateContent")
except Exception as e:
    print(f"❌ Error: {e}")
