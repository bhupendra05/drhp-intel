"""Data structures for DRHP analysis."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional, Dict


@dataclass
class FinancialYear:
    year: str           # "FY2023", "FY2022", etc.
    revenue: Optional[float] = None       # in Crores
    ebitda: Optional[float] = None
    pat: Optional[float] = None           # Profit After Tax
    total_assets: Optional[float] = None
    net_worth: Optional[float] = None
    debt: Optional[float] = None

    @property
    def ebitda_margin(self) -> Optional[float]:
        if self.ebitda and self.revenue:
            return self.ebitda / self.revenue
        return None

    @property
    def pat_margin(self) -> Optional[float]:
        if self.pat and self.revenue:
            return self.pat / self.revenue
        return None

    @property
    def debt_equity(self) -> Optional[float]:
        if self.debt is not None and self.net_worth and self.net_worth > 0:
            return self.debt / self.net_worth
        return None


@dataclass
class ObjectsOfIssue:
    total_issue_size: Optional[float] = None    # in Crores
    fresh_issue: Optional[float] = None
    ofs_size: Optional[float] = None            # Offer For Sale
    uses: List[str] = field(default_factory=list)
    raw_text: str = ""

    @property
    def ofs_pct(self) -> Optional[float]:
        if self.ofs_size and self.total_issue_size and self.total_issue_size > 0:
            return self.ofs_size / self.total_issue_size
        return None


@dataclass
class RiskFactor:
    category: str       # "Business", "Regulatory", "Financial", "General"
    text: str
    severity: str = "medium"  # "high", "medium", "low"


@dataclass
class RelatedPartyTransaction:
    party_name: str
    transaction_type: str
    amount: Optional[float] = None    # in Crores
    relationship: str = ""


@dataclass
class PromoterInfo:
    names: List[str] = field(default_factory=list)
    holding_pct: Optional[float] = None
    pledged_pct: Optional[float] = None
    background_flags: List[str] = field(default_factory=list)


@dataclass
class RedFlagScore:
    total: float            # 0–100 (higher = more flags)
    flags: List[str] = field(default_factory=list)
    positives: List[str] = field(default_factory=list)

    @property
    def grade(self) -> str:
        if self.total < 20:
            return "LOW RISK"
        if self.total < 45:
            return "MODERATE"
        if self.total < 70:
            return "ELEVATED"
        return "HIGH RISK"


@dataclass
class DRHPSummary:
    company_name: str
    cin: str = ""
    issue_type: str = ""          # "IPO", "FPO", "Rights Issue"
    industry: str = ""
    registrar: str = ""
    lead_managers: List[str] = field(default_factory=list)
    financials: List[FinancialYear] = field(default_factory=list)
    objects: Optional[ObjectsOfIssue] = None
    risk_factors: List[RiskFactor] = field(default_factory=list)
    rpt_list: List[RelatedPartyTransaction] = field(default_factory=list)
    promoters: Optional[PromoterInfo] = None
    red_flags: Optional[RedFlagScore] = None
    page_count: int = 0

    def latest_financials(self) -> Optional[FinancialYear]:
        return self.financials[-1] if self.financials else None

    def revenue_cagr(self) -> Optional[float]:
        if len(self.financials) < 2:
            return None
        first = self.financials[0].revenue
        last = self.financials[-1].revenue
        n = len(self.financials) - 1
        if first and last and first > 0:
            return (last / first) ** (1 / n) - 1
        return None
