"""Tests for drhp-intel — all run without any PDF files."""
import pytest
from drhp_intel.sections import (
    extract_company_name, extract_issue_type, extract_lead_managers,
    extract_objects, extract_financials, extract_risk_factors,
    extract_rpt, extract_promoters, _parse_indian_number,
)
from drhp_intel.analyzer import analyze, score_red_flags
from drhp_intel.models import DRHPSummary, FinancialYear, ObjectsOfIssue, PromoterInfo, RedFlagScore


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SAMPLE_DRHP = """
DRAFT RED HERRING PROSPECTUS

FinTech Solutions India Limited
CIN: U72200MH2019PLC123456

BOOK RUNNING LEAD MANAGERS
Kotak Mahindra Capital Company Limited
ICICI Securities Limited
JM Financial Limited

OBJECTS OF THE ISSUE
Total Issue Size: Rs. 3,000 crore
Fresh Issue: Rs. 1,800 crore
Offer for Sale: Rs. 1,200 crore
• Expansion of technology infrastructure — Rs. 800 crore
• Repayment of borrowings — Rs. 600 crore
• General corporate purposes — Rs. 400 crore

RISK FACTORS
1. We have incurred losses and may continue to incur losses in future periods.
2. Our business is subject to regulatory approvals from SEBI and RBI.
3. We face significant competition from established players in the market.
4. Our revenue is concentrated among our top 10 customers.
5. There are pending litigation matters against the company.
6. Our cash flow from operations has been negative in the past.
7. We depend on third-party technology providers for our infrastructure.

RESTATED CONSOLIDATED FINANCIAL STATEMENTS
Summary of Financial Information (Rs. in Crore)

Particulars     FY2023     FY2022     FY2021
Revenue from Operations   2,450.30   1,980.50   1,500.20
EBITDA     367.55   297.08   225.03
Profit After Tax    95.20    62.10    38.50
Total Assets   4,100.50  3,250.30  2,400.80
Net Worth    1,250.20  1,155.00  1,092.90
Total Debt    1,500.00  1,320.00  1,080.00

RELATED PARTY TRANSACTIONS
FinTech Holdings Limited  Loan given  Rs. 250 crore
Promoter Family Trust  Rent payment  Rs. 45 crore
Subsidiary Company  Purchase of services  Rs. 120 crore

OUR PROMOTERS AND PROMOTER GROUP
Mr. Amit Sharma (Promoter and Managing Director)
Promoter holding: 62.5%
Pledged shares: 18.4% of promoter holding
"""

LOSS_MAKING_DRHP = """
DRAFT RED HERRING PROSPECTUS
Startup India Limited

OBJECTS OF THE ISSUE
Total Issue Size: Rs. 500 crore
Offer for Sale: Rs. 450 crore
Fresh Issue: Rs. 50 crore

RESTATED FINANCIAL STATEMENTS
FY2023  FY2022  FY2021
Revenue from Operations  100.50  80.20  60.10
Profit After Tax  -45.20  -32.10  -18.50

OUR PROMOTERS AND PROMOTER GROUP
Promoter holding: 55.0%
Pledged shares: 65.0% of promoter holding
"""


# ---------------------------------------------------------------------------
# _parse_indian_number
# ---------------------------------------------------------------------------

class TestParseIndianNumber:
    def test_rs_crore(self):
        assert _parse_indian_number("Rs. 1,500 crore") == 1500.0

    def test_inr_crore(self):
        assert _parse_indian_number("INR 2,450.30 crore") == 2450.3

    def test_symbol_crore(self):
        assert _parse_indian_number("₹800 crore") == 800.0

    def test_plain_crore(self):
        assert _parse_indian_number("3000 crore") == 3000.0

    def test_lakh_converts(self):
        v = _parse_indian_number("Rs. 1,00,000 lakh")
        assert v == pytest.approx(1000.0)

    def test_no_match_returns_none(self):
        assert _parse_indian_number("hello world") is None

    def test_comma_separated(self):
        assert _parse_indian_number("Rs. 1,234.56 crore") == 1234.56


