# 📑 AI Invoice Extractor

**Parse Google Workspace & Google Cloud invoices into structured data with ease.**

This open-source tool automatically extracts details from **Google PDF invoices** and exports them to **CSV** for easy bookkeeping and accounting.

The repository demonstrates two complementary approaches:

- `ai_invoice_extract.py` – parses invoices with OpenAI’s `gpt-4o-mini` using a strict JSON schema.
- `parse_invoices.py` – a ~10× faster option powered purely by regular expressions. It avoids generic AI and extra dependencies, showing that similar tasks can often be solved with straightforward rules.

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

## ⚡ Regex-based Alternative

For predictable invoice layouts, `parse_invoices.py` processes files roughly **10× faster**. It relies solely on `pdfplumber` and regular expressions—no generic AI models or heavy dependencies. This highlights that many extraction tasks can be handled with classic techniques.

You can also explore ML-driven options such as [spaCy's Matcher](https://www.webdeveloper.today/2023/05/list-of-car-makes-brands-and-you-want.html) for rule-based pattern matching on raw text.

## 🚀 Quick Start

```bash
git clone https://github.com/OnlineSolutionsGroupBV/parse_invoices.git
cd parse_invoices

python3 -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env       # add your OpenAI API key as OPENAI_API_KEY_PARSER
python ai_invoice_extract.py -i "invoices/*.pdf" -o output/invoices.csv

```

Ensure your OpenAI API key is available via the `OPENAI_API_KEY_PARSER` environment variable (the script also falls back to `OPENAI_API_KEY`).


##  Related Blog Post

I also wrote a detailed blog post about this project on [WebDeveloper.today](https://www.webdeveloper.today/2025/08/automating-invoice-parsing-with-ai.html). It covers the concept, the challenges of parsing real-world invoices, and how this tool brings together PDF text normalization, AI-powered parsing (via a cost-efficient OpenAI model), and CSV output into a streamlined bookkeeping workflow.

Read it here: [Automating Invoice Parsing with AI](https://www.webdeveloper.today/2025/08/automating-invoice-parsing-with-ai.html)


## 🔄 Business Process Automation

This project is part of a broader effort to simplify and automate repetitive business processes.  
By combining PDF parsing, AI-assisted data extraction, and clean data export, manual bookkeeping tasks are transformed into automated workflows.  
The same principles can be extended to other domains such as HR, procurement, and CRM — freeing teams from low-value admin work and letting them focus on growth and innovation.

https://onlinesolutionsgroup.website/
