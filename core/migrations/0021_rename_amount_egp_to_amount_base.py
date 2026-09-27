# Generated manually on 2026-09-27 (A6 batch 5): naming-only rename.
# `amount_egp` never meant "always EGP" — it has held the user's own
# base-currency-converted amount since the A6 multi-currency work landed
# (A6 batches 1-4b). This migration only renames the column; it does not
# touch or recompute any stored value.

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0020_lower_ai_max_tokens_cap'),
    ]

    operations = [
        migrations.RenameField(
            model_name='assetacquisitioncost',
            old_name='amount_egp',
            new_name='amount_base',
        ),
        migrations.RenameField(
            model_name='assetfurniture',
            old_name='amount_egp',
            new_name='amount_base',
        ),
        migrations.RenameField(
            model_name='assetrenovation',
            old_name='amount_egp',
            new_name='amount_base',
        ),
        migrations.RenameField(
            model_name='expense',
            old_name='amount_egp',
            new_name='amount_base',
        ),
        migrations.RenameField(
            model_name='creditcardpayment',
            old_name='amount_egp',
            new_name='amount_base',
        ),
        migrations.RenameField(
            model_name='cardrenewalfee',
            old_name='amount_egp',
            new_name='amount_base',
        ),
        migrations.RenameField(
            model_name='perdiem',
            old_name='amount_egp',
            new_name='amount_base',
        ),
    ]
