from __future__ import annotations
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, ConfigDict, model_validator

class PageModel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(min_length=1)
    slug: Optional[str] = None
    url: Optional[str] = None

class ClientModel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: Optional[str] = None
    name: Optional[str] = None
    trade: Optional[Any] = None
    geo_city: Optional[str] = None

class ComponentModel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    component: str = Field(min_length=1)
    props: Dict[str, Any] = Field(default_factory=dict)

class MetaModel(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)
    schema_name: str = Field(min_length=1, alias="schema")
    notes: Optional[str] = None

class FramerPagePayloadV1(BaseModel):
    """Contract: `framer.page_payload.v1`"""
    model_config = ConfigDict(extra="forbid")
    type: str = Field("framer.page_payload.v1", pattern=r"^framer\.page_payload\.v1$")
    page: PageModel
    client: ClientModel
    components: List[ComponentModel] = Field(min_length=1)
    sections: List[Dict[str, Any]] = Field(default_factory=list)
    meta: MetaModel

    @model_validator(mode="after")
    def _enforce_required_component_props(self):
        # Fail-fast minimal semantics so stub artifacts are meaningful.
        for c in self.components:
            if c.component == "Hero":
                headline = c.props.get("headline")
                sub = c.props.get("subheadline")
                if not isinstance(headline, str) or not headline.strip():
                    raise ValueError("Hero.props.headline must be non-empty string")
                if not isinstance(sub, str) or not sub.strip():
                    raise ValueError("Hero.props.subheadline must be non-empty string")
            if c.component == "CTA":
                primary = c.props.get("primary")
                if not isinstance(primary, str) or not primary.strip():
                    raise ValueError("CTA.props.primary must be non-empty string")
        return self
