# -*- coding: utf-8 -*-
"""產生注音聲調位置的 Word 試樣。不改正式試卷程式。"""
import uuid
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parent
FONT_PATH = ROOT / "font" / "BopomofoRuby1909-v1-Regular.ttf"
OUT = ROOT / "bpmf-word.docx"
FONT_NAME = "BopomofoRuby1909-v1"
FONT_KEY = "{8A0E3C51-7B24-4F1A-9C3D-2E6B5A1F0D44}"

SAMPLES = [
    ("一聲", "ㄓ", ""),
    ("二聲", "ㄕ", "ˊ"),
    ("三聲", "ㄓㄜ", "ˇ"),
    ("四聲", "ㄧㄡ", "ˋ"),
    ("輕聲", "ㄉㄜ", "˙"),
    ("四碼", "ㄊㄧㄠ", "ˋ"),
]
COMB = {"ˊ": "\u0301", "ˇ": "\u030c", "ˋ": "\u0300"}


def inline_text(letters, tone):
    if tone == "˙":
        return "˙" + letters
    return letters + tone


def obfuscate_font(data, font_key):
    key = uuid.UUID(font_key.strip("{}")).bytes_le
    out = bytearray(data)
    for i in range(min(32, len(out))):
        out[i] ^= key[i % 16]
    return bytes(out)


def rpr(font, sz, tone_upright=False):
    tone = "<w:eastAsianLayout w:vert=\"1\"/>" if tone_upright else ""
    return (
        f'<w:rPr><w:rFonts w:ascii="{font}" w:hAnsi="{font}" w:eastAsia="{font}" w:hint="eastAsia"/>'
        f'<w:sz w:val="{sz}"/><w:szCs w:val="{sz}"/>{tone}</w:rPr>'
    )


def run(text, font, sz, tone_upright=False):
    return f'<w:r>{rpr(font, sz, tone_upright)}<w:t xml:space="preserve">{escape(text)}</w:t></w:r>'


def paragraph(runs, jc="center", tiny_mark=False):
    mark = '<w:rPr><w:sz w:val="2"/><w:szCs w:val="2"/></w:rPr>' if tiny_mark else ""
    return (
        "<w:p><w:pPr><w:snapToGrid w:val=\"0\"/>"
        '<w:spacing w:before="0" w:after="0" w:line="240" w:lineRule="auto"/>'
        f'<w:jc w:val="{jc}"/>{mark}</w:pPr>{runs}</w:p>'
    )


def cell(inner, width, direction="", valign="center", borders=True):
    dir_xml = f'<w:textDirection w:val="{direction}"/>' if direction else ""
    border = (
        '<w:tcBorders>'
        '<w:top w:val="single" w:sz="4" w:space="0" w:color="666666"/>'
        '<w:left w:val="single" w:sz="4" w:space="0" w:color="666666"/>'
        '<w:bottom w:val="single" w:sz="4" w:space="0" w:color="666666"/>'
        '<w:right w:val="single" w:sz="4" w:space="0" w:color="666666"/>'
        "</w:tcBorders>"
    ) if borders else '<w:tcBorders><w:top w:val="nil"/><w:left w:val="nil"/><w:bottom w:val="nil"/><w:right w:val="nil"/></w:tcBorders>'
    return (
        f'<w:tc><w:tcPr><w:tcW w:w="{width}" w:type="dxa"/>{border}'
        f'<w:vAlign w:val="{valign}"/>{dir_xml}</w:tcPr>{inner}</w:tc>'
    )


