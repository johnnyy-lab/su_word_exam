import os
import re

print("=== 國語字音字形統整題庫 全面自動化驗證 ===")

# 1. 檢查檔案存在與歸檔情況
print("\n[檢查項 1: 檔案歸檔狀態]")
expected_topics = [
    '101年國語字音字形(高中).pdf',
    '102年國語字音字形(高中).pdf',
    '103年國語字音字形(高中).pdf',
    '104年國語字音字形(高中).pdf',
    '105年國語字音字形(高中).pdf',
    '106年國語字音字形(高中).pdf',
    '107年國語字音字形(高中).pdf',
    '108年國語字音字形(高中).pdf',
    '109年國語字音字形(高中).pdf',
    '110年國語字音字形-高中.pdf',
    '111年國語字音字形(高中).pdf',
    '112年國語字音字形(高中).pdf',
    '113年國語字音字形(高中).pdf',
    '114年國語字音字形(高中).pdf'
]
for f in expected_topics:
    path = os.path.join('topics', f)
    exists = os.path.exists(path)
    status = "PASS" if exists else "FAIL"
    print(f"  topics/{f}: {status}")
    assert exists, f"Missing topics/{f}"

expected_old = [
    '101年全國語文競賽成果專輯.pdf',
    '102年.pdf',
    '103-107年國語字音字形勘誤表.pdf',
    '103國語字音字形-國高中.pdf',
    '104國語字音字形-國高中.pdf',
    '105國語字音字形-國高中.pdf',
    '106國語字音字形-國高中.pdf',
    '107國語字音字形-國高中.pdf',
    '108年國語字音字形.pdf',
    '109年國語字音字形.pdf',
    '111年.pdf',
    '112年.pdf',
    '113年.pdf',
    '114年.pdf'
]
for f in expected_old:
    path = os.path.join('old', f)
    exists = os.path.exists(path)
    status = "PASS" if exists else "FAIL"
    print(f"  old/{f}: {status}")
    assert exists, f"Missing old/{f}"

