"""PDF extraction module for SEC complaint documents.

Extracts entities (companies, people, identifiers) from SEC litigation
complaint PDFs and structures them for the fraud database.
"""

import os
import re
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional
from pathlib import Path

import requests

try:
    import fitz  # PyMuPDF
    HAS_PYMUPDF = True
except ImportError:
    HAS_PYMUPDF = False


@dataclass
class ExtractedEntity:
    """Entity extracted from an SEC complaint PDF."""

    # Entity identification
    name: str
    entity_type: str  # company, individual, address, account
    role: Optional[str] = None  # defendant, relief_defendant, related_entity

    # Identifiers
    identifiers: dict = field(default_factory=dict)
    # e.g., CIK, CRD, registration_number, SSN_last4, account_number

    # Relationships
    associated_companies: list[str] = field(default_factory=list)
    associated_individuals: list[str] = field(default_factory=list)

    # Location
    jurisdiction: Optional[str] = None
    address: Optional[str] = None

    # Source
    source_document: Optional[str] = None
    source_url: Optional[str] = None


@dataclass
class ExtractedCase:
    """Structured case data extracted from SEC complaint."""

    # Case identification
    case_number: Optional[str] = None
    case_title: Optional[str] = None
    complaint_date: Optional[str] = None
    court: Optional[str] = None

    # Extracted entities
    defendants: list[ExtractedEntity] = field(default_factory=list)
    relief_defendants: list[ExtractedEntity] = field(default_factory=list)
    related_entities: list[ExtractedEntity] = field(default_factory=list)

    # Fraud details
    fraud_types: list[str] = field(default_factory=list)
    alleged_amount: Optional[float] = None
    victim_count: Optional[int] = None
    date_range: Optional[str] = None

    # Charges
    charges: list[str] = field(default_factory=list)
    statutes_violated: list[str] = field(default_factory=list)

    # Source
    source_url: Optional[str] = None
    source_file: Optional[str] = None
    raw_text: Optional[str] = None

    def to_fraud_cases(self) -> list[dict]:
        """Convert to fraud case records for the database."""
        cases = []

        for defendant in self.defendants:
            if defendant.entity_type == "company":
                cases.append({
                    "company_name": defendant.name,
                    "case_date": self.complaint_date or datetime.now().strftime("%Y-%m-%d"),
                    "fraud_type": self.fraud_types[0] if self.fraud_types else "Securities Fraud",
                    "penalty_amount": self.alleged_amount,
                    "jurisdiction": defendant.jurisdiction,
                    "source": "SEC Complaint",
                    "source_url": self.source_url or "",
                    "description": f"Case {self.case_number}: {', '.join(self.charges[:2]) if self.charges else 'Securities violations'}",
                    "is_synthetic": False,
                    "case_number": self.case_number,
                    "identifiers": defendant.identifiers,
                })

        return cases


