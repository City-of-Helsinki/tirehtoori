from urllib.parse import urljoin

from django.http import Http404
from django.shortcuts import get_object_or_404
from django.shortcuts import redirect as django_redirect
from ninja import Router

from redirect.models import Domain, RedirectRule

router = Router()


@router.get("/{path:path}")
def redirect(request, path: str):
    domain = get_object_or_404(Domain, names__name=request.get_host())
    try:
        redirect_rule = get_object_or_404(
            RedirectRule, path__iexact=path.strip("/"), domain=domain
        )
    except Http404:
        wildcard_redirects = RedirectRule.objects.filter(
            domain=domain, match_subpaths=True
        )
        for wildcard_rule in wildcard_redirects:
            if path.startswith(wildcard_rule.path):
                redirect_rule = wildcard_rule
                break
        else:
            # No wildcard rule matched, raise 404
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
