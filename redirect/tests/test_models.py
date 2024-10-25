import itertools

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
        domain = domain_factory(display_name="foo.com")
        other_domain = domain_factory(display_name="bar.com")

        # These should be fine
        RedirectRule.objects.create(
            domain=domain, path="/foo", destination=self.DEFAULT_DESTINATION
        )
        RedirectRule.objects.create(
            domain=other_domain, path="/foo", destination=self.DEFAULT_DESTINATION
        )

        # This shouldn't be fine
        with pytest.raises(ValidationError):
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
        [("/foo", "/FOO/bar"), ("/FOO/bar", "/foo")],
    )
    def test_match_subpaths_conflict_on_create_case_insensitive(
        self, domain, existing_path, conflicting_path
    ):
        RedirectRule.objects.create(
            domain=domain,
            path=existing_path,
            destination=self.DEFAULT_DESTINATION,
            match_subpaths=True,
            case_sensitive=False,
        )

        with pytest.raises(ValidationError):
            RedirectRule.objects.create(
                domain=domain,
                path=conflicting_path,
                destination=self.DEFAULT_DESTINATION,
                match_subpaths=True,
                case_sensitive=False,
            )

    @pytest.mark.parametrize(
        "existing_path, conflicting_path",
        [("/FOO", "/FOO/bar"), ("/FOO/bar", "/FOO")],
    )
    def test_match_subpaths_conflict_on_create_case_sensitive(
        self, domain, existing_path, conflicting_path
    ):
        RedirectRule.objects.create(
            domain=domain,
            path="/foo/bar",
            destination=self.DEFAULT_DESTINATION,
            match_subpaths=True,
            case_sensitive=True,
        )
        # This should not conflict with the existing rule
        RedirectRule.objects.create(
            domain=domain,
            path=existing_path,
            destination=self.DEFAULT_DESTINATION,
            match_subpaths=True,
            case_sensitive=True,
        )

        with pytest.raises(ValidationError):
            RedirectRule.objects.create(
                domain=domain,
                path=conflicting_path,
                destination=self.DEFAULT_DESTINATION,
                match_subpaths=True,
                case_sensitive=True,
            )

    @pytest.mark.parametrize(
        "existing_path, conflicting_path",
        list(itertools.product(["/foo", "/FOO"], ["/foo/bar", "/FOO/bar"]))
        + list(itertools.product(["/foo/bar", "/FOO/bar"], ["/foo", "/FOO"])),
    )
    @pytest.mark.parametrize(
        "existing_case_sensitive, conflicting_case_sensitive",
        [(True, False), (False, True)],
    )
    def test_match_subpaths_conflict_on_create_different_case_sensitivity(
        self,
        domain,
        existing_path,
        conflicting_path,
        existing_case_sensitive,
        conflicting_case_sensitive,
    ):
        RedirectRule.objects.create(
            domain=domain,
            path=existing_path,
            destination=self.DEFAULT_DESTINATION,
            match_subpaths=True,
            case_sensitive=existing_case_sensitive,
        )

        with pytest.raises(ValidationError):
            RedirectRule.objects.create(
                domain=domain,
                path=conflicting_path,
                destination=self.DEFAULT_DESTINATION,
                match_subpaths=True,
                case_sensitive=conflicting_case_sensitive,
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

    @pytest.mark.parametrize(
        "paths",
        [
            ("/foo", "/FOO"),
            ("/FOO", "/foo"),
            ("/foo", "/foo"),
            ("/FOO", "/FOO"),
            ("/foo/bar", "/foo/BAR"),
        ],
    )
    @pytest.mark.parametrize("case_sensitive", [(True, False), (False, True)])
    def test_path_conflicts_with_differing_case_sensitivity(
        self, domain, paths, case_sensitive, redirect_rule_factory
    ):
        existing_path, conflicting_path = paths
        existing_case_sensitive, conflicting_case_sensitive = case_sensitive

        redirect_rule_factory(
            path=existing_path,
            domain=domain,
            case_sensitive=existing_case_sensitive,
        )

        with pytest.raises(ValidationError):
            redirect_rule_factory(
                path=conflicting_path,
                domain=domain,
                case_sensitive=conflicting_case_sensitive,
            )

    @pytest.mark.parametrize(
        "paths",
        [
            ("/FOO", "/FOO"),
            ("/foo", "/foo"),
            ("/foo/BAR", "/foo/BAR"),
        ],
    )
    def test_path_conflicts_both_case_sensitive(
        self, domain, paths, redirect_rule_factory
    ):
        existing_path, conflicting_path = paths

        redirect_rule_factory(
            path=existing_path,
            domain=domain,
            case_sensitive=True,
        )

        with pytest.raises(ValidationError):
            redirect_rule_factory(
                path=conflicting_path,
                domain=domain,
                case_sensitive=True,
            )

    def test_can_create_case_sensitive_paths_with_same_characters_different_casing(
        self, domain
    ):
        RedirectRule.objects.create(
            domain=domain,
            path="/foo",
            destination=self.DEFAULT_DESTINATION,
            case_sensitive=True,
        )
        RedirectRule.objects.create(
            domain=domain,
            path="/FOO",
            destination=self.DEFAULT_DESTINATION,
            case_sensitive=True,
        )
        # No error, this passes!

    def test_cannot_create_case_insensitive_paths_with_same_characters_different_casing(
        self, domain
    ):
        RedirectRule.objects.create(
            domain=domain,
            path="/foo",
            destination=self.DEFAULT_DESTINATION,
            case_sensitive=False,
        )
        with pytest.raises(ValidationError):
            RedirectRule.objects.create(
                domain=domain,
                path="/FOO",
                destination=self.DEFAULT_DESTINATION,
                case_sensitive=False,
            )

    def test_can_create_same_case_sensitive_paths_on_different_domains(
        self, domain_factory
    ):
        domain = domain_factory(display_name="foo.test")
        other_domain = domain_factory(display_name="bar.test")

        RedirectRule.objects.create(
            domain=domain,
            path="/FOO",
            destination=self.DEFAULT_DESTINATION,
            case_sensitive=True,
        )
        RedirectRule.objects.create(
            domain=other_domain,
            path="/FOO",
            destination=self.DEFAULT_DESTINATION,
            case_sensitive=True,
        )
        # No error, this passes!

    def test_should_validate_case_sensitivity_on_case_sensitive_switch(
        self, domain, redirect_rule_factory
    ):
        rule = redirect_rule_factory(
            path="/foo",
            domain=domain,
            case_sensitive=True,
        )
        redirect_rule_factory(
            path="/FOO",
            domain=domain,
            case_sensitive=True,
        )

        rule.case_sensitive = False

        with pytest.raises(ValidationError):
            rule.save()
