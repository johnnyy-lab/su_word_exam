# -*- coding: utf-8 -*-
"""Word 直排不會套用注音字型的 OpenType vert。

網頁直排會把二三四聲畫在最後一個字母右上角，輕聲點在最上面，字母維持原大小。
這裡把 vert 聲調外形平移進最後一個字母的同一列，讓 Word 用一般橫排堆疊排出同樣的位置。
只供 test/ 試樣，不改正式出卷程式。
"""
import uuid
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
SRC_FONT = ROOT / "font" / "BopomofoRuby1909-v1-Regular.ttf"
SIDE_FONT = ROOT / "font" / "BopomofoRubySide.ttf"
OUT = ROOT / "bpmf-word-vert.docx"
PREVIEW = ROOT / "word-side-preview.png"
SIDE_NAME = "BopomofoRubySide"
SIDE_KEY = "{E4B72A18-6C35-4D90-A17F-3B8E2D5C94A0}"
# 直排 vert 的聲調原點在最後一個字母的下一格。平移回該字母的座標：x、y 各減 1000。
TONE_SRC = {
    "\u02ca": "uni02CA.v",
    "\u02c7": "caron.v",
    "\u02cb": "uni02CB.v",
}
SAMPLES = [
    ("一聲", "ㄓ"),
    ("二聲", "ㄕˊ"),
    ("三聲", "ㄓㄜˇ"),
    ("四聲", "ㄧㄡˋ"),
    ("輕聲", "˙ㄉㄜ"),
    ("四碼", "ㄊㄧㄠˋ"),
]


def bake_side_font():
    font = TTFont(str(SRC_FONT))
    for rec in font["name"].names:
        if rec.nameID in (1, 16):
            rec.string = SIDE_NAME
        elif rec.nameID == 4:
            rec.string = SIDE_NAME + " Regular"
        elif rec.nameID == 6:
            rec.string = SIDE_NAME + "-Regular"
        elif rec.nameID == 3:
            rec.string = "Bopomofo side tone test"
    cmap = font.getBestCmap()
    for ch, src in TONE_SRC.items():
        dst = cmap[ord(ch)]
        src_glyph = font["glyf"][src]
        pen = TTGlyphPen(font.getGlyphSet())
        src_pen = TransformPen(pen, (1, 0, 0, 1, -1000, -1000))
        font.getGlyphSet()[src].draw(src_pen)
        glyph = pen.glyph()
        font["glyf"][dst] = glyph
        glyph.recalcBounds(font["glyf"])
        font["hmtx"].metrics[dst] = (glyph.xMax + 40, glyph.xMin)
        print(
            f"tone {ch} from {src} x {src_glyph.xMin}->{glyph.xMin}..{glyph.xMax}"
            f" y {src_glyph.yMin}->{glyph.yMin}..{glyph.yMax}"
        )
    font.save(str(SIDE_FONT))
    font.close()


def bpmf_parts(text):
    chars = list(text)
    if chars and chars[0] == "˙":
        return "˙", "".join(chars[1:]), "top"
    if chars and chars[-1] in TONE_SRC:
        return chars[-1], "".join(chars[:-1]), "bottom"
    return "", text, ""


def run(text, font, sz):
    return (
        f'<w:r><w:rPr><w:rFonts w:ascii="{font}" w:hAnsi="{font}" w:eastAsia="{font}" w:cs="{font}" w:hint="eastAsia"/>'
        f'<w:sz w:val="{sz}"/><w:szCs w:val="{sz}"/></w:rPr>'
        f'<w:t xml:space="preserve">{escape(text)}</w:t></w:r>'
    )


def para(runs, before, line, ind=0, jc="left"):
    indent = f'<w:ind w:left="{ind}"/>' if ind else ""
    return (
        '<w:p><w:pPr><w:snapToGrid w:val="0"/>'
        f'<w:spacing w:before="{before}" w:after="0" w:line="{line}" w:lineRule="exact"/>'
        f"{indent}"
        f'<w:jc w:val="{jc}"/>'
        '<w:rPr><w:sz w:val="2"/><w:szCs w:val="2"/></w:rPr></w:pPr>'
        f"{runs}</w:p>"
    )


