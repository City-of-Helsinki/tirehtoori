from django.contrib import admin

from .models import Domain, DomainName, RedirectRule


class CommonPathPrefixListFilter(admin.SimpleListFilter):
    title = "Common path prefix"
    parameter_name = "common_path_prefix"

    def lookups(self, request, model_admin: admin.ModelAdmin):
        qs = model_admin.get_queryset(request)
        paths = qs.filter(path__contains="/").values_list("path", flat=True)
        path_counts = {}

        # Count the number of times each prefix appears in the paths
        # e.g. for paths = ["/foo/bar", "/foo/baz", "/foo/bar/baz"],
        # path_counts = {"/foo": 3, "/foo/bar": 2, "/foo/baz": 1, "/foo/bar/baz": 1}
        for path in paths:
            parts = path.split("/")
            for i in range(1, len(parts)):
                prefix = "/".join(parts[:i])
                path_counts[prefix] = path_counts.get(prefix, 0) + 1

        return [(prefix, prefix) for prefix, count in path_counts.items() if count > 1]

    def queryset(self, request, queryset):
        value = self.value()
        if value:
            return queryset.filter(path__startswith=value)


@admin.register(RedirectRule)
class RedirectRuleAdmin(admin.ModelAdmin):
    list_display = ("path", "domain", "destination", "permanent", "case_sensitive")
    search_fields = ("path", "destination")
    list_filter = (
        "permanent",
        "case_sensitive",
        "domain",
        CommonPathPrefixListFilter,
    )
    ordering = ("path",)
    readonly_fields = ("created_at", "updated_at")
    fieldsets = (
        (
            None,
            {
                "fields": (
                    "path",
                    "destination",
                    "domain",
                    "permanent",
                    "case_sensitive",
                )
            },
        ),
        ("Timestamps", {"fields": ("created_at", "updated_at")}),
    )


class DomainNameInline(admin.TabularInline):
    model = DomainName
    extra = 1


@admin.display(description="Domain names")
def domain_names(self):
    return ", ".join(self.names.values_list("name", flat=True))


@admin.register(Domain)
class DomainAdmin(admin.ModelAdmin):
    inlines = [DomainNameInline]
    list_display = (
        "display_name",
        domain_names,
    )
    search_fields = ("display_name", "names__name")
    ordering = ("display_name",)
    readonly_fields = ("created_at", "updated_at")

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related("names")
