from src.constants import CENT


def checksum(net: float, vat: float, gross: float) -> None:
    """Accounting identity Net + VAT == Gross (±1 cent). Shared by Tier 1 and Tier 2."""
    if abs(net + vat - gross) > CENT:
        raise ValueError(f"checksum failed: {net} + {vat} != {gross}")
