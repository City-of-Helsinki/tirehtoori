import json
from dataclasses import dataclass

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from redirect.models import Domain, DomainName, RedirectRule


class SentinelValue:
    def __bool__(self):
        raise ValueError("Value not set")

    def __eq__(self, other):
        raise ValueError("Value not set")


NOT_SET = SentinelValue()


class ImporterError(Exception):
    pass


class DryRunException(Exception):
    pass


class SkipIteration(Exception):
    """Used for flow control in nested loops"""


@dataclass
class Stats:
    successful: int = 0
    failed: int = 0
    total: int = 0

    @property
    def skipped(self):
        return self.total - self.successful - self.failed


class Command(BaseCommand):
    help = "Import redirect rules from a JSON file"

    def __init__(self):
        super().__init__()
        self.force: bool = NOT_SET  # noqa
        self.collected_errors = []
        self.rule_import_stats = Stats()
        self.domain_import_stats = Stats()

    def add_arguments(self, parser):
        parser.add_argument(
            "json_file", type=str, help="The JSON file containing redirect rules"
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Run the import without saving to the database",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Force the import to continue even if there are errors",
        )

    # Shortcuts for printing messages

    def _info(self, message: str):
        self.stdout.write(message)

    def _success(self, message: str):
        self.stdout.write(self.style.SUCCESS(message))

    def _warning(self, message: str):
        self.stdout.write(self.style.WARNING(message))

    def _error(self, message: str):
        self.stdout.write(self.style.ERROR(message))

    # Shortcuts end

    def _prepend_timestamp_note(self, notes: str) -> str:
        return f"Generated by import command on {timezone.now()}\n{notes}"

    def raise_or_skip(self, message: str, error_type=ImporterError):
        """Raise an error or continue if --force is set"""
        self._error(message)
        if self.force:
            self._warning("Continuing due to --force")
            self.collected_errors.append(message)
            raise SkipIteration()
        raise error_type(message)

    def process_rule(self, domain, rule):
        # Validate rule
        if RedirectRule.objects.filter(
            domain=domain, path=rule["path"].strip("/")
        ).exists():
            self.raise_or_skip(
                f"Rule for {rule['path']} already exists for domain {domain}"
            )

        create_kwargs = dict(
            domain=domain,
            path=rule["path"],
            destination=rule["destination"],
            permanent=rule.get("permanent"),
            case_sensitive=rule.get("case_sensitive"),
            pass_query_string=rule.get("pass_query_string"),
            match_subpaths=rule.get("match_subpaths"),
            append_subpath=rule.get("append_subpath"),
            notes=rule.get("notes", ""),
        )
        create_kwargs["notes"] = self._prepend_timestamp_note(create_kwargs["notes"])
        create_kwargs = {k: v for k, v in create_kwargs.items() if v is not None}

        obj = RedirectRule.objects.create(**create_kwargs)

        self._info(f"Created rule {obj.path or '/'} -> {obj.destination}")
        self.rule_import_stats.successful += 1

    def process_domain(self, item, index):
        # Validate domain names
        if len(item["domain_names"]) == 0:
            self.raise_or_skip(f"No domain names provided for item at index {index}")
        if DomainName.objects.filter(name__in=item["domain_names"]).exists():
            self.raise_or_skip(
                f"Domain names {item['domain_names']} already "
                f"exist for item at index {index}"
            )

        domain = Domain.objects.create(
            display_name=item.get("display_name") or item["domain_names"][0],
            notes=self._prepend_timestamp_note(item.get("notes", "")),
        )

        for domain_name in item["domain_names"]:
            DomainName.objects.create(name=domain_name, domain=domain)

        self._info(f"Created domain {domain}")
        self.domain_import_stats.successful += 1

        for rule in item["rules"]:
            try:
                self.process_rule(domain, rule)
            except SkipIteration:
                self.rule_import_stats.failed += 1

    def show_summary(self):
        self._info("\n========== summary ==========")
        self._info("domains:")
        if self.domain_import_stats.successful:
            self._success(f"{self.domain_import_stats.successful} imported")
        if self.domain_import_stats.failed:
            self._error(f"{self.domain_import_stats.failed} failed to import")
        self._info(f"total: {self.domain_import_stats.total}")

        self._info("\nredirect rules:")
        if self.rule_import_stats.successful:
            self._success(f"{self.rule_import_stats.successful} imported")
        if self.rule_import_stats.failed:
            self._error(f"{self.rule_import_stats.failed} failed to import")
        if self.rule_import_stats.skipped:
            self._warning(f"{self.rule_import_stats.skipped} skipped")
        self._info(f"total: {self.rule_import_stats.total}")

        if self.collected_errors:
            self._warning("\n========== errors ==========")
            for error in self.collected_errors:
                self._error(error)

    def handle(self, *args, **kwargs):
        dry_run = kwargs["dry_run"]
        self.force = kwargs["force"]

        if dry_run:
            self._warning("Running in dry-run mode")

        json_file = kwargs["json_file"]
        with open(json_file, "r") as file:
            data = json.load(file)

        self.domain_import_stats.total = len(data)
        self._info(f"Found {self.domain_import_stats.total} item(s).")
        self.rule_import_stats.total = sum(len(item["rules"]) for item in data)
        self._info(f"Found {self.rule_import_stats.total} rule(s) in total.")

        try:
            with transaction.atomic():
                for index, item in enumerate(data):
                    self._info(f"--- Processing item #{index + 1}... ---")
                    try:
                        self.process_domain(item, index)
                    except SkipIteration:
                        self.domain_import_stats.failed += 1
                if dry_run:
                    raise DryRunException()
        except DryRunException:
            pass
        except Exception as e:
            self._error(f"An error occurred: {e}")
            self._error("Rolling back changes")
            raise

        self.show_summary()

        if dry_run:
            self._info("\nFinished import in dry-run mode.")
        else:
            self._info("\nFinished import.")
