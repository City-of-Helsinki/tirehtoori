import pytest
from django.http import Http404
from django.test import Client

from redirect.api import find_wildcard_rule, get_domain_rule_or_404


@pytest.mark.django_db
def test_domain_rule_exact_match(domain, redirect_rule_factory):
    expected_rule = redirect_rule_factory(
        path="TEST", domain=domain, case_sensitive=True
    )
    redirect_rule_factory(path="test", domain=domain, case_sensitive=True)
    result = get_domain_rule_or_404(domain, "/TEST")
    assert result == expected_rule


@pytest.mark.django_db
def test_domain_rule_case_insensitive_match(domain, redirect_rule_factory):
    rule = redirect_rule_factory(path="test", domain=domain, case_sensitive=False)
    result = get_domain_rule_or_404(domain, "/TEST")
    assert result == rule


@pytest.mark.django_db
def test_domain_rule_no_match_raises_404(domain):
    with pytest.raises(Http404):
        get_domain_rule_or_404(domain, "nonexistent")


@pytest.mark.parametrize("path", ["test/", "/test", "/test/"])
@pytest.mark.django_db
def test_domain_rule_or_404_ignores_leading_and_trailing_slashes(
    path, domain, redirect_rule_factory
):
    expected_rule = redirect_rule_factory(path="test", domain=domain)
    result = get_domain_rule_or_404(domain, path)
    assert result == expected_rule


@pytest.mark.django_db
def test_find_wildcard_rule_exact_match(domain, redirect_rule_factory):
    expected_rule = redirect_rule_factory(
        path="/wildcard", domain=domain, match_subpaths=True
    )
    result = find_wildcard_rule(domain, "wildcard/path")
    assert result == expected_rule


@pytest.mark.django_db
def test_find_wildcard_rule_no_match(domain, redirect_rule_factory):
    redirect_rule_factory(path="/wildcard", domain=domain, match_subpaths=True)
    result = find_wildcard_rule(domain, "no-match/path")
    assert result is None


@pytest.mark.django_db
def test_find_wildcard_rule_case_insensitive_match(domain, redirect_rule_factory):
    expected_rule = redirect_rule_factory(
        path="/wildcard", domain=domain, match_subpaths=True
    )
    result = find_wildcard_rule(domain, "WILDCARD/path")
    assert result == expected_rule


