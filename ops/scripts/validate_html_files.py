"""HTML file validation module.

Validates published HTML files for correct structure, tracking JavaScript,
and configuration.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional

# Ensure we can import validation modules
ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / 'src'
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ops.scripts.validation_modules import ValidationCheck, ValidationResult


def validate_html_file(html_path: Path, expected_page_id: Optional[str] = None) -> ValidationResult:
    """Validate a single HTML file.
    
    Args:
        html_path: Path to HTML file
        expected_page_id: Expected page ID (optional, will be extracted if not provided)
        
    Returns:
        ValidationResult with HTML validation checks
    """
    checks: List[ValidationCheck] = []
    
    # Check file exists
    if not html_path.exists():
        checks.append(ValidationCheck(
            name="file_exists",
            status="failed",
            message=f"HTML file not found: {html_path}"
        ))
        return ValidationResult(checks=checks, passed=False, errors=1)
    
    checks.append(ValidationCheck(
        name="file_exists",
        status="passed",
        message=f"HTML file exists: {html_path}"
    ))
    
    # Check file is not empty
    file_size = html_path.stat().st_size
    if file_size == 0:
        checks.append(ValidationCheck(
            name="file_not_empty",
            status="failed",
            message="HTML file is empty"
        ))
        return ValidationResult(checks=checks, passed=False, errors=1)
    
    checks.append(ValidationCheck(
        name="file_not_empty",
        status="passed",
        message=f"HTML file size: {file_size} bytes"
    ))
    
    # Read file content
    try:
        content = html_path.read_text(encoding="utf-8")
    except Exception as e:
        checks.append(ValidationCheck(
            name="file_readable",
            status="failed",
            message=f"Cannot read HTML file: {e}"
        ))
        return ValidationResult(checks=checks, passed=False, errors=1)
    
    # Check HTML structure
    if "<!doctype html>" in content.lower() or "<!DOCTYPE html>" in content:
        checks.append(ValidationCheck(
            name="html_doctype",
            status="passed",
            message="Valid HTML doctype found"
        ))
    else:
        checks.append(ValidationCheck(
            name="html_doctype",
            status="warning",
            message="HTML doctype not found (may still be valid HTML)"
        ))
    
    # Check for tracking JavaScript
    if "Acquisition Engine Tracking" in content:
        checks.append(ValidationCheck(
            name="tracking_js_present",
            status="passed",
            message="Tracking JavaScript found"
        ))
    else:
        checks.append(ValidationCheck(
            name="tracking_js_present",
            status="failed",
            message="Tracking JavaScript not found"
        ))
    
    # Extract and validate PAGE_ID
    page_id_match = re.search(r'PAGE_ID\s*=\s*["\']([^"\']+)["\']', content)
    if page_id_match:
        found_page_id = page_id_match.group(1)
        checks.append(ValidationCheck(
            name="page_id_configured",
            status="passed",
            message=f"PAGE_ID configured: {found_page_id}",
            details={"page_id": found_page_id}
        ))
        
        if expected_page_id and found_page_id != expected_page_id:
            checks.append(ValidationCheck(
                name="page_id_matches",
                status="warning",
                message=f"PAGE_ID mismatch: expected '{expected_page_id}', found '{found_page_id}'"
            ))
        elif expected_page_id:
            checks.append(ValidationCheck(
                name="page_id_matches",
                status="passed",
                message="PAGE_ID matches expected value"
            ))
    else:
        checks.append(ValidationCheck(
            name="page_id_configured",
            status="failed",
            message="PAGE_ID not found in tracking JavaScript"
        ))
    
    # Check API endpoint
    if "/v1/event" in content or "/event" in content:
        checks.append(ValidationCheck(
            name="api_endpoint_present",
            status="passed",
            message="API endpoint found in tracking code"
        ))
    else:
        checks.append(ValidationCheck(
            name="api_endpoint_present",
            status="failed",
            message="API endpoint not found in tracking code"
        ))
    
    # Check UTM parameter extraction
    if "getUTMParams" in content or "utm_source" in content:
        checks.append(ValidationCheck(
            name="utm_extraction",
            status="passed",
            message="UTM parameter extraction code found"
        ))
    else:
        checks.append(ValidationCheck(
            name="utm_extraction",
            status="warning",
            message="UTM parameter extraction code not found"
        ))
    
    # Check event tracking function
    if "trackEvent" in content:
        checks.append(ValidationCheck(
            name="track_event_function",
            status="passed",
            message="trackEvent function found"
        ))
    else:
        checks.append(ValidationCheck(
            name="track_event_function",
            status="failed",
            message="trackEvent function not found"
        ))
    
    # Check event handlers
    event_handlers_found = []
    if "call_click" in content:
        event_handlers_found.append("call_click")
    if "quote_submit" in content:
        event_handlers_found.append("quote_submit")
    if "thank_you_view" in content:
        event_handlers_found.append("thank_you_view")
    
    if event_handlers_found:
        checks.append(ValidationCheck(
            name="event_handlers",
            status="passed",
            message=f"Event handlers found: {', '.join(event_handlers_found)}",
            details={"handlers": event_handlers_found}
        ))
    else:
        checks.append(ValidationCheck(
            name="event_handlers",
            status="warning",
            message="No event handlers found in tracking code"
        ))
    
    # Check sendBeacon fallback
    if "sendBeacon" in content or "fetch" in content:
        checks.append(ValidationCheck(
            name="sendbeacon_fallback",
            status="passed",
            message="sendBeacon or fetch fallback found"
        ))
    else:
        checks.append(ValidationCheck(
            name="sendbeacon_fallback",
            status="warning",
            message="sendBeacon/fetch fallback not found"
        ))
    
    # Check CSS/assets references
    if "assets/styles.css" in content or "styles.css" in content or "<link" in content:
        checks.append(ValidationCheck(
            name="css_reference",
            status="passed",
            message="CSS reference found"
        ))
    else:
        checks.append(ValidationCheck(
            name="css_reference",
            status="warning",
            message="CSS reference not found"
        ))
    
    errors = sum(1 for c in checks if c.status == "failed")
    warnings = sum(1 for c in checks if c.status == "warning")
    passed = errors == 0
    
    return ValidationResult(checks=checks, passed=passed, errors=errors, warnings=warnings)


def validate_published_files(base_dir: str = "exports/static_site", page_id: Optional[str] = None) -> ValidationResult:
    """Validate all published HTML files in the exports directory.
    
    Args:
        base_dir: Base directory for published files
        page_id: Optional specific page ID to validate
        
    Returns:
        ValidationResult with published files validation checks
    """
    checks: List[ValidationCheck] = []
    base_path = Path(base_dir)
    
    if not base_path.exists():
        checks.append(ValidationCheck(
            name="exports_directory_exists",
            status="warning",
            message=f"Exports directory not found: {base_dir} (no pages published yet)"
        ))
        return ValidationResult(checks=checks, passed=True, warnings=1)
    
    checks.append(ValidationCheck(
        name="exports_directory_exists",
        status="passed",
        message=f"Exports directory exists: {base_dir}"
    ))
    
    # Find all HTML files
    if page_id:
        html_files = [base_path / page_id / "index.html"]
    else:
        html_files = list(base_path.glob("*/index.html"))
    
    if not html_files:
        checks.append(ValidationCheck(
            name="html_files_found",
            status="warning",
            message="No published HTML files found"
        ))
        return ValidationResult(checks=checks, passed=True, warnings=1)
    
    checks.append(ValidationCheck(
        name="html_files_found",
        status="passed",
        message=f"Found {len(html_files)} published HTML file(s)"
    ))
    
    # Validate each HTML file
    all_passed = True
    total_errors = 0
    total_warnings = 0
    
    for html_file in html_files:
        if not html_file.exists():
            checks.append(ValidationCheck(
                name=f"validate_{html_file.parent.name}",
                status="failed",
                message=f"HTML file not found: {html_file}"
            ))
            all_passed = False
            total_errors += 1
            continue
        
        page_id_from_path = html_file.parent.name
        result = validate_html_file(html_file, expected_page_id=page_id_from_path)
        
        # Aggregate results
        if not result.passed:
            all_passed = False
        
        total_errors += result.errors
        total_warnings += result.warnings
        
        # Add summary check for this file
        status_str = "passed" if result.passed else "failed"
        checks.append(ValidationCheck(
            name=f"validate_{page_id_from_path}",
            status=status_str,
            message=f"Page {page_id_from_path}: {len(result.checks)} checks, {result.errors} errors, {result.warnings} warnings",
            details={
                "page_id": page_id_from_path,
                "checks": len(result.checks),
                "errors": result.errors,
                "warnings": result.warnings
            }
        ))
    
    return ValidationResult(
        checks=checks,
        passed=all_passed,
        errors=total_errors,
        warnings=total_warnings
    )
