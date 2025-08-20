#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import csv
import glob
import re
import sys
import unicodedata
from pathlib import Path

import pdfplumber

# --- Normalisatie helpers ----------------------------------------------------

DOT_RUN   = re.compile(r"[.\u2022\u00B7\u2219]{2,}")   # meerdere dots/bullets
WS_RUN    = re.compile(r"\s+")
ZWS       = "\u200b"

def normalize(txt: str) -> str:
    if not txt:
        return ""
    txt = unicodedata.normalize("NFKC", txt)
    txt = txt.replace(ZWS, "").replace("\u00A0", " ")

    # 1) vervang lange leader-dot runs door spatie
    txt = DOT_RUN.sub(" ", txt)

    # 2) verwijder puntjes tussen letters/cijfers
    txt = re.sub(r"(?<=\w)\.(?=\w)", "", txt)

    # 3) plak losse letters samen: "I n v o i c e" → "Invoice"
    txt = re.sub(r"(?:[A-Za-z]\s+){2,}[A-Za-z]", lambda m: m.group(0).replace(" ", ""), txt)

    # 4) plak losse cijfers samen, behalve bij decimalen (xx.xx) of minteken
    #    - match >=2 digits gescheiden door spaties
    #    - maar negeer als er een punt of streepje in de buurt is
    def join_digits(m):
        return m.group(0).replace(" ", "")

    txt = re.sub(r"(?<![\d\.\-])(?:\d\s+){1,}\d(?![\.\-])", join_digits, txt)

    # 5) normaliseer whitespace
    txt = WS_RUN.sub(" ", txt).strip()
    return txt


# --- Parsers -----------------------------------------------------------------

PATTERNS = {
    # Factuurnummer – komt twee keer voor, maar hetzelfde nummer
    "invoice_number": re.compile(
        r"Invoice\s*number[:\s]*([0-9]{6,})", re.I),

    # Factuurdatum – bv. "30 Jun 2024" of "3 Jan 2024"
    "invoice_date": re.compile(
        r"Summary\s+for\s+([0-9]{1,2}\s+[A-Za-z]{3}\s+\d{4})\s*-\s*([0-9]{1,2}\s+[A-Za-z]{3}\s+\d{4})", re.I),

    # Billing ID – bv. "5818-9541-5911"
    "billing_id": re.compile(
        r"Billing\s*ID[:\s]*([\d-]{6,})", re.I),

    # Domeinnaam – bv. "dergatsjev.be"
    "domain": re.compile(
        r"Domain\s*name[:\s]*([A-Za-z0-9.-]+\.[A-Za-z]{2,})", re.I),

    # Subtotaal (optioneel extra veld)
    "subtotal": re.compile(
        r"Subtotal\s+in\s+EUR[:\s]*€?\s*([0-9]+[.,][0-9]{2})", re.I),

    # VAT – kan 0% zijn
    "vat": re.compile(
        r"VAT\s*\(.*?\)\s*€?\s*([0-9]+[.,][0-9]{2})", re.I),

    # Totaalbedrag – komt meerdere keren voor, laatste is de echte
    "total_eur": re.compile(
        r"Total\s+in\s+EUR[:\s]*€?\s*([0-9]+[.,][0-9]{2})", re.I),

    # Leverancier
    "supplier": re.compile(
        r"Google\s+Cloud\s+EMEA\s+Limited|Google\s+Workspace", re.I),

    # VAT nummer leverancier
    "supplier_vat": re.compile(
        r"VAT\s+number[:\s]*([A-Z0-9]+)", re.I),

    # Klantnaam (Bill to)
    "customer_name": re.compile(
        r"Bill\s+to\s+([A-Za-z\s]+)", re.I),

    # Klantdomein direct onder "Bill to"
    "customer_domain": re.compile(
        r"Bill\s+to.*?\n([A-Za-z0-9.-]+\.[A-Za-z]{2,})", re.I|re.S),
}



def extract_invoice(pdf_path: str) -> dict:
    with pdfplumber.open(pdf_path) as pdf:
        raw = "\n".join((p.extract_text() or "") for p in pdf.pages)
    #import pdb;pdb.set_trace()
    text = normalize(raw)
    #text = raw

    data = {
        #"file": str(pdf_path),
        "invoice_number": None,
        "invoice_date": None,
        "billing_id": None,
        "domain": None,
        "total_eur": None,
        "supplier": None,
        "error": None,
    }

    import pdb;pdb.set_trace()
    
    m = PATTERNS["invoice_number"].search(text)
    data["invoice_number"] = m.group(1) if m else None

    m = PATTERNS["invoice_date"].search(text)
    if m:
        data["invoice_date"] = m.group(1) + " - " + m.group(2) # 
    else:
        data["invoice_date"] = None

    m = PATTERNS["billing_id"].search(text)
    data["billing_id"] = m.group(1) if m else None

    m = PATTERNS["domain"].search(text)
    data["domain"] = m.group(1) if m else None

    totals = PATTERNS["totals"].findall(text)
    if totals:
        data["total_eur"] = float(totals[-1].replace(",", "."))

    m = PATTERNS["supplier"].search(text)
    data["supplier"] = m.group(0) if m else None
    return data

# --- CLI ---------------------------------------------------------------------

def discover_pdfs(input_path: Path, recursive: bool) -> list[Path]:
    if input_path.is_file() and input_path.suffix.lower() == ".pdf":
        return [input_path]
    pattern = "**/*.pdf" if recursive else "*.pdf"
    return [Path(p) for p in glob.glob(str(input_path / pattern), recursive=recursive)]

def main():
    ap = argparse.ArgumentParser(
        description="Parseer factuurvelden uit PDF's (Invoice number, date, Billing ID, Domain, Total in EUR) en exporteer naar CSV."
    )
    ap.add_argument(
        "-i", "--input", required=True,
        help="Pad naar PDF-bestand of map met PDF's."
    )
    ap.add_argument(
        "-o", "--out", default="invoices_index.csv",
        help="Uitvoer-CSV (standaard: invoices_index.csv)."
    )
    ap.add_argument(
        "-r", "--recursive", action="store_true",
        help="Recursief submappen doorzoeken."
    )
    args = ap.parse_args()

    input_path = Path(args.input).expanduser().resolve()
    pdfs = discover_pdfs(input_path, args.recursive)

    if not pdfs:
        print(f"Geen PDF's gevonden in: {input_path}", file=sys.stderr)
        sys.exit(2)

    rows = []
    for pdf in pdfs:
        #try:
        rows.append(extract_invoice(str(pdf)))
        #except Exception as e:
        #    rows.append({
        #        "file": str(pdf),
        #        "invoice_number": None,
        #        "invoice_date": None,
        #        "billing_id": None,
        #        "domain": None,
        #        "total_eur": None,
        #        "supplier": None,
        #        "error": f"open_error: {e}",
        #    })

    # Schrijf CSV
    fieldnames = ["file", "invoice_number", "invoice_date", "billing_id", "domain", "total_eur", "supplier", "error"]
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)

    ok = sum(1 for r in rows if not r.get("error"))
    print(f"Geschreven: {args.out}  |  {ok}/{len(rows)} records zonder fouten")

if __name__ == "__main__":
    main()

