import os
import sys
import json
import urllib.parse
import subprocess
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
import io

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from data.crop_engine import crop_item_image, CROPS_DIR

PORT = 8000

class DisputeHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=BASE_DIR, **kwargs)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)

        # 根目錄與 dispute 路由跳轉
        if path == '/' or path == '/index.html':
            self.path = '/index.html'
            return super().do_GET()
        elif path == '/dispute' or path == '/dispute.html':
            self.path = '/dispute.html'
            return super().do_GET()

        # API: 取得爭議字資料集
        if path == '/api/disputes':
            json_path = os.path.join(BASE_DIR, 'data', 'disputes_dataset.json')
            if not os.path.exists(json_path):
                # 若不存在則即時產生
                cmd = [sys.executable, os.path.join(BASE_DIR, 'data', 'generate_dispute_assets.py')]
                subprocess.run(cmd, check=True)

            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Cache-Control', 'no-cache')
            self.end_headers()
            with open(json_path, 'rb') as f:
                self.wfile.write(f.read())
            return

        # API: 即時題目裁切圖 (特別針對 Q 類動態生成)
        if path == '/api/crop':
            year = query.get('year', [''])[0]
            sec = query.get('sec', [''])[0]
            num = query.get('num', [''])[0]
            if not (year and sec and num):
                self.send_error(400, '缺少 year, sec, 或 num 參數')
                return

            try:
                img = crop_item_image(int(year), sec, int(num), dpi=180, save_cache=True)
                buf = io.BytesIO()
                img.save(buf, format='PNG')
                img_bytes = buf.getvalue()

                self.send_response(200)
                self.send_header('Content-Type', 'image/png')
                self.send_header('Content-Length', str(len(img_bytes)))
                self.send_header('Cache-Control', 'public, max-age=86400')
                self.end_headers()
                self.wfile.write(img_bytes)
                return
            except Exception as e:
                self.send_error(500, f'裁切影像失敗: {str(e)}')
                return

        # 靜態檔案預設處理
        return super().do_GET()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path == '/api/save':
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            try:
                req_json = json.loads(post_data.decode('utf-8'))
                changes = req_json.get('changes', [])
                if not changes:
                    self._send_json({'success': True, 'updated_count': 0, 'message': '無修改項目'})
                    return

                res = apply_dispute_changes(changes)
                self._send_json(res)
            except Exception as e:
                self._send_json({'success': False, 'error': str(e)}, status_code=500)
            return

        self.send_error(404, 'API not found')

    def _send_json(self, data, status_code=200):
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))

def apply_dispute_changes(changes):
    """
    依使用者勾選批次更新 data/國語字音字形-高中統整.md
    並重新執行 export_dataset.py 與 verify_all.py
    """
    md_path = os.path.join(BASE_DIR, 'data', '國語字音字形-高中統整.md')
    with open(md_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    change_map = {}
    for c in changes:
        # key: (yr, sec, num)
        key = (int(c['year']), c['sec'], f"{int(c['num']):03d}")
        change_map[key] = c

    updated_count = 0
    new_lines = []
    current_sec = '甲'

    for line in lines:
        if '甲、字音部分' in line:
            current_sec = '甲'
        elif '乙、字形部分' in line:
            current_sec = '乙'

        # 解析 Markdown 表格列
        if line.startswith('|') and not line.startswith('| :') and not line.startswith('| 年度'):
            parts = [p.strip() for p in line.strip().split('|')[1:-1]]
            if len(parts) >= 6:
                yr_str, num_str, topic, test_w, ans, status = parts[:6]
                if yr_str.isdigit() and num_str.isdigit():
                    yr = int(yr_str)
                    num_int = int(num_str)
                    num_key = f"{num_int:03d}"
                    key = (yr, current_sec, num_key)

                    if key in change_map:
                        item = change_map[key]
                        act = item.get('action')
                        # 依選項判定新答案與新狀態
                        # 1. 暫不處理 (不改動)
                        if act and act != 'keep':
                            new_ans = ans
                            new_status = status

                            if act == 'current':
                                # 選目前系統: 保留答案，改記為 Y
                                new_status = 'Y'
                            elif act == 'errata':
                                # 選勘誤表: 更新為勘誤表答案，改記為 M
                                val = item.get('errata_val', '')
                                if current_sec == '甲':
                                    new_ans = f"`{val}`"
                                else:
                                    new_ans = f"**{val}**"
                                new_status = 'M'
                            elif act == 'original':
                                # 選原始檔: 更新為原卷辨識答案，改記為 M
                                val = item.get('original_val', '')
                                if current_sec == '甲':
                                    new_ans = f"`{val}`"
                                else:
                                    new_ans = f"**{val}**"
                                new_status = 'M'
                            elif act == 'moe':
                                # 選教育部辭典: 更新為辭典答案，改記為 M
                                val = item.get('moe_val', '')
                                if current_sec == '甲':
                                    new_ans = f"`{val}`"
                                else:
                                    new_ans = f"**{val}**"
                                new_status = 'M'
                            elif act == 'custom':
                                # 選手動自訂: 更新為手動輸入答案，改記為 M
                                val = item.get('custom_val', '').strip()
                                if val:
                                    if current_sec == '甲':
                                        new_ans = f"`{val}`"
                                    else:
                                        new_ans = f"**{val}**"
                                    new_status = 'M'

                            # 重新格式化此列
                            parts[4] = new_ans
                            parts[5] = new_status
                            line = f"| {' | '.join(parts)} |\n"
                            updated_count += 1

        new_lines.append(line)

    if updated_count > 0:
        with open(md_path, 'w', encoding='utf-8') as f:
            f.writelines(new_lines)

        # 準備環境變數強制子程序輸出 UTF-8
        sub_env = {**os.environ, 'PYTHONIOENCODING': 'utf-8'}

        # 重新匯出 su_words_bank.json 與 .js
        exp_script = os.path.join(BASE_DIR, 'data', 'export_dataset.py')
        subprocess.run([sys.executable, exp_script], env=sub_env, check=True)

        # 重新產生爭議字資料集
        gen_script = os.path.join(BASE_DIR, 'data', 'generate_dispute_assets.py')
        subprocess.run([sys.executable, gen_script], env=sub_env, check=True)

        # 執行自動化驗證 (加入 errors='replace' 與 UTF-8 環境變數避免 Windows 解碼異常崩潰)
        verify_script = os.path.join(BASE_DIR, 'verify_all.py')
        res = subprocess.run(
            [sys.executable, verify_script],
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',
            env=sub_env
        )
        verify_passed = (res.returncode == 0)

        return {
            'success': True,
            'updated_count': updated_count,
            'verify_passed': verify_passed,
            'verify_output': res.stdout + res.stderr
        }
    else:
        return {
            'success': True,
            'updated_count': 0,
            'message': '無有效變更項目'
        }

def run_server(port=PORT):
    server_address = ('', port)
    httpd = ThreadingHTTPServer(server_address, DisputeHandler)
    print(f'=================================================')
    print(f' 爭議字維護本機伺服器已啟動: http://localhost:{port}/dispute.html')
    print(f' 主頁面入口: http://localhost:{port}/index.html')
    print(f' 按 Ctrl+C 可停止伺服器')
    print(f'=================================================')
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print('\n伺服器已停止。')

if __name__ == '__main__':
    port = int(sys.argv[1]) if len(sys.argv) > 1 else PORT
    run_server(port)
