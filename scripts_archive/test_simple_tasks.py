import sys
import os
import json
import logging

# Add project root to path
sys.path.append(os.getcwd())

from app.services.ai_service import ai_service

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_json_parsing():
    print("\n=== Testing JSON Parsing Strategies ===")
    
    # 1. Standard correct JSON
    case1 = '{"title": "Test 1", "deadline": "2023-01-01"}'
    try:
        res = ai_service._extract_json(case1)
        print(f"✅ Case 1 (Standard): Success")
    except Exception as e:
        print(f"❌ Case 1 (Standard): Failed - {e}")

    # 2. Naked JSON (Missing braces) - The suspected issue
    case2 = '\n "title": "Test 2",\n "deadline": "2023-01-02"\n'
    try:
        res = ai_service._extract_json(case2)
        print(f"✅ Case 2 (Naked): Success -> {res.get('title')}")
    except Exception as e:
        print(f"❌ Case 2 (Naked): Failed - {e}")

    # 3. Code block with Naked JSON
    case3 = '```json\n "title": "Test 3", "deadline": "2023-01-03"\n```'
    try:
        res = ai_service._extract_json(case3)
        print(f"✅ Case 3 (Block+Naked): Success -> {res.get('title')}")
    except Exception as e:
        print(f"❌ Case 3 (Block+Naked): Failed - {e}")
        
    # 4. Starting with newline + quote (Exact error scenario?)
    case4 = '\n "title"' 
    # This is obviously invalid JSON even with braces: {"title"} is invalid. 
    # But maybe the input is: '\n "title": "foo"'
    case4_real = '\n "title": "Test 4"'
    try:
        res = ai_service._extract_json(case4_real)
        print(f"✅ Case 4 (Newline+Quote): Success -> {res.get('title')}")
    except Exception as e:
        print(f"❌ Case 4 (Newline+Quote): Failed - {e}")

    # 5. Naked JSON with trailing comma (Common AI error)
    case5 = '\n "title": "Test 5",\n "deadline": "2023-01-05",\n'
    try:
        res = ai_service._extract_json(case5)
        print(f"✅ Case 5 (Naked+Comma): Success -> {res.get('title')}")
    except Exception as e:
        print(f"❌ Case 5 (Naked+Comma): Failed - {e}")

if __name__ == '__main__':
    test_json_parsing()
