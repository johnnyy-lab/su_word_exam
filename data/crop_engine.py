import os
import pymupdf
from PIL import Image

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOPICS_DIR = os.path.join(BASE_DIR, 'topics')
OLD_DIR = os.path.join(BASE_DIR, 'old')
CROPS_DIR = os.path.join(BASE_DIR, 'assets', 'crops')
ERRATA_DIR = os.path.join(CROPS_DIR, 'errata')

os.makedirs(CROPS_DIR, exist_ok=True)
os.makedirs(ERRATA_DIR, exist_ok=True)

def get_pdf_path(year):
    y = int(year)
    if y == 110:
        fn = f'{y}年國語字音字形-高中.pdf'
    else:
        fn = f'{y}年國語字音字形(高中).pdf'
    p = os.path.join(TOPICS_DIR, fn)
    if not os.path.exists(p):
        raise FileNotFoundError(f'找不到試卷檔案: {p}')
    return p

def get_crop_box(year, sec, num, img_w, img_h):
    y = int(year)
    n = int(num)
    
    # 橫式兩頁 (102-110)
    if 102 <= y <= 110:
        band_idx = (n - 1) // 25
        col_idx = (n - 1) % 25 # 0 為最右欄
        
        # 4 bands: 各年份的邊界比例
        if y == 110:
            yt, yb = 0.075, 0.880
            xr, xl = 0.840, 0.050
        elif y == 102:
            yt, yb = 0.085, 0.880
            xr, xl = 0.805, 0.045
        else:
            # 103~109
            yt, yb = 0.125, 0.875
            xr, xl = 0.812, 0.048
            
        band_h = (img_h * (yb - yt)) / 4.0
        cy_t = img_h * yt + band_idx * band_h
        cy_b = cy_t + band_h
        
        col_w = (img_w * (xr - xl)) / 25.0
        cx_r = img_w * xr - col_idx * col_w
        cx_l = cx_r - col_w
        
        pad_x = col_w * 0.12
        pad_y = band_h * 0.03
        return (int(max(0, cx_l - pad_x)), int(max(0, cy_t - pad_y)), int(min(img_w, cx_r + pad_x)), int(min(img_h, cy_b + pad_y)))
    else:
        # 直式四頁 (101, 111-114)
        def in_right(q):
            return (1 <= q <= 10) or (26 <= q <= 35) or (51 <= q <= 60) or (76 <= q <= 85)
        is_r = in_right(n)
        
        if (1 <= n <= 25): band_idx = 0
        elif (26 <= n <= 50): band_idx = 1
        elif (51 <= n <= 75): band_idx = 2
        else: band_idx = 3
        
        if y == 101:
            yt, yb = 0.085, 0.825
        else:
            yt, yb = 0.160, 0.950
            
        band_h = (img_h * (yb - yt)) / 4.0
        cy_t = img_h * yt + band_idx * band_h
        cy_b = cy_t + band_h
        
        if is_r:
            if band_idx == 0: col_idx = n - 1
            elif band_idx == 1: col_idx = n - 26
            elif band_idx == 2: col_idx = n - 51
            else: col_idx = n - 76
            xr, xl = 0.760, 0.080
            cols = 10
        else:
            if band_idx == 0: col_idx = n - 11
            elif band_idx == 1: col_idx = n - 36
            elif band_idx == 2: col_idx = n - 61
            else: col_idx = n - 86
            xr, xl = 0.920, 0.080
            cols = 15
            
        col_w = (img_w * (xr - xl)) / cols
        cx_r = img_w * xr - col_idx * col_w
        cx_l = cx_r - col_w
        
        pad_x = col_w * 0.12
        pad_y = band_h * 0.03
        return (int(max(0, cx_l - pad_x)), int(max(0, cy_t - pad_y)), int(min(img_w, cx_r + pad_x)), int(min(img_h, cy_b + pad_y)))

def crop_item_image(year, sec, num, dpi=180, save_cache=True):
    y = int(year)
    n = int(num)
    cache_path = os.path.join(CROPS_DIR, f'{y}_{sec}_{n:03d}.png')
    if os.path.exists(cache_path):
        return Image.open(cache_path)
    
    doc = pymupdf.open(get_pdf_path(y))
    if 102 <= y <= 110:
        page_idx = 0 if sec == '甲' else 1
    else:
        def in_right(q):
            return (1 <= q <= 10) or (26 <= q <= 35) or (51 <= q <= 60) or (76 <= q <= 85)
        is_r = in_right(n)
        if sec == '甲':
            page_idx = 0 if is_r else 1
        else:
            page_idx = 2 if is_r else 3
            
    page = doc[page_idx]
    pix = page.get_pixmap(dpi=dpi)
    img = Image.frombytes('RGB', [pix.width, pix.height], pix.samples)
    box = get_crop_box(y, sec, n, img.width, img.height)
    crop = img.crop(box)
    
    if save_cache:
        crop.save(cache_path)
    return crop

if __name__ == '__main__':
    im = crop_item_image(102, '甲', 37)
    print('Cropped sample:', im.size)
