
import sys
import os
import asyncio

# Add project root to path
sys.path.append(os.getcwd())

from app.services.conversation_service import conversation_service
from app.services.ai_service import ai_service

async def test_ai():
    print("Testing AI Service...")
    
    # 1. Test basic AI call
    try:
        response = ai_service._call_ai("Hello")
        print(f"Basic AI Call Result: {response[:50]}...")
    except Exception as e:
        print(f"Basic AI Call Failed: {e}")
        import traceback
        traceback.print_exc()

    # 2. Test Gather Information (Trigger the bug)
    print("\nTesting Gather Information...")
    try:
        collected_info = {"goal": "Become Ultraman"}
        history = [{"role": "user", "content": "我要三个月成为奥特曼"}]
        
        info_complete, message = conversation_service.gather_information(collected_info, history)
        print(f"Result: Complete={info_complete}, Message={message}")
        
        if message == "好的，让我开始规划。":
            print("FAILURE REPRODUCED: Hit the exception fallback block.")
        else:
            print("Success! (No fallback)")
            
    except Exception as e:
        import traceback
        with open("reproduce_error.log", "w", encoding="utf-8") as f:
             f.write(f"Gather Info Failed: {e}\n")
             traceback.print_exc(file=f)
        print("Error logged to reproduce_error.log")

if __name__ == "__main__":
    if hasattr(asyncio, 'run'):
        asyncio.run(test_ai())
    else:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(test_ai())
