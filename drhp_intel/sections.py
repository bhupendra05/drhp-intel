"""
Section detection and content extraction from DRHP text.
Works on plain strings — no PDF dependency, fully testable.
"""
from __future__ import annotations
import re
from typing import List, Optional, Tuple, Dict
from .models import (
    FinancialYear, ObjectsOfIssue, RiskFactor,
    RelatedPartyTransaction, PromoterInfo,
)

# Section header patterns (SEBI ICDR mandates these sections by name)
_SECTION_PATTERNS = {
    "objects": [
        r"OBJECTS\s+OF\s+THE\s+(ISSUE|OFFER|IPO)",
        r"USE\s+OF\s+(ISSUE\s+)?PROCEEDS",
    ],
    "financials": [
        r"RESTATED\s+(CONSOLIDATED\s+)?FINANCIAL\s+(STATEMENTS?|INFORMATION|SUMMARY)",
        r"SUMMARY\s+OF\s+FINANCIAL\s+INFORMATION",
        r"FINANCIAL\s+HIGHLIGHTS",
    ],
    "risk_factors": [
        r"RISK\s+FACTORS",
        r"RISKS?\s+ASSOCIATED\s+WITH",
    ],
    "rpt": [
        r"RELATED\s+PARTY\s+TRANSACTIONS?",
        r"RPT\s+DISCLOSURES?",
    ],
    "promoters": [
        r"OUR\s+PROMOTERS?\s+AND\s+PROMOTER\s+GROUP",
        r"DETAILS\s+OF\s+OUR\s+PROMOTERS?",
        r"PROMOTERS?\s+AND\s+PROMOTER\s+GROUP",
    ],
    "peers": [
        r"COMPARISON\s+OF\s+ACCOUNTING\s+RATIOS",
        r"PEER\s+COMPARISON",
        r"INDUSTRY\s+PEER",
    ],
}

# Indian number system: parse "₹1,234.56 crore" / "Rs. 1234.56 crore" / "INR 1,234 Crores"
_INR_PATTERN = re.compile(
    r"(?:₹|Rs\.?|INR)\s*"
    r"([\d,]+(?:\.\d+)?)"
    r"\s*(crore|cr\.?|lakh|million|billion)?",
    re.IGNORECASE,
)
_PLAIN_CRORE = re.compile(
    r"([\d,]+(?:\.\d+)?)\s+(?:crore|cr\.?)\b",
    re.IGNORECASE,
)


def _parse_indian_number(text: str) -> Optional[float]:
    """Parse Indian number strings to float (returns value in Crores)."""
    m = _INR_PATTERN.search(text)
    if m:
        val = float(m.group(1).replace(",", ""))
        unit = (m.group(2) or "crore").lower().strip(".")
    else:
        m = _PLAIN_CRORE.search(text)
        if not m:
            return None
        val = float(m.group(1).replace(",", ""))
        unit = "crore"
    if "lakh" in unit:
        val = val / 100.0
    elif "million" in unit:
        val = val / 10.0   # 1 million = 0.1 crore approx (×10M = 1Cr)
    elif "billion" in unit:
        val = val * 100.0  # 1 billion = 100 crore
    return round(val, 2)


def _find_section(text: str, section_key: str, next_section_offset: int = 8000) -> str:
    """Return the first `next_section_offset` chars of the named section."""
    patterns = _SECTION_PATTERNS.get(section_key, [])
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            start = m.start()
            return text[start: start + next_section_offset]
    return ""


def extract_company_name(text: str) -> str:
    """Try to extract company name from DRHP header."""
    patterns = [
        r"(?:Draft\s+Red\s+Herring\s+Prospectus|Red\s+Herring\s+Prospectus|Prospectus)\s+of\s+([A-Z][A-Za-z\s]+(?:Limited|Ltd\.?|LLP))",
        r"([A-Z][A-Z\s]+(?:LIMITED|LTD\.?))\s+(?:CIN|Corporate\s+Identity)",
        r"(?:Company|Issuer)\s+Name\s*[:\-]\s*([A-Z][A-Za-z\s]+(?:Limited|Ltd\.?))",
    ]
    for pat in patterns:
        m = re.search(pat, text[:5000], re.IGNORECASE)
        if m:
            return m.group(1).strip()
    # fallback: first line with "Limited"
    for line in text[:3000].splitlines():
        if re.search(r'\b(limited|ltd\.?)\b', line, re.IGNORECASE) and len(line) < 100:
            return line.strip()
    return "Unknown Company"