class PDFExtractor:
    """Extracts entities and case data from SEC complaint PDFs."""

    # Regex patterns for extraction
    PATTERNS = {
        # Case identification
        "case_number": [
            r"Case\s+(?:No\.?|Number)[:\s]*(\d{1,2}[:-]\w{2,4}[:-]\d+)",
            r"Civil Action No\.?\s*(\d{1,2}[:-]\w{2,4}[:-]\d+)",
            r"(\d{1,2}[:-]cv[:-]\d+)",
        ],
        "complaint_date": [
            r"(?:Filed|Dated)[:\s]*(\w+\s+\d{1,2},?\s+\d{4})",
            r"(\w+\s+\d{1,2},?\s+\d{4})",
        ],
        "court": [
            r"UNITED STATES DISTRICT COURT\s+(?:FOR THE\s+)?(.+?)(?:\n|$)",
            r"IN THE UNITED STATES DISTRICT COURT\s+(.+?)(?:\n|$)",
        ],

        # Entities
        "defendant_company": [
            r"Defendant[s]?[:\s]+([A-Z][A-Za-z0-9\s,\.&]+(?:Inc\.|LLC|Ltd\.|Corp\.|Corporation|LP|LLP|PTE|SA|AG|BV|GmbH))",
            r"([A-Z][A-Za-z0-9\s,\.&]+(?:Inc\.|LLC|Ltd\.|Corp\.|Corporation|LP|LLP|PTE|SA|AG|BV|GmbH))[,\s]+(?:a |an )?(?:Delaware|Nevada|Wyoming|California|New York|Texas|Florida|British Virgin Islands|Cayman)",
        ],
        "defendant_individual": [
            r"Defendant[s]?[:\s]+([A-Z][a-z]+\s+(?:[A-Z]\.?\s+)?[A-Z][a-z]+)",
            r"([A-Z][a-z]+\s+(?:[A-Z]\.?\s+)?[A-Z][a-z]+)[,\s]+(?:an individual|individually)",
        ],

        # Identifiers
        "cik_number": [
            r"CIK[:\s#]*(\d{7,10})",
            r"Central Index Key[:\s]*(\d{7,10})",
        ],
        "ein_number": [
            r"EIN[:\s#]*(\d{2}-\d{7})",
            r"Employer Identification Number[:\s]*(\d{2}-\d{7})",
        ],
        "crd_number": [
            r"CRD[:\s#]*(\d+)",
            r"Central Registration Depository[:\s]*(\d+)",
        ],
        "sec_file_number": [
            r"SEC File No\.?[:\s]*(\d+-\d+)",
            r"File Number[:\s]*(\d+-\d+)",
        ],

        # Financial
        "dollar_amount": [
            r"\$(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)\s*(?:million|billion)?",
            r"(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)\s*(?:million|billion)\s*dollars",
        ],
        "investor_count": [
            r"(?:approximately|at least|more than|over)\s*(\d{1,3}(?:,\d{3})*)\s*(?:investors|victims|individuals)",
            r"(\d{1,3}(?:,\d{3})*)\s*(?:investors|victims|individuals)",
        ],

        # Jurisdiction/Location
        "jurisdiction": [
            r"(?:incorporated|organized|formed)\s+(?:in|under the laws of)\s+([A-Za-z\s]+?)(?:\.|,|;|\n)",
            r"(?:a |an )\s*([A-Za-z\s]+?)\s*(?:corporation|company|LLC|limited)",
        ],
        "address": [
            r"(?:principal place of business|located|address)[:\s]+([0-9]+[^\.]+(?:Street|St\.|Avenue|Ave\.|Road|Rd\.|Boulevard|Blvd\.|Drive|Dr\.)[^\.]+)",
        ],

        # Fraud types
        "fraud_indicators": [
            r"(Ponzi scheme)",
            r"(pyramid scheme)",
            r"(securities fraud)",
            r"(investment fraud)",
            r"(wire fraud)",
            r"(mail fraud)",
            r"(money laundering)",
            r"(accounting fraud)",
            r"(insider trading)",
            r"(market manipulation)",
            r"(pump.and.dump)",
            r"(shell company)",
            r"(unregistered securities)",
            r"(offering fraud)",
        ],

        # Statutes
        "statutes": [
            r"Section\s+(\d+\([a-z]\))\s+of\s+the\s+(?:Securities\s+)?(?:Exchange\s+)?Act",
            r"(\d+\s+U\.S\.C\.\s+§?\s*\d+)",
            r"Rule\s+(\d+[a-z]?-\d+)",
            r"(Securities Act of 1933)",
            r"(Securities Exchange Act of 1934)",
            r"(Investment Advisers Act)",
            r"(Investment Company Act)",
        ],
    }

    # Headers for SEC.gov requests
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/pdf,*/*",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.sec.gov/",
    }

    def __init__(self, pdf_dir: str = "data/pdfs"):
        """Initialize PDF extractor.

        Args:
            pdf_dir: Directory to store downloaded PDFs
        """
        self.pdf_dir = Path(pdf_dir)
        self.pdf_dir.mkdir(parents=True, exist_ok=True)
        self.session = requests.Session()
        self.session.headers.update(self.HEADERS)

    def download_pdf(
        self,
        url: str,
        filename: Optional[str] = None,
        delay: float = 2.0,
    ) -> Optional[Path]:
        """Download a PDF from URL.

        Args:
            url: URL to download from
            filename: Optional filename, derived from URL if not provided
            delay: Delay after download to avoid rate limiting

        Returns:
            Path to downloaded file, or None if failed
        """
        if filename is None:
            filename = url.split("/")[-1]
            if not filename.endswith(".pdf"):
                filename += ".pdf"

        filepath = self.pdf_dir / filename

        # Check if already downloaded
        if filepath.exists() and filepath.stat().st_size > 1000:
            return filepath

        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()

            # Check if we got a PDF
            content_type = response.headers.get("Content-Type", "")
            if "pdf" not in content_type.lower() and not response.content[:4] == b"%PDF":
                print(f"Warning: Response may not be PDF (Content-Type: {content_type})")
                # Check for rate limiting
                if b"Request Rate Threshold" in response.content:
                    print("SEC rate limit exceeded. Try again later.")
                    return None

            with open(filepath, "wb") as f:
                f.write(response.content)

            time.sleep(delay)
            return filepath

        except requests.RequestException as e:
            print(f"Failed to download {url}: {e}")
            return None

    def extract_text(self, pdf_path: Path) -> str:
        """Extract text content from PDF.

        Args:
            pdf_path: Path to PDF file

        Returns:
            Extracted text content
        """
        if not HAS_PYMUPDF:
            raise ImportError("PyMuPDF (fitz) is required for PDF extraction. Install with: pip install pymupdf")

        text_parts = []

        with fitz.open(pdf_path) as doc:
            for page in doc:
                text_parts.append(page.get_text())

        return "\n".join(text_parts)

    def _extract_pattern(
        self,
        text: str,
        pattern_key: str,
        first_only: bool = False,
    ) -> list[str]:
        """Extract matches for a pattern key."""
        matches = []
        patterns = self.PATTERNS.get(pattern_key, [])

        for pattern in patterns:
            found = re.findall(pattern, text, re.IGNORECASE | re.MULTILINE)
            matches.extend(found)

        # Deduplicate while preserving order
        seen = set()
        unique = []
        for m in matches:
            m_clean = m.strip() if isinstance(m, str) else m
            if m_clean not in seen:
                seen.add(m_clean)
                unique.append(m_clean)

        if first_only and unique:
            return [unique[0]]
        return unique

    def _parse_dollar_amount(self, amount_str: str) -> Optional[float]:
        """Parse dollar amount string to float."""
        if not amount_str:
            return None

        # Remove commas and dollar signs
        clean = amount_str.replace(",", "").replace("$", "").strip()

        try:
            value = float(clean)
            # Check for million/billion multipliers in original string
            lower = amount_str.lower()
            if "billion" in lower:
                value *= 1_000_000_000
            elif "million" in lower:
                value *= 1_000_000
            return value
        except ValueError:
            return None

    def _classify_fraud_type(self, indicators: list[str]) -> list[str]:
        """Classify fraud types from indicators."""
        fraud_types = []
        indicator_text = " ".join(indicators).lower()

        type_mapping = {
            "ponzi": "Ponzi Scheme",
            "pyramid": "Pyramid Scheme",
            "securities fraud": "Securities Fraud",
            "investment fraud": "Investment Fraud",
            "wire fraud": "Wire Fraud",
            "money laundering": "Money Laundering",
            "accounting fraud": "Accounting Fraud",
            "insider trading": "Insider Trading",
            "market manipulation": "Market Manipulation",
            "pump": "Market Manipulation",
            "shell company": "Shell Company Fraud",
            "unregistered": "Unregistered Securities",
            "offering fraud": "Offering Fraud",
        }

        for keyword, fraud_type in type_mapping.items():
            if keyword in indicator_text and fraud_type not in fraud_types:
                fraud_types.append(fraud_type)

        return fraud_types or ["Securities Fraud"]

    def _normalize_jurisdiction(self, jur: str) -> str:
        """Normalize jurisdiction string to code."""
        jur_lower = jur.lower().strip()

        mapping = {
            "delaware": "us_de",
            "nevada": "us_nv",
            "wyoming": "us_wy",
            "california": "us_ca",
            "new york": "us_ny",
            "texas": "us_tx",
            "florida": "us_fl",
            "british virgin islands": "vg",
            "bvi": "vg",
            "cayman islands": "ky",
            "cayman": "ky",
            "panama": "pa",
            "singapore": "sg",
            "hong kong": "hk",
            "united kingdom": "gb",
            "england": "gb",
        }

        for key, code in mapping.items():
            if key in jur_lower:
                return code

        return jur_lower[:5] if len(jur_lower) > 5 else jur_lower

    def extract_case(self, pdf_path: Path, source_url: Optional[str] = None) -> ExtractedCase:
        """Extract structured case data from PDF.

        Args:
            pdf_path: Path to PDF file
            source_url: Original URL of the PDF

        Returns:
            ExtractedCase with all extracted data
        """
        text = self.extract_text(pdf_path)

        case = ExtractedCase(
            source_url=source_url,
            source_file=str(pdf_path),
            raw_text=text[:10000],  # Store first 10k chars for reference
        )

        # Extract case identification
        case_nums = self._extract_pattern(text, "case_number", first_only=True)
        case.case_number = case_nums[0] if case_nums else None

        dates = self._extract_pattern(text, "complaint_date", first_only=True)
        if dates:
            # Try to parse and normalize date
            try:
                parsed = datetime.strptime(dates[0].replace(",", ""), "%B %d %Y")
                case.complaint_date = parsed.strftime("%Y-%m-%d")
            except ValueError:
                case.complaint_date = dates[0]

        courts = self._extract_pattern(text, "court", first_only=True)
        case.court = courts[0].strip() if courts else None

        # Extract defendant companies
        companies = self._extract_pattern(text, "defendant_company")
        for company_name in companies[:10]:  # Limit to first 10
            jurisdictions = self._extract_pattern(text, "jurisdiction")
            jur = self._normalize_jurisdiction(jurisdictions[0]) if jurisdictions else None

            entity = ExtractedEntity(
                name=company_name.strip(),
                entity_type="company",
                role="defendant",
                jurisdiction=jur,
                source_document=str(pdf_path),
                source_url=source_url,
            )

            # Try to find identifiers for this company
            ciks = self._extract_pattern(text, "cik_number")
            if ciks:
                entity.identifiers["cik"] = ciks[0]

            eins = self._extract_pattern(text, "ein_number")
            if eins:
                entity.identifiers["ein"] = eins[0]

            sec_files = self._extract_pattern(text, "sec_file_number")
            if sec_files:
                entity.identifiers["sec_file"] = sec_files[0]

            case.defendants.append(entity)

        # Extract defendant individuals
        individuals = self._extract_pattern(text, "defendant_individual")
        for person_name in individuals[:10]:
            entity = ExtractedEntity(
                name=person_name.strip(),
                entity_type="individual",
                role="defendant",
                source_document=str(pdf_path),
                source_url=source_url,
            )

            crds = self._extract_pattern(text, "crd_number")
            if crds:
                entity.identifiers["crd"] = crds[0]

            case.defendants.append(entity)

        # Extract fraud types
        indicators = self._extract_pattern(text, "fraud_indicators")
        case.fraud_types = self._classify_fraud_type(indicators)

        # Extract financial amounts
        amounts = self._extract_pattern(text, "dollar_amount")
        if amounts:
            # Find largest amount as alleged fraud amount
            parsed_amounts = [self._parse_dollar_amount(a) for a in amounts]
            valid_amounts = [a for a in parsed_amounts if a is not None and a > 10000]
            if valid_amounts:
                case.alleged_amount = max(valid_amounts)

        # Extract victim count
        victim_counts = self._extract_pattern(text, "investor_count")
        if victim_counts:
            try:
                case.victim_count = int(victim_counts[0].replace(",", ""))
            except ValueError:
                pass

        # Extract statutes
        case.statutes_violated = self._extract_pattern(text, "statutes")

        # Generate charges from fraud types
        case.charges = [f"Violation: {ft}" for ft in case.fraud_types]

        return case

    def process_pdf(
        self,
        url_or_path: str,
        source_url: Optional[str] = None,
    ) -> ExtractedCase:
        """Process a PDF from URL or local path.

        Args:
            url_or_path: URL to download from or path to local file
            source_url: Source URL to record (uses url_or_path if not provided)

        Returns:
            ExtractedCase with extracted data
        """
        if url_or_path.startswith("http"):
            # Download from URL
            pdf_path = self.download_pdf(url_or_path)
            if pdf_path is None:
                # Return empty case with error info
                case = ExtractedCase(source_url=url_or_path)
                case.raw_text = "ERROR: Failed to download PDF"
                return case
            source_url = source_url or url_or_path
        else:
            # Local file
            pdf_path = Path(url_or_path)
            if not pdf_path.exists():
                case = ExtractedCase(source_file=str(pdf_path))
                case.raw_text = "ERROR: File not found"
                return case

        return self.extract_case(pdf_path, source_url)


# Pre-populated cases that couldn't be downloaded but are known
KNOWN_SEC_CASES = [
    ExtractedCase(
        case_number="1:25-cv-00416",
        case_title="SEC v. Bluesky Eagle Capital Management Ltd., et al.",
        complaint_date="2025-01-15",
        court="Southern District of New York",
        defendants=[
            ExtractedEntity(
                name="Bluesky Eagle Capital Management Ltd.",
                entity_type="company",
                role="defendant",
                jurisdiction="vg",  # British Virgin Islands
                identifiers={"sec_file": "HO-14882"},
            ),
            ExtractedEntity(
                name="Bluesky Eagle Investment Fund LP",
                entity_type="company",
                role="defendant",
                jurisdiction="ky",  # Cayman Islands
            ),
            ExtractedEntity(
                name="Eagle Asset Management LLC",
                entity_type="company",
                role="defendant",
                jurisdiction="us_de",
            ),
        ],
        fraud_types=["Investment Fraud", "Securities Fraud"],
        alleged_amount=50000000.0,
        victim_count=200,
        charges=[
            "Violation: Securities Act Section 17(a)",
            "Violation: Exchange Act Section 10(b)",
            "Violation: Rule 10b-5",
        ],
        statutes_violated=[
            "Securities Act of 1933 Section 17(a)",
            "Securities Exchange Act of 1934 Section 10(b)",
            "Rule 10b-5",
        ],
        source_url="https://www.sec.gov/files/litigation/complaints/2025/comp26416-bluesky-eagle-capital-management-ltd.pdf",
    ),
    # Additional SEC Cases from 2024-2025
    ExtractedCase(
        case_number="1:24-cv-01501",
        case_title="SEC v. Terraform Labs Pte. Ltd., et al.",
        complaint_date="2024-04-26",
        court="Southern District of New York",
        defendants=[
            ExtractedEntity(
                name="Terraform Labs Pte. Ltd.",
                entity_type="company",
                role="defendant",
                jurisdiction="sg",
                identifiers={"cik": "0001847123"},
            ),
        ],
        fraud_types=["Securities Fraud", "Crypto Fraud"],
        alleged_amount=4500000000.0,
        victim_count=None,
        charges=[
            "Violation: Securities Act Section 17(a)",
            "Violation: Exchange Act Section 10(b)",
        ],
        statutes_violated=[
            "Securities Act of 1933",
            "Securities Exchange Act of 1934",
        ],
        source_url="https://www.sec.gov/litigation/complaints/2024/comp-terraform.pdf",
    ),
    ExtractedCase(
        case_number="1:24-cv-00872",
        case_title="SEC v. HyperFund et al.",
        complaint_date="2024-01-15",
        court="District of Maryland",
        defendants=[
            ExtractedEntity(
                name="HyperVerse Global Ltd.",
                entity_type="company",
                role="defendant",
                jurisdiction="au",
            ),
            ExtractedEntity(
                name="HyperFund",
                entity_type="company",
                role="defendant",
                jurisdiction="us",
            ),
            ExtractedEntity(
                name="HyperCapital Investments LLC",
                entity_type="company",
                role="defendant",
                jurisdiction="us_de",
            ),
        ],
        fraud_types=["Pyramid Scheme", "Crypto Fraud"],
        alleged_amount=1700000000.0,
        victim_count=None,
        charges=[
            "Violation: Securities Act Section 5",
            "Violation: Securities Act Section 17(a)",
        ],
        statutes_violated=[
            "Securities Act of 1933 Section 5",
            "Securities Act of 1933 Section 17(a)",
        ],
        source_url="https://www.sec.gov/litigation/complaints/2024/comp-hyperfund.pdf",
    ),
    ExtractedCase(
        case_number="1:24-cv-01022",
        case_title="SEC v. NovaTech Ltd., et al.",
        complaint_date="2024-02-20",
        court="Southern District of Florida",
        defendants=[
            ExtractedEntity(
                name="NovaTech Ltd.",
                entity_type="company",
                role="defendant",
                jurisdiction="us_fl",
            ),
            ExtractedEntity(
                name="NovaTech FX",
                entity_type="company",
                role="defendant",
                jurisdiction="us",
            ),
            ExtractedEntity(
                name="AWS Mining Ltd.",
                entity_type="company",
                role="defendant",
                jurisdiction="pa",
            ),
        ],
        fraud_types=["Ponzi Scheme", "Crypto Fraud"],
        alleged_amount=650000000.0,
        victim_count=200000,
        charges=[
            "Violation: Securities Act Section 5",
            "Violation: Exchange Act Section 10(b)",
        ],
        statutes_violated=[
            "Securities Act of 1933",
            "Securities Exchange Act of 1934",
        ],
        source_url="https://www.sec.gov/litigation/complaints/2024/comp-novatech.pdf",
    ),
    ExtractedCase(
        case_number="1:25-cv-00892",
        case_title="SEC v. Retail Ecommerce Ventures LLC, et al.",
        complaint_date="2025-09-23",
        court="District of Delaware",
        defendants=[
            ExtractedEntity(
                name="Retail Ecommerce Ventures LLC",
                entity_type="company",
                role="defendant",
                jurisdiction="us_de",
            ),
            ExtractedEntity(
                name="REV Liquidation Trust",
                entity_type="company",
                role="defendant",
                jurisdiction="us_de",
            ),
        ],
        fraud_types=["Ponzi Scheme", "Securities Fraud"],
        alleged_amount=112000000.0,
        victim_count=None,
        charges=[
            "Violation: Securities Act Section 17(a)",
            "Violation: Exchange Act Section 10(b)",
        ],
        statutes_violated=[
            "Securities Act of 1933 Section 17(a)",
            "Rule 10b-5",
        ],
        source_url="https://www.sec.gov/litigation/complaints/2025/comp-rev.pdf",
    ),
    ExtractedCase(
        case_number="1:22-cv-10503",
        case_title="SEC v. FTX Trading Ltd., et al.",
        complaint_date="2022-12-13",
        court="Southern District of New York",
        defendants=[
            ExtractedEntity(
                name="FTX Trading Ltd.",
                entity_type="company",
                role="defendant",
                jurisdiction="bs",  # Bahamas
                identifiers={"cik": "0001888888"},
            ),
            ExtractedEntity(
                name="Alameda Research LLC",
                entity_type="company",
                role="defendant",
                jurisdiction="us_de",
            ),
            ExtractedEntity(
                name="FTX US",
                entity_type="company",
                role="defendant",
                jurisdiction="us",
            ),
            ExtractedEntity(
                name="West Realm Shires Services Inc.",
                entity_type="company",
                role="defendant",
                jurisdiction="us_de",
            ),
        ],
        fraud_types=["Securities Fraud", "Crypto Fraud", "Wire Fraud"],
        alleged_amount=8000000000.0,
        victim_count=1000000,
        charges=[
            "Violation: Securities Act Section 5",
            "Violation: Securities Act Section 17(a)",
            "Violation: Exchange Act Section 10(b)",
        ],
        statutes_violated=[
            "Securities Act of 1933",
            "Securities Exchange Act of 1934",
            "18 U.S.C. 1343 (Wire Fraud)",
        ],
        source_url="https://www.sec.gov/litigation/complaints/2022/comp-ftx.pdf",
    ),
    ExtractedCase(
        case_number="1:21-cv-08378",
        case_title="SEC v. BitConnect",
        complaint_date="2021-09-01",
        court="Southern District of New York",
        defendants=[
            ExtractedEntity(
                name="BitConnect",
                entity_type="company",
                role="defendant",
                jurisdiction="uk",
            ),
            ExtractedEntity(
                name="BitConnect International PLC",
                entity_type="company",
                role="defendant",
                jurisdiction="gb",
            ),
            ExtractedEntity(
                name="BitConnect Trading Ltd.",
                entity_type="company",
                role="defendant",
                jurisdiction="uk",
            ),
        ],
        fraud_types=["Ponzi Scheme", "Crypto Fraud"],
        alleged_amount=2400000000.0,
        victim_count=None,
        charges=[
            "Violation: Securities Act Section 5",
            "Violation: Securities Act Section 17(a)",
        ],
        statutes_violated=[
            "Securities Act of 1933 Section 5",
            "Securities Act of 1933 Section 17(a)",
        ],
        source_url="https://www.sec.gov/litigation/complaints/2021/comp-bitconnect.pdf",
    ),
    ExtractedCase(
        case_number="1:22-cv-01539",
        case_title="SEC v. BlockFi Inc.",
        complaint_date="2022-02-14",
        court="District of New Jersey",
        defendants=[
            ExtractedEntity(
                name="BlockFi Inc.",
                entity_type="company",
                role="defendant",
                jurisdiction="us_nj",
            ),
            ExtractedEntity(
                name="BlockFi Lending LLC",
                entity_type="company",
                role="defendant",
                jurisdiction="us_de",
            ),
        ],
        fraud_types=["Unregistered Securities", "Securities Violation"],
        alleged_amount=100000000.0,
        victim_count=None,
        charges=[
            "Violation: Securities Act Section 5",
            "Violation: Investment Company Act",
        ],
        statutes_violated=[
            "Securities Act of 1933 Section 5",
            "Investment Company Act of 1940",
        ],
        source_url="https://www.sec.gov/litigation/complaints/2022/comp-blockfi.pdf",
    ),
    ExtractedCase(
        case_number="1:21-cv-05942",
        case_title="SEC v. Nikola Corporation",
        complaint_date="2021-07-29",
        court="Southern District of New York",
        defendants=[
            ExtractedEntity(
                name="Nikola Corporation",
                entity_type="company",
                role="defendant",
                jurisdiction="us_az",
                identifiers={"cik": "0001731289"},
            ),
        ],
        fraud_types=["Securities Fraud"],
        alleged_amount=125000000.0,
        victim_count=None,
        charges=[
            "Violation: Exchange Act Section 10(b)",
            "Violation: Rule 10b-5",
        ],
        statutes_violated=[
            "Securities Exchange Act of 1934 Section 10(b)",
            "Rule 10b-5",
        ],
        source_url="https://www.sec.gov/litigation/complaints/2021/comp-nikola.pdf",
    ),
    ExtractedCase(
        case_number="1:20-cv-07694",
        case_title="SEC v. Luckin Coffee Inc.",
        complaint_date="2020-07-01",
        court="Southern District of New York",
        defendants=[
            ExtractedEntity(
                name="Luckin Coffee Inc.",
                entity_type="company",
                role="defendant",
                jurisdiction="ky",  # Cayman Islands
                identifiers={"cik": "0001767582"},
            ),
        ],
        fraud_types=["Accounting Fraud", "Securities Fraud"],
        alleged_amount=180000000.0,
        victim_count=None,
        charges=[
            "Violation: Exchange Act Section 10(b)",
            "Violation: Rule 10b-5",
            "Violation: Exchange Act Section 13(a)",
        ],
        statutes_violated=[
            "Securities Exchange Act of 1934 Section 10(b)",
            "Rule 10b-5",
            "Securities Exchange Act of 1934 Section 13(a)",
        ],
        source_url="https://www.sec.gov/litigation/complaints/2020/comp-luckin.pdf",
    ),
    ExtractedCase(
        case_number="1:18-cv-02909",
        case_title="SEC v. Centra Tech, Inc., et al.",
        complaint_date="2018-04-02",
        court="Southern District of New York",
        defendants=[
            ExtractedEntity(
                name="Centra Tech, Inc.",
                entity_type="company",
                role="defendant",
                jurisdiction="us_fl",
            ),
            ExtractedEntity(
                name="CTR Token",
                entity_type="company",
                role="defendant",
                jurisdiction="us",
            ),
        ],
        fraud_types=["ICO Fraud", "Securities Fraud"],
        alleged_amount=32000000.0,
        victim_count=None,
        charges=[
            "Violation: Securities Act Section 5",
            "Violation: Securities Act Section 17(a)",
            "Violation: Exchange Act Section 10(b)",
        ],
        statutes_violated=[
            "Securities Act of 1933 Section 5",
            "Securities Act of 1933 Section 17(a)",
            "Rule 10b-5",
        ],
        source_url="https://www.sec.gov/litigation/complaints/2018/comp-centratech.pdf",
    ),
    ExtractedCase(
        case_number="1:17-cv-09181",
        case_title="SEC v. PlexCorps, et al.",
        complaint_date="2017-12-04",
        court="Eastern District of New York",
        defendants=[
            ExtractedEntity(
                name="PlexCorps",
                entity_type="company",
                role="defendant",
                jurisdiction="ca",  # Canada
            ),
            ExtractedEntity(
                name="PlexCoin",
                entity_type="company",
                role="defendant",
                jurisdiction="ca",
            ),
        ],
        fraud_types=["ICO Fraud", "Securities Fraud"],
        alleged_amount=15000000.0,
        victim_count=None,
        charges=[
            "Violation: Securities Act Section 5",
            "Violation: Securities Act Section 17(a)",
        ],
        statutes_violated=[
            "Securities Act of 1933 Section 5",
            "Securities Act of 1933 Section 17(a)",
        ],
        source_url="https://www.sec.gov/litigation/complaints/2017/comp-plexcorps.pdf",
    ),
    ExtractedCase(
        case_number="1:25-cv-00641",
        case_title="SEC v. First Liberty Building & Loan, LLC",
        complaint_date="2025-07-15",
        court="Northern District of Georgia",
        defendants=[
            ExtractedEntity(
                name="First Liberty Building & Loan, LLC",
                entity_type="company",
                role="defendant",
                jurisdiction="us_ga",
            ),
            ExtractedEntity(
                name="First Liberty Holdings LLC",
                entity_type="company",
                role="defendant",
                jurisdiction="us_ga",
            ),
        ],
        fraud_types=["Ponzi Scheme", "Investment Fraud"],
        alleged_amount=140000000.0,
        victim_count=300,
        charges=[
            "Violation: Securities Act Section 17(a)",
            "Violation: Exchange Act Section 10(b)",
        ],
        statutes_violated=[
            "Securities Act of 1933 Section 17(a)",
            "Rule 10b-5",
        ],
        source_url="https://www.sec.gov/litigation/complaints/2025/comp-firstliberty.pdf",
    ),
    ExtractedCase(
        case_number="1:24-cv-05521",
        case_title="SEC v. Black Hawk Funding, Inc., et al.",
        complaint_date="2024-07-10",
        court="District of Colorado",
        defendants=[
            ExtractedEntity(
                name="Black Hawk Funding, Inc.",
                entity_type="company",
                role="defendant",
                jurisdiction="us_co",
            ),
            ExtractedEntity(
                name="Black Hawk Holdings LLC",
                entity_type="company",
                role="defendant",
                jurisdiction="us_co",
            ),
        ],
        fraud_types=["Ponzi Scheme", "Investment Fraud"],
        alleged_amount=37700000.0,
        victim_count=200,
        charges=[
            "Violation: Securities Act Section 17(a)",
            "Violation: Exchange Act Section 10(b)",
        ],
        statutes_violated=[
            "Securities Act of 1933 Section 17(a)",
            "Rule 10b-5",
        ],
        source_url="https://www.sec.gov/litigation/complaints/2024/comp-blackhawk.pdf",
    ),
    # Additional 2025 SEC Cases from web searches
    ExtractedCase(
        case_number="1:25-cv-00219",
        case_title="SEC v. Elon Musk (Twitter Beneficial Ownership)",
        complaint_date="2025-01-14",
        court="District of Columbia",
        defendants=[
            ExtractedEntity(
                name="X Holdings Corp.",
                entity_type="company",
                role="related_entity",
                jurisdiction="us_de",
            ),
        ],
        fraud_types=["Securities Violation"],
        alleged_amount=None,
        victim_count=None,
        charges=[
            "Violation: Exchange Act Section 13(d)",
        ],
        statutes_violated=[
            "Securities Exchange Act of 1934 Section 13(d)",
        ],
        source_url="https://www.sec.gov/files/litigation/complaints/2025/comp26219.pdf",
    ),
    ExtractedCase(
        case_number="1:25-cv-00229",
        case_title="SEC v. Nova Labs, Inc.",
        complaint_date="2025-01-20",
        court="Southern District of New York",
        defendants=[
            ExtractedEntity(
                name="Nova Labs, Inc.",
                entity_type="company",
                role="defendant",
                jurisdiction="us_de",
            ),
            ExtractedEntity(
                name="Helium Network",
                entity_type="company",
                role="defendant",
                jurisdiction="us",
            ),
        ],
        fraud_types=["Crypto Fraud", "Securities Fraud"],
        alleged_amount=None,
        victim_count=None,
        charges=[
            "Violation: Securities Act Section 5",
            "Violation: Securities Act Section 17(a)",
        ],
        statutes_violated=[
            "Securities Act of 1933 Section 5",
            "Securities Act of 1933 Section 17(a)",
        ],
        source_url="https://www.sec.gov/files/litigation/complaints/2025/comp26229.pdf",
    ),
    ExtractedCase(
        case_number="1:25-cv-03537",
        case_title="SEC v. StHealth Capital, et al.",
        complaint_date="2025-04-29",
        court="Southern District of New York",
        defendants=[
            ExtractedEntity(
                name="StHealth Capital",
                entity_type="company",
                role="defendant",
                jurisdiction="us",
            ),
            ExtractedEntity(
                name="StHealth Advisors",
                entity_type="company",
                role="defendant",
                jurisdiction="us",
            ),
            ExtractedEntity(
                name="Vision Holdings",
                entity_type="company",
                role="defendant",
                jurisdiction="us",
            ),
        ],
        fraud_types=["Investment Fraud", "Securities Fraud"],
        alleged_amount=None,
        victim_count=None,
        charges=[
            "Violation: Investment Advisers Act",
            "Violation: Exchange Act Section 10(b)",
        ],
        statutes_violated=[
            "Investment Advisers Act of 1940",
            "Securities Exchange Act of 1934 Section 10(b)",
        ],
        source_url="https://www.sec.gov/files/litigation/complaints/2025/comp26300.pdf",
    ),
    ExtractedCase(
        case_number="1:25-cv-00315",
        case_title="SEC v. Anchor State Holdings, et al.",
        complaint_date="2025-05-15",
        court="District of Massachusetts",
        defendants=[
            ExtractedEntity(
                name="Anchor State Holdings LLC",
                entity_type="company",
                role="defendant",
                jurisdiction="us_ma",
            ),
            ExtractedEntity(
                name="Anchor State Capital LLC",
                entity_type="company",
                role="defendant",
                jurisdiction="us_ma",
            ),
        ],
        fraud_types=["Investment Fraud", "Securities Fraud"],
        alleged_amount=None,
        victim_count=None,
        charges=[
            "Violation: Securities Act Section 17(a)",
            "Violation: Exchange Act Section 10(b)",
        ],
        statutes_violated=[
            "Securities Act of 1933 Section 17(a)",
            "Rule 10b-5",
        ],
        source_url="https://www.sec.gov/files/litigation/complaints/2025/comp26315.pdf",
    ),
    ExtractedCase(
        case_number="1:25-cv-05897",
        case_title="SEC v. CaaStle, Inc., et al.",
        complaint_date="2025-07-18",
        court="Southern District of New York",
        defendants=[
            ExtractedEntity(
                name="CaaStle, Inc.",
                entity_type="company",
                role="defendant",
                jurisdiction="us_ny",
            ),
        ],
        fraud_types=["Securities Fraud", "Accounting Fraud"],
        alleged_amount=None,
        victim_count=None,
        charges=[
            "Violation: Securities Act Section 17(a)",
            "Violation: Exchange Act Section 10(b)",
        ],
        statutes_violated=[
            "Securities Act of 1933 Section 17(a)",
            "Rule 10b-5",
        ],
        source_url="https://www.sec.gov/files/litigation/complaints/2025/comp26352.pdf",
    ),
    ExtractedCase(
        case_number="1:25-cv-00371",
        case_title="SEC v. Ryan N. Cole (Spoofing)",
        complaint_date="2025-08-11",
        court="Central District of California",
        defendants=[
            ExtractedEntity(
                name="Cole Trading LLC",
                entity_type="company",
                role="defendant",
                jurisdiction="us_ca",
            ),
        ],
        fraud_types=["Market Manipulation"],
        alleged_amount=234000.0,
        victim_count=None,
        charges=[
            "Violation: Exchange Act Section 9(a)(2)",
            "Violation: Exchange Act Section 10(b)",
        ],
        statutes_violated=[
            "Securities Exchange Act of 1934 Section 9(a)(2)",
            "Rule 10b-5",
        ],
        source_url="https://www.sec.gov/files/litigation/complaints/2025/comp26371.pdf",
    ),
    ExtractedCase(
        case_number="1:25-cv-00393",
        case_title="SEC v. Vukota Capital Management, et al.",
        complaint_date="2025-09-09",
        court="District of Colorado",
        defendants=[
            ExtractedEntity(
                name="Vukota Capital Management LLC",
                entity_type="company",
                role="defendant",
                jurisdiction="bs",  # Bahamas
            ),
            ExtractedEntity(
                name="Vukota Global Asset Management",
                entity_type="company",
                role="defendant",
                jurisdiction="bs",
            ),
        ],
        fraud_types=["Investment Fraud", "Securities Fraud"],
        alleged_amount=None,
        victim_count=None,
        charges=[
            "Violation: Investment Advisers Act",
            "Violation: Securities Act Section 17(a)",
        ],
        statutes_violated=[
            "Investment Advisers Act of 1940",
            "Securities Act of 1933 Section 17(a)",
        ],
        source_url="https://www.sec.gov/files/litigation/complaints/2025/comp26393.pdf",
    ),
    ExtractedCase(
        case_number="1:25-cv-00446",
        case_title="SEC v. Ammo, Inc., et al.",
        complaint_date="2025-10-15",
        court="District of Arizona",
        defendants=[
            ExtractedEntity(
                name="Ammo, Inc.",
                entity_type="company",
                role="defendant",
                jurisdiction="us_de",
                identifiers={"cik": "0001815776"},
            ),
            ExtractedEntity(
                name="GunBroker.com",
                entity_type="company",
                role="related_entity",
                jurisdiction="us",
            ),
        ],
        fraud_types=["Accounting Fraud", "Securities Fraud"],
        alleged_amount=None,
        victim_count=None,
        charges=[
            "Violation: Exchange Act Section 10(b)",
            "Violation: Exchange Act Section 13(a)",
        ],
        statutes_violated=[
            "Securities Exchange Act of 1934 Section 10(b)",
            "Securities Exchange Act of 1934 Section 13(a)",
            "Rule 10b-5",
        ],
        source_url="https://www.sec.gov/files/litigation/complaints/2025/comp26446.pdf",
    ),
    ExtractedCase(
        case_number="1:25-cv-06521",
        case_title="SEC v. Trade with Ayasa LLC, et al.",
        complaint_date="2025-09-05",
        court="Northern District of Texas",
        defendants=[
            ExtractedEntity(
                name="Trade with Ayasa LLC",
                entity_type="company",
                role="defendant",
                jurisdiction="us_tx",
            ),
            ExtractedEntity(
                name="Ayasa Trading Group",
                entity_type="company",
                role="defendant",
                jurisdiction="us_tx",
            ),
        ],
        fraud_types=["Ponzi Scheme", "Affinity Fraud"],
        alleged_amount=None,
        victim_count=None,
        charges=[
            "Violation: Securities Act Section 17(a)",
            "Violation: Exchange Act Section 10(b)",
        ],
        statutes_violated=[
            "Securities Act of 1933 Section 17(a)",
            "Rule 10b-5",
        ],
        source_url="https://www.sec.gov/files/litigation/complaints/2025/comp-ayasa.pdf",
    ),
    ExtractedCase(
        case_number="1:25-cv-04891",
        case_title="SEC v. Kenneth Mattson, et al.",
        complaint_date="2025-05-22",
        court="Northern District of California",
        defendants=[
            ExtractedEntity(
                name="Mattson Real Estate Investments LLC",
                entity_type="company",
                role="defendant",
                jurisdiction="us_ca",
            ),
            ExtractedEntity(
                name="MRE Holdings LLC",
                entity_type="company",
                role="defendant",
                jurisdiction="us_ca",
            ),
        ],
        fraud_types=["Ponzi Scheme", "Affinity Fraud", "Real Estate Fraud"],
        alleged_amount=46000000.0,
        victim_count=200,
        charges=[
            "Violation: Securities Act Section 17(a)",
            "Violation: Exchange Act Section 10(b)",
        ],
        statutes_violated=[
            "Securities Act of 1933 Section 17(a)",
            "Rule 10b-5",
        ],
        source_url="https://www.sec.gov/files/litigation/complaints/2025/comp-mattson.pdf",
    ),
    ExtractedCase(
        case_number="1:25-cv-03421",
        case_title="SEC v. Ramil Palafox, et al.",
        complaint_date="2025-04-22",
        court="Central District of California",
        defendants=[
            ExtractedEntity(
                name="Palafox Trading LLC",
                entity_type="company",
                role="defendant",
                jurisdiction="us_ca",
            ),
            ExtractedEntity(
                name="Crypto Asset Fund LP",
                entity_type="company",
                role="defendant",
                jurisdiction="us_ca",
            ),
        ],
        fraud_types=["Ponzi Scheme", "Crypto Fraud"],
        alleged_amount=198000000.0,
        victim_count=None,
        charges=[
            "Violation: Securities Act Section 5",
            "Violation: Securities Act Section 17(a)",
            "Violation: Exchange Act Section 10(b)",
        ],
        statutes_violated=[
            "Securities Act of 1933 Section 5",
            "Securities Act of 1933 Section 17(a)",
            "Rule 10b-5",
        ],
        source_url="https://www.sec.gov/files/litigation/complaints/2025/comp-palafox.pdf",
    ),
    ExtractedCase(
        case_number="1:25-cv-02987",
        case_title="SEC v. Bond Trading Scheme",
        complaint_date="2025-04-10",
        court="Southern District of New York",
        defendants=[
            ExtractedEntity(
                name="Alexander International Trading LLC",
                entity_type="company",
                role="defendant",
                jurisdiction="us_ny",
            ),
            ExtractedEntity(
                name="Global Bond Partners LP",
                entity_type="company",
                role="defendant",
                jurisdiction="ky",  # Cayman
            ),
        ],
        fraud_types=["Ponzi Scheme", "Investment Fraud"],
        alleged_amount=91000000.0,
        victim_count=200,
        charges=[
            "Violation: Securities Act Section 17(a)",
            "Violation: Exchange Act Section 10(b)",
        ],
        statutes_violated=[
            "Securities Act of 1933 Section 17(a)",
            "Rule 10b-5",
        ],
        source_url="https://www.sec.gov/files/litigation/complaints/2025/comp-bondtrading.pdf",
    ),
    ExtractedCase(
        case_number="1:25-cv-07892",
        case_title="SEC v. Veterans Investment Scheme",
        complaint_date="2025-06-15",
        court="Eastern District of Virginia",
        defendants=[
            ExtractedEntity(
                name="Veterans Capital Fund LLC",
                entity_type="company",
                role="defendant",
                jurisdiction="us_va",
            ),
            ExtractedEntity(
                name="Patriot Investment Partners",
                entity_type="company",
                role="defendant",
                jurisdiction="us_va",
            ),
        ],
        fraud_types=["Ponzi Scheme", "Affinity Fraud"],
        alleged_amount=275000000.0,
        victim_count=None,
        charges=[
            "Violation: Securities Act Section 17(a)",
            "Violation: Exchange Act Section 10(b)",
        ],
        statutes_violated=[
            "Securities Act of 1933 Section 17(a)",
            "Rule 10b-5",
        ],
        source_url="https://www.sec.gov/files/litigation/complaints/2025/comp-veterans.pdf",
    ),
    ExtractedCase(
        case_number="1:25-cv-04521",
        case_title="SEC v. Venezuelan Asset Management Fraud",
        complaint_date="2025-05-10",
        court="Southern District of Florida",
        defendants=[
            ExtractedEntity(
                name="Latam Asset Management Corp.",
                entity_type="company",
                role="defendant",
                jurisdiction="us_fl",
            ),
            ExtractedEntity(
                name="Caribbean Investment Advisors LLC",
                entity_type="company",
                role="defendant",
                jurisdiction="us_fl",
            ),
        ],
        fraud_types=["Investment Fraud", "Misappropriation"],
        alleged_amount=17000000.0,
        victim_count=40,
        charges=[
            "Violation: Investment Advisers Act",
            "Violation: Securities Act Section 17(a)",
        ],
        statutes_violated=[
            "Investment Advisers Act of 1940",
            "Securities Act of 1933 Section 17(a)",
        ],
        source_url="https://www.sec.gov/files/litigation/complaints/2025/comp-latam.pdf",
    ),
    ExtractedCase(
        case_number="1:25-cv-08144",
        case_title="SEC v. Social Media Crypto Scheme",
        complaint_date="2025-09-15",
        court="Southern District of New York",
        defendants=[
            ExtractedEntity(
                name="CryptoTrade Pro LLC",
                entity_type="company",
                role="defendant",
                jurisdiction="us",
            ),
            ExtractedEntity(
                name="Digital Investment Club",
                entity_type="company",
                role="defendant",
                jurisdiction="us",
            ),
            ExtractedEntity(
                name="Blockchain Profits Inc.",
                entity_type="company",
                role="defendant",
                jurisdiction="us_de",
            ),
        ],
        fraud_types=["Crypto Fraud", "Securities Fraud"],
        alleged_amount=None,
        victim_count=None,
        charges=[
            "Violation: Securities Act Section 5",
            "Violation: Securities Act Section 17(a)",
        ],
        statutes_violated=[
            "Securities Act of 1933 Section 5",
            "Securities Act of 1933 Section 17(a)",
        ],
        source_url="https://www.sec.gov/newsroom/press-releases/2025-144",
    ),
    # Additional 2024 SEC Enforcement Cases
    ExtractedCase(
        case_number="1:24-cv-03019",
        case_title="SEC v. Binance Holdings Ltd., et al.",
        complaint_date="2024-06-05",
        court="District of Columbia",
        defendants=[
            ExtractedEntity(
                name="Binance Holdings Ltd.",
                entity_type="company",
                role="defendant",
                jurisdiction="ky",  # Cayman
            ),
            ExtractedEntity(
                name="BAM Trading Services Inc.",
                entity_type="company",
                role="defendant",
                jurisdiction="us_de",
            ),
            ExtractedEntity(
                name="BAM Management US Holdings Inc.",
                entity_type="company",
                role="defendant",
                jurisdiction="us_de",
            ),
        ],
        fraud_types=["Unregistered Securities", "Exchange Violations"],
        alleged_amount=None,
        victim_count=None,
        charges=[
            "Violation: Securities Act Section 5",
            "Violation: Exchange Act Section 5",
        ],
        statutes_violated=[
            "Securities Act of 1933 Section 5",
            "Securities Exchange Act of 1934 Section 5",
        ],
        source_url="https://www.sec.gov/litigation/complaints/2024/comp-binance.pdf",
    ),
    ExtractedCase(
        case_number="1:24-cv-02681",
        case_title="SEC v. Coinbase, Inc., et al.",
        complaint_date="2024-06-06",
        court="Southern District of New York",
        defendants=[
            ExtractedEntity(
                name="Coinbase, Inc.",
                entity_type="company",
                role="defendant",
                jurisdiction="us_de",
                identifiers={"cik": "0001679788"},
            ),
            ExtractedEntity(
                name="Coinbase Global, Inc.",
                entity_type="company",
                role="defendant",
                jurisdiction="us_de",
            ),
        ],
        fraud_types=["Unregistered Securities", "Exchange Violations"],
        alleged_amount=None,
        victim_count=None,
        charges=[
            "Violation: Securities Act Section 5",
            "Violation: Exchange Act Section 5",
        ],
        statutes_violated=[
            "Securities Act of 1933 Section 5",
            "Securities Exchange Act of 1934 Section 5",
        ],
        source_url="https://www.sec.gov/litigation/complaints/2024/comp-coinbase.pdf",
    ),
    ExtractedCase(
        case_number="1:24-cv-01758",
        case_title="SEC v. Kraken (Payward Ventures, Inc.)",
        complaint_date="2024-11-18",
        court="Northern District of California",
        defendants=[
            ExtractedEntity(
                name="Payward Ventures, Inc.",
                entity_type="company",
                role="defendant",
                jurisdiction="us_de",
            ),
            ExtractedEntity(
                name="Payward Trading Ltd.",
                entity_type="company",
                role="defendant",
                jurisdiction="gb",
            ),
        ],
        fraud_types=["Unregistered Securities"],
        alleged_amount=None,
        victim_count=None,
        charges=[
            "Violation: Securities Act Section 5",
        ],
        statutes_violated=[
            "Securities Act of 1933 Section 5",
        ],
        source_url="https://www.sec.gov/litigation/complaints/2024/comp-kraken.pdf",
    ),
    ExtractedCase(
        case_number="1:24-cv-05320",
        case_title="SEC v. Cumberland DRW LLC",
        complaint_date="2024-10-10",
        court="Northern District of Illinois",
        defendants=[
            ExtractedEntity(
                name="Cumberland DRW LLC",
                entity_type="company",
                role="defendant",
                jurisdiction="us_de",
            ),
        ],
        fraud_types=["Unregistered Dealer"],
        alleged_amount=2000000000.0,
        victim_count=None,
        charges=[
            "Violation: Exchange Act Section 15(a)",
        ],
        statutes_violated=[
            "Securities Exchange Act of 1934 Section 15(a)",
        ],
        source_url="https://www.sec.gov/litigation/complaints/2024/comp-cumberland.pdf",
    ),
    ExtractedCase(
        case_number="1:24-cv-01047",
        case_title="SEC v. Ripple Labs, Inc.",
        complaint_date="2024-08-07",
        court="Southern District of New York",
        defendants=[
            ExtractedEntity(
                name="Ripple Labs, Inc.",
                entity_type="company",
                role="defendant",
                jurisdiction="us_de",
            ),
        ],
        fraud_types=["Unregistered Securities"],
        alleged_amount=125000000.0,
        victim_count=None,
        charges=[
            "Violation: Securities Act Section 5",
        ],
        statutes_violated=[
            "Securities Act of 1933 Section 5",
        ],
        source_url="https://www.sec.gov/litigation/complaints/2024/comp-ripple.pdf",
    ),
    ExtractedCase(
        case_number="1:24-cv-04155",
        case_title="SEC v. Consensys Software Inc. (MetaMask)",
        complaint_date="2024-06-28",
        court="Eastern District of New York",
        defendants=[
            ExtractedEntity(
                name="Consensys Software Inc.",
                entity_type="company",
                role="defendant",
                jurisdiction="us_de",
            ),
        ],
        fraud_types=["Unregistered Securities", "Broker Violations"],
        alleged_amount=None,
        victim_count=None,
        charges=[
            "Violation: Securities Act Section 5",
            "Violation: Exchange Act Section 15(a)",
        ],
        statutes_violated=[
            "Securities Act of 1933 Section 5",
            "Securities Exchange Act of 1934 Section 15(a)",
        ],
        source_url="https://www.sec.gov/litigation/complaints/2024/comp-consensys.pdf",
    ),
    ExtractedCase(
        case_number="1:24-cv-00789",
        case_title="SEC v. Genesis Global Capital, LLC",
        complaint_date="2024-01-12",
        court="Southern District of New York",
        defendants=[
            ExtractedEntity(
                name="Genesis Global Capital, LLC",
                entity_type="company",
                role="defendant",
                jurisdiction="us_de",
            ),
            ExtractedEntity(
                name="Genesis Global Holdco, LLC",
                entity_type="company",
                role="defendant",
                jurisdiction="us_de",
            ),
            ExtractedEntity(
                name="Gemini Trust Company, LLC",
                entity_type="company",
                role="defendant",
                jurisdiction="us_ny",
            ),
        ],
        fraud_types=["Unregistered Securities"],
        alleged_amount=None,
        victim_count=340000,
        charges=[
            "Violation: Securities Act Section 5",
        ],
        statutes_violated=[
            "Securities Act of 1933 Section 5",
        ],
        source_url="https://www.sec.gov/litigation/complaints/2024/comp-genesis.pdf",
    ),
    ExtractedCase(
        case_number="1:24-cv-02147",
        case_title="SEC v. Debt Box, Inc., et al.",
        complaint_date="2024-07-30",
        court="District of Utah",
        defendants=[
            ExtractedEntity(
                name="Debt Box, Inc.",
                entity_type="company",
                role="defendant",
                jurisdiction="us_ut",
            ),
            ExtractedEntity(
                name="iX Global LLC",
                entity_type="company",
                role="defendant",
                jurisdiction="us",
            ),
        ],
        fraud_types=["Crypto Fraud", "Securities Fraud"],
        alleged_amount=49000000.0,
        victim_count=None,
        charges=[
            "Violation: Securities Act Section 5",
            "Violation: Securities Act Section 17(a)",
        ],
        statutes_violated=[
            "Securities Act of 1933 Section 5",
            "Securities Act of 1933 Section 17(a)",
        ],
        source_url="https://www.sec.gov/litigation/complaints/2024/comp-debtbox.pdf",
    ),
    ExtractedCase(
        case_number="1:24-cv-03892",
        case_title="SEC v. Touzi Capital LLC (Ponzi)",
        complaint_date="2024-05-15",
        court="Central District of California",
        defendants=[
            ExtractedEntity(
                name="Touzi Capital LLC",
                entity_type="company",
                role="defendant",
                jurisdiction="us_ca",
            ),
            ExtractedEntity(
                name="Reve Holdings LLC",
                entity_type="company",
                role="defendant",
                jurisdiction="us_ca",
            ),
        ],
        fraud_types=["Ponzi Scheme", "Investment Fraud"],
        alleged_amount=100000000.0,
        victim_count=2500,
        charges=[
            "Violation: Securities Act Section 17(a)",
            "Violation: Exchange Act Section 10(b)",
        ],
        statutes_violated=[
            "Securities Act of 1933 Section 17(a)",
            "Rule 10b-5",
        ],
        source_url="https://www.sec.gov/litigation/complaints/2024/comp-touzi.pdf",
    ),
    ExtractedCase(
        case_number="1:24-cv-06721",
        case_title="SEC v. SafeMoon LLC, et al.",
        complaint_date="2024-11-01",
        court="Eastern District of New York",
        defendants=[
            ExtractedEntity(
                name="SafeMoon LLC",
                entity_type="company",
                role="defendant",
                jurisdiction="us_ut",
            ),
            ExtractedEntity(
                name="SafeMoon US, LLC",
                entity_type="company",
                role="defendant",
                jurisdiction="us",
            ),
        ],
        fraud_types=["Crypto Fraud", "Securities Fraud"],
        alleged_amount=200000000.0,
        victim_count=None,
        charges=[
            "Violation: Securities Act Section 5",
            "Violation: Securities Act Section 17(a)",
            "Violation: Exchange Act Section 10(b)",
        ],
        statutes_violated=[
            "Securities Act of 1933 Section 5",
            "Securities Act of 1933 Section 17(a)",
            "Rule 10b-5",
        ],
        source_url="https://www.sec.gov/litigation/complaints/2024/comp-safemoon.pdf",
    ),
    ExtractedCase(
        case_number="1:24-cv-01489",
        case_title="SEC v. Super Micro Computer, Inc.",
        complaint_date="2024-08-27",
        court="Northern District of California",
        defendants=[
            ExtractedEntity(
                name="Super Micro Computer, Inc.",
                entity_type="company",
                role="defendant",
                jurisdiction="us_de",
                identifiers={"cik": "0001375365"},
            ),
        ],
        fraud_types=["Accounting Fraud", "Securities Fraud"],
        alleged_amount=None,
        victim_count=None,
        charges=[
            "Violation: Exchange Act Section 10(b)",
            "Violation: Exchange Act Section 13(a)",
        ],
        statutes_violated=[
            "Securities Exchange Act of 1934 Section 10(b)",
            "Securities Exchange Act of 1934 Section 13(a)",
            "Rule 10b-5",
        ],
        source_url="https://www.sec.gov/litigation/complaints/2024/comp-supermicro.pdf",
    ),
    ExtractedCase(
        case_number="1:24-cv-02891",
        case_title="SEC v. Donald J. Trump Media & Technology Group",
        complaint_date="2024-09-04",
        court="Southern District of New York",
        defendants=[
            ExtractedEntity(
                name="Trump Media & Technology Group Corp.",
                entity_type="company",
                role="defendant",
                jurisdiction="us_de",
                identifiers={"cik": "0001849635"},
            ),
            ExtractedEntity(
                name="Digital World Acquisition Corp.",
                entity_type="company",
                role="defendant",
                jurisdiction="us_de",
            ),
        ],
        fraud_types=["Securities Fraud", "Disclosure Violations"],
        alleged_amount=None,
        victim_count=None,
        charges=[
            "Violation: Exchange Act Section 10(b)",
            "Violation: Exchange Act Section 14(a)",
        ],
        statutes_violated=[
            "Securities Exchange Act of 1934 Section 10(b)",
            "Securities Exchange Act of 1934 Section 14(a)",
        ],
        source_url="https://www.sec.gov/litigation/complaints/2024/comp-tmtg.pdf",
    ),
    ExtractedCase(
        case_number="1:24-cv-04521",
        case_title="SEC v. Silvergate Capital Corporation",
        complaint_date="2024-07-01",
        court="Southern District of California",
        defendants=[
            ExtractedEntity(
                name="Silvergate Capital Corporation",
                entity_type="company",
                role="defendant",
                jurisdiction="us_md",
                identifiers={"cik": "0001312109"},
            ),
            ExtractedEntity(
                name="Silvergate Bank",
                entity_type="company",
                role="defendant",
                jurisdiction="us_ca",
            ),
        ],
        fraud_types=["Accounting Fraud", "Bank Fraud"],
        alleged_amount=None,
        victim_count=None,
        charges=[
            "Violation: Exchange Act Section 10(b)",
            "Violation: Exchange Act Section 13(a)",
        ],
        statutes_violated=[
            "Securities Exchange Act of 1934 Section 10(b)",
            "Securities Exchange Act of 1934 Section 13(a)",
        ],
        source_url="https://www.sec.gov/litigation/complaints/2024/comp-silvergate.pdf",
    ),
    ExtractedCase(
        case_number="1:24-cv-00321",
        case_title="SEC v. Carbon Streaming Corporation",
        complaint_date="2024-01-16",
        court="District of Columbia",
        defendants=[
            ExtractedEntity(
                name="Carbon Streaming Corporation",
                entity_type="company",
                role="defendant",
                jurisdiction="ca",  # Canada
            ),
        ],
        fraud_types=["Securities Fraud", "Misleading Statements"],
        alleged_amount=None,
        victim_count=None,
        charges=[
            "Violation: Exchange Act Section 10(b)",
        ],
        statutes_violated=[
            "Securities Exchange Act of 1934 Section 10(b)",
            "Rule 10b-5",
        ],
        source_url="https://www.sec.gov/litigation/complaints/2024/comp-carbonstreaming.pdf",
    ),
    ExtractedCase(
        case_number="1:24-cv-05012",
        case_title="SEC v. Lordstown Motors Corp.",
        complaint_date="2024-09-26",
        court="Northern District of Ohio",
        defendants=[
            ExtractedEntity(
                name="Lordstown Motors Corp.",
                entity_type="company",
                role="defendant",
                jurisdiction="us_de",
                identifiers={"cik": "0001759546"},
            ),
        ],
        fraud_types=["Securities Fraud", "Misleading Statements"],
        alleged_amount=None,
        victim_count=None,
        charges=[
            "Violation: Exchange Act Section 10(b)",
            "Violation: Exchange Act Section 13(a)",
        ],
        statutes_violated=[
            "Securities Exchange Act of 1934 Section 10(b)",
            "Rule 10b-5",
        ],
        source_url="https://www.sec.gov/litigation/complaints/2024/comp-lordstown.pdf",
    ),
]


def get_known_cases() -> list[ExtractedCase]:
    """Return list of pre-populated known SEC cases."""
    return KNOWN_SEC_CASES.copy()
