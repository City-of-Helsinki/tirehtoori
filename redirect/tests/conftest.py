from pytest_factoryboy import register
from redirect.factories import DomainFactory, RedirectRuleFactory

register(DomainFactory)
register(RedirectRuleFactory)
