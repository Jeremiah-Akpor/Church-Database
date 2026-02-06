from django.db import migrations


def seed_default_categories(apps, schema_editor):
    DonationCategory = apps.get_model("donations", "DonationCategory")

    defaults = [
        ("Offertory", "General offering collected during services."),
        ("Tithe", "Regular tithe contribution."),
        ("Missions", "Support for missions and outreach."),
        ("Building Fund", "Building and facility development support."),
        ("Thanksgiving", "Special thanksgiving offering."),
        ("Welfare", "Support for church welfare and benevolence."),
    ]

    for name, description in defaults:
        DonationCategory.objects.get_or_create(
            name=name,
            defaults={
                "description": description,
                "is_active": True,
            },
        )


def remove_default_categories(apps, schema_editor):
    DonationCategory = apps.get_model("donations", "DonationCategory")
    names = [
        "Offertory",
        "Tithe",
        "Missions",
        "Building Fund",
        "Thanksgiving",
        "Welfare",
    ]
    DonationCategory.objects.filter(name__in=names).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("donations", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_default_categories, remove_default_categories),
    ]