@pytest.mark.django_db
class TestRedirectView:
    @pytest.fixture
    def domain_client(self, client, domain):
        """
        An instance of the Django test client with HTTP_HOST set to the domain name
        of the default domain fixture.
        """
        client.defaults["HTTP_HOST"] = domain.names.first().name
        return client

    @pytest.mark.parametrize("path", ["foo", "foo/bar", "foo/bar/baz"])
    def test_redirect_valid_path(
        self, domain_client: Client, domain, redirect_rule_factory, path
    ):
        rule = redirect_rule_factory(path=path, domain=domain)

        response = domain_client.get(f"/{path}")

        assert response.status_code == 302
        assert response["Location"] == rule.destination

    def test_redirect_valid_path_permanent(
        self, domain_client: Client, domain, redirect_rule_factory
    ):
        rule = redirect_rule_factory(
            path="foo",
            permanent=True,
            domain=domain,
        )

        response = domain_client.get("/foo")

        assert response.status_code == 301
        assert response["Location"] == rule.destination

    def test_redirect_valid_path_case_insensitive(
        self, domain_client: Client, domain, redirect_rule_factory
    ):
        rule = redirect_rule_factory(
            path="foo",
            domain=domain,
            case_sensitive=False,
        )

        response = domain_client.get("/FOO")

        assert response.status_code == 302
        assert response["Location"] == rule.destination

    def test_redirect_valid_path_case_sensitive(
        self, domain_client: Client, domain, redirect_rule_factory
    ):
        redirect_rule_factory(
            path="foo",
            domain=domain,
            case_sensitive=True,
        )

        response = domain_client.get("/FOO")

        assert response.status_code == 404

        response = domain_client.get("/foo")

        assert response.status_code == 302

    def test_redirect_valid_path_multiple_domain_names(
        self, client: Client, domain_factory, redirect_rule_factory
    ):
        domain_names = ["acme.test", "www.acme.test"]
        domain = domain_factory(display_name="ACME Inc.", names=domain_names)
        rule = redirect_rule_factory(path="foo", domain=domain)

        response_1 = client.get("/foo", HTTP_HOST=domain_names[0])
        response_2 = client.get("/foo", HTTP_HOST=domain_names[1])

        # Both should redirect to the same destination
        assert response_1.status_code == response_2.status_code == 302
        assert response_1["Location"] == response_2["Location"] == rule.destination

    def test_redirect_from_root_path(
        self, domain_client: Client, domain, redirect_rule_factory
    ):
        rule = redirect_rule_factory(path="", domain=domain)

        response = domain_client.get("/")

        assert response.status_code == 302
        assert response["Location"] == rule.destination

    def test_redirect_invalid_path(
        self, domain_client: Client, domain, redirect_rule_factory
    ):
        redirect_rule_factory(path="foo", domain=domain)

        response = domain_client.get("/bar")

        assert response.status_code == 404

    def test_redirect_invalid_domain(
        self, client: Client, domain_factory, redirect_rule_factory
    ):
        domain = domain_factory(display_name="example.com")
        redirect_rule_factory(path="foo", domain=domain)

        response = client.get("/foo", HTTP_HOST="404.com")

        assert response.status_code == 404

    @pytest.mark.parametrize("query_string", ["?param=value", "?param=value&foo=bar"])
    def test_redirect_with_pass_query_string_should_append_query_string(
        self, domain_client: Client, domain, redirect_rule_factory, query_string
    ):
        rule = redirect_rule_factory(path="foo", domain=domain, pass_query_string=True)

        response = domain_client.get(f"/foo{query_string}")

        assert response.status_code == 302
        assert response["Location"] == f"{rule.destination}{query_string}"

    def test_redirect_with_empty_query_string_should_discard_query_string(
        self, domain_client: Client, domain, redirect_rule_factory
    ):
        rule = redirect_rule_factory(path="foo", domain=domain, pass_query_string=True)

        response = domain_client.get("/foo?")

        assert response.status_code == 302
        assert response["Location"] == rule.destination

    @pytest.mark.parametrize(
        "subpath",
        [
            "",
            "bar",
            "bar/baz",
            "bar/baz/lorem/ipsum/dolor/sit/amet/consectetur/adipiscing/elit",
        ],
    )
    def test_redirect_with_match_sub_paths_should_redirect_subpaths(
        self, domain_client: Client, domain, redirect_rule_factory, subpath
    ):
        rule = redirect_rule_factory(path="foo", domain=domain, match_subpaths=True)

        response = domain_client.get(f"/foo{subpath}")

        assert response.status_code == 302
        assert response["Location"] == rule.destination

    @pytest.mark.parametrize(
        "subpath",
        [
            "",
            "bar",
            "bar/baz",
            "bar/baz/lorem/ipsum/dolor/sit/amet/consectetur/adipiscing/elit",
        ],
    )
    def test_redirect_with_pass_sub_paths_should_append_subpath_to_destination(
        self, domain_client: Client, domain, redirect_rule_factory, subpath
    ):
        rule = redirect_rule_factory(
            path="foo", domain=domain, match_subpaths=True, append_subpath=True
        )

        response = domain_client.get(f"/foo/{subpath}")

        assert response.status_code == 302
        assert response["Location"] == f"{rule.destination}{subpath}"

    def test_redirect_with_exact_match_takes_precedence_over_subpaths(
        self, domain_client: Client, domain, redirect_rule_factory
    ):
        exact_rule = redirect_rule_factory(path="foo/bar", domain=domain)
        redirect_rule_factory(path="foo", domain=domain, match_subpaths=True)

        response = domain_client.get("/foo/bar")

        assert response.status_code == 302
        assert response["Location"] == exact_rule.destination
