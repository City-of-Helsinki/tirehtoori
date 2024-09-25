import json
from django.core.management.base import BaseCommand
from django.db import transaction

from redirect.models import RedirectRule, Domain


class DryRunException(Exception):
    pass


class Command(BaseCommand):
    help = "Import redirect rules from a JSON file"

    def add_arguments(self, parser):
        parser.add_argument(
            "json_file", type=str, help="The JSON file containing redirect rules"
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Run the import without saving to the database",
        )

    def handle(self, *args, **kwargs):
        dry_run = kwargs["dry_run"]

        if dry_run:
            self.stdout.write(self.style.WARNING("Running in dry-run mode"))

        json_file = kwargs["json_file"]
        with open(json_file, "r") as file:
            data = json.load(file)

        domains = {}
        try:
            with transaction.atomic():
                for item in data:
                    if item["domain"] not in domains:
                        domains[item["domain"]] = Domain.objects.get_or_create(
                            name=item["domain"]
                        )
                    domain = domains[item["domain"]]
                    if item.get("response_code", 302) not in [301, 302]:
                        raise ValueError(
                            f"Invalid response code {item.get('response_code', 302)}"
                        )
                    obj = RedirectRule.objects.create(
                        domain=domain,
                        path=item["path"],
                        destination=item["destination"],
                        permanent=item.get("response_code", 302) == 301,
                        case_sensitive=item.get("case_sensitive", False),
                    )
                    self.stdout.write(f"Imported {obj.path} -> {obj.destination}")
                if dry_run:
                    raise DryRunException()
        except DryRunException:
            pass
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"An error occurred: {e}"))
            self.stdout.write(self.style.ERROR("Rolling back changes"))
            raise

        if dry_run:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Successfully imported {len(data)} redirect rules in dry-run mode"
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(f"Successfully imported {len(data)} redirect rules")
            )
