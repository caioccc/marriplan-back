from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0029_weddingidentityinspiration'),
    ]

    operations = [
        migrations.CreateModel(
            name='WeddingIdentityShareToken',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('token', models.CharField(db_index=True, max_length=64, unique=True)),
                ('wedding_profile', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='wedding_identity_share_token', to='app.userweddingprofile')),
            ],
            options={
                'abstract': False,
            },
        ),
    ]