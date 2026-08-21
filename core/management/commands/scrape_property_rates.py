"""
Management command: python manage.py scrape_property_rates

Scrapes Aqarmap for Cairo district price-per-sqm data (EGP)
and saves the result into AppSettings['property_valuation_rate_map'].

Scheduling examples
-------------------
Linux cron (1st of every month at 03:00):
    0 3 1 * * /path/to/venv/bin/python manage.py scrape_property_rates

Windows Task Scheduler (monthly trigger):
    Program : python
    Arguments: manage.py scrape_property_rates
    Start in : C:\\path\\to\\WealthFlow

Flags
-----
--dry-run       Print the map that would be saved without writing to DB.
--baseline-only Skip scraping; build map from hardcoded baseline only.
--timeout N     Playwright page timeout in seconds (default: 25).
--force         Write even if the new map is identical to the current one.
"""
from __future__ import annotations

import json

from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Scrape Aqarmap EGP/sqm rates and update property_valuation_rate_map in AppSettings"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Print the map without saving to DB",
        )
        parser.add_argument(
            "--baseline-only",
            action="store_true",
            help="Skip live scraping; use hardcoded baseline only",
        )
        parser.add_argument(
            "--timeout",
            type=int,
            default=25,
            metavar="SECONDS",
            help="Playwright page timeout in seconds (default: 25)",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Save even if map is unchanged",
        )

    def handle(self, *args, **options):
        from core.models import AppSettings
        from core.services.fixed_assets.aqarmap_scraper import (
            build_rate_map,
            CAIRO_BASELINE,
            GOVERNORATE_BASELINE,
            DEFAULT_RATE,
        )

        dry_run = options["dry_run"]
        baseline_only = options["baseline_only"]
        timeout_ms = options["timeout"] * 1_000
        force = options["force"]

        # ------------------------------------------------------------------ #
        # 1. Build the rate map                                               #
        # ------------------------------------------------------------------ #
        self.stdout.write("Building property rate map …")

        if baseline_only:
            self.stdout.write("  Mode: baseline only (scraping skipped)")
            rate_map = {
                "by_city": CAIRO_BASELINE.copy(),
                "by_governorate": GOVERNORATE_BASELINE.copy(),
                "default": DEFAULT_RATE,
                "source": "baseline_only",
            }
        else:
            self.stdout.write("  Mode: live scrape (Aqarmap) + baseline fallback")
            try:
                rate_map = build_rate_map(timeout_ms=timeout_ms)
            except Exception as exc:
                raise CommandError(f"Failed to build rate map: {exc}") from exc

        source = rate_map.get("source", "unknown")
        n_city = len(rate_map.get("by_city", {}))
        n_gov = len(rate_map.get("by_governorate", {}))

        self.stdout.write(
            self.style.SUCCESS(
                f"  Source       : {source}\n"
                f"  Districts    : {n_city}\n"
                f"  Governorates : {n_gov}\n"
                f"  Default rate : {rate_map['default']:,.0f} EGP/sqm"
            )
        )

        # ------------------------------------------------------------------ #
        # 2. Serialise                                                         #
        # ------------------------------------------------------------------ #
        new_json = json.dumps(rate_map, ensure_ascii=False, indent=2)

        # ------------------------------------------------------------------ #
        # 3. Dry-run: just print                                              #
        # ------------------------------------------------------------------ #
        if dry_run:
            self.stdout.write("\n--- DRY RUN (not saved) ---")
            self.stdout.write(new_json)
            return

        # ------------------------------------------------------------------ #
        # 4. Compare with existing value                                      #
        # ------------------------------------------------------------------ #
        existing_raw = AppSettings.get("property_valuation_rate_map", "")
        if existing_raw and not force:
            try:
                existing = json.loads(existing_raw)
                if (
                    existing.get("by_city") == rate_map.get("by_city")
                    and existing.get("by_governorate") == rate_map.get("by_governorate")
                    and existing.get("default") == rate_map.get("default")
                ):
                    self.stdout.write(
                        self.style.WARNING(
                            "Map is identical to current DB value — skipping save. "
                            "Use --force to override."
                        )
                    )
                    return
            except (json.JSONDecodeError, TypeError):
                pass  # existing value is malformed → overwrite

        # ------------------------------------------------------------------ #
        # 5. Save                                                              #
        # ------------------------------------------------------------------ #
        AppSettings.set(
            "property_valuation_rate_map",
            new_json,
        )

        # Ensure description is set for the settings UI
        try:
            obj = AppSettings.objects.get(key="property_valuation_rate_map")
            if not obj.description:
                obj.description = (
                    "Auto-updated EGP/sqm rates by district/governorate. "
                    "JSON with keys: by_city, by_governorate, default."
                )
                obj.save(update_fields=["description"])
        except AppSettings.DoesNotExist:
            pass

        self.stdout.write(
            self.style.SUCCESS(
                f"\n✓ property_valuation_rate_map saved to AppSettings "
                f"({len(new_json):,} bytes)"
            )
        )

        # ------------------------------------------------------------------ #
        # 6. Summary table                                                    #
        # ------------------------------------------------------------------ #
        self.stdout.write("\nTop 10 districts by rate (EGP/sqm):")
        top = sorted(
            rate_map["by_city"].items(), key=lambda x: x[1], reverse=True
        )[:10]
        for name, rate in top:
            self.stdout.write(f"  {name:<35} {rate:>10,.0f}")
