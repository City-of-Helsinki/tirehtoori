from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q


class TimestampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Domain(TimestampedModel):
    display_name = models.CharField(
        max_length=255,
        unique=True,
        verbose_name="Display name",
        help_text="Display name for the domain. For informational purposes only.",
    )
    notes = models.TextField(
        blank=True,
        verbose_name="Notes",
        help_text="Additional notes about the domain.",
    )

    def __str__(self):
        domain_names = self.names.values_list("name", flat=True)
        return f"{self.display_name} ({', '.join(domain_names)})"


class DomainName(TimestampedModel):
    name = models.CharField(
        max_length=255,
        unique=True,
        verbose_name="Domain name",
        help_text="The domain name to redirect from. Do not include the protocol "
        'or path. E.g. "example.com"',
    )
    domain = models.ForeignKey(
        Domain,
        on_delete=models.CASCADE,
        related_name="names",
        verbose_name="Domain",
    )

    def __str__(self):
        return self.name


class RedirectRule(TimestampedModel):
    domain = models.ForeignKey(
        Domain,
        on_delete=models.CASCADE,
        related_name="redirect_rules",
        verbose_name="Domain",
        help_text="The domain to redirect from.",
    )
    path = models.CharField(
        max_length=1000,
        verbose_name="Path",
        help_text="The path to redirect from. Leading and trailing slashes will be "
        "stripped on save.",
        db_index=True,
    )
    destination = models.URLField(
        max_length=1000,
        verbose_name="Destination URL",
        help_text="The URL to redirect to.",
    )
    permanent = models.BooleanField(
        default=False,
        verbose_name="Permanent redirect",
        help_text="If checked, a 301 status code will be used instead of 302.",
    )
    pass_query_string = models.BooleanField(
        default=False,
        verbose_name="Pass query string to destination URL",
        help_text="If checked, query parameters will be passed to the destination URL. "
        "Similar to nginx's $args/$query_string.",
    )
    match_subpaths = models.BooleanField(
        default=False,
        verbose_name="Match subpaths",
        help_text="If checked, requests to subpaths will also be redirected. For "
        "example, /foo/bar will redirect to the same destination as /foo. "
        "In case of conflict, the most specific rule will be used.",
    )
    append_subpath = models.BooleanField(
        default=False,
        verbose_name="Append subpath",
        help_text="If checked, the subpath will be appended to the destination URL. "
        "For example, /foo/bar will redirect to the destination URL + /bar. "
        'Does nothing if "Match subpaths" is not checked.',
    )
    case_sensitive = models.BooleanField(default=False)
    notes = models.TextField(
        blank=True,
        verbose_name="Notes",
        help_text="Additional notes about the redirect rule.",
    )

    class Meta:
        ordering = ("path",)
        constraints = [
            models.UniqueConstraint(
                fields=["domain", "path"], name="unique_domain_path"
            )
        ]

    def __str__(self):
        return f"{self.domain.display_name}/{self.path} -> {self.destination}"

    def save(self, *args, **kwargs):
        self.clean()
        return super().save(*args, **kwargs)

    def clean(self):
        # Normalize path.
        self.path = self.path.strip().strip("/")

        if self.case_sensitive:
            self._validate_case_sensitive_path()
        else:
            self._validate_case_insensitive_path()

        if self.match_subpaths:
            self._validate_match_subpaths()

    def _validate_case_sensitive_path(self):
        """
        Check for case-sensitive conflicts with existing rules.
        """
        conflicting_rules = RedirectRule.objects.filter(
            # Compare against case-sensitive rules
            Q(domain=self.domain, path=self.path, case_sensitive=True)
            # Compare against case-insensitive rules
            | Q(domain=self.domain, path__iexact=self.path, case_sensitive=False)
        ).exclude(pk=self.pk)
        if conflicting_rules.exists():
            raise ValidationError(
                f"Path {self.path} conflicts with existing rule(s): "
                f"{', '.join(rule.path for rule in conflicting_rules)}"
            )

    def _validate_case_insensitive_path(self):
        """
        Check for case-insensitive conflicts with existing rules.
        """
        conflicting_rules = RedirectRule.objects.filter(
            domain=self.domain, path__iexact=self.path
        ).exclude(pk=self.pk)
        if conflicting_rules.exists():
            raise ValidationError(
                f"Path {self.path} conflicts with existing rule(s): "
                f"{', '.join(rule.path for rule in conflicting_rules)}"
            )

    def _validate_match_subpaths(self):
        """
        Check for conflicts with existing wildcard rules; a path cannot be a subpath of
        a wildcard rule, i.e. only one wildcard rule can match a given path.

        This is so we can avoid dealing with any ambiguity. For example, if we have
        two rules /foo(.*) and /foo/bar(.*) and a request is made to /foo/bar, we'd
        have to otherwise decide which rule to use.
        :return:
        """
        for rule in RedirectRule.objects.filter(
            domain=self.domain, match_subpaths=True
        ):
            if rule == self:
                # No conflicts with itself, e.g. when updating an existing rule
                continue

            if self.case_sensitive and rule.case_sensitive:
                a = self.path
                b = rule.path
            else:
                a = self.path.lower()
                b = rule.path.lower()
            if a.startswith(f"{b}/") or b.startswith(f"{a}/"):
                raise ValidationError(
                    f"Path {self.path} conflicts with existing rule {rule.path}"
                )
