# Generated by Django 4.0.10 on 2024-10-28 19:35

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0013_alter_amenities_options_alter_booking_price'),
    ]

    operations = [
        migrations.AddField(
            model_name='amenities',
            name='expenses',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
        ),
    ]