from ae.schemas import registry

def test_supported_contains_framer():
    assert "framer.page_payload.v1" in registry.supported()

def test_validate_framer_contract_fails_on_missing_components():
    bad = {
        "type": "framer.page_payload.v1",
        "page": {"id": "p1"},
        "client": {},
        "components": [],
        "sections": [],
        "meta": {"schema": "v1"},
    }
    ok, res = registry.validate("framer.page_payload.v1", bad)
    assert ok is False
    assert res.errors