def extract_issue_type(text: str) -> str:
    header = text[:2000].upper()
    if "DRAFT RED HERRING PROSPECTUS" in header:
        return "IPO (DRHP)"
    if "RED HERRING PROSPECTUS" in header:
        return "IPO (RHP)"
    if "FURTHER PUBLIC OFFER" in header or "FPO" in header:
        return "FPO"
    if "RIGHTS ISSUE" in header:
        return "Rights Issue"
    return "IPO"


def extract_lead_managers(text: str) -> List[str]:
    """Extract Book Running Lead Managers."""
    m = re.search(
        r"(?:BOOK\s+RUNNING\s+LEAD\s+MANAGER|BRLM)[S]?\s*[:\-]?\s*(.*?)(?:\n\n|\f|REGISTRAR)",
        text[:8000], re.IGNORECASE | re.DOTALL,
    )
    if not m:
        return []
    block = m.group(1)
    # Each manager typically on its own line or separated by commas
    names = re.findall(r"([A-Z][A-Za-z\s&]+(?:Securities|Capital|Bank|Finance|Advisors?|Partners)[A-Za-z\s.]*)", block)
    return [n.strip() for n in names[:5] if len(n.strip()) > 5]


def extract_objects(text: str) -> ObjectsOfIssue:
    section = _find_section(text, "objects", 6000)
    obj = ObjectsOfIssue(raw_text=section[:500])

    # Total issue size
    total_m = re.search(r"(?:total\s+)?(?:issue|offer)\s+size[^₹\d]*(?:₹|Rs\.?|INR)?\s*([\d,]+(?:\.\d+)?)\s*(?:crore|cr)", section, re.IGNORECASE)
    if total_m:
        obj.total_issue_size = float(total_m.group(1).replace(",", ""))

    # Fresh issue vs OFS
    fresh_m = re.search(r"fresh\s+issue[^₹\d]*(?:₹|Rs\.?|INR)?\s*([\d,]+(?:\.\d+)?)\s*(?:crore|cr)", section, re.IGNORECASE)
    if fresh_m:
        obj.fresh_issue = float(fresh_m.group(1).replace(",", ""))

    ofs_m = re.search(r"offer\s+for\s+sale[^₹\d]*(?:₹|Rs\.?|INR)?\s*([\d,]+(?:\.\d+)?)\s*(?:crore|cr)", section, re.IGNORECASE)
    if ofs_m:
        obj.ofs_size = float(ofs_m.group(1).replace(",", ""))

    # Objects (use of proceeds)
    uses = re.findall(r"(?:•|\*|\d+[\.\)])\s+([A-Z][^\n]{10,120})", section)
    obj.uses = [u.strip() for u in uses[:8]]

    return obj


def extract_financials(text: str) -> List[FinancialYear]:
    """
    Extract 3-year restated financial summary.
    Looks for Revenue/Income, EBITDA/Operating Profit, PAT rows.
    """
    section = _find_section(text, "financials", 12000)
    if not section:
        section = text  # fallback: search whole document

    years: Dict[str, FinancialYear] = {}

    # Find fiscal year columns: "FY2023", "FY 2023", "2022-23", "March 31, 2023"
    fy_pattern = re.compile(
        r"(?:FY\s?|fiscal\s+year\s+)?(?:20(\d{2})-(\d{2})|(?:March|Mar)\.?\s+31[,\s]+20(\d{2})|FY\s*(20\d{2}))",
        re.IGNORECASE,
    )
    for m in fy_pattern.finditer(section):
        if m.group(4):
            label = f"FY{m.group(4)}"
        elif m.group(3):
            label = f"FY20{m.group(3)}"
        else:
            label = f"FY20{m.group(2)}"
        if label not in years:
            years[label] = FinancialYear(year=label)

    if not years:
        # No year headers found — create stubs
        for y in ["FY2023", "FY2022", "FY2021"]:
            years[y] = FinancialYear(year=y)

    sorted_years = sorted(years.keys())

    # Extract Revenue
    rev_m = re.search(
        r"(?:total\s+)?(?:revenue|income\s+from\s+operations?|net\s+revenue)[^\n]*\n((?:[^\n]+\n){1,3})",
        section, re.IGNORECASE,
    )
    if rev_m:
        nums = re.findall(r"([\d,]+(?:\.\d+)?)", rev_m.group(1))
        nums = [float(n.replace(",", "")) for n in nums if float(n.replace(",", "")) > 0]
        for i, label in enumerate(sorted_years):
            if i < len(nums):
                years[label].revenue = nums[i]

    # Extract PAT
    pat_m = re.search(
        r"(?:profit\s+after\s+tax|net\s+profit|PAT)[^\n]*\n((?:[^\n]+\n){1,3})",
        section, re.IGNORECASE,
    )
    if pat_m:
        nums = re.findall(r"(-?[\d,]+(?:\.\d+)?)", pat_m.group(1))
        nums = [float(n.replace(",", "")) for n in nums]
        for i, label in enumerate(sorted_years):
            if i < len(nums):
                years[label].pat = nums[i]

    # Extract EBITDA / Operating Profit
    ebitda_m = re.search(
        r"(?:EBITDA|operating\s+profit|EBIT)[^\n]*\n((?:[^\n]+\n){1,3})",
        section, re.IGNORECASE,
    )
    if ebitda_m:
        nums = re.findall(r"(-?[\d,]+(?:\.\d+)?)", ebitda_m.group(1))
        nums = [float(n.replace(",", "")) for n in nums]
        for i, label in enumerate(sorted_years):
            if i < len(nums):
                years[label].ebitda = nums[i]

    return [years[y] for y in sorted_years]


