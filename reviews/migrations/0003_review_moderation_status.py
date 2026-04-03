from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("reviews", "0002_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="review",
            name="moderation_status",
            field=models.CharField(
                choices=[
                    ("PENDING", "En attente"),
                    ("APPROVED", "Approuvé"),
                    ("REJECTED", "Rejeté"),
                ],
                db_index=True,
                default="PENDING",
                help_text="Statut de modération par le support avant publication.",
                max_length=20,
            ),
        ),
    ]
