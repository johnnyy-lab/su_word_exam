import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import re
import csv
import json
from data.crop_engine import crop_item_image, CROPS_DIR, ERRATA_DIR

DATA_DIR = os.path.join(BASE_DIR, 'data')
MD_PATH = os.path.join(DATA_DIR, '國語字音字形-高中統整.md')
REVIEW_PATH = os.path.join(DATA_DIR, 'recheck_X_review.md')
REPORT_PATH = os.path.join(DATA_DIR, 'recheck_report.csv')
OUTPUT_JSON = os.path.join(DATA_DIR, 'disputes_dataset.json')

ERRATA_MAP = {
    '104_甲_094': {'ans': 'ㄜ', 'crop': 'assets/crops/errata/104_甲_094.png', 'note': '勘誤表辨正定音為 ㄜ'},
    '105_甲_089': {'ans': 'ㄒㄧㄝ', 'crop': 'assets/crops/errata/105_甲_089.png', 'note': '勘誤表辨正定音為 ㄒㄧㄝ'},
    '106_甲_017': {'ans': 'ㄐㄧㄣˇ', 'crop': 'assets/crops/errata/106_甲_017.png', 'note': '勘誤表辨正定音為 ㄐㄧㄣˇ'},
    '106_甲_067': {'ans': 'ㄍㄤˋ', 'crop': 'assets/crops/errata/106_甲_067.png', 'note': '勘誤表辨正定音為 ㄍㄤˋ（原卷誤印ㄓㄨㄤˋ）'},
    '106_乙_024': {'ans': '徇', 'crop': 'assets/crops/errata/106_乙_024.png', 'note': '勘誤表辨正字形為「徇」（提示音ㄒㄩㄣˊ）'},
    '106_乙_041': {'ans': '翮', 'crop': 'assets/crops/errata/106_乙_041.png', 'note': '勘誤表辨正字形為「翮」（提示音ㄏㄜˊ）'},
    '106_乙_044': {'ans': '楬', 'crop': 'assets/crops/errata/106_乙_044.png', 'note': '勘誤表辨正字形為「楬」（提示音ㄐㄧㄝˊ）'},
    '106_乙_056': {'ans': '璿', 'crop': 'assets/crops/errata/106_乙_056.png', 'note': '勘誤表辨正字形為「璿」（提示音ㄒㄩㄢˊ，璿/璇皆可）'},
    '107_甲_026': {'ans': 'ㄧˊ', 'crop': 'assets/crops/errata/107_甲_026.png', 'note': '勘誤表辨正定音為 ㄧˊ'},
    '107_乙_014': {'ans': '沓', 'crop': 'assets/crops/errata/107_乙_014.png', 'note': '勘誤表辨正字形為「沓」（提示音ㄊㄚˋ，沓/遢皆可）'}
}

def extract_target_pronunciation(topic, test_char, full_ph):
    """
    從辭典完整詞條音讀中，精確萃取對應測驗字的單字注音，避免整串成語全部飆出來
    """
    if not full_ph or full_ph == '詞條查無':
        return '詞條查無'
    tokens = full_ph.strip().split()
    if not tokens:
        return full_ph
    # 清理題目詞語中的符號與提示注音
    clean_topic = re.sub(r'[\s\d_、()（）\u3105-\u3129\u02ca\u02c7\u02cb\u02d9]', '', topic)
    if test_char in clean_topic:
        idx = clean_topic.find(test_char)
        if 0 <= idx < len(tokens):
            return tokens[idx]
    if len(clean_topic) == len(tokens):
        for i, ch in enumerate(clean_topic):
            if ch == test_char:
                return tokens[i]
    return tokens[0]

def load_recheck_review():
    review_data = {}
    if not os.path.exists(REVIEW_PATH):
        return review_data
    with open(REVIEW_PATH, 'r', encoding='utf-8') as f:
        for line in f:
            if line.startswith('|') and not line.startswith('| :') and not line.startswith('| 部別'):
                parts = [p.strip() for p in line.strip().split('|')[1:-1]]
                if len(parts) >= 11:
                    sec, yr, num, word, test_w, orig_ph, moe_ph, moe_link, raw_ans, status, note = parts[:11]
                    key = f'{yr}_{sec}_{int(num):03d}'
                    
                    m = re.search(r'\((https://[^\)]+)\)', moe_link)
                    url = m.group(1) if m else ''
                    
                    review_data[key] = {
                        'raw_ans': raw_ans.replace('`', '').strip(),
                        'moe_ph': moe_ph.replace('`', '').strip(),
                        'moe_url': url,
                        'review_note': note
                    }
    return review_data

