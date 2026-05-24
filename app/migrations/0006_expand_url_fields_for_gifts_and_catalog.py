# Generated manually to support long Amazon URLs in gifts and product catalog.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        (
            "app",
            "0005_alter_gift_image_alter_guest_photo_url_and_more",
        ),
    ]

    operations = [
        migrations.AlterField(
            model_name="gift",
            name="link",
            field=models.URLField(blank=True, max_length=2048, null=True),
        ),
        migrations.AlterField(
            model_name="gift",
            name="image",
            field=models.URLField(
                blank=True,
                help_text="Cloudinary image URL",
                max_length=2048,
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name="productcatalog",
            name="image_url",
            field=models.URLField(blank=True, max_length=2048),
        ),
        migrations.AlterField(
            model_name="productcatalog",
            name="product_url",
            field=models.URLField(db_index=True, max_length=2048, unique=True),
        ),
    ]
