# Generated by Django 5.2.4 on 2025-07-16 11:30

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("main", "0011_alter_appointment_status_notificationpreferences"),
    ]

    operations = [
        migrations.AddField(
            model_name="providerprofile",
            name="buffer",
            field=models.IntegerField(default=0),
        ),
    ]
