from decimal import Decimal, ROUND_HALF_UP
from typing import Optional, Tuple
from core.models import ExchangeRate

class CurrencyConversionService:
    """
    Central source of truth for currency conversions across WealthFlow.
    All rate calculations and conversions are performed strictly in the backend.
    """

    @classmethod
    def get_latest_buy_rate(cls, currency_code: str) -> Decimal:
        """
        Get the latest buy_rate for a currency code against EGP (base currency = 1.0).
        """
        code = str(currency_code or "").strip().upper()
        if code == "EGP" or not code:
            return Decimal("1.000000")
        
        rate = ExchangeRate.objects.filter(currency_code=code).order_by("-fetched_at").first()
        if rate and rate.buy_rate and rate.buy_rate > 0:
            return Decimal(str(rate.buy_rate))
        
        return Decimal("1.000000")

    @classmethod
    def calculate_exchange_rate(cls, from_code: str, to_code: str) -> Decimal:
        """
        Calculate exchange rate from from_code to to_code:
        Rate = (Buy Rate of From Currency in EGP) / (Buy Rate of To Currency in EGP)
        """
        from_c = str(from_code or "").strip().upper()
        to_c = str(to_code or "").strip().upper()

        if from_c == to_c:
            return Decimal("1.000000")

        rate_from = cls.get_latest_buy_rate(from_c)
        rate_to = cls.get_latest_buy_rate(to_c)

        if rate_to <= 0:
            return Decimal("1.000000")

        rate = (rate_from / rate_to).quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)
        return rate

    @classmethod
    def convert_amount(cls, amount: Decimal, from_code: str, to_code: str, custom_rate: Optional[Decimal] = None) -> Tuple[Decimal, Decimal]:
        """
        Convert amount from from_code to to_code.
        If custom_rate is provided and > 0, it is used instead of system calculated rate.
        Returns tuple of (applied_rate, converted_amount).
        """
        amt = Decimal(str(amount or 0)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        
        if custom_rate is not None and custom_rate > 0:
            rate = Decimal(str(custom_rate)).quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)
        else:
            rate = cls.calculate_exchange_rate(from_code, to_code)

        to_amount = (amt * rate).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        return rate, to_amount
