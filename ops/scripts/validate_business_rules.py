"""Business rules validation module.

Validates business logic invariants, onboarding compliance, and publish readiness.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

# Ensure we can import ae modules
import sys
from pathlib import Path as PathLib

ROOT = PathLib(__file__).resolve().parents[2]
SRC = ROOT / 'src'
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ae import repo, service
from ae.models import Client, Page, Template
from ae.policies import publish_readiness, REQUIRED_PAGE_EVENTS_V1
from ops.scripts.validation_modules import ValidationCheck, ValidationResult


def validate_publish_readiness(db_path: str, page_id: str) -> ValidationResult:
    """Validate publish readiness for a page (extends beyond basic validation).
    
    Args:
        db_path: Path to SQLite database
        page_id: Page ID to validate
        
    Returns:
        ValidationResult with publish readiness checks
    """
    checks: List[ValidationCheck] = []
    
    try:
        # Get page, client, template
        page = repo.get_page(db_path, page_id)
        if not page:
            checks.append(ValidationCheck(
                name="page_exists",
                status="failed",
                message=f"Page not found: {page_id}"
            ))
            return ValidationResult(checks=checks, passed=False, errors=1)
        
        checks.append(ValidationCheck(
            name="page_exists",
            status="passed",
            message=f"Page found: {page_id}"
        ))
        
        client = repo.get_client(db_path, page.client_id)
        if not client:
            checks.append(ValidationCheck(
                name="client_exists",
                status="failed",
                message=f"Client not found: {page.client_id}"
            ))
            return ValidationResult(checks=checks, passed=False, errors=1)
        
        checks.append(ValidationCheck(
            name="client_exists",
            status="passed",
            message=f"Client found: {page.client_id}"
        ))
        
        template = repo.get_template(db_path, page.template_id)
        if not template:
            checks.append(ValidationCheck(
                name="template_exists",
                status="failed",
                message=f"Template not found: {page.template_id}"
            ))
            return ValidationResult(checks=checks, passed=False, errors=1)
        
        checks.append(ValidationCheck(
            name="template_exists",
            status="passed",
            message=f"Template found: {page.template_id}"
        ))
        
        # Check template version compatibility
        if page.template_version != template.template_version:
            checks.append(ValidationCheck(
                name="template_version_compatibility",
                status="warning",
                message=f"Template version mismatch: page uses {page.template_version}, template is {template.template_version}"
            ))
        else:
            checks.append(ValidationCheck(
                name="template_version_compatibility",
                status="passed",
                message="Template version matches"
            ))
        
        # Check required events
        has_events = repo.has_validated_events(db_path, page_id)
        if has_events:
            checks.append(ValidationCheck(
                name="required_events",
                status="passed",
                message="Required events validated"
            ))
        else:
            checks.append(ValidationCheck(
                name="required_events",
                status="failed",
                message=f"Required events not validated: {', '.join(REQUIRED_PAGE_EVENTS_V1)}"
            ))
        
        # Run publish_readiness check
        ok, errors = publish_readiness(client, page, template, has_events=has_events)
        if ok:
            checks.append(ValidationCheck(
                name="publish_readiness",
                status="passed",
                message="Publish readiness check passed"
            ))
        else:
            checks.append(ValidationCheck(
                name="publish_readiness",
                status="failed",
                message=f"Publish readiness check failed: {', '.join(errors)}",
                details={"errors": errors}
            ))
        
        # Additional checks beyond basic publish_readiness
        
        # Check page URL format
        if page.page_url:
            if page.page_url.startswith("http://") or page.page_url.startswith("https://"):
                checks.append(ValidationCheck(
                    name="page_url_format",
                    status="passed",
                    message="Page URL has valid format"
                ))
            else:
                checks.append(ValidationCheck(
                    name="page_url_format",
                    status="warning",
                    message="Page URL does not start with http:// or https://"
                ))
        else:
            checks.append(ValidationCheck(
                name="page_url_format",
                status="failed",
                message="Page URL is missing"
            ))
        
        # Check page slug format
        if page.page_slug:
            if page.page_slug.replace("-", "").replace("_", "").isalnum():
                checks.append(ValidationCheck(
                    name="page_slug_format",
                    status="passed",
                    message="Page slug has valid format"
                ))
            else:
                checks.append(ValidationCheck(
                    name="page_slug_format",
                    status="warning",
                    message="Page slug contains special characters"
                ))
        else:
            checks.append(ValidationCheck(
                name="page_slug_format",
                status="failed",
                message="Page slug is missing"
            ))
        
    except Exception as e:
        checks.append(ValidationCheck(
            name="publish_readiness_check",
            status="failed",
            message=f"Publish readiness check error: {e}"
        ))
        return ValidationResult(checks=checks, passed=False, errors=1)
    
    errors = sum(1 for c in checks if c.status == "failed")
    warnings = sum(1 for c in checks if c.status == "warning")
    passed = errors == 0
    
    return ValidationResult(checks=checks, passed=passed, errors=errors, warnings=warnings)


def validate_onboarding_compliance(db_path: str, client_id: str) -> ValidationResult:
    """Validate onboarding policy compliance (UTM policy, naming conventions, event map).
    
    Args:
        db_path: Path to SQLite database
        client_id: Client ID to validate
        
    Returns:
        ValidationResult with onboarding compliance checks
    """
    checks: List[ValidationCheck] = []
    
    try:
        # Check client exists
        client = repo.get_client(db_path, client_id)
        if not client:
            checks.append(ValidationCheck(
                name="client_exists",
                status="failed",
                message=f"Client not found: {client_id}"
            ))
            return ValidationResult(checks=checks, passed=False, errors=1)
        
        # Check for onboarding files
        onboarding_dir = Path(f"clients/{client_id}/onboarding")
        
        if not onboarding_dir.exists():
            checks.append(ValidationCheck(
                name="onboarding_directory",
                status="warning",
                message=f"Onboarding directory not found: {onboarding_dir} (may be optional)"
            ))
            return ValidationResult(checks=checks, passed=True, warnings=1)
        
        checks.append(ValidationCheck(
            name="onboarding_directory",
            status="passed",
            message=f"Onboarding directory exists: {onboarding_dir}"
        ))
        
        # Check UTM policy file
        utm_policy_file = onboarding_dir / "utm_policy.md"
        if utm_policy_file.exists():
            checks.append(ValidationCheck(
                name="utm_policy_file",
                status="passed",
                message="UTM policy file found"
            ))
            
            # Basic validation: check file is not empty
            # Use UTF-8 encoding to handle special characters
            try:
                content = utm_policy_file.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                # Fallback to latin-1 if UTF-8 fails
                try:
                    content = utm_policy_file.read_text(encoding="latin-1")
                except Exception as e:
                    checks.append(ValidationCheck(
                        name="utm_policy_content",
                        status="warning",
                        message=f"Cannot read UTM policy file: {e}"
                    ))
                    content = ""
            
            if len(content.strip()) > 0:
                checks.append(ValidationCheck(
                    name="utm_policy_content",
                    status="passed",
                    message="UTM policy file has content"
                ))
            else:
                checks.append(ValidationCheck(
                    name="utm_policy_content",
                    status="warning",
                    message="UTM policy file is empty"
                ))
        else:
            checks.append(ValidationCheck(
                name="utm_policy_file",
                status="warning",
                message="UTM policy file not found"
            ))
        
        # Check naming convention file
        naming_file = onboarding_dir / "naming_convention.md"
        if naming_file.exists():
            checks.append(ValidationCheck(
                name="naming_convention_file",
                status="passed",
                message="Naming convention file found"
            ))
        else:
            checks.append(ValidationCheck(
                name="naming_convention_file",
                status="warning",
                message="Naming convention file not found"
            ))
        
        # Check event map file
        event_map_file = onboarding_dir / "event_map.md"
        if event_map_file.exists():
            checks.append(ValidationCheck(
                name="event_map_file",
                status="passed",
                message="Event map file found"
            ))
            
            # Check event map references required events
            # Use UTF-8 encoding to handle special characters
            try:
                content = event_map_file.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                # Fallback to latin-1 if UTF-8 fails
                try:
                    content = event_map_file.read_text(encoding="latin-1")
                except Exception as e:
                    checks.append(ValidationCheck(
                        name="event_map_content",
                        status="warning",
                        message=f"Cannot read event map file: {e}"
                    ))
                    content = ""
            required_events_found = []
            for event in REQUIRED_PAGE_EVENTS_V1:
                if event in content:
                    required_events_found.append(event)
            
            if len(required_events_found) == len(REQUIRED_PAGE_EVENTS_V1):
                checks.append(ValidationCheck(
                    name="event_map_completeness",
                    status="passed",
                    message="Event map includes all required events"
                ))
            else:
                missing = set(REQUIRED_PAGE_EVENTS_V1) - set(required_events_found)
                checks.append(ValidationCheck(
                    name="event_map_completeness",
                    status="warning",
                    message=f"Event map missing events: {', '.join(missing)}"
                ))
        else:
            checks.append(ValidationCheck(
                name="event_map_file",
                status="warning",
                message="Event map file not found"
            ))
        
    except Exception as e:
        checks.append(ValidationCheck(
            name="onboarding_compliance_check",
            status="failed",
            message=f"Onboarding compliance check error: {e}"
        ))
        return ValidationResult(checks=checks, passed=False, errors=1)
    
    errors = sum(1 for c in checks if c.status == "failed")
    warnings = sum(1 for c in checks if c.status == "warning")
    passed = errors == 0
    
    return ValidationResult(checks=checks, passed=passed, errors=errors, warnings=warnings)


def validate_business_rules(db_path: str, page_id: Optional[str] = None, client_id: Optional[str] = None) -> ValidationResult:
    """Run all business rules validations.
    
    Args:
        db_path: Path to SQLite database
        page_id: Optional page ID to validate
        client_id: Optional client ID to validate
        
    Returns:
        ValidationResult with all business rules checks
    """
    checks: List[ValidationCheck] = []
    
    # Validate publish readiness for pages
    if page_id:
        result = validate_publish_readiness(db_path, page_id)
        checks.extend(result.checks)
    else:
        # Validate all pages
        pages = repo.list_pages(db_path, limit=100)
        for page in pages[:10]:  # Limit to first 10 pages
            result = validate_publish_readiness(db_path, page.page_id)
            checks.extend(result.checks)
    
    # Validate onboarding compliance
    if client_id:
        result = validate_onboarding_compliance(db_path, client_id)
        checks.extend(result.checks)
    else:
        # Validate all clients
        from ae import db
        con = db.connect(db_path)
        try:
            client_ids = [row[0] for row in con.execute("SELECT client_id FROM clients LIMIT 10").fetchall()]
            for cid in client_ids:
                result = validate_onboarding_compliance(db_path, cid)
                checks.extend(result.checks)
        finally:
            con.close()
    
    errors = sum(1 for c in checks if c.status == "failed")
    warnings = sum(1 for c in checks if c.status == "warning")
    passed = errors == 0
    
    return ValidationResult(checks=checks, passed=passed, errors=errors, warnings=warnings)
