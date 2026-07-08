from __future__ import annotations
from decimal import Decimal
from django.db import transaction
from django.db.models import F
from core.models import PerDiem, Company, Currency, Bank, BalanceEntry, ExchangeRate


class PerDiemService:
    def get_latest_buy_rate(self, currency_code: str) -> Decimal:
        """
        Retrieves the latest buy rate for a given currency code.
        If the currency is EGP, returns 1.0.
        """
        code = str(currency_code or "").upper().strip()
        if code == "EGP":
            return Decimal("1.000000")
        
        rate = ExchangeRate.objects.filter(currency_code=code).order_by("-fetched_at").first()
        if rate:
            return Decimal(str(rate.buy_rate))
        return Decimal("0.000000")

    def apply_balance_posting(self, bank: Bank | None, currency: Currency, amount: Decimal):
        """
        Updates the corresponding BalanceEntry by adding the amount.
        Creates a new entry if one doesn't exist.
        """
        # Look up by normalized balance_type='cash', bank, and currency
        balance_entry = BalanceEntry.objects.filter(
            balance_type__iexact="cash",
            bank=bank,
            currency=currency
        ).first()

        if balance_entry:
            balance_entry.amount = F("amount") + amount
            balance_entry.save()
        else:
            BalanceEntry.objects.create(
                title="Per Diem",
                balance_type="cash",
                bank=bank,
                currency=currency,
                purity="",
                amount=amount
            )

    def reverse_balance_posting(self, bank: Bank | None, currency: Currency, amount: Decimal):
        """
        Updates the corresponding BalanceEntry by subtracting the amount.
        """
        BalanceEntry.objects.filter(
            balance_type__iexact="cash",
            bank=bank,
            currency=currency
        ).update(amount=F("amount") - amount)

    @transaction.atomic
    def create_per_diem(self, data: dict) -> PerDiem:
        """
        Creates a new PerDiem record and applies the balance entry update.
        """
        company = Company.objects.get(id=data["company_id"])
        currency = Currency.objects.get(id=data["currency_id"])
        amount = Decimal(str(data["amount"]))
        
        bank_id = data.get("bank_id")
        bank = Bank.objects.get(id=bank_id) if bank_id else None

        buy_rate = self.get_latest_buy_rate(currency.code)
        amount_egp = amount * buy_rate

        from django.utils.dateparse import parse_date
        date_val = parse_date(data["date"]) if isinstance(data["date"], str) else data["date"]

        pd = PerDiem.objects.create(
            company=company,
            year=int(data["year"]),
            date=date_val,
            currency=currency,
            amount=amount,
            amount_egp=amount_egp,
            bank=bank,
            notes=data.get("notes", "")
        )

        self.apply_balance_posting(bank, currency, amount)
        return pd

    @transaction.atomic
    def update_per_diem(self, per_diem_id: int, data: dict) -> PerDiem:
        """
        Updates an existing PerDiem record by first reversing the old posting
        and then applying the new posting.
        """
        pd = PerDiem.objects.select_related("currency", "bank").get(id=per_diem_id)
        
        # Reverse old posting
        self.reverse_balance_posting(pd.bank, pd.currency, pd.amount)

        # Update values
        if "company_id" in data:
            pd.company = Company.objects.get(id=data["company_id"])
        if "year" in data:
            pd.year = int(data["year"])
        if "date" in data:
            from django.utils.dateparse import parse_date
            pd.date = parse_date(data["date"]) if isinstance(data["date"], str) else data["date"]
        if "notes" in data:
            pd.notes = data["notes"]

        if "currency_id" in data:
            pd.currency = Currency.objects.get(id=data["currency_id"])
        if "amount" in data:
            pd.amount = Decimal(str(data["amount"]))
        
        if "bank_id" in data:
            bank_id = data["bank_id"]
            pd.bank = Bank.objects.get(id=bank_id) if bank_id else None
        elif "bank" in data:  # fallback
            pd.bank = data["bank"]

        # Recalculate EGP amount using current latest buy rate
        buy_rate = self.get_latest_buy_rate(pd.currency.code)
        pd.amount_egp = pd.amount * buy_rate

        pd.save()

        # Apply new posting
        self.apply_balance_posting(pd.bank, pd.currency, pd.amount)
        return pd

    @transaction.atomic
    def delete_per_diem(self, per_diem_id: int):
        """
        Deletes a PerDiem record and reverses the balance entry update.
        """
        pd = PerDiem.objects.select_related("currency", "bank").get(id=per_diem_id)
        self.reverse_balance_posting(pd.bank, pd.currency, pd.amount)
        pd.delete()

    def get_currencies_used_in_balance(self):
        """
        Retrieves list of currencies currently used inside BalanceEntry.
        """
        used_currency_ids = BalanceEntry.objects.filter(currency__isnull=False).values_list("currency_id", flat=True).distinct()
        return Currency.objects.filter(id__in=used_currency_ids).order_by("order")
