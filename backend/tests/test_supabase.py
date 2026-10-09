import os
from fastapi.testclient import TestClient
from main import app
from supabase_client import check_supabase_health, get_supabase_credentials

client = TestClient(app)


def test_get_supabase_credentials_default(monkeypatch):
    monkeypatch.setenv("SUPABASE_KEY", "")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "")
    monkeypatch.setenv("SUPABASE_ANON_KEY", "")

    url, key = get_supabase_credentials()
    assert url == "https://usefyrrekudsczopeevv.supabase.co"
    assert key is None or key == ""


def test_check_supabase_health_unconfigured(monkeypatch):
    monkeypatch.setenv("SUPABASE_KEY", "")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "")
    monkeypatch.setenv("SUPABASE_ANON_KEY", "")

    status = check_supabase_health()
    assert status["configured"] is False
    assert status["connected"] is False
    assert status["project_url"] == "https://usefyrrekudsczopeevv.supabase.co"
    assert "backend/.env" in status["message"]


def test_supabase_health_endpoint_response():
    response = client.get("/api/supabase/health")
    assert response.status_code == 200
    data = response.json()
    assert "ok" in data
    assert "configured" in data
    assert "connected" in data
    assert "project_url" in data
    assert data["project_url"] == "https://usefyrrekudsczopeevv.supabase.co"


def test_check_supabase_health_configured_mock(monkeypatch):
    monkeypatch.setenv("SUPABASE_KEY", "sb_test_key_sample_12345")
    status = check_supabase_health()
    assert status["configured"] is True
    assert status["key_present"] is True
    assert status["project_url"] == "https://usefyrrekudsczopeevv.supabase.co"
