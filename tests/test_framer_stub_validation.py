from ae.adapters.publisher_framer_stub import FramerPublisherStub

def test_framer_stub_rejects_invalid_contract():
    pub = FramerPublisherStub(out_dir="exports/framer_payloads")
    res = pub.publish("p1", payload={}, context={"page": None, "client": None})
    assert res.ok is False
    assert res.errors
