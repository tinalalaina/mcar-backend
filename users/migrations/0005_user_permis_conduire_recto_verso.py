from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0004_alter_user_is_staff"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="permis_conduire_recto",
            field=models.ImageField(
                blank=True,
                null=True,
                upload_to="permis/photos/recto/",
            ),
        ),
        migrations.AddField(
            model_name="user",
            name="permis_conduire_verso",
            field=models.ImageField(
                blank=True,
                null=True,
                upload_to="permis/photos/verso/",
            ),
        ),
    ]
