from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("training", "0003_sessionexercise_method"),
    ]

    operations = [
        # Session categories are now derived from the logged exercises.
        migrations.RemoveField(
            model_name="session",
            name="categories",
        ),
        # No exercises exist yet; the default only fills the new column while it is added.
        migrations.AddField(
            model_name="exercise",
            name="position",
            field=models.PositiveSmallIntegerField(
                default=1, help_text="Order of this exercise in its plan template."
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="exercise",
            name="is_active",
            field=models.BooleanField(default=True, help_text="Inactive exercises are hidden when logging."),
        ),
        migrations.AlterModelOptions(
            name="exercise",
            options={"ordering": ["category__name", "position", "name"]},
        ),
    ]
