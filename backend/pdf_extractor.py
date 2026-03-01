"""
PDF data extraction for voter roll files.

Handles both text-based PDFs (pdfplumber table extraction) and
scanned/image PDFs (OCR via tesseract). Outputs a CSV that the
existing processor pipeline can consume.
"""
import os
import re
import csv
import logging
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)


def is_pdf(filepath: str) -> bool:
    """Check if a file is a PDF."""
    return str(filepath).lower().endswith('.pdf')


def extract_pdf_to_csv(pdf_path: str, output_dir: str = None) -> str:
    """
    Extract tabular data from a PDF and write it to a CSV file.

    Strategy:
      1. Try pdfplumber table extraction (fast, works on text-based PDFs).
      2. If that yields no usable rows, fall back to OCR via tesseract.

    Args:
        pdf_path: Path to the PDF file.
        output_dir: Directory for the output CSV. Defaults to same dir as PDF.

    Returns:
        Path to the generated CSV file.

    Raises:
        ValueError: If no tabular data could be extracted.
    """
    pdf_path = str(pdf_path)
    if output_dir is None:
        output_dir = os.path.dirname(pdf_path)

    base = Path(pdf_path).stem
    csv_path = os.path.join(output_dir, f"{base}_extracted.csv")

    logger.info(f"Extracting PDF: {pdf_path}")

    # ── Strategy 1: pdfplumber (text-layer tables) ──────────────────────
    rows = _extract_with_pdfplumber(pdf_path)
    if rows and len(rows) > 1:
        logger.info(f"pdfplumber extracted {len(rows)} rows (incl. header)")
        _write_csv(rows, csv_path)
        return csv_path

    # ── Strategy 2: pdfplumber raw text lines ───────────────────────────
    rows = _extract_text_lines(pdf_path)
    if rows and len(rows) > 1:
        logger.info(f"Text-line extraction got {len(rows)} rows")
        _write_csv(rows, csv_path)
        return csv_path

    # ── Strategy 3: OCR fallback ────────────────────────────────────────
    logger.info("No text tables found — falling back to OCR")
    rows = _extract_with_ocr(pdf_path)
    if rows and len(rows) > 1:
        logger.info(f"OCR extracted {len(rows)} rows")
        _write_csv(rows, csv_path)
        return csv_path

    raise ValueError(
        f"Could not extract tabular data from {Path(pdf_path).name}. "
        "The PDF may not contain recognizable voter data tables."
    )


# ════════════════════════════════════════════════════════════════════════
# Internal helpers
# ════════════════════════════════════════════════════════════════════════

def _extract_with_pdfplumber(pdf_path: str) -> list:
    """Use pdfplumber to pull tables from every page."""
    try:
        import pdfplumber
    except ImportError:
        logger.warning("pdfplumber not installed")
        return []

    all_rows = []
    header = None

    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                tables = page.extract_tables()
                for table in tables:
                    for row in table:
                        # Skip completely empty rows
                        if not row or all(c is None or str(c).strip() == '' for c in row):
                            continue
                        cleaned = [str(c).strip() if c else '' for c in row]
                        # Use first non-empty row as header if it looks like one
                        if header is None and _looks_like_header(cleaned):
                            header = _normalize_header(cleaned)
                            all_rows.append(header)
                        else:
                            all_rows.append(cleaned)
    except Exception as e:
        logger.warning(f"pdfplumber extraction failed: {e}")
        return []

    return all_rows


def _extract_text_lines(pdf_path: str) -> list:
    """
    Fall back to reading raw text and splitting on whitespace/tabs.
    Works for PDFs that have text but no formal table structure.
    """
    try:
        import pdfplumber
    except ImportError:
        return []

    lines = []
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if not text:
                    continue
                for line in text.split('\n'):
                    line = line.strip()
                    if not line:
                        continue
                    lines.append(line)
    except Exception as e:
        logger.warning(f"Text extraction failed: {e}")
        return []

    if not lines:
        return []

    # Try to detect a consistent delimiter (tabs, multiple spaces, pipes)
    return _parse_text_lines_to_rows(lines)


