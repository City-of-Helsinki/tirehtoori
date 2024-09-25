from ninja import Router
from django.shortcuts import redirect as django_redirect, get_object_or_404

from redirect.models import RedirectRule, Domain

router = Router()


@router.get("/{path:value}")
def redirect(request, value: str):
    domain = get_object_or_404(Domain, name=request.get_host())
    obj = get_object_or_404(RedirectRule, path__iexact=value.strip("/"), domain=domain)
    return django_redirect(obj.destination, permanent=obj.permanent)


@router.get("/")
def redirect_root(request):
    return redirect(request, "")
