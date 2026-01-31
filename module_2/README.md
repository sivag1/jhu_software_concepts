Module 2 — GradCafe Scraper
=================================

Purpose
- Short template README for `module_2` to document robots.txt checks, environment, and run instructions.

Python requirement
- This code is intended to run with Python 3.10 or newer. Local dev environment should use `python3.10`.

Setup
- Create and activate a virtual environment and install dependencies:

```bash
python3.10 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Running the scraper and cleaner
- Scrape (will write `applicant_data.json`):

```bash
python scrape.py
```

- Clean (reads `applicant_data.json`, writes `cleaned_applicant_data.json`):

```bash
python clean.py
```

robots.txt compliance
- Before running the scraper, verified robots.txt for https://www.thegradcafe.com/ by visiting:

```bash
curl -s https://www.thegradcafe.com/robots.txt | sed -n '1,200p'
```
The file is saved in name of screenshot.jpg and screenshot.pdf.

Notes and disclaimers
- The scraper uses `urllib` from the Python standard library for URL handling and `beautifulsoup4` for parsing.

Final LLM Cleaning
- Run the updated llm_hosting/app.py to generate two new llm generated columns and append to the existing data set to create llm_extend_applicant_data.json.

```bash
python llm_hosting\app.py --file "cleaned_applicant_data.json" --out "llm_extend_applicant_data.json"
```