from django.db import migrations

# (key, estimate set by migration 0035, speed measured in the [AI-TIMING] log: qwen3.6:27b fully on the RTX 5090)
CHANGES = (("ai_prompt_tps", "700", "2500"), ("ai_decode_tps", "30", "62"))


def _move(apps, old_index, new_index):
    """Only a row still holding the previous estimate is changed: a value typed by the owner is never overwritten."""
    AppSettings = apps.get_model("core", "AppSettings")
    for change in CHANGES:
        AppSettings.objects.filter(key=change[0], owner__isnull=True, value=change[old_index]).update(value=change[new_index])


def forwards(apps, schema_editor):
    _move(apps, 1, 2)


def backwards(apps, schema_editor):
    _move(apps, 2, 1)


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0036_remove_autonomous_scan'),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
