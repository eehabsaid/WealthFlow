from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0018_alter_reminderlog_fired_on"),
    ]

    operations = [
        migrations.CreateModel(
            name="Goal",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=200)),
                ("goal_type", models.CharField(max_length=100)),
                ("target_amount", models.DecimalField(decimal_places=2, default=0, max_digits=18)),
                ("target_date", models.DateField(blank=True, null=True)),
                ("current_saved_amount", models.DecimalField(decimal_places=2, default=0, max_digits=18)),
                (
                    "priority",
                    models.CharField(
                        choices=[("High", "High"), ("Medium", "Medium"), ("Low", "Low")],
                        default="Medium",
                        max_length=20,
                    ),
                ),
                ("notes", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "currency",
                    models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to="core.currency"),
                ),
                (
                    "linked_asset",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="linked_goals",
                        to="core.fixedasset",
                    ),
                ),
            ],
            options={"ordering": ["target_date", "id"]},
        ),
    ]
