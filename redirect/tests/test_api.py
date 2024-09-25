import pytest
from django.test import Client


@pytest.mark.parametrize("path", ["foo", "foo/bar", "foo/bar/baz"])
@pytest.mark.django_db
def test_redirect_valid_path(client: Client, domain, redirect_rule_factory, path):
    rule = redirect_rule_factory(path=path, domain=domain)

    response = client.get(f"/{path}", HTTP_HOST=domain.name)

    assert response.status_code == 302
    assert response["Location"] == rule.destination


@pytest.mark.django_db
def test_redirect_valid_path_permanent(client: Client, domain, redirect_rule_factory):
    rule = redirect_rule_factory(
        path="foo",
        permanent=True,
        domain=domain,
    )

    response = client.get("/foo", HTTP_HOST=domain.name)

    assert response.status_code == 301
    assert response["Location"] == rule.destination


@pytest.mark.django_db
def test_redirect_valid_path_case_insensitive(
    client: Client, domain, redirect_rule_factory
):
    rule = redirect_rule_factory(
        path="foo",
        domain=domain,
        case_sensitive=False,
    )

    response = client.get("/FOO", HTTP_HOST=domain.name)

    assert response.status_code == 302
    assert response["Location"] == rule.destination


@pytest.mark.xfail(reason="Case sensitive paths are not supported")
@pytest.mark.django_db
def test_redirect_valid_path_case_sensitive(
    client: Client, domain, redirect_rule_factory
):
    redirect_rule_factory(
        path="foo",
        domain=domain,
        case_sensitive=True,
    )

    response = client.get("/FOO", HTTP_HOST=domain.name)

    assert response.status_code == 404

    response = client.get("/foo", HTTP_HOST=domain.name)

    assert response.status_code == 302


@pytest.mark.django_db
def test_redirect_from_root_path(client: Client, domain, redirect_rule_factory):
    rule = redirect_rule_factory(path="", domain=domain)

    response = client.get("/", HTTP_HOST=domain.name)

    assert response.status_code == 302
    assert response["Location"] == rule.destination


@pytest.mark.django_db
def test_redirect_invalid_path(client: Client, domain, redirect_rule_factory):
    redirect_rule_factory(path="foo", domain=domain)

    response = client.get("/bar", HTTP_HOST=domain.name)

    assert response.status_code == 404


@pytest.mark.django_db
def test_redirect_invalid_domain(client: Client, domain_factory, redirect_rule_factory):
    domain = domain_factory(name="example.com")
    redirect_rule_factory(path="foo", domain=domain)

    response = client.get("/foo", HTTP_HOST="404.com")

    assert response.status_code == 404