def extract_risk_factors(text: str) -> List[RiskFactor]:
    section = _find_section(text, "risk_factors", 20000)
    if not section:
        return []

    high_keywords = ["material adverse", "cease operations", "insolvency", "criminal",
                     "fraud", "litigation", "regulatory action", "ban", "revoked"]
    financial_keywords = ["revenue", "profit", "cash flow", "debt", "obligation",
                          "repayment", "interest", "working capital"]
    regulatory_keywords = ["sebi", "rbi", "nclt", "nclat", "government", "license",
                           "approval", "compliance", "regulation"]

    risks = []
    # DRHP risk factors are numbered: "1.", "2.", etc. or bullet points
    items = re.split(r"\n\s*(?:\d{1,3}[\.\)]|•|\*)\s+", section)
    for item in items[1:51]:  # max 50 risk factors
        text_clean = " ".join(item.split())[:300]
        if len(text_clean) < 30:
            continue
        text_lower = text_clean.lower()
        severity = "low"
        if any(kw in text_lower for kw in high_keywords):
            severity = "high"
        elif any(kw in text_lower for kw in financial_keywords):
            severity = "medium"

        if any(kw in text_lower for kw in regulatory_keywords):
            category = "Regulatory"
        elif any(kw in text_lower for kw in financial_keywords):
            category = "Financial"
        elif "competition" in text_lower or "market" in text_lower:
            category = "Business"
        else:
            category = "General"

        risks.append(RiskFactor(category=category, text=text_clean, severity=severity))

    return risks


def extract_rpt(text: str) -> List[RelatedPartyTransaction]:
    section = _find_section(text, "rpt", 10000)
    if not section:
        return []

    rpts = []
    # Look for table rows with party names and amounts
    rows = re.findall(
        r"([A-Z][A-Za-z\s&.]+(?:Limited|Ltd\.?|LLP|Private)?)\s+"
        r"([A-Za-z\s]+(?:loan|sale|purchase|lease|service|guarantee|advance|rent)[A-Za-z\s]*)"
        r"[^\d]*([\d,]+(?:\.\d+)?)",
        section, re.IGNORECASE,
    )
    for party, txn_type, amount in rows[:20]:
        try:
            amt = float(amount.replace(",", ""))
        except ValueError:
            amt = None
        rpts.append(RelatedPartyTransaction(
            party_name=party.strip(),
            transaction_type=txn_type.strip(),
            amount=amt,
        ))
    return rpts


def extract_promoters(text: str) -> PromoterInfo:
    section = _find_section(text, "promoters", 8000)
    info = PromoterInfo()

    # Promoter names
    names = re.findall(r"(?:promoter|founder)[:\s]+([A-Z][A-Za-z\s.]+?)(?:\n|,|\band\b)", section, re.IGNORECASE)
    info.names = [n.strip() for n in names[:5] if len(n.strip()) > 3]

    # Promoter holding %
    hold_m = re.search(r"(?:promoter[s']?\s+)?holding[^%\d]*(\d{1,2}(?:\.\d+)?)\s*%", section, re.IGNORECASE)
    if hold_m:
        info.holding_pct = float(hold_m.group(1))

    # Pledged shares
    pledge_m = re.search(r"pledged?[^%\d]*(\d{1,2}(?:\.\d+)?)\s*%", section, re.IGNORECASE)
    if pledge_m:
        info.pledged_pct = float(pledge_m.group(1))

    # Red flags
    flags = []
    section_lower = section.lower()
    if "criminal" in section_lower or "convicted" in section_lower:
        flags.append("Criminal proceedings against promoter")
    if "disqualified" in section_lower:
        flags.append("Promoter disqualified as director")
    if "defaulter" in section_lower:
        flags.append("Promoter listed as defaulter")
    if pledge_m and float(pledge_m.group(1)) > 30:
        flags.append(f"High promoter pledging: {pledge_m.group(1)}%")
    info.background_flags = flags

    return info
