import os
import sys
import re
import json
import subprocess

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from server import apply_dispute_changes

def extract_json_from_text(text):
    # 尋找 ```json ... ``` 區塊
    m = re.search(r'```json\s*([\s\S]*?)\s*```', text)
    if m:
        return json.loads(m.group(1))
    # 否則尋找純 JSON 陣列
    m2 = re.search(r'\[\s*\{[\s\S]*\}\s*\]', text)
    if m2:
        return json.loads(m2.group(0))
    raise ValueError('無法從文字內容中解析出合法的 JSON 修改陣列')

def main():
    # 優先從環境變數或命令行參數讀取
    issue_body = os.environ.get('ISSUE_BODY', '')
    if not issue_body and len(sys.argv) > 1:
        # 可能傳入檔案路徑或直接字串
        arg = sys.argv[1]
        if os.path.exists(arg):
            with open(arg, 'r', encoding='utf-8') as f:
                issue_body = f.read()
        else:
            issue_body = arg

    if not issue_body:
        print('錯誤: 未提供 Issue 內容或修改 JSON。')
        sys.exit(1)

    print('正在解析修改項目...')
    changes = extract_json_from_text(issue_body)
    print(f'共提取出 {len(changes)} 筆待修改項目:')
    for c in changes:
        print(f"  - {c.get('year')} 年 {c.get('sec')} 部 第 {c.get('num')} 題: 選項 [{c.get('action')}]")

    print('\n開始執行題目更新與自動化驗證...')
    res = apply_dispute_changes(changes)

    if not res.get('success'):
        print(f"更新失敗: {res.get('error', '未知錯誤')}")
        sys.exit(1)

    if not res.get('verify_passed'):
        print("驗收失敗 (verify_all.py 未通過):")
        print(res.get('verify_output', ''))
        sys.exit(1)

    print(f"\n成功更新 {res.get('updated_count')} 筆題目，且驗收全部通過 (ALL PASS)！")

if __name__ == '__main__':
    main()
