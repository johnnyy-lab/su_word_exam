#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
國語字音字形題庫——Q類題目四階自動化深度複檢引擎（執行緒安全版）
"""

import os
import sys
import re
import csv
import json
import time
import threading
from urllib.parse import quote
import requests
from bs4 import BeautifulSoup

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MD_PATH = os.path.join(BASE_DIR, 'data', '國語字音字形-高中統整.md')
CACHE_PATH = os.path.join(BASE_DIR, 'data', '.recheck_q_cache.json')
REPORT_PATH = os.path.join(BASE_DIR, 'data', 'recheck_q_results.csv')

HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}

def norm_zh(text):
    return re.sub(r'[\s\u3000、，。；！？「」『』《》（）\(\)\*\`\.\—\─\-\:\：]', '', text or '')

def norm_phone(text):
    return re.sub(r'[\s\u3000\`]', '', text or '')

class DictFetcher:
    def __init__(self, cache_path=CACHE_PATH):
        self.cache_path = cache_path
        self.lock = threading.Lock()
        self.cache = {
            'revised_words': {},
            'revised_chars': {},
            'concise_words': {},
            'concise_chars': {}
        }
        self.load_cache()
        self.dirty_count = 0

    def load_cache(self):
        if os.path.exists(self.cache_path):
            try:
                with open(self.cache_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for k in self.cache:
                        if k in data:
                            self.cache[k] = data[k]
                print(f"載入快取成功: 修訂本詞={len(self.cache['revised_words'])}, 修訂本字={len(self.cache['revised_chars'])}, 簡編本詞={len(self.cache['concise_words'])}, 簡編本字={len(self.cache['concise_chars'])}")
            except Exception as e:
                print(f"載入快取警告: {e}")

    def save_cache(self):
        with self.lock:
            try:
                with open(self.cache_path, 'w', encoding='utf-8') as f:
                    json.dump(self.cache, f, ensure_ascii=False, indent=1)
            except Exception as e:
                print(f"儲存快取錯誤: {e}")

    # 1. 修訂本整詞
    def fetch_revised_word(self, word):
        k = norm_zh(word)
        with self.lock:
            if k in self.cache['revised_words']:
                return self.cache['revised_words'][k]
                
        url = f'https://dict.revised.moe.edu.tw/search.jsp?md=1&word={quote(k)}'
        result = None
        for _ in range(2):
            try:
                r = requests.get(url, headers=HEADERS, timeout=12)
                r.encoding = 'utf-8'
                if '查無資料' not in r.text:
                    soup = BeautifulSoup(r.text, 'html.parser')
                    meta = soup.find('meta', {'name': 'Description'})
                    if meta:
                        cnt = meta.get('content', '')
                        m_w = re.search(r'字詞:([^,]+),', cnt)
                        m_ph = re.search(r'注音:([^,]+),', cnt)
                        if m_w and m_ph:
                            t_w = norm_zh(m_w.group(1))
                            if t_w == k:
                                phones = [p for p in re.split(r'[　\s]+', m_ph.group(1).strip()) if p]
                                result = {'phones': phones, 'content': cnt}
                break
            except Exception:
                time.sleep(0.5)
                
        with self.lock:
            self.cache['revised_words'][k] = result
            self.dirty_count += 1
            if self.dirty_count >= 50:
                self.save_cache()
                self.dirty_count = 0
        return result

    # 2. 修訂本單字
    def fetch_revised_char(self, char):
        k = norm_zh(char)
        with self.lock:
            if k in self.cache['revised_chars']:
                return self.cache['revised_chars'][k]
                
        url = f'https://dict.revised.moe.edu.tw/search.jsp?md=1&word={quote(k)}'
        entries = []
        for _ in range(2):
            try:
                r = requests.get(url, headers=HEADERS, timeout=12)
                r.encoding = 'utf-8'
                soup = BeautifulSoup(r.text, 'html.parser')
                if '辭典檢視' in r.text:
                    meta = soup.find('meta', {'name': 'Description'})
                    if meta:
                        cnt = meta.get('content', '')
                        m_ph = re.search(r'注音:([^,]+),', cnt)
                        ph = m_ph.group(1).strip() if m_ph else ''
                        entries.append({'id': '', 'phone': ph, 'content': cnt})
                else:
                    table = soup.find('table', id='searchL')
                    if table:
                        for tr in table.find_all('tr'):
                            tds = tr.find_all('td', recursive=False)
                            if len(tds) >= 3 and tds[1].get_text(strip=True) == k:
                                link = tr.find('a', href=True)
                                if link and 'ID=' in link['href']:
                                    eid = link['href'].split('ID=')[1].split('&')[0]
                                    rv = requests.get(f'https://dict.revised.moe.edu.tw/dictView.jsp?ID={eid}', headers=HEADERS, timeout=12)
                                    rv.encoding = 'utf-8'
                                    m2 = BeautifulSoup(rv.text, 'html.parser').find('meta', {'name': 'Description'})
                                    if m2:
                                        cnt2 = m2.get('content', '')
                                        m_ph2 = re.search(r'注音:([^,]+),', cnt2)
                                        ph2 = m_ph2.group(1).strip() if m_ph2 else ''
                                        entries.append({'id': eid, 'phone': ph2, 'content': cnt2})
                break
            except Exception:
                time.sleep(0.5)
                
        with self.lock:
            self.cache['revised_chars'][k] = entries
            self.dirty_count += 1
            if self.dirty_count >= 50:
                self.save_cache()
                self.dirty_count = 0
        return entries

    # 3. 簡編本整詞
    def fetch_concise_word(self, word):
        k = norm_zh(word)
        with self.lock:
            if k in self.cache['concise_words']:
                return self.cache['concise_words'][k]
                
        url = f'https://dict.concised.moe.edu.tw/search.jsp?md=1&word={quote(k)}'
        result = None
        for _ in range(2):
            try:
                r = requests.get(url, headers=HEADERS, timeout=12)
                r.encoding = 'utf-8'
                if '查無資料' not in r.text:
                    soup = BeautifulSoup(r.text, 'html.parser')
                    meta = soup.find('meta', {'name': 'Description'})
                    if meta:
                        cnt = meta.get('content', '')
                        m_w = re.search(r'字詞:([^,]+),', cnt)
                        m_ph = re.search(r'注音:([^,]+),', cnt)
                        if m_w and m_ph:
                            t_w = norm_zh(m_w.group(1))
                            if t_w == k:
                                phones = [p for p in re.split(r'[　\s]+', m_ph.group(1).strip()) if p]
                                result = {'phones': phones, 'content': cnt}
                break
            except Exception:
                time.sleep(0.5)
                
        with self.lock:
            self.cache['concise_words'][k] = result
            self.dirty_count += 1
            if self.dirty_count >= 50:
                self.save_cache()
                self.dirty_count = 0
        return result

    # 4. 簡編本單字
    def fetch_concise_char(self, char):
        k = norm_zh(char)
        with self.lock:
            if k in self.cache['concise_chars']:
                return self.cache['concise_chars'][k]
                
        url = f'https://dict.concised.moe.edu.tw/search.jsp?md=1&word={quote(k)}'
        entries = []
        for _ in range(2):
            try:
                r = requests.get(url, headers=HEADERS, timeout=12)
                r.encoding = 'utf-8'
                soup = BeautifulSoup(r.text, 'html.parser')
                if '查無資料' not in r.text:
                    meta = soup.find('meta', {'name': 'Description'})
                    if meta and '簡編本基本檢索' not in meta.get('content', ''):
                        cnt = meta.get('content', '')
                        m_ph = re.search(r'注音:([^,]+),', cnt)
                        ph = m_ph.group(1).strip() if m_ph else ''
                        entries.append({'id': '', 'phone': ph, 'content': cnt})
                    table = soup.find('table', id='searchL')
                    if table:
                        for tr in table.find_all('tr'):
                            tds = tr.find_all('td', recursive=False)
                            if len(tds) >= 3 and tds[1].get_text(strip=True) == k:
                                link = tr.find('a', href=True)
                                if link and 'ID=' in link['href']:
                                    eid = link['href'].split('ID=')[1].split('&')[0]
                                    rv = requests.get(f'https://dict.concised.moe.edu.tw/dictView.jsp?ID={eid}', headers=HEADERS, timeout=12)
                                    rv.encoding = 'utf-8'
                                    m2 = BeautifulSoup(rv.text, 'html.parser').find('meta', {'name': 'Description'})
                                    if m2:
                                        cnt2 = m2.get('content', '')
                                        m_ph2 = re.search(r'注音:([^,]+),', cnt2)
                                        ph2 = m_ph2.group(1).strip() if m_ph2 else ''
                                        entries.append({'id': eid, 'phone': ph2, 'content': cnt2})
                break
            except Exception:
                time.sleep(0.5)
                
        with self.lock:
            self.cache['concise_chars'][k] = entries
            self.dirty_count += 1
            if self.dirty_count >= 50:
                self.save_cache()
                self.dirty_count = 0
        return entries

def check_single_item(item, fetcher):
    sec = item['sec']
    topic = item['topic']
    target = item['test_w']
    ans = item['ans']
    
    if sec == '乙':
        m = re.search(r'[ㄅ-ㄩ]+[ˊˇˋ]?', topic)
        if m:
            clean_topic = topic[:m.start()].strip() + ans + topic[m.end():].strip()
            full_word = re.sub(r'\s+', '', clean_topic)
        else:
            full_word = topic
        char_to_check = ans
        expected_phone = target
    else:
        full_word = topic
        char_to_check = target
        expected_phone = ans
        
    full_word_clean = norm_zh(full_word)
    char_clean = norm_zh(char_to_check)
    expected_phone_clean = norm_phone(expected_phone)
    
    # Step 1: 修訂本整詞
    res1 = fetcher.fetch_revised_word(full_word_clean)
    if res1 and res1.get('phones'):
        phones = res1['phones']
        target_ph = ''
        if char_clean in full_word_clean:
            idx = full_word_clean.find(char_clean)
            if idx < len(phones):
                target_ph = phones[idx]
        if not target_ph and len(phones) > 0:
            target_ph = phones[0]
        match = (norm_phone(target_ph) == expected_phone_clean)
        status = 'Y' if match else 'X'
        return status, 'Step1_修訂本整詞', target_ph, res1['content'][:100]

    # Step 2: 修訂本單字
    res2 = fetcher.fetch_revised_char(char_clean)
    for entry in res2:
        cnt_clean = norm_zh(entry['content'])
        if full_word_clean in cnt_clean:
            target_ph = entry.get('phone', '')
            match = (norm_phone(target_ph) == expected_phone_clean)
            status = 'Y' if match else 'X'
            return status, 'Step2_修訂本單字', target_ph, entry['content'][:100]

    # Step 3: 簡編本整詞
    res3 = fetcher.fetch_concise_word(full_word_clean)
    if res3 and res3.get('phones'):
        phones = res3['phones']
        target_ph = ''
        if char_clean in full_word_clean:
            idx = full_word_clean.find(char_clean)
            if idx < len(phones):
                target_ph = phones[idx]
        if not target_ph and len(phones) > 0:
            target_ph = phones[0]
        match = (norm_phone(target_ph) == expected_phone_clean)
        status = 'Y' if match else 'X'
        return status, 'Step3_簡編本整詞', target_ph, res3['content'][:100]

    # Step 4: 簡編本單字
    res4 = fetcher.fetch_concise_char(char_clean)
    for entry in res4:
        cnt_clean = norm_zh(entry['content'])
        if full_word_clean in cnt_clean:
            target_ph = entry.get('phone', '')
            match = (norm_phone(target_ph) == expected_phone_clean)
            status = 'Y' if match else 'X'
            return status, 'Step4_簡編本單字', target_ph, entry['content'][:100]

    return 'Q', '查無對應詞條', '', ''
