"""Test improved mock chat logic."""
from app.services.conversation_service import ConversationService
import json

def test_mock_chat():
    service = ConversationService()
    service.mock_mode = True
    
    test_cases = [
        "你好",              # Chat
        "知不知道现在几点了",  # Question (Time)
        "你是不是弱智啊",      # Chat/Question (Insult)
        "明天早上七点起床",    # Simple Task
        "我想三个月学完Python", # Complex Project
        "如何提高效率？",      # Question
        "你说什么乱七八糟的"    # Fallback -> Question/Chat
    ]
    
    print("Testing Mock Chat Logic:")
    print("-" * 50)
    
    for msg in test_cases:
        intent, info = service.recognize_intent(msg)
        print(f"Input: {msg}")
        print(f"Intent: {intent}")
        
        if intent == "question":
            answer = service.answer_question(msg)
            print(f"Answer: {answer}")
        elif intent == "chat":
            print(f"Response: (Simulated chat response handled by frontend usually, but intent is correct)")
            # In router logic, chat intent returns simple message. 
            # In mock intent logic we updated, insults return 'chat' now? 
            # Wait, let's check answer_question usage. 
            # Actually valid 'chat' also goes to answer_question often in simple implementation or has its own handler.
            # Let's test answer_question for insult directly to see the specialized response.
            if "弱智" in msg:
                print(f"Insult Response Check: {service.answer_question(msg)}")
                
        print("-" * 30)

if __name__ == "__main__":
    test_mock_chat()
