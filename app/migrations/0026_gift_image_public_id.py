from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0025_guest_photo_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='gift',
            name='image_public_id',
            field=models.CharField(max_length=255, null=True, blank=True),
        ),
    ]
