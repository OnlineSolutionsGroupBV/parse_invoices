#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os, json, csv, glob, re, unicodedata, argparse, sys
from pathlib import Path

import pdfplumber
from dotenv import load_dotenv
from openai import OpenAI

# =========================
#  Normalisatie helpers
# =========================
DOT_RUN   = re.compile(r"[.\u2022\u00B7\u2219]{2,}")   # ...... • • ·
WS_RUN    = re.compile(r"\s+")
ZWS       = "\u200b"

def normalize(txt: str) -> str:
    """
    Maak PDF-tekst modelvriendelijk:
    - verwijder leader dots
    - verwijder losse '.' tussen letters/cijfers
    - plak losse letters/cijfers weer samen
    - laat URLs en decimalen (6.90) ongemoeid
    """
    if not txt:
        return ""
    txt = unicodedata.normalize("NFKC", txt)
    txt = txt.replace(ZWS, "").replace("\u00A0", " ")

    # 1) leader dots -> spatie
    txt = DOT_RUN.sub(" ", txt)

    # 2) verwijder puntje tussen twee word-chars (a.b -> ab, 2.0 -> 20)
    txt = re.sub(r"(?<=\w)\.(?=\w)", "", txt)

    # 3) plak 'I n v o i c e' -> 'Invoice'
    txt = re.sub(r"(?:[A-Za-z]\s+){2,}[A-Za-z]", lambda m: m.group(0).replace(" ", ""), txt)

    # 4) plak '5 0 1 1 6 7 ...' -> '501167...' (niet naast . of -)
    txt = re.sub(r"(?<![\d.\-])(?:\d\s+){1,}\d(?![\.\-])", lambda m: m.group(0).replace(" ", ""), txt)

    # 5) whitespace normaliseren
    txt = WS_RUN.sub(" ", txt).strip()
    return txt

# =========================
#  OpenAI client + schema
# =========================
load_dotenv()
API_KEY = os.getenv("OPENAI_API_KEY")
MODEL   = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

if not API_KEY:
    raise RuntimeError("OPENAI_API_KEY ontbreekt. Zet hem in .env of in je omgeving.")

client = OpenAI(api_key=API_KEY)

SYSTEM_PROMPT = (
    "You are an invoice extraction engine. "
    "Only return valid JSON that exactly matches the provided JSON schema. "
    "If a field is missing, return null for it. Do not guess."
)

INVOICE_SCHEMA = {
    "name": "google_invoice_v1",
    "schema": {
        "type": "object",
        "properties": {
            "supplier":           {"type": "string", "nullable": True},
            "supplier_vat":       {"type": "string", "nullable": True},
            "invoice_number":     {"type": "string"},
            "invoice_date_start": {"type": "string", "nullable": True},
            "invoice_date_end":   {"type": "string", "nullable": True},
            "billing_id":         {"type": "string", "nullable": True},
            "domain":             {"type": "string", "nullable": True},
            "subtotal_eur":       {"type": "number", "nullable": True},
            "vat_percent":        {"type": "string", "nullable": True},
            "vat_amount_eur":     {"type": "number", "nullable": True},
            "total_eur":          {"type": "number"},
            "currency":           {"type": "string", "enum": ["EUR"], "default": "EUR"},
            "source_file":        {"type": "string"}
        },
        "required": ["invoice_number", "total_eur", "source_file"],
        "additionalProperties": False
    },
    "strict": True
}

USER_TEMPLATE = """Extract the fields from the invoice text below.

Rules:
- Prefer values that appear under clear headings (Invoice number, Billing ID, Domain name, Subtotal in EUR, VAT, Total in EUR).
- If a 'Summary for <start> - <end>' range exists, use it for invoice_date_start and invoice_date_end.
- Use EUR amounts as numbers (e.g., 6.90 -> 6.90).
- Do not invent values.

TEXT:
{snippet}
"""

# Minder tokens: houd alleen relevante regels
KEY_LINES = re.compile(
    r"(invoice|summary for|billing id|domain name|subtotal|total in eur|vat|google|workspace|cloud)",
    re.I
)

def text_for_llm(full_text: str) -> str:
    lines = [ln.strip() for ln in full_text.splitlines() if ln.strip()]
    keep = [ln for ln in lines if KEY_LINES.search(ln)]
    snippet = "\n".join(keep) if keep else full_text
    return snippet[:8000]  # veiligheidsgrens

def extract_with_openai(snippet: str, source_file: str) -> dict:
    resp = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": USER_TEMPLATE.format(snippet=snippet)},
        ],
        temperature=0,
        response_format={
            "type": "json_schema",
            "json_schema": INVOICE_SCHEMA
        },
    )
    content = resp.choices[0].message.content
    data = json.loads(content)
    data["source_file"] = source_file
    return data

# =========================
#  PDF -> tekst -> LLM
# =========================
def extract_from_pdf(pdf_path: str) -> dict:
    with pdfplumber.open(pdf_path) as pdf:
        raw = "\n".join((p.extract_text() or "") for p in pdf.pages)
    norm = normalize(raw)
    snippet = text_for_llm(norm)
    return extract_with_openai(snippet, str(pdf_path))

# =========================
#  CLI
# =========================
def discover_pdfs(input_path: Path, recursive: bool) -> list[Path]:
    if input_path.is_file() and input_path.suffix.lower() == ".pdf":
        return [input_path]
    pattern = "**/*.pdf" if recursive else "*.pdf"
    return [Path(p) for p in glob.glob(str(input_path / pattern), recursive=recursive)]

def main(input_path: str, out_csv: str, recursive: bool):
    input_path = Path(input_path).expanduser().resolve()
    pdfs = discover_pdfs(input_path, recursive)

    if not pdfs:
        print(f"Geen PDF's gevonden in: {input_path}")
        sys.exit(2)

    rows, ok = [], 0
    for f in pdfs:
        try:
            data = extract_from_pdf(str(f))
            ok += 1
        except Exception as e:
            data = {
                "supplier": None, "supplier_vat": None, "invoice_number": None,
                "invoice_date_start": None, "invoice_date_end": None,
                "billing_id": None, "domain": None, "subtotal_eur": None,
                "vat_percent": None, "vat_amount_eur": None, "total_eur": None,
                "currency": "EUR", "source_file": str(f), "error": str(e)
            }
        rows.append(data)

    fieldnames = [
        "source_file","supplier","supplier_vat","invoice_number",
        "invoice_date_start","invoice_date_end","billing_id","domain",
        "subtotal_eur","vat_percent","vat_amount_eur","total_eur","currency","error"
    ]
    Path(out_csv).parent.mkdir(parents=True, exist_ok=True)
    with open(out_csv, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            for k in fieldnames:
                r.setdefault(k, None)
            w.writerow(r)

    print(f"Klaar. Succesvol geparsed: {ok}/{len(rows)} → {out_csv}")

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Parse Google invoices via OpenAI (cheap model + strict JSON).")
    ap.add_argument("-i", "--input", required=True, help="Pad naar PDF-bestand of map met PDF's")
    ap.add_argument("-o", "--out", default="invoices_ai.csv", help="Output CSV pad")
    ap.add_argument("-r", "--recursive", action="store_true", help="Recursief submappen doorzoeken")
    args = ap.parse_args()
    main(args.input, args.out, args.recursive)

