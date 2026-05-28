"""Rich terminal report for DRHP analysis."""
from __future__ import annotations
from .models import DRHPSummary

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich import box
    _RICH = True
except ImportError:
    _RICH = False

console = Console() if _RICH else None


def _fmt_cr(v):
    if v is None:
        return "N/A"
    if abs(v) >= 10000:
        return f"₹{v/100:.1f}K Cr"
    return f"₹{v:,.0f} Cr"


def _fmt_pct(v):
    return f"{v*100:.1f}%" if v is not None else "N/A"


def print_report(s: DRHPSummary) -> None:
    if not _RICH:
        _plain(s)
        return

    grade_color = {"LOW RISK": "green", "MODERATE": "yellow", "ELEVATED": "orange3", "HIGH RISK": "red"}
    rf = s.red_flags
    grade = rf.grade if rf else "N/A"
    color = grade_color.get(grade, "white")

    console.print(Panel(
        f"[bold cyan]{s.company_name}[/]  ·  {s.issue_type}\n"
        f"Lead Managers: {', '.join(s.lead_managers) or 'N/A'}\n"
        f"Pages: {s.page_count}  ·  Risk Factors: {len(s.risk_factors)}  ·  RPTs: {len(s.rpt_list)}\n"
        f"Red Flag Score: [{color}]{rf.total:.0f}/100 — {grade}[/]" if rf else "",
        title="[bold]DRHP Intelligence Report[/]", border_style="blue",
    ))

    # Financials
    if s.financials:
        t = Table(title="Restated Financials (₹ Crore)", box=box.SIMPLE_HEAVY)
        t.add_column("Metric", style="bold")
        for fy in s.financials:
            t.add_column(fy.year, justify="right")
        rows = [
            ("Revenue", lambda f: _fmt_cr(f.revenue)),
            ("EBITDA", lambda f: _fmt_cr(f.ebitda)),
            ("EBITDA Margin", lambda f: _fmt_pct(f.ebitda_margin)),
            ("PAT", lambda f: _fmt_cr(f.pat)),
            ("PAT Margin", lambda f: _fmt_pct(f.pat_margin)),
        ]
        for label, fn in rows:
            t.add_row(label, *[fn(f) for f in s.financials])
        cagr = s.revenue_cagr()
        if cagr is not None:
            t.add_row("[dim]Revenue CAGR[/]", *[""] * (len(s.financials) - 1), f"[bold]{_fmt_pct(cagr)}[/]")
        console.print(t)

    # Objects of Issue
    if s.objects:
        obj = s.objects
        t2 = Table(title="Objects of Issue", box=box.SIMPLE_HEAVY)
        t2.add_column("Item", style="bold")
        t2.add_column("Value", justify="right")
        t2.add_row("Total Issue Size", _fmt_cr(obj.total_issue_size))
        t2.add_row("Fresh Issue", _fmt_cr(obj.fresh_issue))
        t2.add_row("Offer for Sale (OFS)", _fmt_cr(obj.ofs_size))
        if obj.ofs_pct is not None:
            ofs_color = "red" if obj.ofs_pct > 0.5 else "yellow" if obj.ofs_pct > 0.3 else "green"
            t2.add_row("OFS %", f"[{ofs_color}]{_fmt_pct(obj.ofs_pct)}[/]")
        console.print(t2)
        if obj.uses:
            console.print("[bold]Use of Proceeds:[/]")
            for u in obj.uses:
                console.print(f"  • {u}")

    # Red flags
    if rf:
        if rf.flags:
            console.print("\n[bold red]⚠ Red Flags:[/]")
            for f in rf.flags:
                console.print(f"  [red]✗[/] {f}")
        if rf.positives:
            console.print("\n[bold green]✓ Positives:[/]")
            for p in rf.positives:
                console.print(f"  [green]✓[/] {p}")

    # Risk factor summary
    if s.risk_factors:
        by_cat: dict = {}
        by_sev: dict = {}
        for r in s.risk_factors:
            by_cat[r.category] = by_cat.get(r.category, 0) + 1
            by_sev[r.severity] = by_sev.get(r.severity, 0) + 1
        console.print(f"\n[bold]Risk Factors:[/] {len(s.risk_factors)} total  "
                      f"([red]{by_sev.get('high', 0)} high[/]  "
                      f"[yellow]{by_sev.get('medium', 0)} medium[/]  "
                      f"{by_sev.get('low', 0)} low)")

    console.print("\n[dim]Not investment advice. Verify all data against original DRHP.[/]\n")


def _plain(s: DRHPSummary) -> None:
    print(f"\n=== DRHP Report: {s.company_name} ===")
    print(f"Type: {s.issue_type}  |  Pages: {s.page_count}")
    if s.red_flags:
        print(f"Red Flag Score: {s.red_flags.total}/100 — {s.red_flags.grade}")
    if s.financials:
        print("\nFinancials (₹ Cr):")
        for f in s.financials:
            print(f"  {f.year}: Revenue={_fmt_cr(f.revenue)}, PAT={_fmt_cr(f.pat)}")
    print(f"\nRisk Factors: {len(s.risk_factors)}")
    print(f"RPTs: {len(s.rpt_list)}")
