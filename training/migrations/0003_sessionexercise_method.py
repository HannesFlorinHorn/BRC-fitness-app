from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("training", "0002_seed_categories"),
    ]

    operations = [
        # No session exercises exist yet; the default only satisfies NOT NULL
        # while the column is added and is not kept on the model.
        migrations.AddField(
            model_name="sessionexercise",
            name="method",
            field=models.PositiveSmallIntegerField(
                choices=[(1, "Methode 1"), (2, "Methode 2")], default=1, editable=False
            ),
            preserve_default=False,
        ),
    ]
