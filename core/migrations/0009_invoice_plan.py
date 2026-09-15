import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0008_plan_allows_ai_workspace'),
    ]

    operations = [
        migrations.AddField(
            model_name='invoice',
            name='plan',
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='invoices',
                to='core.plan',
            ),
        ),
        migrations.RunSQL(
            sql="DELETE FROM core_invoice WHERE plan_id IS NULL;",
            reverse_sql=migrations.RunSQL.noop,
        ),
        migrations.AlterField(
            model_name='invoice',
            name='plan',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name='invoices',
                to='core.plan',
            ),
        ),
    ]
