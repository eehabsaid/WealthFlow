

import datetime
from decimal import Decimal


from ai.training.services.families import balance
from core.ai_pack.training_families import banking, income
from core.models import (
    AssetRental,
    BalanceEntry,
    BalanceTransfer,
    BankCertificate,
    BankCertificateInterestHistory,
    BankInterest,
    Currency,
    CurrencyExchange,
    Expense,
    PerDiem,
    RentReceipt,
)
from .business_families_support import BusinessFamilyBase


class BusinessFamilyTest(BusinessFamilyBase):
    def test_banking_balances_interest_and_active_certificate_principal(self):
        BankInterest.objects.create(
            owner=self.user, bank=self.bank, currency=self.currency,
            interest_date=datetime.date(2025, 3, 1), amount=Decimal("25.00"),
        )
        BalanceEntry.objects.create(
            owner=self.user, title="Certificate funding", balance_type="cash", bank=self.bank,
            currency=self.currency, amount=Decimal("1000.00"),
        )
        active = BankCertificate.objects.create(
            owner=self.user, bank=self.bank, currency=self.currency, status="Active",
            amount=Decimal("1000.00"), frequency="monthly",
        )
        BankCertificateInterestHistory.objects.create(
            certificate=active, posting_date=datetime.date(2025, 4, 1), posting_period="2025-04",
            bank=self.bank, currency=self.currency, interest_amount=Decimal("15.00"),
        )

        training = self._cases(banking, "train", self.user)
        balance_case = self._assert_four_languages(training, f"bank_balance:{self.bank.pk}:")
        interest_case = self._assert_four_languages(training, f"bank_interest_year:{self.bank.pk}:2025:")
        certificate_interest = self._assert_four_languages(training, "certificate_interest_year:2025:")
        self.assertEqual(balance_case.expected["values"], ["500.00"])
        self.assertEqual(interest_case.expected["values"], ["25.00"])
        self.assertEqual(certificate_interest.expected["values"], ["15.00"])

        evaluation = self._cases(banking, "evaluate", self.user)
        principal = self._assert_four_languages(evaluation, f"eval:certificate_principal:{self.bank.pk}:")
        self.assertEqual(principal.expected["values"], ["1000.00"])
        self.assertTrue(all(case.key.startswith("eval:") for case in evaluation))

    def test_balance_transfers_and_exchange_amounts_are_currency_scoped(self):
        BalanceTransfer.objects.create(
            owner=self.user, transfer_date=datetime.date(2025, 6, 1),
            transfer_type=BalanceTransfer.TransferType.BANK_TO_BANK, from_bank=self.bank,
            to_bank=self.bank, currency=self.currency, amount=Decimal("120.00"), fee=Decimal("3.00"),
        )
        euro, _ = Currency.objects.get_or_create(
            owner=self.user, code="EUR", defaults={"name": "Euro"}
        )
        from_balance = BalanceEntry.objects.create(
            owner=self.user, title="Exchange source", balance_type="cash", currency=self.currency,
            amount=Decimal("100.00"),
        )
        to_balance = BalanceEntry.objects.create(
            owner=self.user, title="Exchange destination", balance_type="cash", currency=euro,
            amount=Decimal("30.00"),
        )
        CurrencyExchange.objects.create(
            exchange_date=datetime.date(2025, 7, 1), from_balance=from_balance, to_balance=to_balance,
            from_currency=self.currency, to_currency=euro, from_amount=Decimal("40.00"),
            to_amount=Decimal("36.00"), exchange_rate=Decimal("0.9"), user=self.user,
        )

        training = self._cases(balance, "train", self.user)
        transfer = self._assert_four_languages(training, f"transfer_year:2025:{self.currency.pk}")
        self.assertEqual(transfer.expected["values"], ["120.00", "3.00"])
        self.assertFalse(any(case.key.startswith("eval:") for case in training))

        evaluation = self._cases(balance, "evaluate", self.user)
        exchange = self._assert_four_languages(
            evaluation, f"eval:exchange_year:2025:{self.currency.pk}:{euro.pk}"
        )
        self.assertEqual(exchange.expected["values"], ["40.00", "36.00"])
        self.assertTrue(all(case.key.startswith("eval:") for case in evaluation))

    def test_combined_income_and_salary_remaining_use_independent_base_currency_totals(self):
        PerDiem.objects.create(
            company=self.company, year=2025, date=datetime.date(2025, 2, 1), currency=self.currency,
            amount=Decimal("100.00"), amount_base=Decimal("100.00"),
        )
        Expense.objects.create(
            owner=self.user, date=datetime.date(2025, 1, 15), year=2025, month=1,
            category=self.category, amount=Decimal("250.00"),
            amount_base=Decimal("250.00"), currency=self.currency, bank=self.bank,
        )
        rental = AssetRental.objects.create(
            asset=self.asset, monthly_rent=Decimal("500.00"), occupancy_rate=Decimal("80.00")
        )
        RentReceipt.objects.create(
            owner=self.user, rental=rental, period_start=datetime.date(2025, 1, 1),
            received_date=datetime.date(2025, 1, 5), currency=self.currency, amount=Decimal("200.00"),
        )

        training = self._cases(income, "train", self.user)
        streams = self._assert_four_languages(training, "income_stream_year:2025")
        net = self._assert_four_languages(training, "income_net_year:2025")
        self.assertEqual(streams.expected["values"], ["800.00", "50.00", "100.00", "200.00", "1150.00"])
        self.assertEqual(net.expected["values"], ["1150.00", "250.00", "900.00"])

        evaluation = self._cases(income, "evaluate", self.user)
        remaining = self._assert_four_languages(evaluation, "eval:salary_remaining_year:2025")
        self.assertEqual(remaining.expected["values"], ["200.00"])
        self.assertTrue(all(case.key.startswith("eval:") for case in evaluation))
