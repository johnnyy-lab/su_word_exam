import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import re
from data.crop_engine import crop_item_image, CROPS_DIR

MD_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), '國語字音字形-高中統整.md')

def main():
    print('開始全量批次產出精確單行原卷截圖...')
    items_to_crop = []
    current_sec = '甲'
    with open(MD_PATH, 'r', encoding='utf-8') as f:
        for line in f:
            if '甲、字音部分' in line:
                current_sec = '甲'
            elif '乙、字形部分' in line:
                current_sec = '乙'
            m = re.match(r'\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*([^|]+)\s*\|\s*([^|]+)\s*\|\s*([^|]+)\s*\|\s*([XYMQ])\s*\|', line)
            if m:
                yr, num, topic, test_w, ans, status = m.groups()
                if status in ['X', 'M', 'Q']:
                    items_to_crop.append((int(yr), current_sec, int(num), status))
                    
    total = len(items_to_crop)
    print(f'待處理總題目數: {total} (含 X, M, Q)')
    
    success = 0
    errors = []
    widths = []
    
    for idx, (yr, sec, num, status) in enumerate(items_to_crop):
        try:
            crop = crop_item_image(yr, sec, num, save_cache=True)
            success += 1
            widths.append(crop.width)
            if (idx + 1) % 200 == 0 or (idx + 1) == total:
                print(f'進度: {idx+1}/{total} (已完成 {success} 筆)')
        except Exception as e:
            errors.append((yr, sec, num, str(e)))
            print(f'錯誤: {yr}_{sec}_{num:03d}: {e}')
            
    print(f'\n全量裁切完成！成功: {success}/{total}, 失敗: {len(errors)}')
    if widths:
        print(f'裁切圖片寬度統計: 最小={min(widths)}, 最大={max(widths)}, 平均={sum(widths)/len(widths):.1f}')

if __name__ == '__main__':
    main()
