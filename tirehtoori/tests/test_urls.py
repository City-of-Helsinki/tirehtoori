from tirehtoori import __version__


def test_healthz(client):
    response = client.get("/__healthz")

    assert response.status_code == 200


def test_readiness(client, settings):
    response = client.get("/__readiness")

    data = response.json()
    assert response.status_code == 200
    assert len(data) == 4
    assert data["status"] == "ok"
    assert data["packageVersion"] == __version__
    assert data["commitHash"] == settings.COMMIT_HASH
    assert "buildTime" in data
