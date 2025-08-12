#!/usr/bin/env python3
"""
Extract total amounts and service periods from German receipts (PDF).

Logic:
  1) Search for a “Bruttorechnungs-betrag” section in the text; within it, locate
     the first line containing "Summe" and extract the rightmost amount.
  2) If step 1 fails, search any "Summe" line in the entire text and take the
     rightmost amount.
  3) Extract the service period (Zeitraum) from various possible phrasings.
     If the start year is missing or abbreviated, copy the year from the end date.

Outputs: CSV with columns: file, total_raw, total_number, duration.
"""

from __future__ import annotations

import argparse
import logging
import re
from pathlib import Path
from typing import Optional, List, Dict

import pandas as pd
import pdfplumber

# ------------------------------- Settings ------------------------------------

# Regex pattern to match amounts in European format (with optional currency symbol)
AMOUNT = r"(?:EUR|€)?\s*(\d{1,3}(?:[.\s]\d{3})*(?:[.,]\d{2})|\d+[.,]\d{2})\s*(?:EUR|€)?"
# Pattern to match the numeric portion of amounts only
AMOUNT_TOKEN = re.compile(r"(\d{1,3}(?:[.\s]\d{3})*(?:[.,]\d{2})|\d+[.,]\d{2})")

# Regex for section headers and key lines
BRUTTO_RE = re.compile(r"(?i)bruttorechnungs\s*[-]?\s*betrag")  # Matches "Bruttorechnungsbetrag" with optional hyphen/spaces
SUMME_LINE_RE = re.compile(r"(?im)^.*\bsumme\b.*$")  # Matches any line containing 'summe'

# Date patterns for Zeitraum extraction
DATE_DMY = r"(\d{1,2}\.\d{1,2}\.(\d{2,4})?)"  # e.g., 01.01.23 or 01.01.2023
DATE_DMY_FULL = r"(\d{1,2}\.\d{1,2}\.\d{4})"   # Full year only

# Patterns to match various possible "Zeitraum" phrases
ZEITRAUM_RE = re.compile(rf"(?i)(?:leistungs|abrechnungs)?\s*zeitraum[^0-9]*{DATE_DMY}\s*(?:-|–|bis)\s*{DATE_DMY_FULL}")
FUR_ZEITRAUM_RE = re.compile(rf"(?i)f[üu]r\s+den\s+zeitraum[^0-9]*{DATE_DMY}\s*(?:-|–|bis)\s*{DATE_DMY_FULL}")
VON_BIS_RE = re.compile(rf"(?i)\bvon\b\s*{DATE_DMY}\s*(?:-|–|bis)\s*{DATE_DMY_FULL}")

# Limit of characters scanned after finding "Bruttorechnungsbetrag"
LOCAL_BLOCK_CHARS = 1500

# ----------------------------- Helpers ---------------------------------------

def normalize_amount(amount_str: str) -> Optional[float]:
    """Convert European-formatted amount string to a float.

    Handles commas as decimal separators and dots as thousand separators.
    Strips spaces and currency symbols.
    """
    if not amount_str:
        return None

    s = amount_str.replace(" ", "").replace("€", "").replace("EUR", "")
    # Handle both '.' and ',' present
    if "," in s and "." in s:
        if s.rfind(",") > s.rfind("."):  # Comma appears last → decimal separator
            s = s.replace(".", "").replace(",", ".")
        else:  # Dot appears last → decimal separator
            s = s.replace(",", "")
    else:
        if s.count(",") == 1 and len(s.split(",")[-1]) == 2:
            s = s.replace(",", ".")
        else:
            s = s.replace(",", "")

    try:
        return float(s)
    except ValueError:
        return None

def extract_text_from_pdf(pdf_path: Path) -> str:
    """Read and return all text from a PDF file."""
    with pdfplumber.open(str(pdf_path)) as pdf:
        return "\n".join((page.extract_text() or "") for page in pdf.pages)

