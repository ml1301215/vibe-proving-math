import importlib

from fastapi.testclient import TestClient


def _write_config(path):
    path.write_text(
        """
[llm]
base_url = "https://old.example.com/v1"
api_key = ""
model = "old-model"
timeout = 120

[theorem_search]
base_url = "https://api.theoremsearch.com"
timeout = 60

[latrace]
base_url = "http://localhost:8000"

[nanonets]
api_key = ""
max_poll_seconds = 900
""".strip()
        + "\n",
        encoding="utf-8",
    )


def _client_with_config(monkeypatch, tmp_path):
    cfg_path = tmp_path / "config.toml"
    _write_config(cfg_path)
    monkeypatch.setenv("VP_CONFIG_PATH", str(cfg_path))

    import core.config as config
    config.clear_config_cache()

    import core.llm as llm
    llm.update_config_override({})

    import api.server as server
    server._runtime_config_overrides.clear()
    importlib.reload(server)
    server._runtime_config_overrides.clear()
    return TestClient(server.app), cfg_path


def test_config_llm_save_persists_and_get_redacts_api_key(monkeypatch, tmp_path):
    client, cfg_path = _client_with_config(monkeypatch, tmp_path)

    resp = client.post(
        "/config/llm",
        json={
            "base_url": "https://api.deepseek.com/v1",
            "api_key": "secret-key",
            "model": "deepseek-chat",
        },
    )
    assert resp.status_code == 200, resp.text

    text = cfg_path.read_text(encoding="utf-8")
    assert 'base_url = "https://api.deepseek.com/v1"' in text
    assert 'api_key = "secret-key"' in text
    assert 'model = "deepseek-chat"' in text

    resp = client.get("/config")
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["llm"]["base_url"] == "https://api.deepseek.com/v1"
    assert data["llm"]["model"] == "deepseek-chat"
    assert data["llm"]["api_key_configured"] is True
    assert "api_key" not in data["llm"]


def test_config_nanonets_save_persists_and_get_redacts_api_key(monkeypatch, tmp_path):
    client, cfg_path = _client_with_config(monkeypatch, tmp_path)

    resp = client.post("/config/nanonets", json={"api_key": "nano-secret"})
    assert resp.status_code == 200, resp.text
    assert 'api_key = "nano-secret"' in cfg_path.read_text(encoding="utf-8")

    resp = client.get("/config")
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["nanonets"]["api_key_configured"] is True
    assert "api_key" not in data["nanonets"]
