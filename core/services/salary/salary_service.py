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


def get_current_monthly_salary(year: int = None, month: str = None) -> float:
    """
    Centralized resolver for active monthly salary across all analytics, dashboards, and financial advisor services.

    Rules:
    1. If a paid SalaryEntry exists for the target/current month (year, month), return that paid amount (actual income received for the month).
    2. Else if a company is marked as is_active=True:
       a) Return latest paid SalaryEntry for that active company.
       b) Or expected SalaryEntry for current month for that active company.
       c) Or active company's current_salary_amount setting.
    3. Else (no active company and no paid salary entry for target/current month):
       Return 0.0 (user has resigned or has no active employment for this month).
    """
    try:
        if not year or not month:
            now = datetime.now()
            year = year or now.year
            month = month or MONTH_ORDER[now.month - 1]

        # 1. Paid salary entry for current/specified year & month
        current_paid_entry = SalaryEntry.objects.filter(year=year, month=month, paid__gt=0).first()
        if current_paid_entry:
            return float(current_paid_entry.paid)

        # 2. Check active company
        active_company = Company.objects.filter(is_active=True).order_by("order", "id").first()
        if active_company:
            active_paid_entry = SalaryEntry.objects.filter(company=active_company, paid__gt=0).order_by("-year", "-id").first()
            if active_paid_entry:
                return float(active_paid_entry.paid)

            active_month_entry = SalaryEntry.objects.filter(company=active_company, year=year, month=month).first()
            if active_month_entry and float(active_month_entry.expected) > 0:
                return float(active_month_entry.expected)

            if float(active_company.current_salary_amount) > 0:
                return float(active_company.current_salary_amount)

    except Exception:
        pass

    # 3. No active company and no paid salary for current month -> 0.0 (Resigned / No active employment)
    return 0.0
