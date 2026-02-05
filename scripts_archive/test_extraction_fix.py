"""Test conversation extraction improvement."""
from app.services.conversation_service import ConversationService
import json

def test_extraction():
    service = ConversationService()
    service.mock_mode = True # Ensure mock mode
    
    test_cases = [
        "明天早上七点四十起床",
        "明天7:40出发",
        "今晚8点半跑步",
        "下午3点20开会"
    ]
    
    output = []
    output.append("Testing improved extraction logic:")
    output.append("-" * 50)
    
    for msg in test_cases:
        result = service._mock_extract_simple_task(msg)
        output.append(f"Input: {msg}")
        output.append(f"Title: {result['title']}")
        output.append(f"Deadline: {result['deadline']}")
        output.append("-" * 30)
    
    with open("test_result_utf8.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(output))

if __name__ == "__main__":
    test_extraction()
