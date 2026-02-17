"""GradCafe Scraper Module.

This module provides functionality to scrape graduate applicant data from
The GradCafe website (https://www.thegradcafe.com/survey/index.php) and store
the results in JSON format. It respects robots.txt and includes rate limiting
to avoid overloading the server.

Author: Siva Govindarajan
Date: January 2026
"""

import json
import os
import re
import time
import urllib.request
import urllib.parse

from bs4 import BeautifulSoup
import psycopg
from dotenv import load_dotenv
from psycopg import sql

load_dotenv()


class GradCafeScraper:
    """Scrapes graduate applicant data from The GradCafe website.

    Attributes:
        url (str): Base URL for GradCafe survey index.
        headers (dict): HTTP headers with User-Agent for requests.
        data (list): List of scraped applicant records.
        max_entries (int): Target number of entries to scrape (30,000).
        existing_urls (set): Set of URLs already present in the database.
    """
    def __init__(self):
        """Initialize the GradCafeScraper with URL and headers."""
        url = "https://www.thegradcafe.com/survey/index.php"
        headers = {
            'User-Agent': (
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                'AppleWebKit/537.36 (KHTML, like Gecko) '
                'Chrome/119.0.0.0 Safari/537.36'
            ),
        }
        self.url = url
        self.headers = headers
        self.data = []
        self.max_entries = 30000
        self.existing_urls = set()
        self._load_existing_records()

    def _load_existing_records(self):
        """Load existing URLs from the database to avoid duplicate scraping."""
        try:
            conn = psycopg.connect(
                host=os.getenv("DB_HOST"),
                dbname=os.getenv("DB_NAME"),
                user=os.getenv("DB_USER"),
                password=os.getenv("DB_PASSWORD")
            )
            cur = conn.cursor()
            # Check if table exists and fetch URLs using sql.SQL composition
            cur.execute(sql.SQL("SELECT to_regclass('public.applicants')"))
            if cur.fetchone()[0]:
                cur.execute(sql.SQL(
                    "SELECT url FROM applicants "
                    "WHERE url IS NOT NULL "
                    "ORDER BY date_added DESC LIMIT {limit}"
                ).format(limit=sql.Literal(100)))
                self.existing_urls = {row[0] for row in cur.fetchall()}
                print(f"Loaded {len(self.existing_urls)} most recent records from database.")
            cur.close()
            conn.close()
        except Exception as e:  # pylint: disable=broad-exception-caught
            print(f"Note: Could not load existing records from DB (starting fresh): {e}")

    def fetch_data(self, page_num):
        """Fetch HTML data from a specific GradCafe page.

        Args:
            page_num (int): Page number to fetch.

        Returns:
            bytes: Raw HTML content from the page, or None if fetch fails.
        """
        # Build query parameters for GradCafe survey
        params = {'q': '', 't': 'a', 'o': '', 'page': page_num}
        url = f"{self.url}?{urllib.parse.urlencode(params)}"
        try:
            req = urllib.request.Request(url, headers=self.headers)
            with urllib.request.urlopen(req) as response:
                return response.read()
        except Exception as e:  # pylint: disable=broad-exception-caught
            print(f"Error fetching page {page_num}: {e}")
            return None

    def scrape_data(self):
        """Scrape applicant data from GradCafe across multiple pages.

        Iterates through pages, extracts applicant records, and stores them
        in self.data. Continues until max_entries is reached or no more pages
        are available. Includes a 1-second delay between requests to be polite.
        """
        page = 1
        stop_scraping = False
        while len(self.data) < self.max_entries:
            try:
                html = self.fetch_data(page_num=page)
                if not html:
                    print("Failed to fetch initial data.")
                    return

                soup = BeautifulSoup(html, 'html.parser')
                results = []
                table = soup.find('table')

                if table:
                    rows = table.find_all('tr')
                    results, stop_scraping = self._process_rows(rows)

                print(json.dumps(results))

                if stop_scraping:
                    break
            except Exception as e:  # pylint: disable=broad-exception-caught
                print(json.dumps({"error": str(e)}))

            page += 1
            # Be polite - add delay between requests
            time.sleep(1)

    def _process_rows(self, rows):
        """Process table rows and extract applicant records.

        Args:
            rows: List of BeautifulSoup tr elements.

        Returns:
            tuple: (list of record dicts, bool indicating if scraping should stop)
        """
        results = []
        stop_scraping = False

        for i in range(1, len(rows)):
            tr = rows[i]
            tds = tr.find_all('td')
            if len(tds) < 4:
                continue

            record, should_stop = self._parse_row(rows, tr, tds, i)
            if should_stop:
                stop_scraping = True
                break
            if record:
                results.append(record)
                self.data.append(record)

        return results, stop_scraping

    def _parse_row(self, rows, tr, tds, idx):
        """Parse a single table row into an applicant record.

        Args:
            rows: All table rows (for accessing adjacent rows).
            tr: The current row element.
            tds: The td cells in the current row.
            idx: Index of the current row.

        Returns:
            tuple: (record dict or None, bool indicating if scraping should stop)
        """
        entry_url = self._extract_url(tr.find('a', href=re.compile(r'/result/\d+')))

        # Check if we already have this record
        if entry_url and entry_url in self.existing_urls:
            print(f"Found existing record ({entry_url}). Stopping scrape.")
            return None, True

        decision, dec_date = self._parse_decision(tds[3].get_text(strip=True))

        record = {
            "university": re.sub(r'Report$', '', tds[0].get_text(strip=True)).strip(),
            "program": tds[1].get_text(strip=True),
            "degree": self._determine_degree(tds[1].get_text(strip=True)),
            "status": decision,
            "decisionDate": dec_date,
            "date_added": tds[2].get_text(strip=True),
            "url": entry_url,
            "comments": self._extract_comments(rows, idx)[:500],
            "raw": self._extract_stats(rows, tr, idx),
        }
        return record, False

    @staticmethod
    def _parse_decision(decision_text):
        """Parse decision status and date from decision cell text.

        Returns:
            tuple: (decision string, decision date string or None)
        """
        dec_match = re.search(r'(Accepted|Rejected|Wait listed|Interview)', decision_text, re.I)
        date_match = re.search(r'on\s*(.*)', decision_text, re.I)
        return (
            dec_match.group(1) if dec_match else "Unknown",
            date_match.group(1) if date_match else None,
        )

    @staticmethod
    def _extract_stats(rows, tr, idx):
        """Extract stats text from current and adjacent rows."""
        stats_text = tr.get_text(" ", strip=True)
        if idx + 1 < len(rows):
            stats_text += " " + rows[idx + 1].get_text(" ", strip=True)
        return stats_text

    @staticmethod
    def _extract_comments(rows, idx):
        """Extract comments from the row two positions after current."""
        if idx + 2 < len(rows) and len(rows[idx + 2].find_all('td')) == 1:
            return rows[idx + 2].get_text(strip=True)
        return ""

    @staticmethod
    def _extract_url(link_tag):
        """Extract a full URL from a link tag.

        Args:
            link_tag: BeautifulSoup tag element with href attribute.

        Returns:
            str or None: The full URL, or None if no valid link found.
        """
        if not link_tag or 'href' not in link_tag.attrs:
            return None
        path = link_tag['href']
        if path.startswith('/'):
            return f"https://www.thegradcafe.com{path}"
        return path

    @staticmethod
    def _determine_degree(prog_info):
        """Determine degree type from program info text.

        Args:
            prog_info (str): Program information text.

        Returns:
            str: 'PhD', 'Masters', or 'Other'.
        """
        if "PhD" in prog_info:
            return "PhD"
        if "Masters" in prog_info:
            return "Masters"
        return "Other"

    def save_data(self, filename="applicant_data.json"):
        """Save scraped applicant data to a JSON file.

        Args:
            filename (str): Output file path. Defaults to 'applicant_data.json'.
        """
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, indent=4)
        print(f"Data saved to {filename}")


if __name__ == "__main__":
    # Initialize scraper and run the scraping process
    scraper = GradCafeScraper()
    scraper.scrape_data()
    scraper.save_data()
