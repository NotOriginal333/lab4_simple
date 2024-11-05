# Generated by Django 4.0.10 on 2024-11-05 13:21

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0017_remove_cottage_user_alter_cottage_amenities'),
    ]

    operations = [
        migrations.AddField(
            model_name='cottage',
            name='user',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL),
            preserve_default=False,
        ),
    ]
