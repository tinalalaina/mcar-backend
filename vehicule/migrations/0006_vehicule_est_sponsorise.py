from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("vehicule", "0005_alter_vehicule_est_disponible_alter_vehicule_titre_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="vehicule",
            name="est_sponsorise",
            field=models.BooleanField(db_index=True, default=False, verbose_name="Véhicule sponsorisé"),
        ),
    ]