# ---------------------------------------------------------------------------
# Section extraction
# ---------------------------------------------------------------------------

class TestExtractCompanyName:
    def test_finds_limited_company(self):
        name = extract_company_name(SAMPLE_DRHP)
        assert "Limited" in name or "Ltd" in name

    def test_returns_string(self):
        assert isinstance(extract_company_name(SAMPLE_DRHP), str)

    def test_fallback_on_empty(self):
        assert isinstance(extract_company_name(""), str)


class TestExtractIssueType:
    def test_drhp_detected(self):
        assert "IPO" in extract_issue_type(SAMPLE_DRHP)

    def test_fpo_detected(self):
        text = "FURTHER PUBLIC OFFER\nSome company"
        assert "FPO" in extract_issue_type(text)

    def test_rights_detected(self):
        text = "RIGHTS ISSUE\nSome company"
        assert "Rights" in extract_issue_type(text)


class TestExtractLeadManagers:
    def test_finds_managers(self):
        managers = extract_lead_managers(SAMPLE_DRHP)
        assert isinstance(managers, list)

    def test_returns_list(self):
        assert isinstance(extract_lead_managers("no managers here"), list)


class TestExtractObjects:
    def test_returns_objects_of_issue(self):
        obj = extract_objects(SAMPLE_DRHP)
        assert obj is not None

    def test_parses_total_issue_size(self):
        obj = extract_objects(SAMPLE_DRHP)
        assert obj.total_issue_size == 3000.0

    def test_parses_fresh_issue(self):
        obj = extract_objects(SAMPLE_DRHP)
        assert obj.fresh_issue == 1800.0

    def test_parses_ofs(self):
        obj = extract_objects(SAMPLE_DRHP)
        assert obj.ofs_size == 1200.0

    def test_ofs_pct_calculated(self):
        obj = extract_objects(SAMPLE_DRHP)
        assert obj.ofs_pct == pytest.approx(0.4, abs=0.05)

    def test_uses_extracted(self):
        obj = extract_objects(SAMPLE_DRHP)
        assert isinstance(obj.uses, list)

    def test_empty_text_returns_object(self):
        obj = extract_objects("no objects here")
        assert obj is not None


class TestExtractFinancials:
    def test_returns_list(self):
        result = extract_financials(SAMPLE_DRHP)
        assert isinstance(result, list)

    def test_has_years(self):
        result = extract_financials(SAMPLE_DRHP)
        assert len(result) >= 1

    def test_year_labels(self):
        result = extract_financials(SAMPLE_DRHP)
        for f in result:
            assert "FY" in f.year or "20" in f.year

    def test_revenue_extracted(self):
        result = extract_financials(SAMPLE_DRHP)
        revenues = [f.revenue for f in result if f.revenue]
        assert len(revenues) >= 1

    def test_pat_extracted(self):
        result = extract_financials(SAMPLE_DRHP)
        pats = [f.pat for f in result if f.pat is not None]
        assert len(pats) >= 1


class TestExtractRiskFactors:
    def test_returns_list(self):
        risks = extract_risk_factors(SAMPLE_DRHP)
        assert isinstance(risks, list)

    def test_finds_multiple_risks(self):
        risks = extract_risk_factors(SAMPLE_DRHP)
        assert len(risks) >= 3

    def test_risk_has_category(self):
        risks = extract_risk_factors(SAMPLE_DRHP)
        for r in risks:
            assert r.category in ("Business", "Regulatory", "Financial", "General")

    def test_risk_has_severity(self):
        risks = extract_risk_factors(SAMPLE_DRHP)
        for r in risks:
            assert r.severity in ("high", "medium", "low")

    def test_high_severity_for_criminal(self):
        text = "RISK FACTORS\n1. Criminal proceedings against the promoter are pending."
        risks = extract_risk_factors(text)
        if risks:
            assert any(r.severity == "high" for r in risks)

    def test_regulatory_category(self):
        text = "RISK FACTORS\n1. SEBI may take regulatory action against us."
        risks = extract_risk_factors(text)
        if risks:
            assert any(r.category == "Regulatory" for r in risks)


