import factory
from faker import Faker
from faker.proxy import UniqueProxy
from pytest_factoryboy import register

from redirect.models import Domain, DomainName, RedirectRule


# As suggested in:
# https://github.com/FactoryBoy/factory_boy/issues/305#issuecomment-986154884
class UniqueFaker(factory.Faker):
    def evaluate(self, instance, step, extra):
        locale = extra.pop("locale")
        subfaker: Faker = self._get_faker(locale)
        unique_proxy: UniqueProxy = subfaker.unique
        return unique_proxy.format(self.provider, **extra)


@register
class DomainNameFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = DomainName

    name = UniqueFaker("domain_name")


@register
class DomainFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Domain
        skip_postgeneration_save = True

    display_name = UniqueFaker("domain_name")

    @factory.post_generation
    def names(obj, create, extracted, **__):  # noqa: N805
        if not create:
            return

        if extracted:
            # Create domain names from the extracted list or str,
            # e.g. DomainFactory(names=["example.com", "example.org"])
            if isinstance(extracted, str):
                extracted = [extracted]
            for name in extracted:
                DomainNameFactory(domain=obj, name=name)
        else:
            # Create a default domain name
            DomainNameFactory(domain=obj)
        obj.save()


@register
class RedirectRuleFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = RedirectRule

    # Not strictly unique, but needs to be unique with domain
    path = UniqueFaker("uri_path")
    destination = factory.Faker("url")
    domain = factory.SubFactory(DomainFactory)
