import factory
from pytest_factoryboy import register

from redirect.models import Domain, RedirectRule


@register
class DomainFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Domain

    name = factory.Faker("domain_name")


@register
class RedirectRuleFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = RedirectRule

    path = factory.Faker("uri_path")
    destination = factory.Faker("url")
    domain = factory.SubFactory(DomainFactory)
