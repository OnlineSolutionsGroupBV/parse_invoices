# 📑 AI Invoice Extractor

**Parse Google Workspace & Google Cloud invoices into structured data with ease.**

This open-source tool automatically extracts details from **Google PDF invoices** and exports them to **CSV** for easy bookkeeping and accounting.

## ✨ Features
- 🔍 Extracts key fields:
  - Invoice number  
  - Billing ID  
  - Domain name  
  - Invoice period (start & end dates)  
  - Subtotal, VAT, Total (EUR)  
  - Supplier & VAT number  
- 📂 Batch processing of multiple PDFs at once (`invoices/*.pdf`)  
- 🧹 Smart text normalization (fixes dotted/fragmented text in PDFs)  
- 🤖 AI parsing with **OpenAI gpt-4o-mini** (cheap & accurate) using **strict JSON schema**  
- 📊 Clean CSV export ready for bookkeeping software  

## 🚀 Quick Start

```bash
git clone https://github.com/OnlineSolutionsGroupBV/parse_invoices.git
cd parse_invoices

python3 -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env       # add your OpenAI API key
python ai_invoice_extract.py -i "invoices/*.pdf" -o output/invoices.csv
