import pytest
from django.contrib.admin import AdminSite

from redirect.admin import CommonPathPrefixListFilter, RedirectRuleAdmin
from redirect.models import RedirectRule


class TestCommonPathPrefixFilter:
    @pytest.fixture
    def model_admin(self):
        return RedirectRuleAdmin(RedirectRule, AdminSite())

    @pytest.fixture
    def filter_factory(self, model_admin):
        def factory(**kwargs):
            kwargs.setdefault("request", None)
            kwargs.setdefault("params", {})
            kwargs.setdefault("model", RedirectRule)
            kwargs.setdefault("model_admin", model_admin)

            return CommonPathPrefixListFilter(**kwargs)

        return factory

    @pytest.fixture
    def filter_instance(self, filter_factory):
        return filter_factory()

    @pytest.mark.django_db
    def test_lookups_returns_common_prefixes(
        self, model_admin, filter_instance, redirect_rule_factory
    ):
        redirect_rule_factory(path="/foo/bar")
        redirect_rule_factory(path="/foo/baz")
        redirect_rule_factory(path="/foo/bar/xyz")
        redirect_rule_factory(path="/foo/bar/baz")

        lookups = filter_instance.lookups(request=None, model_admin=model_admin)

        assert ("foo", "foo") in lookups
        assert ("foo/bar", "foo/bar") in lookups

    @pytest.mark.django_db
    def test_lookups_excludes_unique_prefixes(
        self, model_admin, filter_instance, redirect_rule_factory
    ):
        redirect_rule_factory(path="/foo/bar")
        redirect_rule_factory(path="/bar/baz")

        lookups = filter_instance.lookups(request=None, model_admin=model_admin)

        assert lookups == []

    @pytest.mark.django_db
    def test_queryset_filters_by_prefix(
        self,
        model_admin,
        filter_factory,
        redirect_rule_factory,
    ):
        rule1 = redirect_rule_factory(path="/foo/bar")
        rule2 = redirect_rule_factory(path="/foo/baz")
        rule3 = redirect_rule_factory(path="/bar/baz")
        filter_instance = filter_factory(params={"common_path_prefix": ["foo"]})

        queryset = filter_instance.queryset(
            request=None, queryset=RedirectRule.objects.all()
        )

        assert rule1 in queryset
        assert rule2 in queryset
        assert rule3 not in queryset

    @pytest.mark.django_db
    def test_queryset_returns_none_if_no_prefix(
        self, model_admin, filter_factory, redirect_rule_factory
    ):
        redirect_rule_factory(path="/foo/bar")
        filter_instance = filter_factory()

        queryset = filter_instance.queryset(
            request=None, queryset=RedirectRule.objects.all()
        )

        assert queryset is None
