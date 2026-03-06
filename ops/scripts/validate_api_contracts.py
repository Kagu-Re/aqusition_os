"""API contract validation module.

Validates API contracts, event schemas, and payload structures without
requiring services to be running.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

# Ensure we can import ae modules
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / 'src'
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ae.enums import EventName
from ae.op_event_registry import REGISTRY, get_event_spec
from ae.schemas.registry import validate as validate_schema, supported as supported_schemas
from ops.scripts.validation_modules import ValidationCheck, ValidationResult


def validate_event_schemas() -> ValidationResult:
    """Validate that event schemas are properly registered and have valid structure.
    
    Returns:
        ValidationResult with event schema validation checks
    """
    checks: List[ValidationCheck] = []
    
    try:
        # Check registry is loaded
        if not REGISTRY:
            checks.append(ValidationCheck(
                name="registry_loaded",
                status="warning",
                message="Event registry is empty"
            ))
        else:
            checks.append(ValidationCheck(
                name="registry_loaded",
                status="passed",
                message=f"Event registry loaded with {len(REGISTRY)} event types",
                details={"event_count": len(REGISTRY)}
            ))
        
        # Validate each registered event
        invalid_events = []
        for topic, spec in REGISTRY.items():
            # Check topic format
            if not topic.startswith("op."):
                invalid_events.append({
                    "topic": topic,
                    "issue": "Topic should start with 'op.'"
                })
                continue
            
            # Check schema version
            if spec.schema_version < 1:
                invalid_events.append({
                    "topic": topic,
                    "issue": f"Invalid schema_version: {spec.schema_version}"
                })
                continue
            
            # Check required_keys is a list
            if not isinstance(spec.required_keys, list):
                invalid_events.append({
                    "topic": topic,
                    "issue": "required_keys must be a list"
                })
                continue
        
        if invalid_events:
            checks.append(ValidationCheck(
                name="event_schema_structure",
                status="failed",
                message=f"Found {len(invalid_events)} invalid event schemas",
                details={"invalid_events": invalid_events[:10]}
            ))
        else:
            checks.append(ValidationCheck(
                name="event_schema_structure",
                status="passed",
                message="All event schemas have valid structure"
            ))
        
        # Test get_event_spec function
        test_topics = list(REGISTRY.keys())[:3]  # Test first 3
        for topic in test_topics:
            spec = get_event_spec(topic)
            if spec is None:
                checks.append(ValidationCheck(
                    name=f"get_spec_{topic}",
                    status="failed",
                    message=f"Cannot retrieve spec for topic: {topic}"
                ))
            else:
                checks.append(ValidationCheck(
                    name=f"get_spec_{topic}",
                    status="passed",
                    message=f"Successfully retrieved spec for: {topic}"
                ))
        
    except Exception as e:
        checks.append(ValidationCheck(
            name="event_schema_validation",
            status="failed",
            message=f"Event schema validation error: {e}"
        ))
        return ValidationResult(checks=checks, passed=False, errors=1)
    
    errors = sum(1 for c in checks if c.status == "failed")
    warnings = sum(1 for c in checks if c.status == "warning")
    passed = errors == 0
    
    return ValidationResult(checks=checks, passed=passed, errors=errors, warnings=warnings)


def validate_event_payload_structure(event_name: str, payload: Dict[str, Any]) -> ValidationResult:
    """Validate an event payload structure against registered schema.
    
    Args:
        event_name: Event name (e.g., "call_click")
        payload: Event payload dictionary
        
    Returns:
        ValidationResult with payload validation checks
    """
    checks: List[ValidationCheck] = []
    
    try:
        # Check event name is valid enum
        try:
            event_enum = EventName(event_name)
            checks.append(ValidationCheck(
                name="event_name_valid",
                status="passed",
                message=f"Event name '{event_name}' is valid"
            ))
        except ValueError:
            checks.append(ValidationCheck(
                name="event_name_valid",
                status="failed",
                message=f"Invalid event name: {event_name}"
            ))
            return ValidationResult(checks=checks, passed=False, errors=1)
        
        # Check payload structure
        if not isinstance(payload, dict):
            checks.append(ValidationCheck(
                name="payload_structure",
                status="failed",
                message="Payload must be a dictionary"
            ))
            return ValidationResult(checks=checks, passed=False, errors=1)
        
        checks.append(ValidationCheck(
            name="payload_structure",
            status="passed",
            message="Payload is a valid dictionary"
        ))
        
        # Check for required fields (basic validation)
        # Note: Full validation would require checking against op_event registry
        # but public events (call_click, quote_submit, thank_you_view) are simpler
        required_fields = ["page_id"]
        missing_fields = [f for f in required_fields if f not in payload]
        
        if missing_fields:
            checks.append(ValidationCheck(
                name="required_fields",
                status="failed",
                message=f"Missing required fields: {', '.join(missing_fields)}"
            ))
        else:
            checks.append(ValidationCheck(
                name="required_fields",
                status="passed",
                message="All required fields present"
            ))
        
        # Check payload size (basic limit)
        import json
        payload_size = len(json.dumps(payload))
        max_size = 100000  # 100KB
        
        if payload_size > max_size:
            checks.append(ValidationCheck(
                name="payload_size",
                status="warning",
                message=f"Payload size ({payload_size} bytes) exceeds recommended limit ({max_size} bytes)"
            ))
        else:
            checks.append(ValidationCheck(
                name="payload_size",
                status="passed",
                message=f"Payload size: {payload_size} bytes"
            ))
        
    except Exception as e:
        checks.append(ValidationCheck(
            name="payload_validation",
            status="failed",
            message=f"Payload validation error: {e}"
        ))
        return ValidationResult(checks=checks, passed=False, errors=1)
    
    errors = sum(1 for c in checks if c.status == "failed")
    warnings = sum(1 for c in checks if c.status == "warning")
    passed = errors == 0
    
    return ValidationResult(checks=checks, passed=passed, errors=errors, warnings=warnings)


def validate_schema_registry() -> ValidationResult:
    """Validate schema registry (for CMS payloads, etc.).
    
    Returns:
        ValidationResult with schema registry validation checks
    """
    checks: List[ValidationCheck] = []
    
    try:
        # Check supported schemas
        schemas = supported_schemas()
        if not schemas:
            checks.append(ValidationCheck(
                name="schemas_available",
                status="warning",
                message="No schemas registered"
            ))
        else:
            checks.append(ValidationCheck(
                name="schemas_available",
                status="passed",
                message=f"Found {len(schemas)} registered schemas",
                details={"schemas": schemas}
            ))
        
        # Test schema validation with sample data
        for schema_name in schemas[:2]:  # Test first 2 schemas
            # Try with empty dict (should fail validation)
            is_valid, result = validate_schema(schema_name, {})
            if not is_valid:
                checks.append(ValidationCheck(
                    name=f"schema_validation_{schema_name}",
                    status="passed",
                    message=f"Schema '{schema_name}' correctly rejects invalid data"
                ))
            else:
                checks.append(ValidationCheck(
                    name=f"schema_validation_{schema_name}",
                    status="warning",
                    message=f"Schema '{schema_name}' accepts empty data (may be intentional)"
                ))
        
    except Exception as e:
        checks.append(ValidationCheck(
            name="schema_registry_validation",
            status="failed",
            message=f"Schema registry validation error: {e}"
        ))
        return ValidationResult(checks=checks, passed=False, errors=1)
    
    errors = sum(1 for c in checks if c.status == "failed")
    warnings = sum(1 for c in checks if c.status == "warning")
    passed = errors == 0
    
    return ValidationResult(checks=checks, passed=passed, errors=errors, warnings=warnings)


def validate_api_contracts() -> ValidationResult:
    """Run all API contract validations.
    
    Returns:
        ValidationResult with all API contract checks
    """
    checks: List[ValidationCheck] = []
    
    # Validate event schemas
    event_result = validate_event_schemas()
    checks.extend(event_result.checks)
    
    # Validate schema registry
    schema_result = validate_schema_registry()
    checks.extend(schema_result.checks)
    
    # Test sample event payloads
    test_payloads = [
        ("call_click", {"page_id": "p1", "params": {"utm_source": "test"}}),
        ("quote_submit", {"page_id": "p1", "params": {"utm_campaign": "test"}}),
        ("thank_you_view", {"page_id": "p1", "params": {}}),
    ]
    
    for event_name, payload in test_payloads:
        payload_result = validate_event_payload_structure(event_name, payload)
        checks.extend(payload_result.checks)
    
    errors = sum(1 for c in checks if c.status == "failed")
    warnings = sum(1 for c in checks if c.status == "warning")
    passed = errors == 0
    
    return ValidationResult(checks=checks, passed=passed, errors=errors, warnings=warnings)
