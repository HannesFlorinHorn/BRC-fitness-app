from django.db import migrations

CATEGORIES = ["legs", "arms", "core"]


def add_categories(apps, schema_editor):
    Category = apps.get_model("training", "Category")
    for name in CATEGORIES:
        Category.objects.get_or_create(name=name)


class Migration(migrations.Migration):

    dependencies = [
        ("training", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(add_categories, migrations.RunPython.noop),
    ]
