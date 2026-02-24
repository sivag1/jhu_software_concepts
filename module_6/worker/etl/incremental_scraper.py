"""Incremental scraper utilities for GradCafe data.

Shared scraping logic used by the consumer worker to fetch new applicant
records from The GradCafe website.
"""

from __future__ import annotations

import re
import time
import urllib.parse
import urllib.request

from bs4 import BeautifulSoup


def fetch_page(page_num):
    """Fetch a single page of GradCafe survey results.

    Args:
        page_num: Page number to fetch.

    Returns:
        bytes: Raw HTML content.
    """
    base_url = "https://www.thegradcafe.com/survey/index.php"
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/119.0.0.0 Safari/537.36"
        ),
    }
    params = {"q": "", "t": "a", "o": "", "page": page_num}
    url = f"{base_url}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req) as resp:
        return resp.read()


def parse_decision(text):
    """Parse decision status and date from decision cell text."""
    dec = re.search(r"(Accepted|Rejected|Wait listed|Interview)", text, re.I)
    date = re.search(r"on\s*(.*)", text, re.I)
    return (dec.group(1) if dec else "Unknown", date.group(1) if date else None)


def determine_degree(prog):
    """Determine degree type from program text."""
    if "PhD" in prog:
        return "PhD"
    if "Masters" in prog:
        return "Masters"
    return "Other"


def scrape_new_records(existing_urls, max_pages=50):
    """Scrape GradCafe for records whose URL is not in existing_urls.

    Args:
        existing_urls: Set of already-known URLs.
        max_pages: Maximum pages to fetch.

    Returns:
        list[dict]: Newly scraped records.
    """
    records = []
    for page in range(1, max_pages + 1):
        try:
            html = fetch_page(page)
        except Exception:
            break

        soup = BeautifulSoup(html, "html.parser")
        table = soup.find("table")
        if not table:
            break

        rows = table.find_all("tr")
        stop = False
        for i in range(1, len(rows)):
            tds = rows[i].find_all("td")
            if len(tds) < 4:
                continue

            link = rows[i].find("a", href=re.compile(r"/result/\d+"))
            entry_url = None
            if link and "href" in link.attrs:
                path = link["href"]
                entry_url = (
                    f"https://www.thegradcafe.com{path}" if path.startswith("/") else path
                )

            if entry_url and entry_url in existing_urls:
                stop = True
                break

            decision, dec_date = parse_decision(tds[3].get_text(strip=True))
            comments = ""
            if i + 2 < len(rows) and len(rows[i + 2].find_all("td")) == 1:
                comments = rows[i + 2].get_text(strip=True)[:500]

            records.append({
                "university": re.sub(r"Report$", "", tds[0].get_text(strip=True)).strip(),
                "program": tds[1].get_text(strip=True),
                "degree": determine_degree(tds[1].get_text(strip=True)),
                "status": decision,
                "decisionDate": dec_date,
                "date_added": tds[2].get_text(strip=True),
                "url": entry_url,
                "comments": comments,
            })

        if stop:
            break
        time.sleep(1)

    return records
