from pytest_factoryboy import register

from redirect.factories import DomainFactory, DomainNameFactory, RedirectRuleFactory

register(DomainFactory)
register(DomainNameFactory)
register(RedirectRuleFactory)
