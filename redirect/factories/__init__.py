import factory
from pytest_factoryboy import register

from redirect.models import Domain, DomainName, RedirectRule


@register
class DomainNameFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = DomainName

    name = factory.Faker("domain_name")


@register
class DomainFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Domain

    display_name = factory.Faker("domain_name")

    @factory.post_generation
    def names(self, create, extracted, **__):
        if not create:
            return

        if extracted:
            # Create domain names from the extracted list or str,
            # e.g. DomainFactory(names=["example.com", "example.org"])
            if isinstance(extracted, str):
                extracted = [extracted]
            for name in extracted:
                DomainNameFactory(domain=self, name=name)
        else:
            # Create a default domain name
            DomainNameFactory(domain=self)


@register
class RedirectRuleFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = RedirectRule

    path = factory.Faker("uri_path")
    destination = factory.Faker("url")
    domain = factory.SubFactory(DomainFactory)
