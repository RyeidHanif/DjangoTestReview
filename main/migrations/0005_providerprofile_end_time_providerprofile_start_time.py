# Generated by Django 5.2.4 on 2025-07-11 05:39

import datetime

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("main", "0004_appointment_event_id"),
    ]

    operations = [
        migrations.AddField(
            model_name="providerprofile",
            name="end_time",
            field=models.TimeField(default=datetime.time(17, 0)),
        ),
        migrations.AddField(
            model_name="providerprofile",
            name="start_time",
            field=models.TimeField(default=datetime.time(9, 0)),
        ),
    ]