def side_table(letters, tone, vertical, sz=28, letter_w=None, tone_w=None, tone_sz=None, mar=20):
    """注音與聲調分成兩格。輕聲放左側，其餘聲調放右側上方。"""
    light = tone == "˙"
    if letter_w is None:
        letter_w = 420 if vertical else 900
    if tone_w is None:
        tone_w = 280
    if tone_sz is None:
        tone_sz = max(12, sz // 2)
    letter_runs = run(letters, "標楷體", sz)
    tone_runs = run(tone, "標楷體", tone_sz) if tone else ""
    if vertical:
        letter_inner = paragraph(letter_runs, tiny_mark=True)
        letter_cell = cell(letter_inner, letter_w, direction="tbRlV", borders=False)
    else:
        letter_inner = paragraph(letter_runs)
        letter_cell = cell(letter_inner, letter_w, borders=False)
    tone_inner = paragraph(tone_runs) if tone else paragraph("")
    tone_cell = cell(tone_inner, tone_w, valign="top", borders=False)
    if light:
        cells = tone_cell + letter_cell
        grid = f'<w:gridCol w:w="{tone_w}"/><w:gridCol w:w="{letter_w}"/>'
    else:
        cells = letter_cell + tone_cell
        grid = f'<w:gridCol w:w="{letter_w}"/><w:gridCol w:w="{tone_w}"/>'
    total = letter_w + tone_w
    tbl = (
        f'<w:tbl><w:tblPr><w:tblW w:w="{total}" w:type="dxa"/>'
        '<w:tblLayout w:type="fixed"/><w:tblCellMar>'
        f'<w:top w:w="0" w:type="dxa"/><w:left w:w="{mar}" w:type="dxa"/>'
        f'<w:bottom w:w="0" w:type="dxa"/><w:right w:w="{mar}" w:type="dxa"/>'
        "</w:tblCellMar></w:tblPr>"
        f"<w:tblGrid>{grid}</w:tblGrid><w:tr>{cells}</w:tr></w:tbl>"
        + paragraph("")
    )
    return tbl


def label_cell(text, width=1800):
    return cell(paragraph(run(text, "PMingLiU", 18), jc="left"), width, valign="center")


def header_row():
    cells = label_cell("試法")
    for name, _letters, _tone in SAMPLES:
        cells += cell(paragraph(run(name, "PMingLiU", 18)), 1500)
    return f"<w:tr>{cells}</w:tr>"


def text_row(title, builder, direction=""):
    cells = label_cell(title)
    for _name, letters, tone in SAMPLES:
        inner = builder(letters, tone)
        cells += cell(inner, 1500, direction=direction, valign="center")
    return f"<w:tr>{cells}</w:tr>"


def now_h(letters, tone):
    return paragraph(run(inline_text(letters, tone), "標楷體", 28))


def now_v(letters, tone):
    text = inline_text(letters, tone)
    runs = ""
    buf = ""
    def flush(is_tone):
        nonlocal runs, buf
        if buf:
            runs += run(buf, "標楷體", 28, tone_upright=is_tone)
            buf = ""
    for ch in text:
        is_tone = ch in "ˊˇˋ˙"
        if buf and is_tone != (buf[0] in "ˊˇˋ˙"):
            flush(buf[0] in "ˊˇˋ˙")
        buf += ch
    flush(bool(buf) and buf[0] in "ˊˇˋ˙")
    return paragraph(runs, tiny_mark=True)


def font_h(letters, tone):
    return paragraph(run(inline_text(letters, tone), FONT_NAME, 28))


def font_comb(letters, tone):
    if tone == "˙":
        text = "˙" + letters
    else:
        text = letters + COMB.get(tone, "")
    return paragraph(run(text, FONT_NAME, 28))


def font_v(letters, tone):
    return paragraph(run(inline_text(letters, tone), FONT_NAME, 28), tiny_mark=True)


def hand_h(letters, tone):
    return side_table(letters, tone, vertical=False)


def hand_v(letters, tone):
    return side_table(letters, tone, vertical=True)


def narrow_row():
    """B4 橫式直書目前一欄 704 twips、解答 10pt。看四碼注音能不能留在格內。"""
    letters, tone = "ㄊㄧㄠ", "ˋ"
    cells = label_cell("B4欄寬10pt", 1800)
    cells += cell(side_table(letters, tone, False, sz=20, letter_w=600, tone_w=100, tone_sz=10, mar=0), 704)
    cells += cell(side_table(letters, tone, True, sz=20, letter_w=280, tone_w=140, tone_sz=10, mar=0), 704)
    cells += cell(paragraph(run(inline_text(letters, tone), "標楷體", 20)), 704)
    cells += cell(now_v(letters, tone).replace('w:val="28"', 'w:val="20"'), 704, direction="tbRlV")
    return f"<w:tr>{cells}</w:tr>"


def document_xml():
    rows = [
        header_row(),
        text_row("標楷體橫排，聲調接在後面", now_h),
        text_row("標楷體直排，聲調是下一個字", now_v, direction="tbRlV"),
        text_row("注音字型橫排，原字串", font_h),
        text_row("注音字型橫排，組合聲調", font_comb),
        text_row("注音字型直排", font_v, direction="tbRlV"),
        text_row("手動橫排，聲調在右上", hand_h),
        text_row("手動直排，聲調在旁邊", hand_v),
    ]
    grid = '<w:gridCol w:w="1800"/>' + '<w:gridCol w:w="1500"/>' * len(SAMPLES)
    table = (
        '<w:tbl><w:tblPr><w:tblW w:w="10800" w:type="dxa"/>'
        '<w:tblLayout w:type="fixed"/>'
        '<w:tblCellMar><w:top w:w="40" w:type="dxa"/><w:left w:w="40" w:type="dxa"/>'
        '<w:bottom w:w="40" w:type="dxa"/><w:right w:w="40" w:type="dxa"/></w:tblCellMar>'
        f"</w:tblPr><w:tblGrid>{grid}</w:tblGrid>{''.join(rows)}</w:tbl>"
    )
    narrow_head = (
        "<w:tr>"
        + label_cell("窄欄對照", 1800)
        + cell(paragraph(run("手動橫排", "PMingLiU", 16)), 704)
        + cell(paragraph(run("手動直排", "PMingLiU", 16)), 704)
        + cell(paragraph(run("現況橫排", "PMingLiU", 16)), 704)
        + cell(paragraph(run("現況直排", "PMingLiU", 16)), 704)
        + "</w:tr>"
    )
    narrow = (
        '<w:tbl><w:tblPr><w:tblW w:w="4616" w:type="dxa"/><w:tblLayout w:type="fixed"/>'
        '<w:tblCellMar><w:top w:w="0" w:type="dxa"/><w:left w:w="0" w:type="dxa"/>'
        '<w:bottom w:w="0" w:type="dxa"/><w:right w:w="0" w:type="dxa"/></w:tblCellMar>'
        "</w:tblPr><w:tblGrid>"
        '<w:gridCol w:w="1800"/><w:gridCol w:w="704"/><w:gridCol w:w="704"/>'
        '<w:gridCol w:w="704"/><w:gridCol w:w="704"/>'
        f"</w:tblGrid>{narrow_head}{narrow_row()}</w:tbl>"
    )
    intro = paragraph(run("注音聲調標在旁邊：Word 試樣。最後一列窄欄寬 704 twips、字級 10pt，等於目前 B4 橫式直書的字音解答格。試的是四碼「ㄊㄧㄠˋ」。", "PMingLiU", 21), jc="left")
    gap = paragraph(run("", "PMingLiU", 21))
    body = intro + gap + table + gap + narrow + paragraph(run("", "PMingLiU", 21))
    sect = (
        "<w:sectPr>"
        '<w:pgSz w:w="16838" w:h="11906" w:orient="landscape"/>'
        '<w:pgMar w:top="567" w:right="567" w:bottom="567" w:left="567" '
        'w:header="0" w:footer="0" w:gutter="0"/>'
        '<w:docGrid w:linePitch="360"/>'
        "</w:sectPr>"
    )
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        f"<w:body>{body}{sect}</w:body></w:document>"
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
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/font" Target="fonts/BopomofoRuby.odttf"/>
</Relationships>
"""

STYLES = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:docDefaults>
    <w:rPrDefault><w:rPr>
      <w:rFonts w:ascii="PMingLiU" w:hAnsi="PMingLiU" w:eastAsia="PMingLiU"/>
      <w:sz w:val="21"/><w:szCs w:val="21"/>
    </w:rPr></w:rPrDefault>
    <w:pPrDefault><w:pPr><w:spacing w:after="0" w:line="240" w:lineRule="auto"/></w:pPr></w:pPrDefault>
  </w:docDefaults>
  <w:style w:type="paragraph" w:default="1" w:styleId="Normal">
    <w:name w:val="Normal"/>
    <w:qFormat/>
  </w:style>
</w:styles>
"""

SETTINGS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:settings xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:zoom w:percent="120"/>
  <w:compat>
    <w:compatSetting w:name="compatibilityMode" w:uri="http://schemas.microsoft.com/office/word" w:val="15"/>
  </w:compat>
</w:settings>
"""

CORE = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" xmlns:dc="http://purl.org/dc/elements/1.1/">
  <dc:title>注音聲調位置試樣</dc:title>
  <dc:creator>su_word_exam test</dc:creator>
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
  <w:font w:name="{FONT_NAME}">
    <w:charset w:val="00"/>
    <w:family w:val="auto"/>
    <w:pitch w:val="variable"/>
    <w:embedRegular r:id="rId1" w:fontKey="{FONT_KEY}"/>
  </w:font>
  <w:font w:name="標楷體">
    <w:charset w:val="88"/>
    <w:family w:val="script"/>
    <w:pitch w:val="fixed"/>
  </w:font>
  <w:font w:name="PMingLiU">
    <w:altName w:val="新細明體"/>
    <w:charset w:val="88"/>
    <w:family w:val="roman"/>
    <w:pitch w:val="variable"/>
  </w:font>
</w:fonts>
"""


def main():
    font_bytes = obfuscate_font(FONT_PATH.read_bytes(), FONT_KEY)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(OUT, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", CONTENT_TYPES)
        zf.writestr("_rels/.rels", RELS)
        zf.writestr("word/_rels/document.xml.rels", DOC_RELS)
        zf.writestr("word/_rels/fontTable.xml.rels", FONT_RELS)
        zf.writestr("word/document.xml", document_xml())
        zf.writestr("word/styles.xml", STYLES)
        zf.writestr("word/settings.xml", SETTINGS)
        zf.writestr("word/fontTable.xml", font_table())
        zf.writestr("word/fonts/BopomofoRuby.odttf", font_bytes)
        zf.writestr("docProps/core.xml", CORE)
        zf.writestr("docProps/app.xml", APP)
    print(OUT)


if __name__ == "__main__":
    main()
