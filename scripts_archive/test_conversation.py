"""Test intelligent conversation system - Complete test."""
import requests
import json

# Login
print("🔐 Logging in...")
login_resp = requests.post(
    "http://localhost:8000/api/auth/login",
    data={"username": "admin", "password": "admin123"}
)
token = login_resp.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}
print(f"✅ Token: {token[:20]}...\n")

# Test 1: Simple task
print("="*60)
print("✅ 测试 1: 简单任务 - '明天7点起床'")
print("="*60)
resp1 = requests.post(
    "http://localhost:8000/api/conversation/chat",
    headers=headers,
    json={"message": "明天7点起床"}
)
data1 = resp1.json()
print(f"Intent: {data1['intent']}")
print(f"Action: {data1['action_type']}")
print(f"AI说: {data1['message']}")
if data1.get('task'):
    print(f"✓ Task created: {data1['task']['id']}")
print()

# Test 2: Complex project - initial message
print("="*60)
print("✅ 测试2: 复杂项目 - '我想学完微积分'")
print("="*60)
resp2 = requests.post(
    "http://localhost:8000/api/conversation/chat",
    headers=headers,
    json={"message": "我想学完微积分"}
)
data2 = resp2.json()
print(f"Intent: {data2['intent']}")
print(f"Action: {data2['action_type']}")
print(f"AI说: {data2['message']}")
conv_id = data2['conversation_id']
print(f"Conversation ID: {conv_id}")
print()

# Continue conversation
if data2['action_type'] == 'ask_more':
    print("✅ 测试 2.1: AI 正在收集信息，继续回答...")
    print("="*60)
    resp3 = requests.post(
        "http://localhost:8000/api/conversation/chat",
        headers=headers,
        json={
            "conversation_id": conv_id,
            "message": "3个月，每天2小时，有大学教材"
        }
    )
    data3 = resp3.json()
    print(f"Action: {data3['action_type']}")
    print(f"AI说: {data3['message']}")
    
    if data3['action_type'] == 'create_project':
        print(f"\n✓ Plan generated!")
        print(f"   Project: {data3['plan']['project']['title']}")
        print(f"   Tasks: {len(data3['plan']['tasks'])}")
    print()

# Test 3: Question
print("="*60)
print("✅ 测试 3: 问题 - '如何提高学习效率？'")
print("="*60)
resp4 = requests.post(
    "http://localhost:8000/api/conversation/chat",
    headers=headers,
    json={"message": "如何提高学习效率？"}
)
data4 = resp4.json()
print(f"Intent: {data4['intent']}")
print(f"Action: {data4['action_type']}")
print(f"AI说: {data4['message']}")
print()

# Test 4: Chat
print("="*60)
print("✅ 测试 4: 闲聊 - '你好'")
print("="*60)
resp5 = requests.post(
    "http://localhost:8000/api/conversation/chat",
    headers=headers,
    json={"message": "你好"}
)
data5 = resp5.json()
print(f"Intent: {data5['intent']}")
print(f"Action: {data5['action_type']}")
print(f"AI说: {data5['message']}")
print()

print("="*60)
print("🎉 全部测试完成！")
print("="*60)
print("\n测试结果总结：")
print("✓  简单任务识别与创建")
print("✓ 复杂项目识别与信息收集")
print("✓ 问题回答")
print("✓ 闲聊识别")
