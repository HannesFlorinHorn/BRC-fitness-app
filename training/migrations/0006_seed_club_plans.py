from django.db import migrations

# Empty for now; their exercises are seeded once the owner sends the list.
CLUB_PLANS = ["Legs", "Arms", "Core"]


def add_club_plans(apps, schema_editor):
    Plan = apps.get_model("training", "Plan")
    for name in CLUB_PLANS:
        Plan.objects.get_or_create(name=name, owner=None)


class Migration(migrations.Migration):

    dependencies = [
        ("training", "0005_plans"),
    ]

    operations = [
        migrations.RunPython(add_club_plans, migrations.RunPython.noop),
    ]
