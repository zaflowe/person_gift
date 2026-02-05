import re

cn_num = {'一': 1, '二': 2, '三': 3, '四': 4, '五': 5, 
          '六': 6, '七': 7, '八': 8, '九': 9, '十': 10, '零': 0, '两':2}

def parse_cn_number(text):
    if not text: return 0
    try:
        return int(text)
    except ValueError:
        pass
        
    if text == '半': return 30
    
    val = 0
    temp_val = 0
    
    # Handle "四十", "三十" etc
    if '十' in text:
        parts = text.split('十')
        # Before '十'
        if parts[0]:
            temp_val = cn_num.get(parts[0], 0)
            val += temp_val * 10
        else:
            val += 10
            
        # After '十'
        if len(parts) > 1 and parts[1]:
            val += cn_num.get(parts[1], 0)
        return val
    else:
        # e.g. "五"
        return cn_num.get(text, 0)

messages = ["明天7点40起床", "早上七点四十", "八点半开会", "19点吃饭", "7:40出发", "7点五十"]

print("Testing Regex Logic:")
regex = r'(\d+|[一二三四五六七八九十两]+)(?:点|:|：)(\d+|[一二三四五六七八九十零]+|半)?(?:分)?'

for msg in messages:
    time_pattern = re.search(regex, msg)
    if time_pattern:
        # print(f"Match: {msg} -> {time_pattern.groups()}")
        h_str = time_pattern.group(1)
        m_str = time_pattern.group(2)
        
        h = parse_cn_number(h_str)
        m = parse_cn_number(m_str)
        print(f"Original: {msg} -> Parsed: {h:02d}:{m:02d}")
    else:
        print(f"No match: {msg}")
