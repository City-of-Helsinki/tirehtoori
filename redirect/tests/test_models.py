import pytest
from redirect.models import RedirectRule


@pytest.mark.django_db
class TestRedirectRule:
    DEFAULT_DESTINATION = "https://test.test"

    def test_clean_strips_leading_and_trailing_slashes(self, domain):
        rule = RedirectRule(
            domain=domain, path="/foo/", destination=self.DEFAULT_DESTINATION
        )

        rule.clean()

        assert rule.path == "foo"

    def test_save_calls_clean_method(self, domain):
        rule = RedirectRule.objects.create(
            domain=domain, path="/foo/", destination=self.DEFAULT_DESTINATION
        )

        assert rule.path == "foo"

    def test_clean_handles_empty_path(self, domain):
        rule = RedirectRule(
            domain=domain, path="/", destination=self.DEFAULT_DESTINATION
        )

        rule.clean()

        assert rule.path == ""

    def test_save_handles_empty_path(self, domain):
        rule = RedirectRule.objects.create(
            domain=domain, path="/", destination=self.DEFAULT_DESTINATION
        )

        assert rule.path == ""

    def test_unique_together(self, domain_factory):
        domain = domain_factory(name="foo.com")
        other_domain = domain_factory(name="bar.com")

        # These should be fine
        RedirectRule.objects.create(
            domain=domain, path="/foo", destination=self.DEFAULT_DESTINATION
        )
        RedirectRule.objects.create(
            domain=other_domain, path="/foo", destination=self.DEFAULT_DESTINATION
        )

        # This shouldn't
        with pytest.raises(Exception):
            RedirectRule.objects.create(
                domain=domain, path="/foo", destination=self.DEFAULT_DESTINATION
            )