def _extract_with_ocr(pdf_path: str) -> list:
    """Convert PDF pages to images, run tesseract OCR, parse output."""
    try:
        from pdf2image import convert_from_path
        import pytesseract
    except ImportError as e:
        logger.warning(f"OCR dependencies missing: {e}")
        return []

    all_text_lines = []

    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            images = convert_from_path(pdf_path, dpi=300, output_folder=tmpdir)
            for i, img in enumerate(images):
                logger.info(f"OCR page {i+1}/{len(images)}")
                text = pytesseract.image_to_string(img)
                for line in text.split('\n'):
                    line = line.strip()
                    if line:
                        all_text_lines.append(line)
    except Exception as e:
        logger.warning(f"OCR extraction failed: {e}")
        return []

    if not all_text_lines:
        return []

    return _parse_text_lines_to_rows(all_text_lines)


def _parse_text_lines_to_rows(lines: list) -> list:
    """
    Given raw text lines, try to parse them into structured rows.
    Looks for VUID-like patterns (7-10 digit numbers) to identify voter rows.
    Handles special formats like ePulse (Brooks County) where all fields are
    on one line separated by single spaces.
    """
    rows = []
    header = None

    # Known header keywords for voter files
    header_keywords = [
        'VUID', 'CERT', 'NAME', 'LASTNAME', 'FIRSTNAME', 'ADDRESS',
        'PRECINCT', 'PARTY', 'BALLOT', 'CHECK-IN', 'SITE', 'ID',
        'VOTER', 'REGISTRATION', 'DOB', 'SEX', 'GENDER', 'STATE ID'
    ]

    # ePulse format regex: [No] [NAME] [10-digit VUID] [optional DOB] [ADDRESS, CITY, TX ZIP] [SEX] [PRECINCT] [PARTY]
    # With DOB: "1 RUBY SANDOVAL ALLEN 1024073022 12/17/1957 1525 S CALDWELL ST FALFURRIAS, TX 78355 S 3.2 DEM"
    # Without DOB: "1 VANESSA LAMAR ALANIZ 1022180991 224 E MAUPIN ST FALFURRIAS, TX 78355 S 3.2 DEM"
    epulse_pattern = re.compile(
        r'^(\d+)\s+'                          # Row number
        r'(.+?)\s+'                           # Name (greedy until VUID)
        r'(\d{10})\s+'                        # State ID / VUID (exactly 10 digits)
        r'(?:(\d{2}/\d{2}/\d{4})\s+)?'       # DOB (optional)
        r'(.+?,\s*TX\s+\d{5})\s+'            # Address (up to TX ZIP)
        r'([SMF])\s+'                         # Sex (S/M/F)
        r'([\d.]+)\s+'                        # Precinct
        r'(DEM|REP|LIB|GRN|IND)\s*$',        # Party
        re.IGNORECASE
    )

    # First pass: check if this is ePulse format
    epulse_matches = 0
    for line in lines:
        if epulse_pattern.match(line.strip()):
            epulse_matches += 1
        if epulse_matches >= 3:
            break

    if epulse_matches >= 3:
        # ePulse format detected — parse with regex
        rows.append(['voter_name', 'vuid', 'birth_year', 'address', 'sex', 'precinct', 'party'])
        for line in lines:
            m = epulse_pattern.match(line.strip())
            if m:
                name = m.group(2).strip()
                vuid = m.group(3)
                dob = m.group(4)  # May be None if DOB was missing
                # Extract birth year from DOB
                birth_year = ''
                if dob:
                    try:
                        birth_year = dob.split('/')[-1]
                    except Exception:
                        birth_year = ''
                address = m.group(5).strip()
                sex = m.group(6).upper()
                precinct = m.group(7)
                party = m.group(8).upper()
                rows.append([name, vuid, birth_year, address, sex, precinct, party])
        return rows

    # Standard parsing for other formats
    for line in lines:
        upper = line.upper()

        # Detect header line
        if header is None:
            kw_count = sum(1 for kw in header_keywords if kw in upper)
            if kw_count >= 2:
                # Split on tabs first, then multiple spaces
                parts = _split_line(line)
                if len(parts) >= 2:
                    header = _normalize_header(parts)
                    rows.append(header)
                    continue

        # Detect data rows — look for VUID-like numbers
        if re.search(r'\b\d{7,10}\b', line):
            parts = _split_line(line)
            if len(parts) >= 2:
                rows.append(parts)

    return rows


