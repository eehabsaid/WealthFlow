"""
Adds one sample Fixed Asset record for each asset type that currently has
ZERO records in the database (specifically: "Vehicles" and "Other Assets").

WHY THIS EXISTS
----------------
The Documentation Capture engine (doc_engine) discovers "Edit"/"View" asset
modals to screenshot by reading REAL rows from the fixed_assets table for
each asset type - it does not synthesize fake data on the fly. If a given
asset type has no rows, its Edit/View screenshots can never be captured,
no matter how the capture engine or inventory.json are configured.

At the time this command was written, the database contained:
    Real Estate: 1 record
    Gold:        4 records
    Vehicles:    0 records
    Other Assets: 0 records

This command is SAFE and IDEMPOTENT:
  - It NEVER deletes, modifies, or touches any existing record.
  - It only INSERTS a new record for a type if that type currently has
    zero rows. Running it multiple times will not create duplicates.
  - It only acts on "Vehicles" and "Other Assets" - the two types
    confirmed to be empty. If you later add real Vehicle/Other Asset
    records yourself, this command becomes a no-op for those types.

This command does NOT run automatically as part of any capture or
deployment step. Run it manually, only if you want sample data purely so
the Documentation Capture engine can produce complete screenshots:

    python manage.py seed_fixed_asset_type_samples

Use --dry-run to see what would be created without writing anything.
"""
from datetime import date, timedelta

from django.core.management.base import BaseCommand
from django.db import transaction

from core.models.fixed_assets import FixedAsset
from core.models.fixed_assets_vehicle import VehicleDetails
from core.models.fixed_assets_other import OtherAssetDetails


class Command(BaseCommand):
    help = (
        "Adds one sample Fixed Asset record for each asset type (Vehicles, "
        "Other Assets) that currently has zero records, so the Documentation "
        "Capture engine can produce Edit/View screenshots for every asset "
        "type. Never touches existing records. Safe to run multiple times."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be created without writing to the database.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]

        existing_types = set(
            FixedAsset.objects.values_list("asset_type", flat=True).distinct()
        )

        today = date.today()
        purchase_date = today - timedelta(days=365)

        plan = []

        if "Vehicles" not in existing_types:
            plan.append(("Vehicles", self._create_vehicle))

        if "Other Assets" not in existing_types:
            plan.append(("Other Assets", self._create_other_asset))

        if not plan:
            self.stdout.write(self.style.SUCCESS(
                "Nothing to do - both 'Vehicles' and 'Other Assets' already "
                "have at least one record."
            ))
            return

        for asset_type, _ in plan:
            self.stdout.write(f"Will create 1 sample '{asset_type}' record.")

        if dry_run:
            self.stdout.write(self.style.WARNING(
                "--dry-run set: no changes written."
            ))
            return

        with transaction.atomic():
            for asset_type, creator in plan:
                creator(purchase_date)

        self.stdout.write(self.style.SUCCESS(
            f"Done. Created sample record(s) for: {', '.join(t for t, _ in plan)}."
        ))
        self.stdout.write(
            "You can identify these later by the note "
            "'[Doc-engine sample data - safe to delete]' on each record."
        )

    def _create_vehicle(self, purchase_date):
        asset = FixedAsset.objects.create(
            name="Sample Vehicle (Doc Capture)",
            asset_type="Vehicles",
            status="Owned",
            purchase_date=purchase_date,
            purchase_price=500000,
            purchase_usd_rate=50.9,
            purchase_price_usd=9823.18,
            current_market_value=450000,
            valuation_source="Manual",
            notes="[Doc-engine sample data - safe to delete]",
        )
        VehicleDetails.objects.create(
            asset=asset,
            brand="Sample Brand",
            model="Sample Model",
            year=2022,
            vin="SAMPLE0000000001",
            engine="2.0L",
            transmission="Automatic",
            fuel_type="Petrol",
            mileage=15000,
            plate_number="ABC 1234",
            color="White",
        )

    def _create_other_asset(self, purchase_date):
        asset = FixedAsset.objects.create(
            name="Sample Other Asset (Doc Capture)",
            asset_type="Other Assets",
            status="Owned",
            purchase_date=purchase_date,
            purchase_price=20000,
            purchase_usd_rate=50.9,
            purchase_price_usd=392.93,
            current_market_value=18000,
            valuation_source="Manual",
            notes="[Doc-engine sample data - safe to delete]",
        )
        OtherAssetDetails.objects.create(
            asset=asset,
            category="Electronics",
            manufacturer="Sample Manufacturer",
            model="Sample Model",
            serial_number="SN-0000001",
            description="Sample item created only so the Documentation "
                         "Capture engine can screenshot the 'Other Assets' "
                         "edit view.",
        )
