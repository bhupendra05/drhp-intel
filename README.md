# drhp-intel

**DRHP/IPO prospectus intelligence for Indian capital markets — auto-extract financials, risk flags, RPTs from any SEBI filing.**

```bash
pip install "drhp-intel[pdf]"
drhp analyze paytm_drhp.pdf
```

[![CI](https://github.com/bhupendra05/drhp-intel/actions/workflows/ci.yml/badge.svg)](https://github.com/bhupendra05/drhp-intel/actions/workflows/ci.yml)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

---

## The Problem

Every IPO in India generates a **Draft Red Herring Prospectus (DRHP)** — a 600–900 page PDF filed with SEBI. Before any deal, every investment banker, equity researcher, and institutional investor manually reads through it to extract:

- 3-year restated financials (Revenue, EBITDA, PAT)
- Objects of the Issue (how the money will be used)
- Related Party Transactions (biggest red flag in Indian deals)
- Risk factors (legal, regulatory, financial risks)
- Promoter background and pledging data

**That's 12–16 hours per DRHP.** For an IPO season with 40+ filings, that's months of analyst time.

---

## What You Get in 10 Seconds

```
╭──────────── DRHP Intelligence Report ────────────╮
│  FinTech Solutions India Limited  ·  IPO (DRHP)  │
│  Lead Managers: Kotak, ICICI Securities, JM Fin  │
│  Pages: 684  ·  Risk Factors: 47  ·  RPTs: 12   │
│  Red Flag Score: 28/100 — MODERATE               │
╰───────────────────────────────────────────────────╯

Restated Financials (₹ Crore)
 Metric          FY2021      FY2022      FY2023
 Revenue         1,500       1,980       2,450   ← CAGR: 28%
 EBITDA            225         297         367
 EBITDA Margin    15.0%       15.0%       15.0%
 PAT                38          62          95

Objects of Issue
 Total Issue Size   ₹3,000 Cr
 Fresh Issue        ₹1,800 Cr
 Offer for Sale     ₹1,200 Cr  ← 40% OFS
 Use of Proceeds: Expansion, Debt repayment, General corporate

⚠ Red Flags:
  ✗ Elevated D/E ratio: 1.2x
  ✗ 2 RPTs exceeding ₹100 Cr

✓ Positives:
  ✓ Strong revenue growth: 28% CAGR
  ✓ Improving PAT margins
```

---

## Installation

```bash
# Core library (text analysis only)
pip install drhp-intel

# With PDF reading support
pip install "drhp-intel[pdf]"
```

---

## Usage

```bash
# Analyze a DRHP PDF
drhp analyze zomato_drhp.pdf

# Output as JSON (for downstream processing)
drhp analyze paytm_drhp.pdf --json

# See demo with synthetic data
drhp demo
```

### Python API

```python
from drhp_intel import analyze
from drhp_intel.parser import read_pdf

# From PDF
text, pages = read_pdf("nykaa_drhp.pdf")
summary = analyze(text, page_count=pages)

print(f"Company: {summary.company_name}")
print(f"Red Flag Score: {summary.red_flags.total}/100 — {summary.red_flags.grade}")
print(f"Revenue CAGR: {summary.revenue_cagr():.1%}")

# Financials
for fy in summary.financials:
    print(f"{fy.year}: Revenue ₹{fy.revenue:,.0f} Cr, PAT ₹{fy.pat:,.0f} Cr")

# Red flags
for flag in summary.red_flags.flags:
    print(f"⚠ {flag}")

# From already-extracted text
summary = analyze(drhp_text_string)
```

---

## What It Detects

### Financial Extraction
- 3-year restated Revenue, EBITDA, PAT, Net Worth, Debt
- EBITDA margin, PAT margin, D/E ratio trends
- Revenue CAGR across years

### Red Flag Scoring (0–100)
| Flag | Score Impact |
|------|-------------|
| Very high OFS (>70%) | +20 pts |
| Critical promoter pledging (>50%) | +25 pts |
| Criminal proceedings against promoter | +15 pts |
| Loss-making company | +15 pts |
| Revenue declining | +15 pts |
| High D/E ratio (>3x) | +12 pts |
| >60 risk factors | +8 pts |
| Large RPT volume | +6–8 pts |

**Grades:** LOW RISK (<20) · MODERATE (<45) · ELEVATED (<70) · HIGH RISK (≥70)

### RPT Intelligence
- Identifies related party names and transaction types
- Flags large RPTs exceeding ₹100 Cr
- Counts total RPT volume

### Promoter Analysis
- Promoter holding % and pledging level
- Background red flags (criminal proceedings, disqualification)

---

## SEBI DRHPs are Public

All DRHPs filed with SEBI are publicly available:
- **SEBI website**: sebi.gov.in → Issues & Listings → Public Issues
- **BSE**: bseindia.com → Corporates → DRHP
- **NSE**: nseindia.com → Corporates → IPO

---

## License

MIT
