"""
Management command: python manage.py fetch_rates
Fetches latest exchange rates AND gold price and saves to DB.
Can be scheduled with Windows Task Scheduler or cron.
"""
from django.core.management.base import BaseCommand
import json


class Command(BaseCommand):
    help = "Fetch latest exchange rates and gold price from internet"

    def add_arguments(self, parser):
        parser.add_argument("--rates-only", action="store_true", help="Only fetch exchange rates")
        parser.add_argument("--gold-only",  action="store_true", help="Only fetch gold price")

    def handle(self, *args, **options):
        from django.test import RequestFactory
        from core.views import ExchangeRateRefreshView, GoldPriceRefreshView

        rates_only = options.get("rates_only")
        gold_only  = options.get("gold_only")

        if not gold_only:
            self.stdout.write("Fetching exchange rates...")
            try:
                factory = RequestFactory()
                req     = factory.post("/api/rates/refresh/")
                resp    = ExchangeRateRefreshView.as_view()(req)
                data    = json.loads(resp.content)
                if "error" in data:
                    self.stdout.write(self.style.ERROR(f"  Exchange rates error: {data['error']}"))
                else:
                    self.stdout.write(self.style.SUCCESS(f"  Exchange rates: {data['message']}"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"  Exchange rates exception: {e}"))

        if not rates_only:
            self.stdout.write("Fetching gold price...")
            try:
                factory = RequestFactory()
                req     = factory.post("/api/gold/refresh/")
                resp    = GoldPriceRefreshView.as_view()(req)
                data    = json.loads(resp.content)
                if "error" in data:
                    self.stdout.write(self.style.ERROR(f"  Gold price error: {data['error']}"))
                else:
                    gd = data["gold"]
                    self.stdout.write(self.style.SUCCESS(
                        f"  Gold 21K = {gd['carat_21k']} EGP/g  "
                        f"| USD/EGP = {gd['usd_to_egp']}"
                    ))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"  Gold price exception: {e}"))
