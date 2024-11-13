"""
URL configuration for tirehtoori project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.conf import settings
from django.contrib import admin
from django.urls import path, re_path

from .api import api

urlpatterns = []

if settings.ENABLE_ADMIN_APP:
    urlpatterns.append(path(f"{settings.ADMIN_URL}/", admin.site.urls))

if settings.ENABLE_REDIRECT_APP:
    if settings.ENABLE_ADMIN_APP:
        # NOTE: Django uses a cache for url resolving. If any other, non-system url is
        # requested before admin, the cache will be populated with the catch-all
        # redirect url, causing all admin urls to be resolved to the catch-all
        # redirect view. Using a negative lookahead assertion to exclude admin urls
        # fixes this issue.
        # Keep this in mind if you need to add any other "reserved" urls.
        urlpatterns.append(re_path(rf"^(?!{settings.ADMIN_URL})", api.urls))
    else:
        urlpatterns.append(path("", api.urls))
