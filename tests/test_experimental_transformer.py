from backend.experimental_transformer import generate_experimental_candidate, transformer_status

def test_transformer_disabled_by_default(monkeypatch):
    monkeypatch.delenv("ULTRON_TINY_ENABLED", raising=False)
    result = generate_experimental_candidate("Olá")
    assert result["status"] == "disabled"
    assert result["role"] == "experimental_candidate_only"

def test_transformer_missing_checkpoint_is_reported(monkeypatch, tmp_path):
    monkeypatch.setenv("ULTRON_TINY_ENABLED", "true")
    monkeypatch.setenv("ULTRON_TINY_CHECKPOINT", str(tmp_path / "missing.pt"))
    assert transformer_status()["available"] is False
    assert generate_experimental_candidate("Olá")["status"] == "checkpoint_missing"
