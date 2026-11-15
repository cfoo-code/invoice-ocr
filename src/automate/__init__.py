from pydantic import BaseModel


class Totals(BaseModel):
    """Invoice summary row as read by either tier. Unvalidated: gates live in pipeline.py."""

    total_net: float
    total_vat: float
    total_gross: float
