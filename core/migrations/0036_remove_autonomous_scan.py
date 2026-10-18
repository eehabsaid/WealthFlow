from django.db import migrations, models


def drop_scan_entries(apps, schema_editor):
    """The removed Autonomous App Scan wrote three one-line entries that were injected into every AI prompt."""
    apps.get_model("core", "AIKnowledgeEntry").objects.filter(
        source="autonomous_learning",
        key__in=["app_models_structure", "app_capabilities_registry", "app_codebase_ast_index"],
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0035_refresh_ai_throughput_settings"),
    ]

    operations = [
        migrations.RunPython(drop_scan_entries, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="aiknowledgeentry",
            name="source",
            field=models.CharField(default="manual", max_length=100),
        ),
    ]
