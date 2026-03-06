from ae.log_safety import sanitize_text


def test_redacts_email():
    s = "Contact me at john.doe@example.com please"
    out = sanitize_text(s)
    assert "@" in out
    assert "john.doe" not in out
    assert "example.com" not in out


def test_redacts_phone_like():
    s = "Call +1 (415) 555-1234 now"
    out = sanitize_text(s)
    assert "555" not in out


def test_redacts_long_tokens():
    token = "Bearer " + ("A" * 40)
    out = sanitize_text(token)
    assert "A" * 20 not in out
    assert "*" in out


def test_caps_length(monkeypatch):
    monkeypatch.setenv("AE_LOG_MAX_CHARS", "10")
    out = sanitize_text("x" * 100)
    assert out.endswith("...(truncated)")
    assert len(out) <= 10 + len("...(truncated)")
