#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
國語字音字形題庫結構化 JSON 匯出腳本
將 `國語字音字形-高中統整.md` 完整無損解析並匯出為結構化 JSON 檔案（su_words_bank.json）。
供線上刷題介面、後端題庫 API 及 Word 考卷產出程式直接使用。
"""

import os
import re
import json
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MD_PATH = os.path.join(BASE_DIR, '國語字音字形-高中統整.md')
OUTPUT_JSON = os.path.join(BASE_DIR, 'su_words_bank.json')
OUTPUT_JS = os.path.join(BASE_DIR, 'su_words_bank.js')

def clean_value(val: str) -> str:
    """清理 Markdown 粗體、反引號與多餘空白"""
    if not val:
        return ""
    v = val.strip()
    v = re.sub(r'^\*\*(.*?)\*\*$', r'\1', v)  # 去除前後粗體
    v = v.replace('**', '')                  # 清除殘留粗體
    v = re.sub(r'^`(.*?)`$', r'\1', v)        # 去除前後反引號
    v = v.replace('`', '')                    # 清除殘留反引號
    return v.strip()

def parse_markdown(md_file: str):
    if not os.path.exists(md_file):
        raise FileNotFoundError(f"找不到 Markdown 檔案: {md_file}")

    with open(md_file, 'r', encoding='utf-8') as f:
        content = f.read()

    parts = content.split('## 乙、字形部分')
    if len(parts) < 2:
        raise ValueError("Markdown 檔案格式錯誤：找不到 '## 乙、字形部分'")

    yin_text = parts[0]
    xing_text = '## 乙、字形部分' + parts[1]

    years = ['101', '102', '103', '104', '105', '106', '107', '108', '109', '110', '111', '112', '113', '114']

    all_questions = []
    by_year = {}

    for y in years:
        by_year[y] = {
            "pronunciation": [],
            "character": []
        }

    # 1. 解析字音部分
    # 表格格式: | 年度 | 題號 | 題目詞語 | 測驗字 | 標準注音 |
    row_pattern = r'^\|\s*(\d{3})\s*\|\s*(\d{3})\s*\|\s*([^|]+)\s*\|\s*([^|]+)\s*\|\s*([^|]+)\s*\|$'
    
    yin_count = 0
    for line in yin_text.splitlines():
        line = line.strip()
        m = re.match(row_pattern, line)
        if m:
            yr_str, num_str, question, target_char, ans_phonetic = m.groups()
            if yr_str in years:
                item = {
                    "id": f"{yr_str}-yin-{num_str}",
                    "year": int(yr_str),
                    "category": "高中組",
                    "type": "pronunciation",
                    "type_name": "字音",
                    "num": int(num_str),
                    "num_str": num_str,
                    "prompt": question.strip(),
                    "target": clean_value(target_char),
                    "answer": clean_value(ans_phonetic)
                }
                by_year[yr_str]["pronunciation"].append(item)
                all_questions.append(item)
                yin_count += 1

    # 2. 解析字形部分
    # 表格格式: | 年度 | 題號 | 題目提示詞語 | 測驗字注音 | 標準答案（國字） |
    xing_count = 0
    for line in xing_text.splitlines():
        line = line.strip()
        m = re.match(row_pattern, line)
        if m:
            yr_str, num_str, question, test_phonetic, ans_char = m.groups()
            if yr_str in years:
                item = {
                    "id": f"{yr_str}-xing-{num_str}",
                    "year": int(yr_str),
                    "category": "高中組",
                    "type": "character",
                    "type_name": "字形",
                    "num": int(num_str),
                    "num_str": num_str,
                    "prompt": question.strip(),
                    "target": clean_value(test_phonetic),
                    "answer": clean_value(ans_char)
                }
                by_year[yr_str]["character"].append(item)
                all_questions.append(item)
                xing_count += 1

    # 驗證完整性
    for y in years:
        y_yin = len(by_year[y]["pronunciation"])
        y_xing = len(by_year[y]["character"])
        if y_yin != 100:
            raise ValueError(f"年度 {y} 字音題數異常：預期 100 題，實際 {y_yin} 題")
        if y_xing != 100:
            raise ValueError(f"年度 {y} 字形題數異常：預期 100 題，實際 {y_xing} 題")

    dataset = {
        "metadata": {
            "title": "全國語文競賽 國語字音字形題庫（高中學生組）",
            "description": "收錄民國 101 至 114 年全國語文競賽高中學生組決賽試題與標準答案，全題經 300+ DPI 原卷影像考證與官方勘誤核實。",
            "source_file": "國語字音字形-高中統整.md",
            "version": "1.0.0",
            "created_at": datetime.now().isoformat(),
            "total_questions": len(all_questions),
            "total_years": len(years),
            "years": [int(y) for y in years],
            "counts": {
                "pronunciation": yin_count,
                "character": xing_count
            }
        },
        "by_year": by_year,
        "questions": all_questions
    }

    return dataset

def export_json():
    print(f"正在從 {MD_PATH} 解析題庫...")
    dataset = parse_markdown(MD_PATH)
    meta = dataset["metadata"]

    with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
        json.dump(dataset, f, ensure_ascii=False, indent=2)

    with open(OUTPUT_JS, 'w', encoding='utf-8') as f:
        f.write('window.SU_WORDS_BANK = ' + json.dumps(dataset, ensure_ascii=False) + ';\n')

    file_size_kb = os.path.getsize(OUTPUT_JSON) / 1024
    print("=== 匯出成功 ===")
    print(f"目標檔案: {OUTPUT_JSON}")
    print(f"檔案大小: {file_size_kb:.2f} KB")
    print(f"收錄年度: {meta['years'][0]} ~ {meta['years'][-1]} 年（共 {meta['total_years']} 個年度）")
    print(f"字音題數: {meta['counts']['pronunciation']} 題")
    print(f"字形題數: {meta['counts']['character']} 題")
    print(f"總題數: {meta['total_questions']} 題")

if __name__ == '__main__':
    export_json()
