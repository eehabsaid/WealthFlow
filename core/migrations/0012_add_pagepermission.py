from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0011_alter_balanceentry_entry_date'),
    ]

    operations = [
        migrations.CreateModel(
            name='PagePermission',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('page', models.CharField(choices=[('dashboard', 'Dashboard'), ('companies', 'Companies'), ('salary', 'Salary'), ('banks', 'Banks'), ('bank_certificates', 'Bank Certificates'), ('currencies', 'Currencies'), ('balance', 'Balance'), ('settings', 'Settings'), ('exchange_rates', 'Exchange Rates'), ('gold_price', 'Gold Price'), ('user_management', 'User Management')], max_length=50)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='page_permissions', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['user__username', 'page'],
                'unique_together': {('user', 'page')},
            },
        ),
    ]
