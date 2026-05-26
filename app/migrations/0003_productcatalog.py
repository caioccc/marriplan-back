# Generated manually to persist the local product catalog used by the gift scraper.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0002_alter_supplier_city_alter_supplier_company_name_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='ProductCatalog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=255)),
                ('description', models.TextField(blank=True)),
                ('price', models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True)),
                ('image_url', models.URLField(blank=True)),
                ('product_url', models.URLField(db_index=True, unique=True)),
                ('store', models.CharField(db_index=True, max_length=120)),
                ('category', models.CharField(blank=True, db_index=True, max_length=120)),
                ('search_term', models.CharField(blank=True, db_index=True, max_length=255)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'ordering': ['-created_at', 'store', 'title'],
            },
        ),
        migrations.AddIndex(
            model_name='productcatalog',
            index=models.Index(fields=['store', 'category'], name='app_product_store_cat_idx'),
        ),
        migrations.AddIndex(
            model_name='productcatalog',
            index=models.Index(fields=['search_term'], name='app_product_search_idx'),
        ),
    ]
