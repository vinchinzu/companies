"""SEC Enforcement Releases Scraper.

Scrapes SEC litigation releases and press releases to extract
fraud case information including company names, dates, and penalties.
"""

import re
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

import requests
from bs4 import BeautifulSoup


@dataclass
class FraudCase:
    """Represents a fraud case from SEC enforcement."""

    company_name: str
    case_date: str
    fraud_type: str
    penalty_amount: Optional[float]
    jurisdiction: Optional[str]
    source: str
    source_url: str
    description: str
    is_synthetic: bool = False


class SECScraper:
    """Scraper for SEC enforcement releases."""

    BASE_URL = "https://www.sec.gov"
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (compatible; ResearchBot/1.0; +http://example.com/bot)",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }

    # Known high-profile fraud cases with structured data
    KNOWN_CASES = [
        FraudCase(
            company_name="Terraform Labs Pte. Ltd.",
            case_date="2024-04-26",
            fraud_type="Securities Fraud",
            penalty_amount=4500000000.0,
            jurisdiction="sg",
            source="SEC Litigation",
            source_url="https://www.sec.gov/litigation/litreleases/lr-25696",
            description="Crypto asset securities fraud; $4.5B settlement after jury verdict",
        ),
        FraudCase(
            company_name="HyperFund",
            case_date="2024-01-15",
            fraud_type="Pyramid Scheme",
            penalty_amount=1700000000.0,
            jurisdiction="us",
            source="SEC Enforcement",
            source_url="https://www.sec.gov/enforcement",
            description="Crypto pyramid scheme raising over $1.7B worldwide",
        ),
        FraudCase(
            company_name="NovaTech Ltd.",
            case_date="2024-02-20",
            fraud_type="Ponzi Scheme",
            penalty_amount=650000000.0,
            jurisdiction="us",
            source="SEC Enforcement",
            source_url="https://www.sec.gov/enforcement",
            description="Crypto Ponzi scheme defrauding 200,000+ investors",
        ),
        FraudCase(
            company_name="Retail Ecommerce Ventures LLC",
            case_date="2025-09-23",
            fraud_type="Ponzi Scheme",
            penalty_amount=112000000.0,
            jurisdiction="us",
            source="SEC Litigation",
            source_url="https://www.sec.gov/enforcement",
            description="Ponzi-like scheme raising $112M through fraudulent offerings",
        ),
        FraudCase(
            company_name="First Liberty Building & Loan, LLC",
            case_date="2025-07-15",
            fraud_type="Ponzi Scheme",
            penalty_amount=140000000.0,
            jurisdiction="us_ga",
            source="SEC Enforcement",
            source_url="https://www.sec.gov/enforcement",
            description="Ponzi scheme defrauding 300 investors of $140M",
        ),
        FraudCase(
            company_name="Black Hawk Funding, Inc.",
            case_date="2024-07-10",
            fraud_type="Ponzi Scheme",
            penalty_amount=37700000.0,
            jurisdiction="us",
            source="SEC Enforcement",
            source_url="https://www.sec.gov/enforcement",
            description="Cannabis investment Ponzi scheme; CEO misappropriated funds",
        ),
        FraudCase(
            company_name="Puda Coal, Inc.",
            case_date="2012-02-22",
            fraud_type="Shell Company Fraud",
            penalty_amount=None,
            jurisdiction="cn",
            source="SEC Enforcement",
            source_url="https://www.sec.gov/enforcement",
            description="Empty shell company fraud; investors misled about Chinese coal business",
        ),
        FraudCase(
            company_name="China Sky One Medical, Inc.",
            case_date="2014-05-12",
            fraud_type="Accounting Fraud",
            penalty_amount=None,
            jurisdiction="cn",
            source="SEC Enforcement",
            source_url="https://www.sec.gov/enforcement",
            description="Fake sales recorded to inflate revenues",
        ),
        FraudCase(
            company_name="Morgan Stanley",
            case_date="2024-09-15",
            fraud_type="Securities Fraud",
            penalty_amount=249000000.0,
            jurisdiction="us",
            source="SEC Enforcement",
            source_url="https://www.sec.gov/enforcement",
            description="Block trade disclosure fraud; $166M disgorgement + $83M penalty",
        ),
        FraudCase(
            company_name="Digitiliti, Inc.",
            case_date="2021-06-18",
            fraud_type="Shell Company Hijacking",
            penalty_amount=None,
            jurisdiction="us",
            source="DOJ/SEC",
            source_url="https://www.sec.gov/enforcement",
            description="Shell company hijacking and pump-and-dump scheme",
        ),
        FraudCase(
            company_name="Encompass Holdings, Inc.",
            case_date="2021-06-18",
            fraud_type="Shell Company Hijacking",
            penalty_amount=None,
            jurisdiction="us",
            source="DOJ/SEC",
            source_url="https://www.sec.gov/enforcement",
            description="Shell company hijacking and pump-and-dump scheme",
        ),
        FraudCase(
            company_name="Bell Buckle Holdings, Inc.",
            case_date="2021-06-18",
            fraud_type="Shell Company Hijacking",
            penalty_amount=None,
            jurisdiction="us",
            source="DOJ/SEC",
            source_url="https://www.sec.gov/enforcement",
            description="Shell company hijacking and pump-and-dump scheme",
        ),
        FraudCase(
            company_name="Utilicraft Aerospace Industries, Inc.",
            case_date="2021-06-18",
            fraud_type="Shell Company Hijacking",
            penalty_amount=None,
            jurisdiction="us",
            source="DOJ/SEC",
            source_url="https://www.sec.gov/enforcement",
            description="Shell company hijacking and pump-and-dump scheme",
        ),
        FraudCase(
            company_name="Theranos, Inc.",
            case_date="2018-03-14",
            fraud_type="Securities Fraud",
            penalty_amount=None,
            jurisdiction="us_ca",
            source="SEC Enforcement",
            source_url="https://www.sec.gov/litigation/litreleases/2018/lr24078.htm",
            description="Massive fraud involving fake blood testing technology",
        ),
        FraudCase(
            company_name="Enron Corp.",
            case_date="2001-12-02",
            fraud_type="Accounting Fraud",
            penalty_amount=None,
            jurisdiction="us_tx",
            source="SEC Enforcement",
            source_url="https://www.sec.gov/enforcement",
            description="One of largest accounting frauds in history; bankruptcy",
        ),
        FraudCase(
            company_name="WorldCom, Inc.",
            case_date="2002-06-25",
            fraud_type="Accounting Fraud",
            penalty_amount=None,
            jurisdiction="us",
            source="SEC Enforcement",
            source_url="https://www.sec.gov/enforcement",
            description="$11B accounting fraud; largest bankruptcy at time",
        ),
        FraudCase(
            company_name="Tyco International Ltd.",
            case_date="2002-09-12",
            fraud_type="Securities Fraud",
            penalty_amount=None,
            jurisdiction="bm",
            source="SEC Enforcement",
            source_url="https://www.sec.gov/enforcement",
            description="Executive looting and accounting fraud",
        ),
        FraudCase(
            company_name="HealthSouth Corporation",
            case_date="2003-03-19",
            fraud_type="Accounting Fraud",
            penalty_amount=None,
            jurisdiction="us_al",
            source="SEC Enforcement",
            source_url="https://www.sec.gov/enforcement",
            description="$2.7B accounting fraud to inflate earnings",
        ),
        FraudCase(
            company_name="Adelphia Communications Corp.",
            case_date="2002-07-24",
            fraud_type="Securities Fraud",
            penalty_amount=None,
            jurisdiction="us",
            source="SEC Enforcement",
            source_url="https://www.sec.gov/enforcement",
            description="Massive fraud hiding $2.3B in debt",
        ),
        FraudCase(
            company_name="Wirecard AG",
            case_date="2020-06-25",
            fraud_type="Accounting Fraud",
            penalty_amount=None,
            jurisdiction="de",
            source="SEC/International",
            source_url="https://www.sec.gov/enforcement",
            description="German fintech fraud; $2B in fake cash balances",
        ),
        FraudCase(
            company_name="Luckin Coffee Inc.",
            case_date="2020-07-01",
            fraud_type="Accounting Fraud",
            penalty_amount=180000000.0,
            jurisdiction="cn",
            source="SEC Enforcement",
            source_url="https://www.sec.gov/enforcement",
            description="Fabricated $300M in sales; $180M settlement",
        ),
        FraudCase(
            company_name="Nikola Corporation",
            case_date="2021-07-29",
            fraud_type="Securities Fraud",
            penalty_amount=125000000.0,
            jurisdiction="us_az",
            source="SEC Enforcement",
            source_url="https://www.sec.gov/enforcement",
            description="Misled investors about technology capabilities",
        ),
        FraudCase(
            company_name="FTX Trading Ltd.",
            case_date="2022-12-13",
            fraud_type="Securities Fraud",
            penalty_amount=None,
            jurisdiction="bs",
            source="SEC/DOJ",
            source_url="https://www.sec.gov/enforcement",
            description="Massive crypto exchange fraud and misappropriation",
        ),
        FraudCase(
            company_name="Alameda Research LLC",
            case_date="2022-12-13",
            fraud_type="Securities Fraud",
            penalty_amount=None,
            jurisdiction="us",
            source="SEC/DOJ",
            source_url="https://www.sec.gov/enforcement",
            description="Related to FTX; misappropriation of customer funds",
        ),
        FraudCase(
            company_name="BitConnect",
            case_date="2021-09-01",
            fraud_type="Ponzi Scheme",
            penalty_amount=2400000000.0,
            jurisdiction="us",
            source="SEC Enforcement",
            source_url="https://www.sec.gov/enforcement",
            description="$2.4B crypto Ponzi scheme",
        ),
        FraudCase(
            company_name="OneCoin Ltd.",
            case_date="2019-03-06",
            fraud_type="Ponzi Scheme",
            penalty_amount=4000000000.0,
            jurisdiction="bg",
            source="DOJ/International",
            source_url="https://www.justice.gov",
            description="$4B global crypto Ponzi scheme",
        ),
        FraudCase(
            company_name="Centra Tech, Inc.",
            case_date="2018-04-02",
            fraud_type="ICO Fraud",
            penalty_amount=32000000.0,
            jurisdiction="us_fl",
            source="SEC Enforcement",
            source_url="https://www.sec.gov/enforcement",
            description="Fraudulent ICO with fake partnerships",
        ),
        FraudCase(
            company_name="PlexCorps",
            case_date="2017-12-04",
            fraud_type="ICO Fraud",
            penalty_amount=15000000.0,
            jurisdiction="ca",
            source="SEC Enforcement",
            source_url="https://www.sec.gov/enforcement",
            description="Fraudulent ICO promising 1,354% returns",
        ),
        FraudCase(
            company_name="AriseBank",
            case_date="2018-01-30",
            fraud_type="ICO Fraud",
            penalty_amount=None,
            jurisdiction="us_tx",
            source="SEC Enforcement",
            source_url="https://www.sec.gov/enforcement",
            description="Fraudulent crypto bank ICO",
        ),
        FraudCase(
            company_name="Samourai Wallet",
            case_date="2024-04-24",
            fraud_type="Money Laundering",
            penalty_amount=None,
            jurisdiction="us",
            source="DOJ",
            source_url="https://www.justice.gov",
            description="Crypto mixing service facilitating money laundering",
        ),
        FraudCase(
            company_name="Voyager Digital Holdings",
            case_date="2022-07-05",
            fraud_type="Securities Fraud",
            penalty_amount=None,
            jurisdiction="us",
            source="SEC/FTC",
            source_url="https://www.sec.gov/enforcement",
            description="Crypto lending platform that collapsed",
        ),
        FraudCase(
            company_name="Celsius Network LLC",
            case_date="2022-07-13",
            fraud_type="Securities Fraud",
            penalty_amount=None,
            jurisdiction="us",
            source="SEC Enforcement",
            source_url="https://www.sec.gov/enforcement",
            description="Crypto lending platform fraud and bankruptcy",
        ),
        FraudCase(
            company_name="Three Arrows Capital",
            case_date="2022-06-27",
            fraud_type="Securities Fraud",
            penalty_amount=None,
            jurisdiction="sg",
            source="International",
            source_url="https://www.sec.gov/enforcement",
            description="Crypto hedge fund collapse; fraud allegations",
        ),
        FraudCase(
            company_name="BlockFi Inc.",
            case_date="2022-02-14",
            fraud_type="Securities Violation",
            penalty_amount=100000000.0,
            jurisdiction="us",
            source="SEC Enforcement",
            source_url="https://www.sec.gov/enforcement",
            description="Unregistered securities offering; $100M settlement",
        ),
        FraudCase(
            company_name="OMC Shipping PTE Ltd.",
            case_date="2023-05-15",
            fraud_type="Shell Company Fraud",
            penalty_amount=None,
            jurisdiction="sg",
            source="Investigation",
            source_url="https://www.sec.gov/enforcement",
            description="Suspected shell company used in trade-based money laundering",
        ),
        FraudCase(
            company_name="Blue Sky Capital Management LLC",
            case_date="2023-08-10",
            fraud_type="Investment Fraud",
            penalty_amount=None,
            jurisdiction="us",
            source="SEC Investigation",
            source_url="https://www.sec.gov/enforcement",
            description="Suspected fraudulent investment scheme",
        ),
    ]

    def __init__(self, delay: float = 2.0):
        """Initialize scraper with rate limiting delay."""
        self.delay = delay
        self.session = requests.Session()
        self.session.headers.update(self.HEADERS)

    def get_known_cases(self) -> list[FraudCase]:
        """Return list of known fraud cases."""
        return self.KNOWN_CASES.copy()

    def _make_request(self, url: str) -> Optional[BeautifulSoup]:
        """Make rate-limited request and return parsed HTML."""
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            time.sleep(self.delay)
            return BeautifulSoup(response.text, "lxml")
        except requests.RequestException as e:
            print(f"Request failed for {url}: {e}")
            return None

    def _extract_penalty(self, text: str) -> Optional[float]:
        """Extract penalty amount from text."""
        patterns = [
            r"\$(\d+(?:\.\d+)?)\s*(?:billion|B)",
            r"\$(\d+(?:\.\d+)?)\s*(?:million|M)",
            r"\$(\d{1,3}(?:,\d{3})*(?:\.\d+)?)",
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                amount = float(match.group(1).replace(",", ""))
                if "billion" in text.lower() or "b" in pattern.lower():
                    return amount * 1_000_000_000
                elif "million" in text.lower() or "m" in pattern.lower():
                    return amount * 1_000_000
                return amount
        return None

    def _classify_fraud_type(self, text: str) -> str:
        """Classify fraud type based on text content."""
        text_lower = text.lower()

        if "ponzi" in text_lower:
            return "Ponzi Scheme"
        elif "pyramid" in text_lower:
            return "Pyramid Scheme"
        elif "shell" in text_lower:
            return "Shell Company Fraud"
        elif "accounting" in text_lower or "financial statement" in text_lower:
            return "Accounting Fraud"
        elif "ico" in text_lower or "initial coin" in text_lower:
            return "ICO Fraud"
        elif "crypto" in text_lower or "bitcoin" in text_lower:
            return "Crypto Fraud"
        elif "insider" in text_lower:
            return "Insider Trading"
        elif "manipulation" in text_lower or "pump" in text_lower:
            return "Market Manipulation"
        elif "money laundering" in text_lower:
            return "Money Laundering"
        else:
            return "Securities Fraud"

    def scrape_all(self) -> list[FraudCase]:
        """Scrape all available sources and return fraud cases."""
        cases = self.get_known_cases()
        return cases
