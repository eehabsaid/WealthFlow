from decimal import Decimal, ROUND_HALF_UP
from typing import Optional, Tuple, Dict
from datetime import date
from core.models import ExchangeRate

class CurrencyConversionService:
    """
    Central source of truth for currency conversions across WealthFlow.
    All rate calculations and conversions are performed strictly using buy_rate in the backend.
    """

    @classmethod
    def get_latest_buy_rate(cls, currency_code: str, target_date: Optional[date] = None) -> Decimal:
        """
        Get the latest buy_rate for a currency code against EGP (base currency = 1.0).
        If target_date is provided, filters for rates fetched on or before target_date.
        """
        code = str(currency_code or "").strip().upper()
        if code == "EGP" or not code:
            return Decimal("1.000000")
        
        qs = ExchangeRate.objects.filter(currency_code__iexact=code)
        if target_date:
            qs = qs.filter(fetched_at__date__lte=target_date)
            
        rate = qs.order_by("-fetched_at").first()
        if rate and rate.buy_rate and rate.buy_rate > 0:
            return Decimal(str(rate.buy_rate))
        
        return Decimal("1.000000")

    @classmethod
    def get_all_latest_buy_rates(cls) -> Dict[str, Decimal]:
        """
        Return a dictionary mapping currency_code -> latest buy_rate (Decimal) for all currencies.
        """
        rates: Dict[str, Decimal] = {"EGP": Decimal("1.000000")}
        for rate in ExchangeRate.objects.order_by("currency_code", "-fetched_at"):
            code = str(rate.currency_code or "").upper()
            if code and code not in rates:
                rates[code] = Decimal(str(rate.buy_rate)) if rate.buy_rate and rate.buy_rate > 0 else Decimal("1.000000")
        return rates

    @classmethod
    def calculate_exchange_rate(cls, from_code: str, to_code: str, target_date: Optional[date] = None) -> Decimal:
        """
        Calculate exchange rate from from_code to to_code:
        Rate = (Buy Rate of From Currency in EGP) / (Buy Rate of To Currency in EGP)
        """
        from_c = str(from_code or "").strip().upper()
        to_c = str(to_code or "").strip().upper()

        if from_c == to_c:
            return Decimal("1.000000")

        rate_from = cls.get_latest_buy_rate(from_c, target_date=target_date)
        rate_to = cls.get_latest_buy_rate(to_c, target_date=target_date)

        if rate_to <= 0:
            return Decimal("1.000000")

        rate = (rate_from / rate_to).quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)
        return rate

    @classmethod
    def convert_amount(cls, amount: Decimal, from_code: str, to_code: str, custom_rate: Optional[Decimal] = None, target_date: Optional[date] = None) -> Tuple[Decimal, Decimal]:
        """
        Convert amount from from_code to to_code.
        If custom_rate is provided and > 0, it is used instead of system calculated rate.
        Returns tuple of (applied_rate, converted_amount).
        """
        amt = Decimal(str(amount or 0)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        
        if custom_rate is not None and custom_rate > 0:
            rate = Decimal(str(custom_rate)).quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)
        else:
            rate = cls.calculate_exchange_rate(from_code, to_code, target_date=target_date)

        to_amount = (amt * rate).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        return rate, to_amount

