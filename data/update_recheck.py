#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
國語字音字形題庫——教育部《重編國語辭典修訂本》自動複檢程式

將「甲、字音部分」與「乙、字形部分」表格中的答案，逐一與
教育部《重編國語辭典修訂本》（https://dict.revised.moe.edu.tw）的詞條音讀比對，
並更新表格最後一欄「複檢」的狀態碼：

    N   已建立，未複檢（本程式不會主動寫入 N）
    Q   辭典查詢不到（查無對應詞條）
    X   辭典查詢得到，但與表格答案不符
    Y   辭典查詢得到，且完全正確
    E   網路或解析錯誤（可重跑覆寫為正確狀態）

比對規則：
  甲部（字音）：以「題目詞語」查辭典，取完全相符詞條之逐字音讀，
                比對「測驗字」所在位置之注音與表格「標準注音」是否一致。
  乙部（字形）：以「提示詞語」中的注音佔位還原答案字，組成完整詞語後查辭典，
                比對答案字位置之注音與提示注音是否一致。

用法：
  python data/update_recheck.py                        # 複檢所有 N / E 列
  python data/update_recheck.py --section 甲 --year 101
  python data/update_recheck.py --limit 20 --dry-run   # 試跑 20 筆，不寫入任何檔案
  python data/update_recheck.py --force                # 全部重跑（含 Y / X / Q）
  python data/update_recheck.py --delay 0.4 --no-cache # 不使用快取

產出（預設寫入 data/ 目錄）：
  .dict_cache.json       辭典查詢快取（word -> 查詢結果），可刪除
  recheck_report.csv     逐題複檢報告，含辭典直達連結，供人工複審 X / Q 用
