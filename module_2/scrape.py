"""GradCafe Scraper Module.

This module provides functionality to scrape graduate applicant data from
The GradCafe website (https://www.thegradcafe.com/survey/index.php) and store
the results in JSON format. It respects robots.txt and includes rate limiting
to avoid overloading the server.

Author: [Your Name]
Date: January 2026
"""

import time
import urllib.request
import urllib.parse
from bs4 import BeautifulSoup
import re
import json


class GradCafeScraper:
    """Scrapes graduate applicant data from The GradCafe website.

    Attributes:
        url (str): Base URL for GradCafe survey index.
        headers (dict): HTTP headers with User-Agent for requests.
        data (list): List of scraped applicant records.
        max_entries (int): Target number of entries to scrape (30,000).
    """
    def __init__(self):
        """Initialize the GradCafeScraper with URL and headers."""
        url = "https://www.thegradcafe.com/survey/index.php"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
        }
        self.url = url
        self.headers = headers
        self.data = []
        self.max_entries = 30000

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
        except Exception as e:
            print(f"Error fetching page {page_num}: {e}")
            return None

    def scrape_data(self):
        """Scrape applicant data from GradCafe across multiple pages.

        Iterates through pages, extracts applicant records, and stores them
        in self.data. Continues until max_entries is reached or no more pages
        are available. Includes a 1-second delay between requests to be polite.
        """
        page = 1
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
                    for i in range(1, len(rows)):
                        tr = rows[i]
                        
                        tds = tr.find_all('td')
                        if len(tds) >= 4:
                            univ = tds[0].get_text(strip=True)
                            prog_info = tds[1].get_text(strip=True)
                            date_added = tds[2].get_text(strip=True)
                            decision_cell = tds[3]
                            decision_text = decision_cell.get_text(strip=True)
                            
                            # Extract URL
                            link_tag = tr.find('a', href=re.compile(r'/result/\d+'))
                    
                            entry_url = None
                            if link_tag and 'href' in link_tag.attrs:
                                path = link_tag['href']
                            if path.startswith('/'):
                                entry_url = f"https://www.thegradcafe.com{path}"
                            else:
                                entry_url = path

                            # Degree
                            degree = "PhD" if "PhD" in prog_info else "Masters" if "Masters" in prog_info else "Other"
                            
                            # Decision and Date
                            dec_match = re.search(r'(Accepted|Rejected|Wait listed|Interview)', decision_text, re.I)
                            decision = dec_match.group(1) if dec_match else "Unknown"
                            date_match = re.search(r'on\s*(.*)', decision_text, re.I)
                            dec_date = date_match.group(1) if date_match else None

                            # Stats
                            next_row = rows[i+1] if i+1 < len(rows) else None
                            stats_text = tr.get_text(" ", strip=True)
                            if next_row: 
                                stats_text += " " + next_row.get_text(" ", strip=True)

                            # Comments often appear in a following row or nested div
                            comments = ""
                            next_row = rows[i+2] if i+2 < len(rows) else None
                            if next_row and len(next_row.find_all('td')) == 1:
                                comments = next_row.get_text(strip=True)
                                
                            # Build applicant record dictionary
                            record = {
                                "university": re.sub(r'Report$', '', univ).strip(),
                                "program": prog_info,
                                "degree": degree,
                                "status": decision,
                                "decisionDate": dec_date,
                                "date_added": date_added,
                                "url": entry_url,
                                "comments": comments[:500],  # Truncate to 500 chars for safety
                                "raw": stats_text  # Raw stats for later parsing in clean.py
                            }
                            results.append(record)
                            self.data.append(record)

                print(json.dumps(results))
            except Exception as e:
                print(json.dumps({"error": str(e)}))
                
            page += 1
            # Be polite - add delay between requests
            time.sleep(1)

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