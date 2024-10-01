import pytest
from django.core.exceptions import ValidationError

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

    def test_save_calls_clean_method(self, monkeypatch, domain):
        call_count = 0

        def mock_clean(*_, **__):
            nonlocal call_count
            call_count += 1

        monkeypatch.setattr(RedirectRule, "clean", mock_clean)
        RedirectRule.objects.create(
            domain=domain, path="/foo/", destination=self.DEFAULT_DESTINATION
        )

        assert call_count == 1

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

        # This shouldn't be fine
        with pytest.raises(Exception):
            RedirectRule.objects.create(
                domain=domain, path="/foo", destination=self.DEFAULT_DESTINATION
            )

    @pytest.mark.parametrize(
        "existing_path, conflicting_path",
        [("/foo", "/foo/bar"), ("/foo/bar", "/foo")],
    )
    def test_match_subpaths_conflict_on_create(
        self, domain, existing_path, conflicting_path
    ):
        RedirectRule.objects.create(
            domain=domain,
            path=existing_path,
            destination=self.DEFAULT_DESTINATION,
            match_subpaths=True,
        )

        with pytest.raises(ValidationError):
            RedirectRule.objects.create(
                domain=domain,
                path=conflicting_path,
                destination=self.DEFAULT_DESTINATION,
                match_subpaths=True,
            )

    @pytest.mark.parametrize(
        "existing_path, conflicting_path",
        [("/foo", "/foo/bar"), ("/foo/bar", "/foo")],
    )
    def test_match_subpaths_conflict_on_update(
        self, domain, existing_path, conflicting_path
    ):
        RedirectRule.objects.create(
            domain=domain,
            path=existing_path,
            destination=self.DEFAULT_DESTINATION,
            match_subpaths=True,
        )
        rule_to_update = RedirectRule.objects.create(
            domain=domain,
            path="/this-will-be-replaced",
            destination=self.DEFAULT_DESTINATION,
            match_subpaths=True,
        )

        rule_to_update.path = conflicting_path

        with pytest.raises(ValidationError):
            rule_to_update.save()

    def test_match_subpaths_should_not_conflict_itself(self, domain):
        # Amusingly enough, this could happen if updating a rule.
        rule = RedirectRule.objects.create(
            domain=domain,
            path="/foo",
            destination=self.DEFAULT_DESTINATION,
            match_subpaths=True,
        )

        rule.path = "/foo/bar"
        rule.save()
