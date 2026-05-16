# Generated migration for adding status_presenca field to Guest model

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0016_giftlistsharetoken'),
    ]

    operations = [
        migrations.AddField(
            model_name='guest',
            name='status_presenca',
            field=models.CharField(
                blank=True,
                choices=[('Pending', 'Pendente'), ('Confirmed', 'Confirmado'), ('Refused', 'Recusado')],
                default='Pending',
                help_text='Status de presença do convidado',
                max_length=20,
                null=True
            ),
        ),
    ]
