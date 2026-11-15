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

# 150 DPI 下各年度高精確度單格校準參數 (格線精確對齊，嚴禁超寬雙行，高度精確避開下行題號)
GRID_CONFIGS = {
    # 橫式兩頁 (102-110)
    102: {
        'type': 'landscape',
        '甲': {'x_left': 103, 'step': 50.72, 'bands_y': [(100, 360), (350, 620), (610, 880), (870, 1140)]},
        '乙': {'x_left': 103, 'step': 50.72, 'bands_y': [(100, 360), (350, 620), (610, 880), (870, 1140)]}
    },
    103: {
        'type': 'landscape',
        '甲': {'x_left': 118, 'step': 47.32, 'bands_y': [(185, 415), (425, 655), (665, 895), (905, 1135)]},
        '乙': {'x_left': 120, 'step': 47.32, 'bands_y': [(130, 350), (370, 590), (610, 830), (850, 1070)]}
    },
    104: {
        'type': 'landscape',
        '甲': {'x_left': 173, 'step': 44.00, 'bands_y': [(135, 350), (365, 580), (595, 810), (825, 1040)]},
        '乙': {'x_left': 158, 'step': 44.00, 'bands_y': [(135, 345), (365, 575), (595, 805), (825, 1035)]}
    },
    105: {
        'type': 'landscape',
        '甲': {'x_left': 136, 'step': 45.96, 'bands_y': [(130, 360), (370, 600), (610, 840), (850, 1080)]},
        '乙': {'x_left': 136, 'step': 45.96, 'bands_y': [(130, 360), (370, 600), (610, 840), (850, 1080)]}
    },
    106: {
        'type': 'landscape',
        '甲': {'x_left': 123, 'step': 47.48, 'bands_y': [(135, 360), (375, 600), (615, 840), (855, 1080)]},
        '乙': {'x_left': 118, 'step': 46.80, 'bands_y': [(130, 355), (370, 595), (610, 835), (850, 1075)]}
    },
    107: {
        'type': 'landscape',
        '甲': {'x_left': 150, 'step': 45.52, 'bands_y': [(145, 370), (385, 610), (625, 850), (865, 1090)]},
        '乙': {'x_left': 150, 'step': 45.04, 'bands_y': [(140, 365), (380, 605), (620, 845), (860, 1085)]}
    },
    108: {
        'type': 'landscape',
        '甲': {'x_left': 140, 'step': 45.60, 'bands_y': [(125, 350), (360, 585), (595, 820), (830, 1055)]},
        '乙': {'x_left': 140, 'step': 45.60, 'bands_y': [(125, 350), (360, 585), (595, 820), (830, 1055)]}
    },
    109: {
        'type': 'landscape',
        '甲': {'x_left': 166, 'step': 43.80, 'bands_y': [(145, 370), (375, 600), (605, 830), (835, 1060)]},
        '乙': {'x_left': 166, 'step': 43.80, 'bands_y': [(145, 370), (375, 600), (605, 830), (835, 1060)]}
    },
    110: {
        'type': 'landscape',
        '甲': {'x_left': 123, 'step': 72.00, 'bands_y': [(110, 440), (480, 810), (850, 1180), (1220, 1550)]},
        '乙': {'x_left': 123, 'step': 72.00, 'bands_y': [(110, 440), (480, 810), (850, 1180), (1220, 1550)]}
    },
    # 直式四頁 (101, 111-114)
    101: {
        'type': 'portrait',
        'right_x_left': 164, 'right_step': 63.5,
        'left_x_left': 175, 'left_step': 68.8,
        'bands_y': [(270, 560), (560, 870), (870, 1230), (1230, 1530)]
    },
    111: {
        'type': 'portrait',
        'right_x_left': 112, 'right_step': 65.5,
        'left_x_left': 134, 'left_step': 65.5,
        'bands_y': [(255, 590), (590, 920), (920, 1255), (1255, 1580)]
    },
    112: {
        'type': 'portrait',
        'right_x_left': 106, 'right_step': 66.2,
        'left_x_left': 107, 'left_step': 66.2,
        'bands_y': [(245, 550), (550, 880), (880, 1220), (1220, 1550)]
    },
    113: {
        'type': 'portrait',
        'right_x_left': 124, 'right_step': 66.8,
        'left_x_left': 125, 'left_step': 64.8,
        'bands_y': [(210, 530), (540, 870), (875, 1205), (1210, 1540)]
    },
    114: {
        'type': 'portrait',
        'right_x_left': 124, 'right_step': 66.8,
        'left_x_left': 125, 'left_step': 64.8,
        'bands_y': [(235, 565), (575, 905), (915, 1225), (1235, 1555)]
    }
}

def get_crop_box(year, sec, num, img_w=None, img_h=None):
    y = int(year)
    n = int(num)
    cfg = GRID_CONFIGS.get(y)
    if not cfg:
        cfg = GRID_CONFIGS[105]

    if cfg['type'] == 'landscape':
        sub_cfg = cfg.get(sec, cfg.get('甲'))
        band_idx = (n - 1) // 25
        col_idx = (n - 1) % 25 # 0 為最右欄
        
        y_top, y_bot = sub_cfg['bands_y'][band_idx]
        x_left = sub_cfg['x_left']
        step = sub_cfg['step']
        
        # 精確單行：最右欄為 (24 - col_idx)
        x_l = x_left + (24 - col_idx) * step
        x_r = x_l + step
        
        # 左右微幅內縮 1 像素避免包含相鄰隔線，徹底杜絕雙行
        return (int(x_l + 1), int(y_top), int(x_r - 1), int(y_bot))
    else:
        # 直式四頁
        def in_right(q):
            return (1 <= q <= 10) or (26 <= q <= 35) or (51 <= q <= 60) or (76 <= q <= 85)
        is_r = in_right(n)
        
        if (1 <= n <= 25): band_idx = 0
        elif (26 <= n <= 50): band_idx = 1
        elif (51 <= n <= 75): band_idx = 2
        else: band_idx = 3
        
        y_top, y_bot = cfg['bands_y'][band_idx]
        
        if is_r:
            # 右頁 10 題
            if band_idx == 0: col_idx = n - 1
            elif band_idx == 1: col_idx = n - 26
            elif band_idx == 2: col_idx = n - 51
            else: col_idx = n - 76
            
            x_l = cfg['right_x_left'] + (9 - col_idx) * cfg['right_step']
            x_r = x_l + cfg['right_step']
        else:
            # 左頁 15 題
            if band_idx == 0: col_idx = n - 11
            elif band_idx == 1: col_idx = n - 36
            elif band_idx == 2: col_idx = n - 61
            else: col_idx = n - 86
            
            x_l = cfg['left_x_left'] + (14 - col_idx) * cfg['left_step']
            x_r = x_l + cfg['left_step']
            
        return (int(x_l + 1), int(y_top), int(x_r - 1), int(y_bot))

def crop_item_image(year, sec, num, dpi=150, save_cache=True):
    y = int(year)
    n = int(num)
    cache_path = os.path.join(CROPS_DIR, f'{y}_{sec}_{n:03d}.png')
    
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
        crop.save(cache_path, optimize=True)
    return crop