# 2. 檢查 Markdown 內容結構與品質
print("\n[檢查項 2: Markdown 結構與內容解析]")
md_path = os.path.join('data', '國語字音字形-高中統整.md') if os.path.exists(os.path.join('data', '國語字音字形-高中統整.md')) else '國語字音字形-高中統整.md'
with open(md_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

print(f"  總行數: {len(lines)}")

parts = ''.join(lines).split('## 乙、字形部分')
yin_text = parts[0]
xing_text = '## 乙、字形部分' + parts[1]

years = ['101', '102', '103', '104', '105', '106', '107', '108', '109', '110', '111', '112', '113', '114']

# 驗證字音
print("\n[檢查項 3: 甲、字音部分 逐年驗證]")
for y in years:
    pattern = rf'^\|\s*{y}\s*\|\s*(\d{{3}})\s*\|\s*([^|]+)\s*\|\s*([^|]+)\s*\|\s*([^|]+)\s*\|$'
    rows = []
    for line in yin_text.splitlines():
        m = re.match(pattern, line.strip())
        if m:
            rows.append(m.groups())
    
    print(f"  年度 {y}: 抓取到 {len(rows)} 題")
    assert len(rows) == 100, f"年度 {y} 字音題數不為 100: {len(rows)}"
    
    for i, (num_str, q, test_char, ans) in enumerate(rows, 1):
        num = int(num_str)
        assert num == i, f"年度 {y} 字音題號不連續: 預期 {i:03d}, 實際 {num_str}"
        assert len(q.strip()) > 0, f"年度 {y} 字音第 {i} 題題目為空"
        assert len(test_char.strip()) > 0, f"年度 {y} 字音第 {i} 題測驗字為空"
        assert len(ans.strip()) > 0, f"年度 {y} 字音第 {i} 題答案為空"
        assert '?' not in q and '□' not in q and '?' not in ans, f"年度 {y} 字音第 {i} 題含有問號或佔位符"

print("  -> 字音部分所有年度連續性、完整性檢驗全部 PASS！")

# 驗證字形
print("\n[檢查項 4: 乙、字形部分 逐年驗證]")
for y in years:
    pattern = rf'^\|\s*{y}\s*\|\s*(\d{{3}})\s*\|\s*([^|]+)\s*\|\s*([^|]+)\s*\|\s*([^|]+)\s*\|$'
    rows = []
    for line in xing_text.splitlines():
        m = re.match(pattern, line.strip())
        if m:
            rows.append(m.groups())
    
    print(f"  年度 {y}: 抓取到 {len(rows)} 題")
    assert len(rows) == 100, f"年度 {y} 字形題數不為 100: {len(rows)}"
    
    for i, (num_str, q, test_zhuyin, ans) in enumerate(rows, 1):
        num = int(num_str)
        assert num == i, f"年度 {y} 字形題號不連續: 預期 {i:03d}, 實際 {num_str}"
        assert len(q.strip()) > 0, f"年度 {y} 字形第 {i} 題題目為空"
        assert len(test_zhuyin.strip()) > 0, f"年度 {y} 字形第 {i} 題測驗注音為空"
        assert len(ans.strip()) > 0, f"年度 {y} 字形第 {i} 題答案為空"
        assert '?' not in q and '□' not in q and '?' not in ans, f"年度 {y} 字形第 {i} 題含有問號或佔位符"

print("  -> 字形部分所有年度連續性、完整性檢驗全部 PASS！")

# 3. 勘誤表與關鍵題目核驗
print("\n[檢查項 5: 各年度關鍵題目核驗]")
with open(md_path, 'r', encoding='utf-8') as f:
    full_content = f.read()

# 102 年
assert '| 102 | 012 | 鬲鼎 | **鬲** | ㄌㄧˋ |' in full_content, '102 音 012 鬲鼎 未正確收錄'
assert '| 102 | 014 | 庋藏 | **庋** | ㄐㄧˇ |' in full_content, '102 音 014 庋藏 未正確收錄'
assert '| 102 | 052 | 干越夷貉 | **貉** | ㄇㄛˋ |' in full_content, '102 音 052 干越夷貉 未正確收錄'
assert '| 102 | 067 | 卬須我友 | **卬** | ㄤˊ |' in full_content, '102 音 067 卬須我友 未正確收錄'
assert '| 102 | 098 | 雜臿其間 | **臿** | ㄔㄚ |' in full_content, '102 音 098 雜臿其間 未正確收錄'
assert '| 102 | 010 | ㄉㄧㄢˋ 腳石 | ㄉㄧㄢˋ | **墊** |' in full_content, '102 形 010 墊腳石 未正確收錄'
assert '| 102 | 027 | 媒體 ㄆㄧ 露 | ㄆㄧ | **披** |' in full_content, '102 形 027 媒體披露 未正確收錄'
assert '| 102 | 035 | 一 ㄒㄧㄝˋ 千里 | ㄒㄧㄝˋ | **瀉** |' in full_content, '102 形 035 一瀉千里 未正確收錄'
assert '| 102 | 062 | ㄕㄥ 價十倍 | ㄕㄥ | **聲** |' in full_content, '102 形 062 聲價十倍 未正確收錄'
print("  102 年關鍵題目 9 項: 全部 PASS")

# 106 年
assert '| 106 | 017 | 合巹酒 | **巹** | ㄐㄧㄣˇ |' in full_content, '106 音 017 勘誤未生效'
assert '| 106 | 067 | 戇頭戇腦 | **戇** | ㄓㄨㄤˋ |' in full_content, '106 音 067 勘誤未生效'
assert '| 106 | 024 | ㄒㄩㄣˋ 私廢公 | ㄒㄩㄣˋ | **徇** |' in full_content, '106 形 024 勘誤未生效'
assert '| 106 | 041 | 羽 ㄍㄜˊ 已就 | ㄍㄜˊ | **翮** |' in full_content, '106 形 041 勘誤未生效'
assert '| 106 | 044 | ㄐㄧㄝˊ 櫫綱要 | ㄐㄧㄝˊ | **楬** |' in full_content, '106 形 044 勘誤未生效'
assert '| 106 | 056 | ㄒㄩㄢˊ 璣玉衡 | ㄒㄩㄢˊ | **璿** |' in full_content, '106 形 056 勘誤未生效'
print("  106 年勘誤 6 項: 全部 PASS")

# 107 年
assert '| 107 | 026 | 手如柔荑 | **荑** | ㄧˊ |' in full_content, '107 音 026 勘誤未生效'
assert '| 107 | 014 | 紛至 ㄊㄚˋ 來 | ㄊㄚˋ | **沓** |' in full_content, '107 形 014 勘誤未生效'
print("  107 年勘誤 2 項: 全部 PASS")

# 108 年
assert '| 108 | 002 | 愉惰 | **愉** | ㄊㄡ |' in full_content, '108 音 002 愉惰 未正確收錄'
assert '| 108 | 009 | 蜑戶 | **蜑** | ㄉㄢˋ |' in full_content, '108 音 009 蜑戶 未正確收錄'
assert '| 108 | 040 | 楩楠之材 | **楩** | ㄆㄧㄢˊ |' in full_content, '108 音 040 楩楠之材 未正確收錄'
assert '| 108 | 082 | ㄓㄨ 墨爛然 | ㄓㄨ | **朱** |' in full_content, '108 形 082 朱墨爛然 未正確收錄'
assert '| 108 | 084 | ㄧㄡˋ 如充耳 | ㄧㄡˋ | **褎** |' in full_content, '108 形 084 褎如充耳 未正確收錄'
assert '| 108 | 097 | 引君入 ㄍㄡˋ | ㄍㄡˋ | **彀** |' in full_content, '108 形 097 引君入彀 未正確收錄'
print("  108 年關鍵題目 6 項: 全部 PASS")

# 109 年
assert '| 109 | 025 | 頑肩奡比 | **奡** | ㄠˋ |' in full_content, '109 音 025 頑肩奡比 未正確收錄'
assert '| 109 | 047 | 狎翫靈胥 | **翫** | ㄨㄢˋ |' in full_content, '109 音 047 狎翫靈胥 未正確收錄'
assert '| 109 | 086 | 潢洋無涯 | **潢** | ㄨㄤˇ |' in full_content, '109 音 086 潢洋無涯 未正確收錄'
assert '| 109 | 100 | 伐善攘羭 | **羭** | ㄩˊ |' in full_content, '109 音 100 伐善攘羭 未正確收錄'
assert '| 109 | 013 | 捐款 ㄉㄡˇ 增 | ㄉㄡˇ | **陡** |' in full_content, '109 形 013 捐款陡增 未正確收錄'
assert '| 109 | 032 | 公案 ㄅㄧˇ 語 | ㄅㄧˇ | **比** |' in full_content, '109 形 032 公案比語 未正確收錄'
assert '| 109 | 088 | 跌宕 ㄑㄧㄡˊ 麗 | ㄑㄧㄡˊ | **遒** |' in full_content, '109 形 088 跌宕遒麗 未正確收錄'
assert '| 109 | 098 | 銘 ㄌㄟˇ 尚實 | ㄌㄟˇ | **誄** |' in full_content, '109 形 098 銘誄尚實 未正確收錄'
print("  109 年關鍵題目 8 項: 全部 PASS")

# 111 年
assert '| 111 | 007 | 輿謣 | **謣** | ㄒㄩ |' in full_content, '111 音 007 輿謣 未正確收錄'
assert '| 111 | 023 | 獸足厹地 | **厹** | ㄖㄡˊ |' in full_content, '111 音 023 獸足厹地 未正確收錄'
assert '| 111 | 029 | 衙衙緩行 | **衙** | ㄩˊ |' in full_content, '111 音 029 衙衙緩行 未正確收錄'
assert '| 111 | 038 | 魚躍奫淪 | **奫** | ㄩㄣ |' in full_content, '111 音 038 魚躍奫淪 未正確收錄'
assert '| 111 | 042 | 有冽氿泉 | **氿** | ㄍㄨㄟˇ |' in full_content, '111 音 042 有冽氿泉 未正確收錄'
assert '| 111 | 050 | 詩經泂酌 | **泂** | ㄐㄩㄥˇ |' in full_content, '111 音 050 詩經泂酌 未正確收錄'
assert '| 111 | 096 | 晅晒衣物 | **晅** | ㄒㄩㄢ |' in full_content, '111 音 096 晅晒衣物 未正確收錄'
assert '| 111 | 100 | 山氣巃嵸 | **嵸** | ㄗㄨㄥ |' in full_content, '111 音 100 山氣巃嵸 未正確收錄'
assert '| 111 | 008 | 面縛輿 ㄔㄣˋ | ㄔㄣˋ | **櫬** |' in full_content, '111 形 008 面縛輿櫬 未正確收錄'
assert '| 111 | 026 | 傾家 ㄉㄤˋ 產 | ㄉㄤˋ | **蕩** |' in full_content, '111 形 026 傾家蕩產 未正確收錄'
assert '| 111 | 042 | ㄒㄧ 和馭日 | ㄒㄧ | **羲** |' in full_content, '111 形 042 羲和馭日 未正確收錄'
assert '| 111 | 057 | ㄧˊ 堂燕雀 | ㄧˊ | **怡** |' in full_content, '111 形 057 怡堂燕雀 未正確收錄'
assert '| 111 | 071 | 旁招俊 ㄧˋ | ㄧˋ | **乂** |' in full_content, '111 形 071 旁招俊乂 未正確收錄'
assert '| 111 | 098 | 隆恩 ㄎㄨㄤˋ 典 | ㄎㄨㄤˋ | **曠** |' in full_content, '111 形 098 隆恩曠典 未正確收錄'
assert '| 111 | 099 | 應圖受 ㄌㄨˋ | ㄌㄨˋ | **籙** |' in full_content, '111 形 099 應圖受籙 未正確收錄'
print("  111 年評審總講評關鍵題目 15 項: 全部 PASS")

# 112 年
assert '| 112 | 009 | 襒席 | **襒** | ㄅㄧㄝˊ |' in full_content, '112 音 009 襒席 未正確收錄'
assert '| 112 | 013 | 佷戾 | **佷** | ㄏㄣˇ |' in full_content, '112 音 013 佷戾 未正確收錄'
assert '| 112 | 044 | 眾怒難任 | **任** | ㄖㄣˋ |' in full_content, '112 音 044 眾怒難任 未正確收錄'
assert '| 112 | 056 | 謾天昧地 | **謾** | ㄇㄢˋ |' in full_content, '112 音 056 謾天昧地 未正確收錄'
assert '| 112 | 063 | 獶為獮猴 | **獮** | ㄒㄧㄢˇ |' in full_content, '112 音 063 獶為獮猴 未正確收錄'
assert '| 112 | 078 | 香港紅磡 | **磡** | ㄎㄢˋ |' in full_content, '112 音 078 香港紅磡 未正確收錄'
assert '| 112 | 081 | 牛羊之湩 | **湩** | ㄉㄨㄥˋ |' in full_content, '112 音 081 牛羊之湩 未正確收錄'
assert '| 112 | 096 | 長波浹渫 | **渫** | ㄒㄧㄝˋ |' in full_content, '112 音 096 長波浹渫 未正確收錄'
assert '| 112 | 045 | ㄈㄨˋ 蛇螫手 | ㄈㄨˋ | **蝮** |' in full_content, '112 形 045 蝮蛇螫手 未正確收錄'
assert '| 112 | 081 | ㄌㄧㄣˊ 鴻附便 | ㄌㄧㄣˊ | **鱗** |' in full_content, '112 形 081 鱗鴻附便 未正確收錄'
assert '| 112 | 083 | 推賢 ㄒㄩㄣˋ 能 | ㄒㄩㄣˋ | **遜** |' in full_content, '112 形 083 推賢遜能 未正確收錄'
assert '| 112 | 089 | 清 ㄅㄧˋ 傳道 | ㄅㄧˋ | **蹕** |' in full_content, '112 形 089 清蹕傳道 未正確收錄'
assert '| 112 | 095 | ㄏㄢ 咀寓意 | ㄏㄢ | **涵** |' in full_content, '112 形 095 涵咀寓意 未正確收錄'
assert '| 112 | 100 | ㄇㄠˋ 首之仇 | ㄇㄠˋ | **貿** |' in full_content, '112 形 100 貿首之仇 未正確收錄'
print("  112 年評審總講評關鍵題目 14 項: 全部 PASS")

# 113 年
assert '| 113 | 005 | 剚刃 | **剚** | ㄗˋ |' in full_content, '113 音 005 剚刃 未正確收錄'
assert '| 113 | 019 | 滮水 | **滮** | ㄅㄧㄠ |' in full_content, '113 音 019 滮水 未正確收錄'
assert '| 113 | 044 | 才窘氣苶 | **苶** | ㄋㄧㄝˊ |' in full_content, '113 音 044 才窘氣苶 未正確收錄'
assert '| 113 | 060 | 顧盼暐如 | **暐** | ㄨㄟˇ |' in full_content, '113 音 060 顧盼暐如 未正確收錄'
assert '| 113 | 072 | 南蠻北貉 | **貉** | ㄇㄛˋ |' in full_content, '113 音 072 南蠻北貉 未正確收錄'
assert '| 113 | 077 | 輮以為輪 | **輮** | ㄖㄡˊ |' in full_content, '113 音 077 輮以為輪 未正確收錄'
assert '| 113 | 079 | 左右僕射 | **射** | ㄧㄝˋ |' in full_content, '113 音 079 左右僕射 未正確收錄'
assert '| 113 | 082 | 癯而實肥 | **癯** | ㄑㄩˊ |' in full_content, '113 音 082 癯而實肥 未正確收錄'
assert '| 113 | 090 | 霡霂霏霏 | **霡** | ㄇㄞˋ |' in full_content, '113 音 090 霡霂霏霏 未正確收錄'
assert '| 113 | 092 | 錚錚鏦鏦 | **鏦** | ㄔㄨㄥ |' in full_content, '113 音 092 錚錚鏦鏦 未正確收錄'
assert '| 113 | 001 | 從中 ㄨㄛˋ 旋 | ㄨㄛˋ | **斡** |' in full_content, '113 形 001 從中斡旋 未正確收錄'
assert '| 113 | 002 | 伯喈倒 ㄒㄧˇ | ㄒㄧˇ | **屣** |' in full_content, '113 形 002 伯喈倒屣 未正確收錄'
assert '| 113 | 015 | 鳩工 ㄆㄧˇ 材 | ㄆㄧˇ | **庀** |' in full_content, '113 形 015 鳩工庀材 未正確收錄'
assert '| 113 | 026 | 羽扇 ㄍㄨㄢ 巾 | ㄍㄨㄢ | **綸** |' in full_content, '113 形 026 羽扇綸巾 未正確收錄'
assert '| 113 | 039 | 身體 ㄌㄟˊ 弱 | ㄌㄟˊ | **羸** |' in full_content, '113 形 039 身體羸弱 未正確收錄'
assert '| 113 | 048 | 攢眉 ㄘㄨˋ 鼻 | ㄘㄨˋ | **蹙** |' in full_content, '113 形 048 攢眉蹙鼻 未正確收錄'
assert '| 113 | 061 | 疑人竊 ㄐㄧㄚˊ | ㄐㄧㄚˊ | **鋏** |' in full_content, '113 形 061 疑人竊鋏 未正確收錄'
assert '| 113 | 076 | 佩 ㄗˇ 懷黃 | ㄗˇ | **紫** |' in full_content, '113 形 076 佩紫懷黃 未正確收錄'
assert '| 113 | 084 | 戰功 ㄅㄧㄠ 炳 | ㄅㄧㄠ | **彪** |' in full_content, '113 形 084 戰功彪炳 未正確收錄'
assert '| 113 | 096 | ㄏㄞˋ 人聽聞 | ㄏㄞˋ | **駭** |' in full_content, '113 形 096 駭人聽聞 未正確收錄'
print("  113 年關鍵題目 20 項: 全部 PASS")

# 114 年
assert '| 114 | 001 | 厥疾勿瘳 | **瘳** | ㄔㄡ |' in full_content, '114 音 001 厥疾勿瘳 未正確收錄'
assert '| 114 | 005 | 靈鼉之鼓 | **鼉** | ㄊㄨㄛˊ |' in full_content, '114 音 005 靈鼉之鼓 未正確收錄'
assert '| 114 | 008 | 用力勒緊 | **勒** | ㄌㄟ |' in full_content, '114 音 008 用力勒緊 未正確收錄'
assert '| 114 | 013 | 酸酵作用 | **酵** | ㄒㄧㄠˋ |' in full_content, '114 音 013 酸酵作用 未正確收錄'
assert '| 114 | 016 | 胡夷蜑蠻 | **蜑** | ㄉㄢˋ |' in full_content, '114 音 016 胡夷蜑蠻 未正確收錄'
assert '| 114 | 046 | 深中肯綮 | **綮** | ㄑㄧㄥˋ |' in full_content, '114 音 046 深中肯綮 未正確收錄'
assert '| 114 | 057 | 細密數罟 | **數** | ㄘㄨˋ |' in full_content, '114 音 057 細密數罟 未正確收錄'
assert '| 114 | 063 | 雕章繪句 | **繪** | ㄏㄨㄟˋ |' in full_content, '114 音 063 雕章繪句 未正確收錄'
assert '| 114 | 064 | 黍稷或彧 | **彧** | ㄩˋ |' in full_content, '114 音 064 黍稷或彧 未正確收錄'
assert '| 114 | 076 | 入戶奉匜 | **匜** | ㄧˊ |' in full_content, '114 音 076 入戶奉匜 未正確收錄'
assert '| 114 | 081 | 踉蹌蹀躞 | **踉** | ㄌㄧㄤˋ |' in full_content, '114 音 081 踉蹌蹀躞 未正確收錄'
assert '| 114 | 095 | 銷耗鈍眊 | **眊** | ㄇㄠˋ |' in full_content, '114 音 095 銷耗鈍眊 未正確收錄'
assert '| 114 | 002 | 引君入 ㄍㄡˋ | ㄍㄡˋ | **彀** |' in full_content, '114 形 002 引君入彀 未正確收錄'
assert '| 114 | 004 | ㄊㄥˊ 蛇無足 | ㄊㄥˊ | **滕** |' in full_content, '114 形 004 滕蛇無足 未正確收錄'
assert '| 114 | 005 | 旱 ㄅㄚˊ 為虐 | ㄅㄚˊ | **魃** |' in full_content, '114 形 005 旱魃為虐 未正確收錄'
assert '| 114 | 010 | 安徽 ㄕㄜˋ 硯 | ㄕㄜˋ | **歙** |' in full_content, '114 形 010 安徽歙硯 未正確收錄'
assert '| 114 | 020 | ㄗ 盛祭服 | ㄗ | **粢** |' in full_content, '114 形 020 粢盛祭服 未正確收錄'
assert '| 114 | 027 | ㄔㄣˋ 如疾首 | ㄔㄣˋ | **疢** |' in full_content, '114 形 027 疢如疾首 未正確收錄'
assert '| 114 | 044 | 巫 ㄒㄧˊ 之言 | ㄒㄧˊ | **覡** |' in full_content, '114 形 044 巫覡之言 未正確收錄'
assert '| 114 | 059 | 詢於 ㄔㄨˊ 蕘 | ㄔㄨˊ | **蒭** |' in full_content, '114 形 059 詢於蒭蕘 未正確收錄'
assert '| 114 | 086 | 翫歲 ㄎㄞˋ 日 | ㄎㄞˋ | **愒** |' in full_content, '114 形 086 翫歲愒日 未正確收錄'
assert '| 114 | 087 | 合 ㄅㄧㄢˇ 同葬 | ㄅㄧㄢˇ | **窆** |' in full_content, '114 形 087 合窆同葬 未正確收錄'
assert '| 114 | 100 | ㄠˊ 頭獨占 | ㄠˊ | **鰲** |' in full_content, '114 形 100 鰲頭獨占 未正確收錄'
print("  114 年關鍵題目 23 項: 全部 PASS")

# 6. 檢查 JSON 結構化題庫
print("\n[檢查項 6: JSON 結構化題庫驗證]")
import json
json_path = os.path.join('data', 'su_words_bank.json')
assert os.path.exists(json_path), f"找不到 JSON 檔案: {json_path}"
with open(json_path, 'r', encoding='utf-8') as f:
    data = json.load(f)

meta = data.get('metadata', {})
assert meta.get('total_questions') == 2800, f"JSON 總題數不為 2800: {meta.get('total_questions')}"
assert meta.get('counts', {}).get('pronunciation') == 1400, "JSON 字音題數不為 1400"
assert meta.get('counts', {}).get('character') == 1400, "JSON 字形題數不為 1400"
assert len(data.get('questions', [])) == 2800, "JSON 題目列表長度不為 2800"

for q in data['questions']:
    assert q.get('id'), f"題目缺漏 ID: {q}"
    assert q.get('year') in [int(y) for y in years], f"年份異常: {q}"
    assert q.get('prompt'), f"題目 prompt 為空: {q}"
    assert q.get('target'), f"題目 target 為空: {q}"
    assert q.get('answer'), f"題目 answer 為空: {q}"
    assert '?' not in q['prompt'] and '□' not in q['prompt'], f"題目含有問號: {q}"
    assert '?' not in q['answer'], f"答案含有問號: {q}"

print("  data/su_words_bank.json: PASS (總題數 2,800 題完整無損)")

print("\n=============================================")
print("=== 所有 6 大檢查項目全部通過 (ALL PASS)！ ===")
print("=============================================")
