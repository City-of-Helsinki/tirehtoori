# Generated by Django 5.1.1 on 2024-09-30 11:44

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("redirect", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="redirectrule",
            name="pass_query_string",
            field=models.BooleanField(
                default=False,
                help_text="If checked, query parameters will be passed to the "
                "destination URL. Similar to nginx's $args/$query_string.",
                verbose_name="Pass query string to destination URL",
            ),
        ),
    ]
