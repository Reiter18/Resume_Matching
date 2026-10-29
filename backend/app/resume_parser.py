import io
import re
import unicodedata
import zipfile
from collections import Counter

import pymupdf
from docx import Document
from docx.table import Table
from docx.text.paragraph import Paragraph

MAX_PAGES = 30
MIN_CHARS = 30
MAX_CHARS = 100_000
MAX_UNZIPPED_BYTES = 50 * 1024 * 1024  


class ResumeError(ValueError):
    """Файл не удалось обработать; сообщение можно показывать пользователю."""



def extract_text(filename: str, data: bytes) -> str:
    if not data:
        raise ResumeError("Файл пустой")
    name = (filename or "").lower()
    if data.startswith(b"%PDF-"):
        raw = _pdf_to_text(data)
    elif data.startswith(b"PK\x03\x04"):
        raw = _docx_to_text(data)
    elif data.startswith(b"\xd0\xcf\x11\xe0") or name.endswith(".doc"):
        raise ResumeError("Старый формат .doc не поддерживается: сохраните резюме как DOCX или PDF")
    elif name.endswith((".txt", ".md")):
        raw = _decode_text(data)
    else:
        raise ResumeError("Поддерживаются файлы PDF, DOCX и TXT")
    return finalize(raw)


def finalize(raw: str) -> str:
    text = clean_text(raw)
    if len(text) < MIN_CHARS:
        raise ResumeError("Не удалось извлечь текст. Если это скан или фото, загрузите PDF с текстом или DOCX")
    if len(text) > MAX_CHARS:
        raise ResumeError("Слишком длинный текст для резюме")
    return text



def _pdf_to_text(data: bytes) -> str:
    try:
        doc = pymupdf.open(stream=data, filetype="pdf")
    except Exception as e:
        raise ResumeError("Не удалось прочитать PDF: файл повреждён") from e
    with doc:
        if doc.needs_pass:
            raise ResumeError("PDF защищён паролем")
        if doc.page_count > MAX_PAGES:
            raise ResumeError(f"Слишком длинный документ (больше {MAX_PAGES} страниц)")
        pages = [_page_lines(page) for page in doc]
    pages = _drop_repeated_lines(pages)
    return "\n\n".join("\n".join(lines) for lines in pages)


def _page_lines(page) -> list[str]:
    lines = []
    for block in page.get_text("dict")["blocks"]:
        if block.get("type") != 0:
            continue
        for line in block["lines"]:
            text = "".join(span["text"] for span in line["spans"]).strip()
            if text:
                lines.append((*line["bbox"], text))  # (x0, y0, x1, y1, text)
    return [line[4] for line in _reading_order(lines, page.rect.width)]


def _reading_order(lines: list, width: float) -> list:
    key = lambda ln: (round(ln[1] / 4), ln[0])  
    spans = [ln for ln in lines if ln[2] - ln[0] > 0.6 * width]
    cols = [ln for ln in lines if ln not in spans]
    gutter = _find_gutter(cols, width)
    if gutter is None:
        return sorted(lines, key=key)
    left = sorted((ln for ln in cols if ln[2] <= gutter), key=key)
    right = sorted((ln for ln in cols if ln[0] >= gutter), key=key)
    top = min(ln[1] for ln in cols)
    head = sorted((ln for ln in spans if ln[1] < top), key=key)
    tail = sorted((ln for ln in spans if ln[1] >= top), key=key)
    return head + left + right + tail


def _find_gutter(cols: list, width: float):
    if len(cols) < 8:
        return None
    for x in range(int(width * 0.3), int(width * 0.7) + 1, 4):
        if any(ln[0] < x < ln[2] for ln in cols):
            continue
        left = [ln for ln in cols if ln[2] <= x]
        right = [ln for ln in cols if ln[0] >= x]
        if min(len(left), len(right)) >= 4 and all(
            sum(len(ln[4]) for ln in side) / len(side) >= 14 for side in (left, right)
        ):
            return x
    return None


def _drop_repeated_lines(pages: list[list[str]]) -> list[list[str]]:
    if len(pages) < 3:
        return pages

    def norm(line: str) -> str:
        return re.sub(r"\d+", "#", line.strip().lower())

    counts: Counter = Counter()
    for lines in pages:
        counts.update({norm(line) for line in lines if line.strip() and len(line.strip()) <= 80})
    limit = max(3, round(len(pages) * 0.6))
    repeated = {k for k, c in counts.items() if c >= limit}
    return [[line for line in lines if norm(line) not in repeated] for lines in pages]



def _docx_to_text(data: bytes) -> str:
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            if sum(i.file_size for i in z.infolist()) > MAX_UNZIPPED_BYTES:
                raise ResumeError("Файл слишком большой после распаковки")
            if "word/document.xml" not in z.namelist():
                raise ResumeError("Это не документ DOCX")
        doc = Document(io.BytesIO(data))
    except ResumeError:
        raise
    except Exception as e:
        raise ResumeError("Не удалось прочитать DOCX: файл повреждён") from e
    return "\n".join(_docx_lines(doc))


def _docx_lines(doc):
    for child in doc.element.body.iterchildren():
        tag = child.tag.rsplit("}", 1)[-1]
        if tag == "p":
            yield Paragraph(child, doc).text
        elif tag == "tbl":
            yield from _table_lines(Table(child, doc))


def _table_lines(table):
    for row in table.rows:
        seen, cells = [], []
        for cell in row.cells:
            if any(cell._tc is s for s in seen):  
                continue
            seen.append(cell._tc)
            text = " ".join(p.text.strip() for p in cell.paragraphs if p.text.strip())
            if text:
                cells.append(text)
        if cells:
            yield " | ".join(cells)



def _decode_text(data: bytes) -> str:
    if b"\x00" in data:
        raise ResumeError("Файл не похож на текстовый")
    for enc in ("utf-8-sig", "cp1251"):  
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            continue
    raise ResumeError("Не удалось определить кодировку файла")



_BULLETS = re.compile(r"^[ \t]*[•●▪■◦·‣⁃][ \t]*", re.M)
_PAGE_NUM = re.compile(
    r"^[ \t]*(?:page|стр\.?|страница)?[ \t]*\d{1,3}(?:[ \t]*(?:/|из|of)[ \t]*\d{1,3})?[ \t]*$", re.I | re.M
)


def clean_text(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)  
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = "".join(ch for ch in text if ch in "\n\t" or unicodedata.category(ch) not in ("Cc", "Cf", "Cs"))
    text = re.sub(r"(?<=\w)-\n(?=[a-zа-яё])", "", text)  # перенос слова: «разра-\nботчик»
    text = _BULLETS.sub("- ", text)
    text = _PAGE_NUM.sub("", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = "\n".join(line.strip() for line in text.split("\n"))
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def detect_language(text: str) -> str:
    cyr = len(re.findall(r"[а-яё]", text, re.I))
    lat = len(re.findall(r"[a-z]", text, re.I))
    total = cyr + lat
    if total < 20:
        return "unknown"
    share = cyr / total  
    if share >= 0.4:
        return "ru"
    return "en" if share <= 0.08 else "mixed"
