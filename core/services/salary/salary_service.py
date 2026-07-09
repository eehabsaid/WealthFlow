from datetime import datetime
from decimal import Decimal
from django.db import transaction
from django.db.models import F
from core.models import Company, SalaryEntry, BalanceEntry, Currency

MONTH_ORDER = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December"
]

class SalaryService:
    @transaction.atomic
    def generate_current_month_salaries(self, company_id: int = None) -> dict:
        current_year = datetime.now().year
        current_month = MONTH_ORDER[datetime.now().month - 1]
        
        if company_id:
            companies = Company.objects.filter(id=company_id, is_active=True)
        else:
            companies = Company.objects.filter(is_active=True)
            
        created = 0
        skipped = 0
        for company in companies:
            # Check if entry already exists
            exists = SalaryEntry.objects.filter(
                company=company, year=current_year, month=current_month
            ).exists()
            if exists:
                skipped += 1
                continue
            # Create new entry
            SalaryEntry.objects.create(
                company=company,
                year=current_year,
                month=current_month,
                expected=company.current_salary_amount,
                paid=0,
                bonus=0,
                notes="",
            )
            created += 1
            
        return {"created": created, "skipped": skipped}

    @transaction.atomic
    def mark_salary_paid(self, salary_id: int, mark_paid: bool) -> dict:
        salary = SalaryEntry.objects.select_related("company").get(id=salary_id)
        
        currency = salary.company.current_salary_currency
        if not currency:
            currency = Currency.objects.filter(code="EGP").first() or Currency.objects.first()

        if mark_paid and salary.paid == 0:
            # Mark as PAID
            salary.paid = salary.expected
            # Update bank balance
            if salary.company.default_bank:
                balance_entry = BalanceEntry.objects.filter(
                    bank=salary.company.default_bank,
                    currency=currency
                ).first()
                if not balance_entry:
                    balance_entry = BalanceEntry.objects.create(
                        bank=salary.company.default_bank,
                        balance_type=BalanceEntry.BalanceType.CASH,
                        currency=currency,
                        title=f"{salary.company.default_bank.name} Bank Account Balance",
                        amount=Decimal("0.00"),
                    )
                balance_entry.amount = F("amount") + salary.expected
                balance_entry.save()
            salary.save()
            return {"success": True, "message": "Salary marked as paid. Bank balance updated."}
            
        elif not mark_paid and salary.paid > 0:
            # REVERSE payment
            amount_to_reverse = salary.paid
            salary.paid = Decimal("0.00")
            # Reverse bank balance
            if salary.company.default_bank:
                BalanceEntry.objects.filter(
                    bank=salary.company.default_bank,
                    currency=currency,
                ).update(amount=F("amount") - amount_to_reverse)
            salary.save()
            return {"success": True, "message": "Payment reversed. Bank balance adjusted."}
            
        return {"success": False, "message": "No change needed"}

    @transaction.atomic
    def update_salary(self, salary_id: int, data: dict) -> SalaryEntry:
        entry = SalaryEntry.objects.select_related("company").get(id=salary_id)
        old_paid = entry.paid
        
        for field in ["year", "month", "expected", "paid", "bonus", "notes"]:
            if field in data:
                if field in ["expected", "paid", "bonus"]:
                    entry.__setattr__(field, Decimal(str(data[field] or 0)))
                else:
                    entry.__setattr__(field, data[field])
                    
        new_paid = entry.paid
        diff = new_paid - old_paid
        
        if diff != 0 and entry.company.default_bank:
            currency = entry.company.current_salary_currency
            if not currency:
                currency = Currency.objects.filter(code="EGP").first() or Currency.objects.first()
                
            balance_entry = BalanceEntry.objects.filter(
                bank=entry.company.default_bank,
                currency=currency
            ).first()
            if not balance_entry:
                balance_entry = BalanceEntry.objects.create(
                    bank=entry.company.default_bank,
                    balance_type=BalanceEntry.BalanceType.CASH,
                    currency=currency,
                    title=f"{entry.company.default_bank.name} Bank Account Balance",
                    amount=Decimal("0.00"),
                )
            balance_entry.amount = F("amount") + diff
            balance_entry.save()
            
        entry.save()
        return entry

    @transaction.atomic
    def delete_salary(self, salary_id: int) -> None:
        entry = SalaryEntry.objects.select_related("company").get(id=salary_id)
        
        if entry.paid > 0 and entry.company.default_bank:
            currency = entry.company.current_salary_currency
            if not currency:
                currency = Currency.objects.filter(code="EGP").first() or Currency.objects.first()
                
            BalanceEntry.objects.filter(
                bank=entry.company.default_bank,
                currency=currency,
            ).update(amount=F("amount") - entry.paid)
            
        entry.delete()
