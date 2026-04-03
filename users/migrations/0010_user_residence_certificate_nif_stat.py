from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0009_merge_20260318_1148"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="nif",
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AddField(
            model_name="user",
            name="residence_certificate",
            field=models.ImageField(blank=True, null=True, upload_to="residence/certificates/"),
        ),
        migrations.AddField(
            model_name="user",
            name="stat",
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
    ]
