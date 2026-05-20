from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0024_checklisttask_notes'),
    ]

    operations = [
        migrations.AddField(
            model_name='guest',
            name='photo_public_id',
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name='guest',
            name='photo_url',
            field=models.URLField(blank=True, null=True),
        ),
    ]