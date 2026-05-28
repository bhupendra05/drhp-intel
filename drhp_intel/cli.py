"""CLI for drhp-intel."""
from __future__ import annotations
import json
import sys
import click
from .analyzer import analyze
from .report import print_report


@click.group()
def cli():
    """drhp-intel — AI-powered DRHP/IPO prospectus intelligence for Indian markets."""


@cli.command("analyze")
@click.argument("pdf_path", type=click.Path(exists=True))
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.option("--no-financials", is_flag=True, help="Skip financial extraction")
def analyze_cmd(pdf_path, as_json, no_financials):
    """Analyze a DRHP/RHP PDF and generate an intelligence report.

    Example: drhp analyze paytm_drhp.pdf
    """
    click.echo(f"\nReading PDF: {pdf_path} ...")
    try:
        from .parser import read_pdf
        text, pages = read_pdf(pdf_path)
    except ImportError as e:
        click.echo(str(e), err=True)
        sys.exit(1)
    except ValueError as e:
        click.echo(str(e), err=True)
        sys.exit(1)

    click.echo(f"Extracted {pages} pages, {len(text):,} characters. Analyzing...")
    summary = analyze(text, page_count=pages)

    if as_json:
        out = {
            "company": summary.company_name,
            "issue_type": summary.issue_type,
            "lead_managers": summary.lead_managers,
            "page_count": summary.page_count,
            "risk_factor_count": len(summary.risk_factors),
            "rpt_count": len(summary.rpt_list),
            "red_flag_score": summary.red_flags.total if summary.red_flags else None,
            "red_flag_grade": summary.red_flags.grade if summary.red_flags else None,
            "flags": summary.red_flags.flags if summary.red_flags else [],
            "financials": [
                {"year": f.year, "revenue": f.revenue, "pat": f.pat, "ebitda": f.ebitda}
                for f in summary.financials
            ],
        }
        click.echo(json.dumps(out, indent=2))
    else:
        print_report(summary)


@cli.command("demo")
def demo_cmd():
    """Run a demo with a synthetic DRHP to show output format."""
    sample_text = """
DRAFT RED HERRING PROSPECTUS

TechVenture India Limited
CIN: U72200MH2019PLC123456

BOOK RUNNING LEAD MANAGERS
Kotak Mahindra Capital Company Limited
ICICI Securities Limited

OBJECTS OF THE ISSUE
Total Issue Size: Rs. 2,500 crore
Fresh Issue: Rs. 1,500 crore
Offer for Sale: Rs. 1,000 crore

Objects of the Issue:
1. Expansion of technology infrastructure
2. Repayment of outstanding borrowings
3. General corporate purposes

RISK FACTORS
1. We have incurred losses in the past and may continue to incur losses.
2. Our business depends on regulatory approvals that may be revoked.
3. Competition from large established players may adversely affect our market share.
4. We face significant litigation risks including criminal proceedings.
5. Our revenue is concentrated among top 10 customers.

RESTATED CONSOLIDATED FINANCIAL STATEMENTS
Summary of Financial Information (₹ in Crore)

Particulars     FY2023     FY2022     FY2021
Revenue from Operations   1,245.30   980.50   750.20
EBITDA     186.80     147.08     112.53
Profit After Tax    45.20    32.10    18.50
Total Assets   2,100.50  1,650.30  1,200.80
Net Worth     650.20    605.00    572.90
Total Debt     850.00    720.00    580.00

RELATED PARTY TRANSACTIONS
TechVenture Holdings Limited   Loan given   Rs. 150 crore
Promoter Family Trust   Rent payment   Rs. 25 crore

OUR PROMOTERS AND PROMOTER GROUP
Mr. Rajesh Kumar (Promoter)
Promoter holding: 68.5%
Pledged shares: 22.3% of promoter holding

"""
    summary = analyze(sample_text, page_count=650)
    print_report(summary)


def main():
    cli()


if __name__ == "__main__":
    main()
