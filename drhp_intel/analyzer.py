"""
DRHP analysis engine — scores red flags, assembles DRHPSummary.
"""
from __future__ import annotations
from typing import Optional
from .models import DRHPSummary, RedFlagScore
from .sections import (
    extract_company_name, extract_issue_type, extract_lead_managers,
    extract_objects, extract_financials, extract_risk_factors,
    extract_rpt, extract_promoters,
)


def score_red_flags(summary: DRHPSummary) -> RedFlagScore:
    flags = []
    positives = []
    score = 0.0

    # --- OFS ratio (high OFS = promoters cashing out) ---
    if summary.objects and summary.objects.ofs_pct is not None:
        ofs = summary.objects.ofs_pct
        if ofs > 0.70:
            flags.append(f"Very high OFS ratio ({ofs:.0%}) — promoters cashing out heavily")
            score += 20
        elif ofs > 0.50:
            flags.append(f"High OFS ratio ({ofs:.0%}) — significant secondary sale")
            score += 10
        elif ofs < 0.20:
            positives.append(f"Low OFS ({ofs:.0%}) — mostly fresh capital for growth")

    # --- Promoter pledging ---
    if summary.promoters and summary.promoters.pledged_pct is not None:
        pledged = summary.promoters.pledged_pct
        if pledged > 50:
            flags.append(f"Critical promoter pledging: {pledged:.1f}% of holding pledged")
            score += 25
        elif pledged > 25:
            flags.append(f"High promoter pledging: {pledged:.1f}%")
            score += 12
        elif pledged == 0:
            positives.append("Zero promoter pledging")

    # --- Promoter background ---
    if summary.promoters:
        for f in summary.promoters.background_flags:
            flags.append(f)
            score += 15

    # --- Financial health ---
    latest = summary.latest_financials()
    if latest:
        if latest.pat is not None and latest.pat < 0:
            flags.append("Company is loss-making in latest year")
            score += 15
        if latest.debt_equity is not None and latest.debt_equity > 3:
            flags.append(f"Very high D/E ratio: {latest.debt_equity:.1f}x")
            score += 12
        elif latest.debt_equity is not None and latest.debt_equity > 1.5:
            flags.append(f"Elevated D/E ratio: {latest.debt_equity:.1f}x")
            score += 6
        if latest.ebitda_margin is not None and latest.ebitda_margin < 0.05:
            flags.append(f"Very thin EBITDA margin: {latest.ebitda_margin:.1%}")
            score += 8

    # --- Revenue trend ---
    cagr = summary.revenue_cagr()
    if cagr is not None:
        if cagr > 0.30:
            positives.append(f"Strong revenue growth: {cagr:.0%} CAGR")
        elif cagr < 0:
            flags.append(f"Revenue declining: {cagr:.0%} CAGR")
            score += 15

    # --- Risk factor count ---
    high_risks = [r for r in summary.risk_factors if r.severity == "high"]
    if len(summary.risk_factors) > 60:
        flags.append(f"Unusually high risk factor count: {len(summary.risk_factors)}")
        score += 8
    if len(high_risks) > 10:
        flags.append(f"{len(high_risks)} high-severity risk factors")
        score += 10

    # --- RPT volume ---
    if len(summary.rpt_list) > 15:
        flags.append(f"Large number of related party transactions: {len(summary.rpt_list)}")
        score += 8
    large_rpts = [r for r in summary.rpt_list if r.amount and r.amount > 100]
    if large_rpts:
        flags.append(f"{len(large_rpts)} RPTs exceeding ₹100 Cr")
        score += 6

    return RedFlagScore(
        total=min(100.0, round(score, 1)),
        flags=flags,
        positives=positives,
    )


def analyze(text: str, page_count: int = 0) -> DRHPSummary:
    """
    Full DRHP analysis from extracted text.

    Parameters
    ----------
    text       : Full text of the DRHP (from PDF extraction or mock)
    page_count : Number of pages in the PDF
    """
    summary = DRHPSummary(
        company_name=extract_company_name(text),
        issue_type=extract_issue_type(text),
        lead_managers=extract_lead_managers(text),
        financials=extract_financials(text),
        objects=extract_objects(text),
        risk_factors=extract_risk_factors(text),
        rpt_list=extract_rpt(text),
        promoters=extract_promoters(text),
        page_count=page_count,
    )
    summary.red_flags = score_red_flags(summary)
    return summary
