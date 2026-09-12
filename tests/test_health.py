from fastapi.testclient import TestClient

from postupashki_mvp import api
from postupashki_mvp.api import app


def test_health() -> None:
    response = TestClient(app).get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_local_vite_origin_is_allowed() -> None:
    response = TestClient(app).options(
        "/campaigns",
        headers={
            "Origin": "http://127.0.0.1:5174",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://127.0.0.1:5174"
    assert "POST" in response.headers["access-control-allow-methods"]


def test_analytics_report_is_reused_and_can_be_invalidated(monkeypatch) -> None:
    calls = 0
    expected = {"overall_funnel": "calculated"}

    def fake_build_analytics_report(**_kwargs: object) -> dict[str, object]:
        nonlocal calls
        calls += 1
        return expected

    monkeypatch.setattr(api, "build_analytics_report", fake_build_analytics_report)
    api.invalidate_analytics_cache()

    first = api.analytics_report("synthetic", "last_touch", None)
    second = api.analytics_report("synthetic", "last_touch", None)

    assert first is expected
    assert second is expected
    assert calls == 1

    api.invalidate_analytics_cache()
    api.analytics_report("synthetic", "last_touch", None)

    assert calls == 2
    api.invalidate_analytics_cache()