class TestExtractRPT:
    def test_returns_list(self):
        rpts = extract_rpt(SAMPLE_DRHP)
        assert isinstance(rpts, list)

    def test_empty_if_no_section(self):
        rpts = extract_rpt("no related parties here")
        assert rpts == []


class TestExtractPromoters:
    def test_returns_promoter_info(self):
        info = extract_promoters(SAMPLE_DRHP)
        assert info is not None

    def test_holding_extracted(self):
        info = extract_promoters(SAMPLE_DRHP)
        assert info.holding_pct == pytest.approx(62.5, abs=0.5)

    def test_pledging_extracted(self):
        info = extract_promoters(SAMPLE_DRHP)
        assert info.pledged_pct == pytest.approx(18.4, abs=0.5)

    def test_high_pledging_flagged(self):
        info = extract_promoters(LOSS_MAKING_DRHP)
        assert info.pledged_pct > 50
        assert any("pledg" in f.lower() for f in info.background_flags)


# ---------------------------------------------------------------------------
# Red flag scoring
# ---------------------------------------------------------------------------

class TestRedFlagScore:
    def test_returns_score(self):
        summary = analyze(SAMPLE_DRHP)
        assert summary.red_flags is not None
        assert 0 <= summary.red_flags.total <= 100

    def test_loss_making_scored_higher(self):
        s_healthy = analyze(SAMPLE_DRHP)
        s_loss = analyze(LOSS_MAKING_DRHP)
        assert s_loss.red_flags.total > s_healthy.red_flags.total

    def test_high_ofs_flagged(self):
        s = analyze(LOSS_MAKING_DRHP)
        flag_texts = " ".join(s.red_flags.flags).lower()
        assert "ofs" in flag_texts or "offer for sale" in flag_texts

    def test_grade_is_valid(self):
        s = analyze(SAMPLE_DRHP)
        assert s.red_flags.grade in ("LOW RISK", "MODERATE", "ELEVATED", "HIGH RISK")

    def test_high_pledge_raises_score(self):
        s = analyze(LOSS_MAKING_DRHP)
        assert s.red_flags.total >= 20

    def test_positives_list(self):
        s = analyze(SAMPLE_DRHP)
        assert isinstance(s.red_flags.positives, list)


# ---------------------------------------------------------------------------
# Full analysis
# ---------------------------------------------------------------------------

class TestAnalyze:
    def test_returns_drhp_summary(self):
        s = analyze(SAMPLE_DRHP)
        assert isinstance(s, DRHPSummary)

    def test_company_name_set(self):
        s = analyze(SAMPLE_DRHP)
        assert len(s.company_name) > 3

    def test_revenue_cagr(self):
        s = analyze(SAMPLE_DRHP)
        cagr = s.revenue_cagr()
        if cagr is not None:
            assert -0.5 < cagr < 2.0

    def test_latest_financials(self):
        s = analyze(SAMPLE_DRHP)
        latest = s.latest_financials()
        assert latest is not None

    def test_empty_text_doesnt_crash(self):
        s = analyze("")
        assert isinstance(s, DRHPSummary)


# ---------------------------------------------------------------------------
# FinancialYear model
# ---------------------------------------------------------------------------

class TestFinancialYear:
    def test_ebitda_margin(self):
        f = FinancialYear("FY2023", revenue=1000, ebitda=200)
        assert f.ebitda_margin == pytest.approx(0.20)

    def test_pat_margin(self):
        f = FinancialYear("FY2023", revenue=1000, pat=80)
        assert f.pat_margin == pytest.approx(0.08)

    def test_debt_equity(self):
        f = FinancialYear("FY2023", debt=500, net_worth=250)
        assert f.debt_equity == pytest.approx(2.0)

    def test_zero_revenue_margin(self):
        f = FinancialYear("FY2023", revenue=0, ebitda=100)
        assert f.ebitda_margin is None

    def test_zero_networth_de(self):
        f = FinancialYear("FY2023", debt=500, net_worth=0)
        assert f.debt_equity is None
