#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
執行全量 Q 類題目深度複檢

流程：
1. 讀取 data/國語字音字形-高中統整.md 取得所有 Q 類題目（共 1,254 筆）
2. 透過 ThreadPoolExecutor（並行數 8）執行四階查驗
3. 產生詳細檢核結果報告 CSV: data/recheck_q_results.csv
4. 更新 data/國語字音字形-高中統整.md 中的狀態欄 (Q -> Y 或 X)
5. 自動呼叫 data/export_dataset.py 與 data/generate_dispute_assets.py 同步題庫與爭議字資料集
6. 執行 verify_all.py 驗收
"""

import os
import sys
import re
import csv
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from data.recheck_q_engine import DictFetcher, check_single_item, MD_PATH, REPORT_PATH

def main():
    print("=== 開始 Q 類題目四階自動化深度複檢 ===")
    fetcher = DictFetcher()
    
    with open(MD_PATH, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        
    q_items = []
    sec = '甲'
    for idx, line in enumerate(lines):
        if '甲、字音部分' in line: sec = '甲'
        elif '乙、字形部分' in line: sec = '乙'
        if line.startswith('|') and line.endswith('|\n'):
            parts = [p.strip() for p in line.split('|')[1:-1]]
            if len(parts) >= 6 and parts[5] == 'Q':
                q_items.append({
                    'line_idx': idx,
                    'sec': sec,
                    'year': parts[0],
                    'num': parts[1],
                    'topic': parts[2].replace('**', '').replace('`', '').strip(),
                    'test_w': parts[3].replace('**', '').replace('`', '').strip(),
                    'ans': parts[4].replace('**', '').replace('`', '').strip(),
                    'raw_parts': parts
                })
                
    total = len(q_items)
    print(f"總共找到 {total} 筆 Q 類題目待複檢。")
    
    results = []
    updated_count = {'Y': 0, 'X': 0, 'Q': 0}
    
    # 建立多執行緒執行
    # 為確保快取執行緒安全，DictFetcher 本身內部有快取，我們可以用一個 worker 函數
    lock = None
    import threading
    lock = threading.Lock()
    
    def process_item(item):
        status, step, dict_ph, snippet = check_single_item(item, fetcher)
        with lock:
            if fetcher.dirty_count >= 30:
                fetcher.save_cache()
                fetcher.dirty_count = 0
        return {
            'item': item,
            'new_status': status,
            'step': step,
            'dict_ph': dict_ph,
            'snippet': snippet
        }

    completed = 0
    t0 = time.time()
    
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {executor.submit(process_item, it): it for it in q_items}
        for fut in as_completed(futures):
            res = fut.result()
            results.append(res)
            completed += 1
            st = res['new_status']
            updated_count[st] += 1
            if st != 'Q':
                it = res['item']
                print(f"[{completed}/{total}] {it['year']} {it['sec']} {it['num']} {it['topic']} ({it['test_w']}) -> 改記為 [{st}]! 命中途徑: {res['step']} (辭典:{res['dict_ph']})")
            elif completed % 50 == 0:
                print(f"[{completed}/{total}] 進度 {(completed/total*100):.1f}% (目前 Y:{updated_count['Y']}, X:{updated_count['X']}, Q:{updated_count['Q']})")

    # 儲存最終快取
    fetcher.save_cache()
    
    # 依照 line_idx 排序結果
    results.sort(key=lambda x: x['item']['line_idx'])
    
    # 寫出詳細報告 CSV
    with open(REPORT_PATH, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['部別', '年度', '題號', '題目詞語', '測驗字', '系統答案', '新狀態', '命中途徑', '辭典注音', '詞條摘要'])
        for r in results:
            it = r['item']
            writer.writerow([it['sec'], it['year'], it['num'], it['topic'], it['test_w'], it['ans'], r['new_status'], r['step'], r['dict_ph'], r['snippet']])
            
    print(f"\n報告已寫入: {REPORT_PATH}")
    print(f"統計結果: Y = {updated_count['Y']} 筆, X = {updated_count['X']} 筆, Q = {updated_count['Q']} 筆 (耗時 {(time.time()-t0):.1f} 秒)")
    
    # 更新 Markdown 表格
    changes_made = 0
    for r in results:
        new_st = r['new_status']
        if new_st != 'Q':
            idx = r['item']['line_idx']
            parts = r['item']['raw_parts']
            parts[5] = new_st
            lines[idx] = '| ' + ' | '.join(parts) + ' |\n'
            changes_made += 1
            
    if changes_made > 0:
        with open(MD_PATH, 'w', encoding='utf-8') as f:
            f.writelines(lines)
        print(f"成功更新 {changes_made} 筆資料於: {MD_PATH}")
        
        # 連動更新題庫與爭議字資料集
        print("\n--- 自動同步題庫資料集 ---")
        import subprocess
        subprocess.run([sys.executable, os.path.join(BASE_DIR, 'data', 'export_dataset.py')], check=True)
        subprocess.run([sys.executable, os.path.join(BASE_DIR, 'data', 'generate_dispute_assets.py')], check=True)
        
        print("\n--- 執行全量驗證 verify_all.py ---")
        res_v = subprocess.run([sys.executable, os.path.join(BASE_DIR, 'verify_all.py')], capture_output=True, text=True, encoding='utf-8', errors='replace')
        print(res_v.stdout)
        if res_v.returncode != 0:
            print("驗證出現錯誤！", res_v.stderr)
    else:
        print("無狀態變更。")

if __name__ == '__main__':
    main()
