"""
Unit tests for each tool. These fail until you implement the tools.

Run a single test:
    pytest tests/test_tools.py::test_extract_invoice_happy_path -v
"""

from __future__ import annotations

import pytest

from src.agent.schemas import (
    ExtractInvoiceInput,
    LookupGoodsReceiptInput,
    LookupPOInput,
    LookupVendorInput,
    ScreenSanctionsInput,
    ValidateTaxInput,
)
from src.tools import extract, po, sanctions, tax, vendor


# -------- extract_invoice --------


def test_extract_invoice_happy_path():
    out = extract.extract_invoice(ExtractInvoiceInput(invoice_id="INV-001"))
    assert out.ok is True
    assert out.data is not None
    assert out.data.invoice_number == "NW-2026-0412"
    assert out.data.total == out.data.subtotal + out.data.tax


def test_extract_invoice_missing_file():
    out = extract.extract_invoice(ExtractInvoiceInput(invoice_id="DOES-NOT-EXIST"))
    assert out.ok is False
    assert out.error is not None
    assert out.error.code == "INVOICE_NOT_FOUND"


# -------- lookup_vendor --------


def test_lookup_vendor_by_tax_id():
    out = vendor.lookup_vendor(LookupVendorInput(tax_id="123456789RT0001"))
    assert out.ok is True
    assert out.data is not None
    assert out.data.vendor_id == "V-1001"


def test_lookup_vendor_no_keys():
    out = vendor.lookup_vendor(LookupVendorInput())
    assert out.ok is False
    assert out.error is not None
    assert out.error.code == "MISSING_LOOKUP_KEY"


def test_lookup_vendor_not_found():
    out = vendor.lookup_vendor(LookupVendorInput(tax_id="000000000RT0001"))
    assert out.ok is False
    assert out.error is not None
    assert out.error.code == "VENDOR_NOT_FOUND"


# -------- lookup_po --------


def test_lookup_po_happy_path():
    out = po.lookup_po(LookupPOInput(po_number="PO-5001"))
    assert out.ok is True
    assert out.data is not None
    assert out.data.vendor_id == "V-1001"


def test_lookup_po_not_found():
    out = po.lookup_po(LookupPOInput(po_number="PO-9999"))
    assert out.ok is False
    assert out.error is not None
    assert out.error.code == "PO_NOT_FOUND"


# -------- lookup_goods_receipt --------


def test_lookup_goods_receipt_happy_path():
    out = po.lookup_goods_receipt(LookupGoodsReceiptInput(po_number="PO-5001"))
    assert out.ok is True
    assert out.data is not None


def test_lookup_goods_receipt_not_yet_received():
    """PO-5005 (catering offsite) intentionally has no goods receipt."""
    out = po.lookup_goods_receipt(LookupGoodsReceiptInput(po_number="PO-5005"))
    assert out.ok is False
    assert out.error is not None
    assert out.error.code == "GR_NOT_FOUND"


# -------- validate_tax --------


def test_validate_tax_valid_canada():
    out = tax.validate_tax(ValidateTaxInput(tax_id="123456789RT0001", country="CA"))
    assert out.ok is True
    assert out.valid is True


def test_validate_tax_bad_format():
    out = tax.validate_tax(ValidateTaxInput(tax_id="not-a-tax-id", country="CA"))
    assert out.ok is True
    assert out.valid is False


def test_validate_tax_unknown_country():
    out = tax.validate_tax(ValidateTaxInput(tax_id="123", country="ZZ"))
    assert out.ok is True
    assert out.valid is False


# -------- screen_sanctions --------


def test_screen_sanctions_hit():
    out = sanctions.screen_sanctions(ScreenSanctionsInput(name="Shadowfall Holdings"))
    assert out.ok is True
    assert out.is_hit is True


def test_screen_sanctions_clean():
    out = sanctions.screen_sanctions(ScreenSanctionsInput(name="Northwind Office Supplies Inc"))
    assert out.ok is True
    assert out.is_hit is False
