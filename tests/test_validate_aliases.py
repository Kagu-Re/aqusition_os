import os
import tempfile
import json

from ae import service

def test_validate_aliases_flags_duplicates_and_empties():
    with tempfile.TemporaryDirectory() as td:
        path=os.path.join(td,"aliases.json")
        aliases={
            "google": {
                "spend": ["Cost", "cost", ""],
            }
        }
        with open(path,"w",encoding="utf-8") as f:
            json.dump(aliases,f)

        rep=service.validate_ad_platform_aliases(path)
        assert rep["ok"] is False
        errs=[i["error"] for i in rep["issues"]]
        assert "duplicate_aliases" in errs
        assert "empty_aliases" in errs
