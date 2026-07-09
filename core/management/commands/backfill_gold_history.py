from django.core.management.base import BaseCommand
from core.models import GoldPriceHistory
import yfinance as yf
from datetime import datetime

class Command(BaseCommand):
    help = "Backfill one year of gold history"

    def handle(self, *args, **kwargs):
        self.stdout.write("Downloading Gold history...")

        # Download and clean Gold data
        gold = yf.download("GC=F", period="1y", interval="1d", auto_adjust=True)
        if hasattr(gold.columns, "nlevels") and gold.columns.nlevels > 1:
            gold.columns = gold.columns.get_level_values(0)
        gold.columns = gold.columns.astype(str)

        self.stdout.write("Downloading USD/EGP history...")

        # Download and clean USD/EGP data
        usd_egp = yf.download("EGP=X", period="1y", interval="1d", auto_adjust=True)
        if hasattr(usd_egp.columns, "nlevels") and usd_egp.columns.nlevels > 1:
            usd_egp.columns = usd_egp.columns.get_level_values(0)
        usd_egp.columns = usd_egp.columns.astype(str)

        if gold.empty or usd_egp.empty:
            self.stdout.write(self.style.ERROR("Data not found"))
            return

        inserted = 0

        for date_index, row in gold.iterrows():
            try:
                # Use .at for safe scalar access
                gold_close = float(row.at["Close"])

                if date_index in usd_egp.index:
                    fx_rate = float(usd_egp.at[date_index, "Close"])
                else:
                    continue

                usd_per_oz = gold_close
                usd_per_gram = usd_per_oz / 31.1035
                egp_per_gram_24 = usd_per_gram * fx_rate
                egp_per_gram_21 = egp_per_gram_24 * 0.875
                egp_per_gram_18 = egp_per_gram_24 * 0.75

                GoldPriceHistory.objects.get_or_create(
                    timestamp=datetime.combine(
                        date_index.date(),
                        datetime.min.time()
                    ),
                    defaults={
                        "carat_24k": round(egp_per_gram_24, 2),
                        "carat_21k": round(egp_per_gram_21, 2),
                        "carat_18k": round(egp_per_gram_18, 2),
                        "usd_gram_24k": round(usd_per_gram, 6),
                        "usd_per_oz": round(usd_per_oz, 4),
                        "usd_to_egp": round(fx_rate, 6),
                    }
                )
                inserted += 1

            except Exception as e:
                self.stdout.write(self.style.WARNING(f"Error processing row {date_index}: {e}"))
                continue

        self.stdout.write(
            self.style.SUCCESS(f"Inserted {inserted} historical records.")
        )