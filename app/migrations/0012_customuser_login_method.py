from django.db import migrations, models
from django.contrib.auth.hashers import is_password_usable


def forwards_set_login_method(apps, schema_editor):
    CustomUser = apps.get_model('app', 'CustomUser')

    for user in CustomUser.objects.all().iterator():
        login_method = 'LOGIN_MARRIPLAN'
        if not is_password_usable(user.password):
            login_method = 'LOGIN_GOOGLE'
        if user.login_method != login_method:
            user.login_method = login_method
            user.save(update_fields=['login_method'])


def reverse_set_login_method(apps, schema_editor):
    CustomUser = apps.get_model('app', 'CustomUser')
    CustomUser.objects.filter(login_method='LOGIN_GOOGLE').update(login_method='LOGIN_MARRIPLAN')


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0011_alter_gift_product_code'),
    ]

    operations = [
        migrations.AddField(
            model_name='customuser',
            name='login_method',
            field=models.CharField(choices=[('LOGIN_GOOGLE', 'Google'), ('LOGIN_MARRIPLAN', 'Marriplan')], default='LOGIN_MARRIPLAN', max_length=20),
        ),
        migrations.RunPython(forwards_set_login_method, reverse_set_login_method),
    ]