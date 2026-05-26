from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0007_alter_gift_name_alter_gift_purchased_by_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='productcatalog',
            name='is_essential_template',
            field=models.BooleanField(db_index=True, default=False, verbose_name='Template básico'),
        ),
        migrations.AddIndex(
            model_name='productcatalog',
            index=models.Index(fields=['is_essential_template'], name='app_product_is_essential_idx'),
        ),
    ]