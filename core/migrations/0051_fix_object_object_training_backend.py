from django.db import migrations


def fix_object_object_training_backend(apps, schema_editor):
    """
    Fixes AIModelVersion rows whose training_backend was corrupted to the
    literal string "[object Object]" by a pre-existing frontend bug
    (b98ed64) that built <option> tags from {name, is_available} backend
    objects instead of their .name field. Every currently supported
    training backend is Ollama-based, so any corrupted row is corrected
    to "ollama". No other field is touched.
    """
    AIModelVersion = apps.get_model("core", "AIModelVersion")
    AIModelVersion.objects.filter(training_backend="[object Object]").update(
        training_backend="ollama"
    )


def noop_reverse(apps, schema_editor):
    # Not reversible: the original corrupted value carried no information
    # worth restoring.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0050_alter_aimodelversion_base_model"),
    ]

    operations = [
        migrations.RunPython(fix_object_object_training_backend, noop_reverse),
    ]
