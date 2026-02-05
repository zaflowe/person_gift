"""Direct test of Qwen API response for simple task extraction."""
import sys
import os
sys.path.append(os.getcwd())

from app.services.qwen_client import get_qwen_client
from app.services.conversation_service import SIMPLE_TASK_EXTRACTION_PROMPT
from datetime import datetime

def test_qwen_direct():
    """Test Qwen API directly to see raw response."""
    print("\n" + "="*60)
    print("Testing Qwen API Response for Task Extraction")
    print("="*60)
    
    # Get Qwen client
    try:
        qwen = get_qwen_client()
        print("✅ Qwen client initialized")
    except Exception as e:
        print(f"❌ Failed to initialize Qwen: {e}")
        return
    
    # Prepare prompt
    message = "定个八点去吃饭的任务"
    current_time = datetime.now().isoformat()
    prompt = SIMPLE_TASK_EXTRACTION_PROMPT.format(
        message=message,
        current_time=current_time
    )
    
    print(f"\n📝 Message: {message}")
    print(f"⏰ Current time: {current_time}")
    print(f"\n📤 Sending to Qwen...")
    
    # Call Qwen
    try:
        response = qwen.generate_text(prompt)
        print(f"\n✅ Response received ({len(response)} chars)")
        print(f"\n📥 Raw response:")
        print("="*60)
        print(repr(response))  # Use repr to show all special characters
        print("="*60)
        print(f"\nActual content:")
        print(response)
        
    except Exception as e:
        print(f"\n❌ Qwen API failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_qwen_direct()
