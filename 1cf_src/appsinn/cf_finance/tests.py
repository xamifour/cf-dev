# cf-dev/cf_src/appsinn/cf_finance/tests.py

"""Tests for finance domain models."""

from datetime import date, timedelta
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase

from cf_users.models import Branch, Organization

from .models import Fund, FinancialPeriod, Transaction


class FinanceModelTests(TestCase):
    def setUp(self):
        self.org = Organization.objects.create(
            name="Finance Org",
            address="Street",
            city="Accra",
            country="GH",
        )
        self.branch = Branch.objects.create(
            organization=self.org,
            name="HQ",
            address="Street",
            city="Accra",
            country="GH",
            is_default=True,
        )
        self.period = FinancialPeriod.objects.create(
            branch=self.branch,
            period_name="FY2026-Q1",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 3, 31),
        )

    def test_period_date_validation(self):
        bad = FinancialPeriod(
            branch=self.branch,
            period_name="Bad",
            start_date=date(2026, 5, 1),
            end_date=date(2026, 4, 1),
        )
        with self.assertRaises(ValidationError):
            bad.full_clean()

    def test_fund_create_and_choices(self):
        fund = Fund.objects.create(
            branch=self.branch,
            fund_type="TITHE",
            name="General Tithe",
            description="Weekly tithe",
            amount=Decimal("1500.50"),
        )
        self.assertEqual(fund.get_fund_type_display(), "Tithe")
        self.assertEqual(fund.amount, Decimal("1500.50"))
        self.assertIn("TITHE", dict(Fund.FUND_TYPE_CHOICES))
        self.assertIn("OFFERINGS", dict(Fund.FUND_TYPE_CHOICES))
        self.assertIn("PROJECT", dict(Fund.FUND_TYPE_CHOICES))
        self.assertIn("CHARITY", dict(Fund.FUND_TYPE_CHOICES))

    def test_fund_unique_per_branch_type_name(self):
        Fund.objects.create(
            branch=self.branch,
            fund_type="OFFERINGS",
            name="Sunday Offerings",
        )
        dup = Fund(
            branch=self.branch,
            fund_type="OFFERINGS",
            name="Sunday Offerings",
        )
        with self.assertRaises(Exception):
            dup.save()

    def test_transaction_code_auto(self):
        fund = Fund.objects.create(
            branch=self.branch,
            fund_type="TITHE",
            name="General Tithe",
        )
        txn = Transaction.objects.create(
            branch=self.branch,
            financial_period=self.period,
            fund=fund,
            transaction_type="INCOME",
            category="Tithe",
            amount=Decimal("100.00"),
        )
        self.assertTrue(txn.reference_code.startswith("TXN"))
        self.assertEqual(len(txn.reference_code), 11)  # TXN + 8 digits
        self.assertEqual(txn.fund_id, fund.pk)
