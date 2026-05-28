"""drhp-intel — DRHP/IPO prospectus intelligence for Indian capital markets."""
from .analyzer import analyze
from .models import DRHPSummary

__version__ = "1.0.0"
__all__ = ["analyze", "DRHPSummary"]
