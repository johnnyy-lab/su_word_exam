import os
import sys
import json
import time

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import pymupdf
from PIL import Image
from data.crop_engine import get_pdf_path, get_crop_box, CROPS_DIR

def batch_crop_all():
    json_path = os.path.join(BASE_DIR, 'data', 'disputes_dataset.json')
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # 收集所有項目 (X, M, Q)
    all_items = []
    for cat in ['X', 'M', 'Q']:
        for it in data.get(cat, []):
            all_items.append((it['year'], it['sec'], int(it['num'])))

    # 依照 (year, sec) 分組以最大化快取 pixmap
    grouped = {}
    for yr, sec, num in all_items:
        key = (yr, sec)
        if key not in grouped:
            grouped[key] = []
        grouped[key].append(num)

    total_cropped = 0
    start_time = time.time()

    print(f'開始批次產生靜態截圖，共 {len(all_items)} 題...')

    for (yr, sec), nums in grouped.items():
        # 檢查是否有任何一題尚未產生
        pending_nums = []
        for n in nums:
            fn = f'{yr}_{sec}_{n:03d}.png'
            fp = os.path.join(CROPS_DIR, fn)
            if not os.path.exists(fp):
                pending_nums.append(n)

        if not pending_nums:
            continue

        doc = pymupdf.open(get_pdf_path(yr))
        
        # 決定需要渲染哪些 page_idx
        # 橫式 (102-110): 甲=0, 乙=1
        # 直式 (101, 111-114): 甲右=0, 甲左=1, 乙右=2, 乙左=3
        pages_to_render = {}
        for n in pending_nums:
            if 102 <= yr <= 110:
                p_idx = 0 if sec == '甲' else 1
            else:
                def in_right(q):
                    return (1 <= q <= 10) or (26 <= q <= 35) or (51 <= q <= 60) or (76 <= q <= 85)
                is_r = in_right(n)
                if sec == '甲':
                    p_idx = 0 if is_r else 1
                else:
                    p_idx = 2 if is_r else 3
            if p_idx not in pages_to_render:
                pages_to_render[p_idx] = []
            pages_to_render[p_idx].append(n)

        for p_idx, p_nums in pages_to_render.items():
            page = doc[p_idx]
            pix = page.get_pixmap(dpi=180)
            img = Image.frombytes('RGB', [pix.width, pix.height], pix.samples)
            w, h = img.size

            for n in p_nums:
                box = get_crop_box(yr, sec, n, w, h)
                cropped = img.crop(box)
                out_path = os.path.join(CROPS_DIR, f'{yr}_{sec}_{n:03d}.png')
                cropped.save(out_path, optimize=True)
                total_cropped += 1

        print(f'已完成 {yr} 年 {sec} 部截圖 (本批產生 {len(pending_nums)} 張)')

    elapsed = time.time() - start_time
    print(f'批次裁切完成！共新產出 {total_cropped} 張截圖，耗時 {elapsed:.2f} 秒。')

if __name__ == '__main__':
    batch_crop_all()
