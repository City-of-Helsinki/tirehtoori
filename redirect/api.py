from django.shortcuts import get_object_or_404
from django.shortcuts import redirect as django_redirect
from ninja import Router

from redirect.models import Domain, RedirectRule

router = Router()


@router.get("/{path:value}")
def redirect(request, value: str):
    domain = get_object_or_404(Domain, name=request.get_host())
    obj = get_object_or_404(RedirectRule, path__iexact=value.strip("/"), domain=domain)
    return django_redirect(obj.destination, permanent=obj.permanent)


@router.get("/")
def redirect_root(request):
    return redirect(request, "")