def get_summe_total(text: str) -> Optional[str]:
    """Find the 'Summe' amount, prioritizing those near 'Bruttorechnungsbetrag'."""
    m = BRUTTO_RE.search(text)
    if m:
        # Search only a limited block after the heading
        block = text[m.end(): m.end() + LOCAL_BLOCK_CHARS]
        lines = SUMME_LINE_RE.findall(block)
        if lines:
            amts = AMOUNT_TOKEN.findall(lines[0])
            if amts:
                return amts[-1]  # Rightmost amount in the line

    # Fallback: search all 'Summe' lines in the text
    for line in SUMME_LINE_RE.findall(text):
        amts = AMOUNT_TOKEN.findall(line)
        if amts:
            return amts[-1]
    return None

def _pad_dd_mm(date_str: str) -> str:
    """Ensure day and month are zero-padded (e.g., 1.1.2023 → 01.01.2023)."""
    parts = date_str.split(".")
    if len(parts) < 3:
        return date_str
    return f"{parts[0].zfill(2)}.{parts[1].zfill(2)}.{parts[2]}"

def get_duration(text: str) -> str:
    """Extract service period date range from the text."""
    for pat in (ZEITRAUM_RE, FUR_ZEITRAUM_RE, VON_BIS_RE):
        m = pat.search(text)
        if not m:
            continue

        start_raw = m.group(1)
        end_full = m.group(3)

        start_parts = start_raw.split(".")
        if len(start_parts) >= 3 and len(start_parts[-1]) == 4:
            start_full = _pad_dd_mm(start_raw)
        else:
            end_year = end_full.split(".")[-1]
            start_full = f"{start_parts[0].zfill(2)}.{start_parts[1].zfill(2)}.{end_year}"

        return f"{start_full} - {end_full}"
    return ""

def scan_receipts(base_dir: Path) -> pd.DataFrame:
    """Walk through a directory of PDFs, extract totals and durations."""
    rows: List[Dict[str, object]] = []
    pdf_paths = sorted(p for p in base_dir.rglob("*.pdf") if p.is_file())

    for path in pdf_paths:
        try:
            text = extract_text_from_pdf(path)
        except Exception as e:
            logging.warning("Failed to read %s: %s", path, e)
            text = ""

        total_raw = get_summe_total(text) if text else None
        total_num = normalize_amount(total_raw) if total_raw else None
        duration = get_duration(text) if text else ""

        rows.append({
            "file": path.name,
            "total_raw": total_raw or "",
            "total_number": total_num,
            "duration": duration or "",
        })

    return pd.DataFrame(rows)

def maybe_display_dataframe(df: pd.DataFrame, name: str) -> None:
    """Display DataFrame to user if ace_tools is available; otherwise skip."""
    try:
        import ace_tools as tools  # type: ignore
        tools.display_dataframe_to_user(name=name, dataframe=df)
    except Exception:
        pass

def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-i", "--input", type=Path, default=Path.cwd() / "receipts",
                        help="Directory to scan for PDFs (default: ./receipts)")
    parser.add_argument("-o", "--output", type=Path, default=Path.cwd() / "receipt_totals_with_duration_textonly.csv",
                        help="Output CSV path")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose logging")
    return parser.parse_args()

def main() -> None:
    args = parse_args()
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO,
                        format="%(levelname)s: %(message)s")

    base_dir: Path = args.input
    if not base_dir.exists() or not base_dir.is_dir():
        logging.error("Input directory does not exist or is not a directory: %s", base_dir)
        raise SystemExit(2)

    logging.info("Scanning PDFs in: %s", base_dir)
    df = scan_receipts(base_dir)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(args.output, index=False)
    logging.info("Saved CSV to %s", args.output)

    maybe_display_dataframe(df, name="Receipt Totals (text-only parsing)")

if __name__ == "__main__":
    main()
