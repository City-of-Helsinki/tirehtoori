from urllib.parse import urljoin

from django.http import Http404
from django.shortcuts import get_object_or_404
from django.shortcuts import redirect as django_redirect
from ninja import Router

from redirect.models import Domain, RedirectRule

router = Router()


def get_domain_rule_or_404(domain, path) -> RedirectRule:
    """Get a redirect rule for a domain or raise Http404 if not found."""
    try:
        # Try to find an exact match first
        redirect_rule = RedirectRule.objects.get(
            path=path.strip("/"), domain=domain, case_sensitive=True
        )
    except RedirectRule.DoesNotExist:
        # If no exact match is found, try a case-insensitive match
        redirect_rule = get_object_or_404(
            RedirectRule,
            path__iexact=path.strip("/"),
            domain=domain,
            case_sensitive=False,
        )
    return redirect_rule


def find_wildcard_rule(domain, path) -> RedirectRule | None:
    cleaned_path = path.strip("/")
    wildcard_redirects = RedirectRule.objects.filter(domain=domain, match_subpaths=True)
    for wildcard_rule in wildcard_redirects:
        if wildcard_rule.case_sensitive and cleaned_path.startswith(wildcard_rule.path):
            return wildcard_rule
        if not wildcard_rule.case_sensitive and cleaned_path.lower().startswith(
            wildcard_rule.path.lower()
        ):
            return wildcard_rule

    return None


@router.get("/{path:path}")
def redirect(request, path: str):
    domain = get_object_or_404(Domain, names__name=request.get_host())
    try:
        redirect_rule = get_domain_rule_or_404(domain, path)
    except Http404:
        redirect_rule = find_wildcard_rule(domain, path)
        if redirect_rule is None:
            # No rule found at all, raise 404
            raise

    destination = redirect_rule.destination

    # Append subpath if needed
    if redirect_rule.match_subpaths and redirect_rule.append_subpath:
        # Needs to behave like /foo/(.*) -> someurl.com/(.*), where (.*) is the subpath
        subpath = path.lstrip(redirect_rule.path)
        destination = urljoin(destination, subpath)

    # Append query string if needed
    if redirect_rule.pass_query_string and (
        query_string := request.META.get("QUERY_STRING")
    ):
        destination += f"?{query_string}"

    return django_redirect(destination, permanent=redirect_rule.permanent)


@router.get("/")
def redirect_root(request):
    return redirect(request, "")