def label_run(text, sz=21):
    return (
        '<w:r><w:rPr><w:rFonts w:ascii="PMingLiU" w:hAnsi="PMingLiU" w:eastAsia="PMingLiU"/>'
        f'<w:sz w:val="{sz}"/><w:szCs w:val="{sz}"/></w:rPr>'
        f"<w:t>{escape(text)}</w:t></w:r>"
    )


def syllable(text, sz):
    """一個音一列。聲調跟最後一個字母同一列，外形已含在字型裡。"""
    tone, letters, where = bpmf_parts(text)
    line = sz * 10
    em = (sz // 2) * 20
    parts = []
    if where == "top":
        parts.append(para(run(tone, SIDE_NAME, sz), 0, max(160, int(line * 0.42)), ind=int(em * 0.30)))
    for i, ch in enumerate(letters):
        chunk = ch
        before = 0
        if where == "bottom" and i == len(letters) - 1:
            chunk += tone
            if len(letters) == 1:
                before = (sz // 2) * 8
        parts.append(para(run(chunk, SIDE_NAME, sz), before, line))
    return "".join(parts)


def cell(inner, width, valign="center"):
    return (
        f'<w:tc><w:tcPr><w:tcW w:w="{width}" w:type="dxa"/>'
        '<w:tcBorders>'
        '<w:top w:val="single" w:sz="4" w:space="0" w:color="888888"/>'
        '<w:left w:val="single" w:sz="4" w:space="0" w:color="888888"/>'
        '<w:bottom w:val="single" w:sz="4" w:space="0" w:color="888888"/>'
        '<w:right w:val="single" w:sz="4" w:space="0" w:color="888888"/>'
        "</w:tcBorders>"
        '<w:tcMar><w:top w:w="60" w:type="dxa"/><w:left w:w="80" w:type="dxa"/>'
        '<w:bottom w:w="40" w:type="dxa"/><w:right w:w="80" w:type="dxa"/></w:tcMar>'
        f'<w:vAlign w:val="{valign}"/></w:tcPr>{inner}</w:tc>'
    )


def sample_row(title, sz, height):
    cells = cell(para(label_run(title), 0, 280), 2600, valign="center")
    for _name, text in SAMPLES:
        cells += cell(syllable(text, sz), 1500, valign="top")
    return f'<w:tr><w:trPr><w:trHeight w:val="{height}" w:hRule="atLeast"/></w:trPr>{cells}</w:tr>'


def document_xml():
    intro = para(label_run(
        "Word 直排不會套用注音字型的 vert。下面用同一套直排聲調外形：字母維持原大小，二三四聲在最後一個字母右上角，輕聲點在最上面。"
    ), 0, 320, jc="left")
    head = cell(para(label_run("試法"), 0, 280), 2600)
    for name, _text in SAMPLES:
        head += cell(para(label_run(name), 0, 280, jc="center"), 1500)
    grid = '<w:gridCol w:w="2600"/>' + '<w:gridCol w:w="1500"/>' * len(SAMPLES)
    table = (
        '<w:tbl><w:tblPr><w:tblW w:w="11600" w:type="dxa"/><w:tblLayout w:type="fixed"/>'
        '<w:tblCellMar><w:top w:w="40" w:type="dxa"/><w:left w:w="40" w:type="dxa"/>'
        '<w:bottom w:w="40" w:type="dxa"/><w:right w:w="40" w:type="dxa"/></w:tblCellMar>'
        f"</w:tblPr><w:tblGrid>{grid}</w:tblGrid>"
        f"<w:tr>{head}</w:tr>"
        + sample_row("放大 36pt", 72, 4200)
        + sample_row("試卷字音解答 10pt", 20, 1600)
        + "</w:tbl>"
    )
    sect = (
        "<w:sectPr>"
        '<w:pgSz w:w="16838" w:h="11906" w:orient="landscape"/>'
        '<w:pgMar w:top="420" w:right="420" w:bottom="420" w:left="420" w:header="0" w:footer="0" w:gutter="0"/>'
        "</w:sectPr>"
    )
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        f"<w:body>{intro}{table}{sect}</w:body></w:document>"
    )


CONTENT_TYPES = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Default Extension="odttf" ContentType="application/vnd.openxmlformats-officedocument.obfuscatedFont"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
  <Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>
  <Override PartName="/word/settings.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.settings+xml"/>
  <Override PartName="/word/fontTable.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.fontTable+xml"/>
  <Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>
  <Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>
</Types>
"""

RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>
  <Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>
</Relationships>
"""

DOC_RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/settings" Target="settings.xml"/>
  <Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/fontTable" Target="fontTable.xml"/>
</Relationships>
"""

FONT_RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/font" Target="fonts/side.odttf"/>
</Relationships>
"""

STYLES = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/></w:style>
</w:styles>
"""

SETTINGS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:settings xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:zoom w:percent="140"/>
  <w:compat><w:compatSetting w:name="compatibilityMode" w:uri="http://schemas.microsoft.com/office/word" w:val="15"/></w:compat>
</w:settings>
"""

CORE = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" xmlns:dc="http://purl.org/dc/elements/1.1/">
  <dc:title>Word 對應網頁直排 vert</dc:title>
</cp:coreProperties>
"""

APP = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties">
  <Application>Microsoft Office Word</Application>
</Properties>
"""


def font_table():
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:fonts xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <w:font w:name="{SIDE_NAME}"><w:embedRegular r:id="rId1" w:fontKey="{SIDE_KEY}"/></w:font>
  <w:font w:name="PMingLiU"><w:charset w:val="88"/></w:font>
</w:fonts>
"""


def obfuscate(data, key):
    kb = uuid.UUID(key.strip("{}")).bytes_le
    out = bytearray(data)
    for i in range(min(32, len(out))):
        out[i] ^= kb[i % 16]
    return bytes(out)


def write_preview():
    size = 80
    font = ImageFont.truetype(str(SIDE_FONT), size)
    gap = 36
    width = 180 * len(SAMPLES) + 20
    height = size * 5 + 80
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    for index, (name, text) in enumerate(SAMPLES):
        tone, letters, where = bpmf_parts(text)
        x = 20 + index * 180
        top = 30
        draw.text((x, 4), name, fill=(80, 80, 80), font=ImageFont.truetype("C:/Windows/Fonts/mingliu.ttc", 16))
        baseline = top + size
        if where == "top":
            draw.text((x + int(size * 0.30), baseline), tone, fill="black", font=font, anchor="ls")
            baseline += int(size * 0.42)
        for i, ch in enumerate(letters):
            chunk = ch + tone if where == "bottom" and i == len(letters) - 1 else ch
            draw.text((x, baseline), chunk, fill="black", font=font, anchor="ls")
            baseline += size
    image.save(PREVIEW)
    print(PREVIEW)


def main():
    bake_side_font()
    write_preview()
    with zipfile.ZipFile(OUT, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", CONTENT_TYPES)
        zf.writestr("_rels/.rels", RELS)
        zf.writestr("word/_rels/document.xml.rels", DOC_RELS)
        zf.writestr("word/_rels/fontTable.xml.rels", FONT_RELS)
        zf.writestr("word/document.xml", document_xml())
        zf.writestr("word/styles.xml", STYLES)
        zf.writestr("word/settings.xml", SETTINGS)
        zf.writestr("word/fontTable.xml", font_table())
        zf.writestr("word/fonts/side.odttf", obfuscate(SIDE_FONT.read_bytes(), SIDE_KEY))
        zf.writestr("docProps/core.xml", CORE)
        zf.writestr("docProps/app.xml", APP)
    print(OUT)


if __name__ == "__main__":
    main()
