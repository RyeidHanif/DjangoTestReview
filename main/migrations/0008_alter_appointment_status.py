# Generated by Django 5.2.4 on 2025-07-14 11:02

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("main", "0007_appointment_total_price_providerprofile_rate"),
    ]

    operations = [
        migrations.AlterField(
            model_name="appointment",
            name="status",
            field=models.CharField(
                choices=[
                    ("pending", "Pending"),
                    ("accepted", "Accepted"),
                    ("rejected", "Rejected"),
                    ("completed", "Completed"),
                    ("cancelled", "Cancelled"),
                ],
                default="pending",
                max_length=12,
            ),
        ),
    ]
