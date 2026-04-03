from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("vehicule", "0006_vehicule_est_sponsorise"),
    ]

    operations = [
        migrations.AddField(
            model_name="vehicule",
            name="est_coup_de_coeur",
            field=models.BooleanField(
                db_index=True,
                default=False,
                verbose_name="Véhicule coup de cœur",
            ),
        ),
    ]