def _split_line(line: str) -> list:
    """Split a text line into fields using tabs, pipes, or multi-space."""
    # Tab-delimited
    if '\t' in line:
        return [c.strip() for c in line.split('\t')]
    # Pipe-delimited
    if '|' in line:
        return [c.strip() for c in line.split('|')]
    # Multiple spaces (2+)
    parts = re.split(r'\s{2,}', line.strip())
    if len(parts) >= 3:
        return parts
    # Comma-delimited
    if ',' in line:
        return [c.strip() for c in line.split(',')]
    # Single space — only if it produces enough columns
    parts = line.split()
    return parts if len(parts) >= 3 else [line]


def _looks_like_header(row: list) -> bool:
    """Check if a row looks like a column header."""
    header_words = {
        'VUID', 'CERT', 'ID', 'NAME', 'LASTNAME', 'FIRSTNAME', 'MIDDLENAME',
        'ADDRESS', 'PRECINCT', 'PCT', 'PARTY', 'BALLOT', 'STYLE',
        'CHECK-IN', 'CHECKIN', 'SITE', 'VOTER', 'DOB', 'SEX', 'GENDER',
        'COUNTY', 'ZIP', 'CITY', 'REGISTRATION', 'DATE', 'METHOD',
        'SUFFIX', 'MIDDLE', 'LAST', 'FIRST', 'NO', 'NUMBER'
    }
    upper_cells = [c.upper().strip() for c in row if c.strip()]
    matches = sum(1 for c in upper_cells if any(hw in c for hw in header_words))
    return matches >= 2


def _normalize_header(row: list) -> list:
    """Normalize header names to match expected CSV column names."""
    mapping = {
        'VOTER UNIQUE ID': 'VUID',
        'VOTER ID': 'VUID',
        'VOTER_ID': 'VUID',
        'VUID': 'VUID',
        'CERT': 'CERT',
        'CERTIFICATE': 'CERT',
        'LAST NAME': 'LASTNAME',
        'LAST': 'LASTNAME',
        'FIRST NAME': 'FIRSTNAME',
        'FIRST': 'FIRSTNAME',
        'MIDDLE NAME': 'MIDDLENAME',
        'MIDDLE': 'MIDDLENAME',
        'ADDR': 'ADDRESS',
        'STREET': 'ADDRESS',
        'RESIDENTIAL ADDRESS': 'ADDRESS',
        'RES ADDRESS': 'ADDRESS',
        'PCT': 'PRECINCT',
        'PRECINCT NO': 'PRECINCT',
        'PRECINCT NUMBER': 'PRECINCT',
        'BALLOT STYLE': 'BALLOT STYLE',
        'BALLOT': 'BALLOT STYLE',
        'CHECK IN': 'CHECK-IN',
        'CHECKIN': 'CHECK-IN',
        'CHECK-IN': 'CHECK-IN',
        'LOCATION': 'SITE',
        'POLLING PLACE': 'SITE',
        'VOTE SITE': 'SITE',
        'GENDER': 'SEX',
        'DOB': 'BIRTH_YEAR',
        'DATE OF BIRTH': 'BIRTH_YEAR',
        'REGISTRATION DATE': 'REGISTRATION_DATE',
        'REG DATE': 'REGISTRATION_DATE',
    }
    normalized = []
    for cell in row:
        upper = cell.upper().strip()
        matched = mapping.get(upper, None)
        if matched:
            normalized.append(matched)
        else:
            # Check partial matches
            found = False
            for key, val in mapping.items():
                if key in upper:
                    normalized.append(val)
                    found = True
                    break
            if not found:
                normalized.append(upper)
    return normalized


def _write_csv(rows: list, csv_path: str):
    """Write rows to a CSV file."""
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        # Pad rows to match header length
        if rows:
            max_cols = max(len(r) for r in rows)
            for row in rows:
                while len(row) < max_cols:
                    row.append('')
                writer.writerow(row)
    logger.info(f"Wrote {len(rows)} rows to {csv_path}")
