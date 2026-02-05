"""Test script for Qwen API integration."""
import asyncio
import os
from dotenv import load_dotenv

# Load environment
load_dotenv()

# Override to test Qwen specifically
os.environ['AI_PROVIDER'] = 'qwen'
os.environ['GEMINI_MOCK_MODE'] = 'false'

from app.services.ai_service import ai_service
from app.services.conversation_service import conversation_service

async def test_qwen_basic():
    """Test basic Qwen API call."""
    print("=" * 60)
    print("🧪 Test 1: Basic Text Generation (Qwen)")
    print("=" * 60)
    
    try:
        result = await ai_service.judge_evidence(
            task_title="测试任务",
            evidence_type="text",
            evidence_criteria="需要提供详细的学习笔记",
            evidence_content="今天我学习了Python的装饰器，写了500字的笔记"
        )
        print(f"✅ Result: {result['result']}")
        print(f"📝 Reason: {result['reason']}")
    except Exception as e:
        print(f"❌ Error: {e}")

async def test_conversation():
    """Test conversation service."""
    print("\n" + "=" * 60)
    print("🧪 Test 2: Intent Recognition")
    print("=" * 60)
    
    try:
        intent, info = conversation_service.recognize_intent("我要考研")
        print(f"✅ Intent: {intent}")
        print(f"📝 Info: {info}")
    except Exception as e:
        print(f"❌ Error: {e}")

async def test_task_extraction():
    """Test task extraction."""
    print("\n" + "=" * 60)
    print("🧪 Test 3: Task Extraction")
    print("=" * 60)
    
    try:
        task_info = conversation_service.extract_simple_task("明天早上7点起床跑步")
        print(f"✅ Title: {task_info['title']}")
        print(f"📅 Deadline: {task_info['deadline']}")
        print(f"📋 Type: {task_info['evidence_type']}")
    except Exception as e:
        print(f"❌ Error: {e}")

async def test_auto_switching():
    """Test auto-switching between providers."""
    print("\n" + "=" * 60)
    print("🧪 Test 4: Auto-Switching (Gemini → Qwen)")
    print("=" * 60)
    
    # Set to auto mode
    os.environ['AI_PROVIDER'] = 'auto'
    
    # Reinitialize service
    from app.services import ai_service
    import importlib
    importlib.reload(ai_service)
    
    print("Provider set to 'auto' - will try Gemini first, then Qwen on failure")
    
    try:
        result = await ai_service.ai_service.judge_evidence(
            task_title="自动切换测试",
            evidence_type="text",
            evidence_criteria="测试自动切换功能",
            evidence_content="这是一个测试"
        )
        print(f"✅ Successfully got result from AI")
        print(f"📝 Result: {result['result']}")
    except Exception as e:
        print(f"❌ Error: {e}")

async def main():
    """Run all tests."""
    print("\n🚀 Starting Qwen API Integration Tests\n")
    
    await test_qwen_basic()
    await test_conversation()
    await test_task_extraction()
    await test_auto_switching()
    
    print("\n" + "=" * 60)
    print("✅ All tests completed!")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())
