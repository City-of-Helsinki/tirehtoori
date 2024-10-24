import pytest
from django.test import Client


@pytest.fixture
def domain_client(client, domain):
    """
    An instance of the Django test client with HTTP_HOST set to the domain name
    of the default domain fixture.
    """
    client.defaults["HTTP_HOST"] = domain.names.first().name
    return client


@pytest.mark.parametrize("path", ["foo", "foo/bar", "foo/bar/baz"])
@pytest.mark.django_db
def test_redirect_valid_path(
    domain_client: Client, domain, redirect_rule_factory, path
):
    rule = redirect_rule_factory(path=path, domain=domain)

    response = domain_client.get(f"/{path}")

    assert response.status_code == 302
    assert response["Location"] == rule.destination


@pytest.mark.django_db
def test_redirect_valid_path_permanent(
    domain_client: Client, domain, redirect_rule_factory
):
    rule = redirect_rule_factory(
        path="foo",
        permanent=True,
        domain=domain,
    )

    response = domain_client.get("/foo")

    assert response.status_code == 301
    assert response["Location"] == rule.destination


@pytest.mark.django_db
def test_redirect_valid_path_case_insensitive(
    domain_client: Client, domain, redirect_rule_factory
):
    rule = redirect_rule_factory(
        path="foo",
        domain=domain,
        case_sensitive=False,
    )

    response = domain_client.get("/FOO")

    assert response.status_code == 302
    assert response["Location"] == rule.destination


@pytest.mark.xfail(reason="Case sensitive paths are not supported")
@pytest.mark.django_db
def test_redirect_valid_path_case_sensitive(
    domain_client: Client, domain, redirect_rule_factory
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


@pytest.mark.django_db
def test_redirect_valid_path_multiple_domain_names(
    client: Client, domain_factory, redirect_rule_factory
):
    domain_names = ["acme.test", "www.acme.test"]
    domain = domain_factory(display_name="ACME Inc.", names=domain_names)
    rule = redirect_rule_factory(path="foo", domain=domain)

    response_1 = client.get("/foo", HTTP_HOST=domain_names[0])
    response_2 = client.get("/foo", HTTP_HOST=domain_names[1])

    # Both should redirect to the same destination
    assert response_1.status_code == response_2.status_code == 302
    assert response_1["Location"] == response_2["Location"] == rule.destination


@pytest.mark.django_db
def test_redirect_from_root_path(domain_client: Client, domain, redirect_rule_factory):
    rule = redirect_rule_factory(path="", domain=domain)

    response = domain_client.get("/")

    assert response.status_code == 302
    assert response["Location"] == rule.destination


@pytest.mark.django_db
def test_redirect_invalid_path(domain_client: Client, domain, redirect_rule_factory):
    redirect_rule_factory(path="foo", domain=domain)

    response = domain_client.get("/bar")

    assert response.status_code == 404


@pytest.mark.django_db
def test_redirect_invalid_domain(client: Client, domain_factory, redirect_rule_factory):
    domain = domain_factory(display_name="example.com")
    redirect_rule_factory(path="foo", domain=domain)

    response = client.get("/foo", HTTP_HOST="404.com")

    assert response.status_code == 404


@pytest.mark.parametrize("query_string", ["?param=value", "?param=value&foo=bar"])
@pytest.mark.django_db
def test_redirect_with_pass_query_string_should_append_query_string(
    domain_client: Client, domain, redirect_rule_factory, query_string
):
    rule = redirect_rule_factory(path="foo", domain=domain, pass_query_string=True)

    response = domain_client.get(f"/foo{query_string}")

    assert response.status_code == 302
    assert response["Location"] == f"{rule.destination}{query_string}"


@pytest.mark.django_db
def test_redirect_with_empty_query_string_should_discard_query_string(
    domain_client: Client, domain, redirect_rule_factory
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
@pytest.mark.django_db
def test_redirect_with_match_sub_paths_should_redirect_subpaths(
    domain_client: Client, domain, redirect_rule_factory, subpath
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
@pytest.mark.django_db
def test_redirect_with_pass_sub_paths_should_append_subpath_to_destination(
    domain_client: Client, domain, redirect_rule_factory, subpath
):
    rule = redirect_rule_factory(
        path="foo", domain=domain, match_subpaths=True, append_subpath=True
    )

    response = domain_client.get(f"/foo/{subpath}")

    assert response.status_code == 302
    assert response["Location"] == f"{rule.destination}{subpath}"


@pytest.mark.django_db
def test_redirect_with_exact_match_takes_precedence_over_subpaths(
    domain_client: Client, domain, redirect_rule_factory
):
    exact_rule = redirect_rule_factory(path="foo/bar", domain=domain)
    redirect_rule_factory(path="foo", domain=domain, match_subpaths=True)

    response = domain_client.get("/foo/bar")

    assert response.status_code == 302
    assert response["Location"] == exact_rule.destination
