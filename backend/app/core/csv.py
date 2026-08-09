"""Helpers for CSV export (formula-injection safe)."""

_FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


def csv_cell(value) -> str:
    """Neutralize spreadsheet formula injection in exported cells.

    Cells that begin with a formula trigger character are prefixed with a
    single quote so Excel/Sheets treat them as text, never as a formula.
    """
    if value is None:
        return ""
    text = str(value)
    if text and text.startswith(_FORMULA_PREFIXES):
        return "'" + text
    return text