"""

import argparse
import csv
import json
import os
import re
import shutil
import sys
import time
from urllib.parse import quote

import requests
from bs4 import BeautifulSoup

# ---------------------------------------------------------------------------
# 常數
# ---------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MD_PATH = os.path.join(BASE_DIR, 'data', '國語字音字形-高中統整.md')
CACHE_PATH = os.path.join(BASE_DIR, 'data', '.dict_cache.json')
REPORT_PATH = os.path.join(BASE_DIR, 'data', 'recheck_report.csv')
DICT_SEARCH = 'https://dict.revised.moe.edu.tw/search.jsp'
DICT_VIEW = 'https://dict.revised.moe.edu.tw/dictView.jsp'
USER_AGENT = ('Mozilla/5.0 (compatible; su-word-exam-recheck/1.0; '
              '+https://dict.revised.moe.edu.tw)')

STATUS_N, STATUS_Q, STATUS_X, STATUS_Y, STATUS_E = 'N', 'Q', 'X', 'Y', 'E'
FINAL_STATUSES = (STATUS_Y, STATUS_X, STATUS_Q)

# 注音 token：可帶輕聲前導「˙」，後接注音符號與調號
ZHUYIN_TOKEN = re.compile(r'˙?[ㄅ-ㄩ]+[ˊˇˋ]?˙?')


# ---------------------------------------------------------------------------
# 工具函式
# ---------------------------------------------------------------------------
def norm(text):
    """移除所有空白，用於注音或詞語比對。"""
    return re.sub(r'\s+', '', text or '')


def strip_mark(cell):
    """去除 Markdown 粗體記號。"""
    return (cell or '').replace('**', '').strip()


def search_url(word):
    return f'{DICT_SEARCH}?md=1&word={quote(word)}'


def entry_url(entry):
    return f'{DICT_VIEW}?ID={entry["id"]}' if entry and entry.get('id') else ''


def parse_table_rows(lines):
    """解析 Markdown 表格，回傳 [(行索引, 部別, 欄位清單)]。"""
    section = None
    rows = []
    for idx, raw in enumerate(lines):
        line = raw.rstrip('\r').strip()
        if line.startswith('## 甲'):
            section = '甲'
            continue
        if line.startswith('## 乙'):
            section = '乙'
            continue
        if section is None or not line.startswith('|'):
            continue
        cells = [c.strip() for c in line.strip('|').split('|')]
        # 資料列：年度(3 碼) + 題號(3 碼)
        if len(cells) >= 6 and re.fullmatch(r'\d{3}', cells[0]) \
                and re.fullmatch(r'\d{3}', cells[1]):
            rows.append((idx, section, cells))
    return rows


def render_row(cells):
    return '| ' + ' | '.join(cells) + ' |'


# ---------------------------------------------------------------------------
# 辭典查詢
# ---------------------------------------------------------------------------
def parse_view_page(html, soup, word):
    """
    解析「單一詞條完全命中」時直接呈現的檢視頁。
    以 <meta name="Description"> 的「字詞、注音」欄為準（注音以全形空格分隔），
    字詞與查詢詞不一致時視為未命中（回傳 None）；
    meta 解析失敗時，退回擷取頁面前 len(字詞) 個 <code> 注音。
    """
    meta = re.search(r'<meta name="Description" content="字詞:([^,]*),注音:([^,]*),釋義:', html)
    if not meta:
        return None
    title = meta.group(1).strip()
    if norm(title) != norm(word):
        return None
    phones = [p for p in re.split(r'[　\s]+', meta.group(2).strip()) if p]
    if not phones:
        for table in soup.find_all('table', id='searchL'):
            table.decompose()
        codes = [code.get_text(strip=True) for code in soup.find_all('code')]
        phones = codes[:len(title)]
    if not phones:
        return None
    entry_id = ''
    canonical = re.search(r'dictView\.jsp\?ID=(\d+)', html)
    if canonical:
        entry_id = canonical.group(1)
    return [{'id': entry_id, 'phones': phones}]


def parse_list_page(soup, word):
    """解析「檢索結果列表」頁，取出詞目完全相符之條目逐字音讀。"""
    table = soup.find('table', id='searchL')
    if table is None:
        return None
    found = []
    for tr in table.find_all('tr'):
        tds = tr.find_all('td', recursive=False)
        if len(tds) < 3:
            continue
        title = tds[1].get_text(strip=True)
        if title != word:
            continue
        codes = tds[2].find_all('code')
        phones = [c.get_text(strip=True) for c in codes]
        link = tr.find('a', href=True)
        entry_id = ''
        if link:
            m = re.search(r'ID=(\d+)', link['href'])
            if m:
                entry_id = m.group(1)
        if phones:
            found.append({'id': entry_id, 'phones': phones})
    return found or None


def fetch_entries(word, session, cache):
    """
    查詢辭典，回傳「詞目完全相符」之條目清單：
        [{'id': 條目ID, 'phones': [逐字注音, ...]}, ...]
    查無對應詞條時回傳 None。

    辭典檢索頁有三種型態：
      1. 單一詞條完全命中 → 直接呈現「辭典檢視」頁（由 parse_view_page 解析）
      2. 多筆結果           → 「檢索結果列表」頁（由 parse_list_page 解析）
      3. 查無資料           → 列表框架內顯示「查無資料」
    """
    key = norm(word)
    if key in cache:
        return cache[key]

    entries = None
    try:
        resp = session.get(
            DICT_SEARCH,
            params={'md': '1', 'word': word, 'qMd': '0', 'qRow': '0'},
            timeout=30,
        )
        resp.raise_for_status()
        resp.encoding = 'utf-8'
        soup = BeautifulSoup(resp.text, 'html.parser')
        if '辭典檢視' in resp.text:
            entries = parse_view_page(resp.text, soup, word)
        else:
            entries = parse_list_page(soup, word)
    except requests.RequestException as exc:
        raise RuntimeError(f'辭典連線失敗：{exc}') from exc

    cache[key] = entries
    return entries


# ---------------------------------------------------------------------------
# 判定邏輯
# ---------------------------------------------------------------------------
def judge_phonetic(word, target, table_phone, entries):
    """甲部字音判定：比對測驗字位置（或任一位置）的注音。"""
    want = norm(table_phone)
    for entry in entries:
        phones = entry['phones']
        for pos, char in enumerate(word):
            if char == target and pos < len(phones) \
                    and norm(phones[pos]) == want:
                return STATUS_Y, entry
        if any(norm(p) == want for p in phones):
            return STATUS_Y, entry
    return STATUS_X, entries[0]


def build_word(hint, answer):
    """
    乙部：由提示詞與答案字還原完整詞語，並推算答案字在詞中的位置。
    例如 '相去 ㄔˇ 尺' + '咫' -> ('相去咫尺', 2)
    """
    m = ZHUYIN_TOKEN.search(hint)
    if not m:
        return None, None
    prefix = norm(hint[:m.start()])
    suffix = norm(hint[m.end():])
    return prefix + answer + suffix, len(prefix)


def judge_glyph(position, hint_phone, entries):
    """乙部字形判定：比對答案字位置的注音與提示注音。"""
    want = norm(hint_phone)
    for entry in entries:
        phones = entry['phones']
        if position < len(phones) and norm(phones[position]) == want:
            return STATUS_Y, entry
        if any(norm(p) == want for p in phones):
            return STATUS_Y, entry
    return STATUS_X, entries[0]


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------
def load_cache():
    if os.path.exists(CACHE_PATH):
        try:
            with open(CACHE_PATH, 'r', encoding='utf-8') as fh:
                return json.load(fh)
        except (OSError, ValueError):
            print(f'  [警告] 快取檔無法讀取，改用全新快取：{CACHE_PATH}')
    return {}


def save_cache(cache):
    with open(CACHE_PATH, 'w', encoding='utf-8') as fh:
        json.dump(cache, fh, ensure_ascii=False, indent=1)


def main():
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')

    parser = argparse.ArgumentParser(
        description='以教育部《重編國語辭典修訂本》複檢字音字形表格答案')
    parser.add_argument('--section', choices=['甲', '乙', 'all'], default='all',
                        help='只處理指定部別（預設 all）')
    parser.add_argument('--year', default=None,
                        help='只處理指定年度，逗號分隔，如 101,114')
    parser.add_argument('--limit', type=int, default=None,
                        help='本次最多處理筆數（預設全部）')
    parser.add_argument('--force', action='store_true',
                        help='重跑所有列（預設跳過已為 Y / X / Q 之列）')
    parser.add_argument('--delay', type=float, default=0.4,
                        help='每次請求間隔秒數（預設 0.4，對辭典主機友善）')
    parser.add_argument('--dry-run', action='store_true',
                        help='只執行判定與印報，不寫入任何檔案')
    parser.add_argument('--no-cache', action='store_true',
                        help='不使用（也不更新）查詢快取')
    args = parser.parse_args()

    print('=== 國語字音字形題庫 辭典複檢 ===')
    print(f'目標檔案：{MD_PATH}')

    with open(MD_PATH, 'r', encoding='utf-8') as fh:
        lines = fh.read().split('\n')

    rows = parse_table_rows(lines)
    print(f'解析資料列：{len(rows)} 列'
          f'（甲 {sum(1 for r in rows if r[1] == "甲")}、'
          f'乙 {sum(1 for r in rows if r[1] == "乙")}）')

    years = None
    if args.year:
        years = {y.strip() for y in args.year.split(',') if y.strip()}

    # 篩選待處理列
    todo = []
    for idx, section, cells in rows:
        if args.section != 'all' and section != args.section:
            continue
        if years and cells[0] not in years:
            continue
        status = cells[5] if len(cells) > 5 else STATUS_N
        if not args.force and status in FINAL_STATUSES:
            continue
        todo.append((idx, section, cells))
    if args.limit:
        todo = todo[:args.limit]
    print(f'待複檢列數：{len(todo)}（'
          f'{"全部重跑" if args.force else "僅 N / E"}，'
          f'延遲 {args.delay}s）')

    cache = {} if args.no_cache else load_cache()
    session = requests.Session()
    session.headers.update({'User-Agent': USER_AGENT})

    stats = {STATUS_Y: 0, STATUS_X: 0, STATUS_Q: 0, STATUS_E: 0}
    stats_sec = {'甲': dict(stats), '乙': dict(stats)}
    report = []
    changed = 0

    for count, (idx, section, cells) in enumerate(todo, 1):
        year, no = cells[0], cells[1]
        old_status = cells[5] if len(cells) > 5 else STATUS_N
        status, note, entry, query = STATUS_E, '', None, ''
        try:
            if section == '甲':
                word = cells[2].strip()
                target = strip_mark(cells[3])
                table_phone = cells[4]
                query = word
                entries = fetch_entries(word, session, cache)
                if entries is None:
                    status, note = STATUS_Q, '辭典查無此詞條'
                else:
                    status, entry = judge_phonetic(
                        word, target, table_phone, entries)
                    note = '' if status == STATUS_Y else '注音與辭典音讀不符'
                report.append([
                    section, year, no, query, target, table_phone,
                    entry['id'] if entry else '',
                    entry_url(entry) if entry else search_url(word),
                    ' '.join(entry['phones']) if entry else '',
                    status, note,
                ])
            else:
                hint = cells[2]
                hint_phone = cells[3]
                answer = strip_mark(cells[4])
                full, position = build_word(hint, answer)
                if full is None:
                    status = STATUS_X
                    note = '提示詞解析不到注音，無法還原詞語'
                    report.append([section, year, no, hint, answer,
                                   hint_phone, '', search_url(hint), '',
                                   status, note])
                else:
                    query = full
                    entries = fetch_entries(full, session, cache)
                    if entries is None:
                        status, note = STATUS_Q, '辭典查無此詞條'
                    else:
                        status, entry = judge_glyph(
                            position, hint_phone, entries)
                        note = '' if status == STATUS_Y else '注音與辭典音讀不符'
                    report.append([
                        section, year, no, full, answer, hint_phone,
                        entry['id'] if entry else '',
                        entry_url(entry) if entry else search_url(full),
                        ' '.join(entry['phones']) if entry else '',
                        status, note,
                    ])
        except RuntimeError as exc:
            status = STATUS_E
            note = str(exc)
            report.append([section, year, no, query, '', '', '', '', '',
                           status, note])

        # 更新記憶體中的資料列
        while len(cells) < 6:
            cells.append(STATUS_N)
        cells[5] = status
        lines[idx] = render_row(cells)
        if status != old_status:
            changed += 1

        stats[status] = stats.get(status, 0) + 1
        stats_sec[section][status] += 1
        time.sleep(args.delay)

        if count % 25 == 0 or count == len(todo):
            print(f'  進度 {count}/{len(todo)}｜'
                  f'Y {stats[STATUS_Y]}、X {stats[STATUS_X]}、'
                  f'Q {stats[STATUS_Q]}、E {stats[STATUS_E]}')

    # 輸出統計
    print('\n=== 複檢結果統計 ===')
    for section in ('甲', '乙'):
        s = stats_sec[section]
        total = sum(s.values())
        print(f'  {section}部：{total} 筆 → '
              f'Y {s[STATUS_Y]}、X {s[STATUS_X]}、'
              f'Q {s[STATUS_Q]}、E {s[STATUS_E]}')
    print(f'  合計：Y {stats[STATUS_Y]}、X {stats[STATUS_X]}、'
          f'Q {stats[STATUS_Q]}、E {stats[STATUS_E]}'
          f'（本次實際改動 {changed} 列）')

    if args.dry_run:
        print('\n[dry-run] 未寫入任何檔案。')
        print('\n前 10 筆明細：')
        for row in report[:10]:
            print('  ' + ' | '.join(str(c) for c in row))
        return

    # 備份（僅第一次）
    backup = MD_PATH + '.bak'
    if not os.path.exists(backup):
        shutil.copy2(MD_PATH, backup)
        print(f'\n已備份原檔：{backup}')

    with open(MD_PATH, 'w', encoding='utf-8', newline='') as fh:
        fh.write('\n'.join(lines))
    print(f'已更新複檢欄位：{MD_PATH}（改動 {changed} 列）')

    if not args.no_cache:
        save_cache(cache)
        print(f'已更新查詢快取：{CACHE_PATH}')

    with open(REPORT_PATH, 'w', encoding='utf-8-sig', newline='') as fh:
        writer = csv.writer(fh)
        writer.writerow(['部別', '年度', '題號', '查詢詞', '測驗字/答案',
                         '表格注音', '辭典條目ID', '辭典連結',
                         '辭典音讀', '複檢', '備註'])
        writer.writerows(report)
    print(f'已產出複檢報告：{REPORT_PATH}（{len(report)} 筆）')

    if stats[STATUS_E]:
        print('\n[提示] 有連線或解析錯誤（E），修正網路後重跑即可覆寫。')
    if stats[STATUS_X] or stats[STATUS_Q]:
        print('[提示] X / Q 列請參閱 recheck_report.csv 人工複審。')


if __name__ == '__main__':
    main()
