from ae.log_safety import sanitize_text, safe_client_ip


def test_sanitize_text_masks_email():
    s = "user.name+tag@example.com failed"
    out = sanitize_text(s)
    assert out is not None
    assert "@" in out
    assert "user" not in out  # masked
    assert "example" not in out  # masked


def test_sanitize_text_masks_phone():
    s = "call +66 81-234-5678 now"
    out = sanitize_text(s)
    assert out is not None
    assert "81" not in out or "*" in out


def test_safe_client_ip_default_hidden(monkeypatch):
    monkeypatch.delenv("AE_LOG_CLIENT_IP", raising=False)
    assert safe_client_ip("1.2.3.4") is None


def test_safe_client_ip_coarse(monkeypatch):
    monkeypatch.setenv("AE_LOG_CLIENT_IP", "1")
    assert safe_client_ip("1.2.3.4") == "1.2.x.x"