def load_recheck_report():
    report_data = {}
    if not os.path.exists(REPORT_PATH):
        return report_data
    with open(REPORT_PATH, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            sec = row.get('\ufeff部別') or row.get('部別')
            yr = row.get('年度')
            num = row.get('題號')
            if sec and yr and num:
                key = f'{yr}_{sec}_{int(num):03d}'
                report_data[key] = {
                    'moe_url': row.get('辭典連結', ''),
                    'moe_ans': row.get('辭典音讀', '')
                }
    return report_data

def main():
    review_map = load_recheck_review()
    report_map = load_recheck_report()
    
    current_sec = '甲'
    dataset = {'X': [], 'M': [], 'Q': []}
    seq_map = {'X': 1, 'M': 1, 'Q': 1}
    
    with open(MD_PATH, 'r', encoding='utf-8') as f:
        for line in f:
            if '甲、字音部分' in line:
                current_sec = '甲'
            elif '乙、字形部分' in line:
                current_sec = '乙'
                
            m = re.match(r'\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*([^|]+)\s*\|\s*([^|]+)\s*\|\s*([^|]+)\s*\|\s*([XYMQ])\s*\|', line)
            if m:
                yr, num, topic, test_w, ans, status = m.groups()
                yr = int(yr)
                num_int = int(num)
                num_str = f'{num_int:03d}'
                topic = topic.strip()
                test_w = test_w.replace('**', '').replace('`', '').strip()
                clean_ans = ans.replace('**', '').replace('`', '').strip()
                key = f'{yr}_{current_sec}_{num_str}'
                
                if status not in ['X', 'M', 'Q']:
                    continue
                
                pdf_filename = f'{yr}年國語字音字形-高中.pdf' if yr == 110 else f'{yr}年國語字音字形(高中).pdf'
                pdf_rel_path = f'topics/{pdf_filename}'
                crop_rel_path = f'assets/crops/{key}.png'
                
                # 勘誤表資訊
                errata_info = ERRATA_MAP.get(key)
                if errata_info:
                    errata_obj = {
                        'has_errata': True,
                        'ans': errata_info['ans'],
                        'crop_path': errata_info['crop'],
                        'pdf_url': 'old/103-107年國語字音字形勘誤表.pdf',
                        'note': errata_info['note']
                    }
                else:
                    errata_obj = {
                        'has_errata': False,
                        'ans': '(無勘誤)',
                        'crop_path': '',
                        'pdf_url': '',
                        'note': ''
                    }
                
                rev_item = review_map.get(key, {})
                rep_item = report_map.get(key, {})
                raw_ans = rev_item.get('raw_ans', '')
                if not raw_ans:
                    raw_ans = clean_ans
                
                # 教育部辭典資料：精確保留測驗字之注音或國字
                if status in ['X', 'M']:
                    raw_moe = rev_item.get('moe_ph') or rep_item.get('moe_ans', '')
                    if current_sec == '甲':
                        moe_ans = extract_target_pronunciation(topic, test_w, raw_moe)
                    else:
                        # 乙部直接顯示測驗字本身之字形
                        moe_ans = clean_ans
                    moe_url = rev_item.get('moe_url') or rep_item.get('moe_url', '')
                    is_found = bool(moe_url)
                    char_url = f'https://dict.revised.moe.edu.tw/search.jsp?md=2&word={test_w}'
                else: # Q 類
                    moe_ans = '詞條查無'
                    moe_url = ''
                    is_found = False
                    char_url = f'https://dict.revised.moe.edu.tw/search.jsp?md=2&word={test_w}'
                
                note = rev_item.get('review_note', '')
                if not note:
                    if status == 'Q':
                        note = '教育部《重編國語辭典修訂本》查無完整詞條，建議以原卷或單字音審訂'
                    elif status == 'X':
                        note = '待人工審查'
                    elif status == 'M':
                        note = '已比對修正'
                        
                entry = {
                    'id': seq_map[status],
                    'category': status,
                    'sec': current_sec,
                    'year': yr,
                    'num': num_str,
                    'topic': topic,
                    'test_w': test_w,
                    'current_ans': clean_ans,
                    'errata': errata_obj,
                    'original': {
                        'ans': raw_ans,
                        'crop_path': crop_rel_path,
                        'pdf_url': pdf_rel_path
                    },
                    'moe': {
                        'is_found': is_found,
                        'ans': moe_ans,
                        'url': moe_url,
                        'char_url': char_url
                    },
                    'note': note,
                    'action': 'keep'
                }
                dataset[status].append(entry)
                seq_map[status] += 1
                
    with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
        json.dump(dataset, f, ensure_ascii=False, indent=2)
        
    print(f'成功產生爭議字資料集: {OUTPUT_JSON}')
    print(f'X 類: {len(dataset["X"])} 筆')
    print(f'M 類: {len(dataset["M"])} 筆')
    print(f'Q 類: {len(dataset["Q"])} 筆')

if __name__ == '__main__':
    main()
