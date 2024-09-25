from django.db import models


class TimestampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Domain(TimestampedModel):
    name = models.CharField(
        max_length=255,
        unique=True,
        verbose_name="Domain name",
        help_text="The domain name to redirect from. Do not include the protocol or path.",
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
        help_text="The path to redirect from. Leading and trailing slashes will be stripped on save.",
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
    case_sensitive = models.BooleanField(default=False)

    class Meta:
        ordering = ("path",)
        constraints = [
            models.UniqueConstraint(
                fields=["domain", "path"], name="unique_domain_path"
            )
        ]

    def clean(self):
        self.path = self.path.strip().strip("/")

    def save(self, *args, **kwargs):
        self.clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.domain.name}/{self.path} -> {self.destination}"
