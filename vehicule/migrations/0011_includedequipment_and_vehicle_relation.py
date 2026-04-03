from django.db import migrations, models
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ("vehicule", "0010_vehicledocuments_rejection_reason_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="IncludedEquipment",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("code", models.CharField(max_length=50, unique=True)),
                ("label", models.CharField(max_length=100)),
                ("description", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Équipement inclus",
                "verbose_name_plural": "Équipements inclus",
                "ordering": ["label"],
            },
        ),
        migrations.AddField(
            model_name="vehicule",
            name="included_equipments",
            field=models.ManyToManyField(blank=True, related_name="vehicules", to="vehicule.includedequipment"),
        ),
    ]
