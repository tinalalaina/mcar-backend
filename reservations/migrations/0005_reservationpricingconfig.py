from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("reservations", "0004_reservation_reference"),
    ]

    operations = [
        migrations.CreateModel(
            name="ReservationPricingConfig",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("service_fee", models.DecimalField(decimal_places=2, default=5000, max_digits=10)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Configuration tarification réservation",
                "verbose_name_plural": "Configuration tarification réservation",
            },
        ),
    ]
