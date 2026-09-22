from django.db import migrations

# Real measured decode rate on this hardware (from AI-TIMING logs): ~1.18-1.9
# tok/s. At the previous ai_max_tokens=4096, a runaway generation could take
# up to ~58 minutes before the model itself stops (ai_total_loop_timeout=300s
# would eventually abort the request, but abruptly mid-answer rather than the
# model finishing cleanly). 800 gives ~2x headroom over the longest real
# answer seen so far (434 tokens, full correct answer) while capping the
# worst case at ~11 minutes instead of ~58.
OLD_VALUE = "4096"
NEW_VALUE = "1024"


def lower_max_tokens(apps, schema_editor):
    AppSettings = apps.get_model("core", "AppSettings")
    row = AppSettings.objects.filter(key="ai_max_tokens", owner__isnull=True).first()
    if row is None:
        AppSettings.objects.create(key="ai_max_tokens", owner=None, value=NEW_VALUE)
    elif row.value == OLD_VALUE:
        # Only touch it if it's still at the old default — don't clobber a
        # value Ehab may have already changed by hand since.
        row.value = NEW_VALUE
        row.save(update_fields=["value"])


def restore_previous_value(apps, schema_editor):
    AppSettings = apps.get_model("core", "AppSettings")
    row = AppSettings.objects.filter(key="ai_max_tokens", owner__isnull=True).first()
    if row is not None and row.value == NEW_VALUE:
        row.value = OLD_VALUE
        row.save(update_fields=["value"])


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0019_pin_user_default_currency"),
    ]

    operations = [
        migrations.RunPython(lower_max_tokens, restore_previous_value),
    ]
