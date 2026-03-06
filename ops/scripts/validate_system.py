#!/usr/bin/env python3
"""Comprehensive system validation script.

Validates system functionality in phases without requiring full deployment.
Can run individual phases or all phases together.

Usage:
    python ops/scripts/validate_system.py [--phase PHASE] [--all] [--json] [--db-path PATH]
    
Examples:
    # Run all phases
    python ops/scripts/validate_system.py --all
    
    # Run specific phase
    python ops/scripts/validate_system.py --phase 1
    
    # JSON output
    python ops/scripts/validate_system.py --all --json
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

# Ensure we can import ae modules
ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / 'src'
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

# Import validation modules
# Add ops to path for imports
OPS_SCRIPTS = ROOT / "ops" / "scripts"
if str(OPS_SCRIPTS.parent.parent) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ops.scripts.validation_modules import (
    ValidationCheck,
    ValidationResult,
    validate_database,
    validate_data_quality,
    validate_cross_consistency,
    validate_state_machines,
)
from ops.scripts.validate_html_files import validate_published_files
from ops.scripts.validate_api_contracts import validate_api_contracts
from ops.scripts.validate_business_rules import validate_business_rules


class Colors:
    """ANSI color codes for terminal output."""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'


def print_step(phase_num: int, total: int, message: str):
    """Print a formatted phase message."""
    try:
        print(f"\n{Colors.BOLD}{Colors.BLUE}[Phase {phase_num}/{total}]{Colors.RESET} {message}")
    except UnicodeEncodeError:
        print(f"\n[Phase {phase_num}/{total}] {message}")


def print_check(check: ValidationCheck, indent: int = 2):
    """Print a validation check result."""
    prefix = " " * indent
    # Use ASCII-safe symbols for Windows compatibility
    if check.status == "passed":
        symbol = f"{Colors.GREEN}[OK]{Colors.RESET}"
    elif check.status == "failed":
        symbol = f"{Colors.RED}[FAIL]{Colors.RESET}"
    elif check.status == "warning":
        symbol = f"{Colors.YELLOW}[WARN]{Colors.RESET}"
    elif check.status == "info":
        symbol = f"{Colors.BLUE}[INFO]{Colors.RESET}"
    else:
        symbol = "[SKIP]"
    
    try:
        print(f"{prefix}{symbol} {check.name}: {check.message}")
    except UnicodeEncodeError:
        # ASCII fallback
        if check.status == "passed":
            symbol = "[OK]"
        elif check.status == "failed":
            symbol = "[FAIL]"
        elif check.status == "warning":
            symbol = "[WARN]"
        elif check.status == "info":
            symbol = "[INFO]"
        else:
            symbol = "[SKIP]"
        print(f"{prefix}{symbol} {check.name}: {check.message}")


class ValidationPhase:
    """Base class for validation phases."""
    
    def __init__(self, phase_num: int, name: str, description: str):
        self.phase_num = phase_num
        self.name = name
        self.description = description
    
    def run(self, db_path: Optional[str] = None, **kwargs) -> ValidationResult:
        """Run validation phase. Must be implemented by subclasses."""
        raise NotImplementedError
    
    def requires_deployment(self) -> bool:
        """Whether this phase requires deployment/services running."""
        return False


class Phase0Prerequisites(ValidationPhase):
    """Phase 0: Prerequisites check."""
    
    def __init__(self):
        super().__init__(0, "Prerequisites", "Check Python version, dependencies, environment")
    
    def run(self, db_path: Optional[str] = None, **kwargs) -> ValidationResult:
        checks: List[ValidationCheck] = []
        
        # Check Python version
        if sys.version_info < (3, 10):
            checks.append(ValidationCheck(
                name="python_version",
                status="failed",
                message=f"Python 3.10+ required, found {sys.version.split()[0]}"
            ))
        else:
            checks.append(ValidationCheck(
                name="python_version",
                status="passed",
                message=f"Python version: {sys.version.split()[0]}"
            ))
        
        # Check dependencies
        required_modules = ["pydantic", "fastapi", "typer"]
        for module in required_modules:
            try:
                __import__(module)
                checks.append(ValidationCheck(
                    name=f"dependency_{module}",
                    status="passed",
                    message=f"Module '{module}' is installed"
                ))
            except ImportError:
                checks.append(ValidationCheck(
                    name=f"dependency_{module}",
                    status="failed",
                    message=f"Module '{module}' is not installed"
                ))
        
        errors = sum(1 for c in checks if c.status == "failed")
        warnings = sum(1 for c in checks if c.status == "warning")
        passed = errors == 0
        
        return ValidationResult(checks=checks, passed=passed, errors=errors, warnings=warnings)


class Phase1CoreFunctionality(ValidationPhase):
    """Phase 1: Core functionality (no deployment required)."""
    
    def __init__(self):
        super().__init__(1, "Core Functionality", "Database, models, business logic")
    
    def run(self, db_path: Optional[str] = None, **kwargs) -> ValidationResult:
        if not db_path:
            db_path = "acq.db"
        
        checks: List[ValidationCheck] = []
        
        # Database validation
        print("  Validating database...")
        db_result = validate_database(db_path)
        checks.extend(db_result.checks)
        
        # Data quality validation
        print("  Validating data quality...")
        quality_result = validate_data_quality(db_path)
        checks.extend(quality_result.checks)
        
        # Cross-consistency validation
        print("  Validating cross-component consistency...")
        consistency_result = validate_cross_consistency(db_path)
        checks.extend(consistency_result.checks)
        
        # State machine validation
        print("  Validating state machines...")
        state_result = validate_state_machines(db_path)
        checks.extend(state_result.checks)
        
        errors = sum(1 for c in checks if c.status == "failed" or c.status == "error")
        warnings = sum(1 for c in checks if c.status == "warning")
        passed = errors == 0
        
        return ValidationResult(checks=checks, passed=passed, errors=errors, warnings=warnings)


class Phase2FileSystem(ValidationPhase):
    """Phase 2: File system validation (no deployment required)."""
    
    def __init__(self):
        super().__init__(2, "File System", "Published files, HTML validation")
    
    def run(self, db_path: Optional[str] = None, **kwargs) -> ValidationResult:
        checks: List[ValidationCheck] = []
        
        # Validate published HTML files
        print("  Validating published HTML files...")
        html_result = validate_published_files()
        checks.extend(html_result.checks)
        
        errors = sum(1 for c in checks if c.status == "failed")
        warnings = sum(1 for c in checks if c.status == "warning")
        passed = errors == 0
        
        return ValidationResult(checks=checks, passed=passed, errors=errors, warnings=warnings)


class Phase3APIContracts(ValidationPhase):
    """Phase 3: API contract validation (no deployment required)."""
    
    def __init__(self):
        super().__init__(3, "API Contracts", "Schema validation, model validation")
    
    def run(self, db_path: Optional[str] = None, **kwargs) -> ValidationResult:
        checks: List[ValidationCheck] = []
        
        # Validate API contracts
        print("  Validating API contracts...")
        api_result = validate_api_contracts()
        checks.extend(api_result.checks)
        
        errors = sum(1 for c in checks if c.status == "failed")
        warnings = sum(1 for c in checks if c.status == "warning")
        passed = errors == 0
        
        return ValidationResult(checks=checks, passed=passed, errors=errors, warnings=warnings)


class Phase4Integration(ValidationPhase):
    """Phase 4: Integration validation (requires local services)."""
    
    def __init__(self):
        super().__init__(4, "Integration", "API endpoints, console UI")
    
    def requires_deployment(self) -> bool:
        return True
    
    def run(self, db_path: Optional[str] = None, **kwargs) -> ValidationResult:
        checks: List[ValidationCheck] = []
        
        # Check if services are running
        try:
            import httpx
            console_url = kwargs.get("console_url", "http://localhost:8000")
            public_url = kwargs.get("public_url", "http://localhost:8001")
            
            # Test console health
            try:
                response = httpx.get(f"{console_url}/health", timeout=2.0)
                if response.status_code == 200:
                    checks.append(ValidationCheck(
                        name="console_health",
                        status="passed",
                        message="Console health endpoint responds"
                    ))
                else:
                    checks.append(ValidationCheck(
                        name="console_health",
                        status="failed",
                        message=f"Console health endpoint returned {response.status_code}"
                    ))
            except Exception as e:
                checks.append(ValidationCheck(
                    name="console_health",
                    status="failed",
                    message=f"Cannot reach console: {e}"
                ))
            
            # Test public API health
            try:
                response = httpx.get(f"{public_url}/health", timeout=2.0)
                if response.status_code == 200:
                    checks.append(ValidationCheck(
                        name="public_api_health",
                        status="passed",
                        message="Public API health endpoint responds"
                    ))
                else:
                    checks.append(ValidationCheck(
                        name="public_api_health",
                        status="failed",
                        message=f"Public API health endpoint returned {response.status_code}"
                    ))
            except Exception as e:
                checks.append(ValidationCheck(
                    name="public_api_health",
                    status="failed",
                    message=f"Cannot reach public API: {e}"
                ))
            
        except ImportError:
            checks.append(ValidationCheck(
                name="integration_check",
                status="warning",
                message="httpx not installed, skipping integration checks"
            ))
        
        errors = sum(1 for c in checks if c.status == "failed")
        warnings = sum(1 for c in checks if c.status == "warning")
        passed = errors == 0
        
        return ValidationResult(checks=checks, passed=passed, errors=errors, warnings=warnings)


class Phase5Deployment(ValidationPhase):
    """Phase 5: Deployment validation (requires full deployment)."""
    
    def __init__(self):
        super().__init__(5, "Deployment", "Reverse proxy, HTTPS, production config")
    
    def requires_deployment(self) -> bool:
        return True
    
    def run(self, db_path: Optional[str] = None, **kwargs) -> ValidationResult:
        checks: List[ValidationCheck] = []
        
        # Check environment variables
        import os
        required_env = ["AE_ENV", "AE_CONSOLE_SECRET"]
        for env_var in required_env:
            if os.getenv(env_var):
                checks.append(ValidationCheck(
                    name=f"env_{env_var}",
                    status="passed",
                    message=f"Environment variable {env_var} is set"
                ))
            else:
                checks.append(ValidationCheck(
                    name=f"env_{env_var}",
                    status="warning",
                    message=f"Environment variable {env_var} is not set (may be optional for dev)"
                ))
        
        # Check CORS configuration
        cors_origins = os.getenv("AE_PUBLIC_CORS_ORIGINS", "*")
        if cors_origins == "*":
            checks.append(ValidationCheck(
                name="cors_config",
                status="warning",
                message="CORS is set to '*' (should be restricted in production)"
            ))
        else:
            checks.append(ValidationCheck(
                name="cors_config",
                status="passed",
                message="CORS is configured with specific origins"
            ))
        
        errors = sum(1 for c in checks if c.status == "failed")
        warnings = sum(1 for c in checks if c.status == "warning")
        passed = errors == 0
        
        return ValidationResult(checks=checks, passed=passed, errors=errors, warnings=warnings)


class Phase6BusinessRules(ValidationPhase):
    """Phase 6: Business rules validation (no deployment required)."""
    
    def __init__(self):
        super().__init__(6, "Business Rules", "Onboarding compliance, publish readiness")
    
    def run(self, db_path: Optional[str] = None, **kwargs) -> ValidationResult:
        if not db_path:
            db_path = "acq.db"
        
        checks: List[ValidationCheck] = []
        
        # Validate business rules
        print("  Validating business rules...")
        business_result = validate_business_rules(db_path)
        checks.extend(business_result.checks)
        
        errors = sum(1 for c in checks if c.status == "failed")
        warnings = sum(1 for c in checks if c.status == "warning")
        passed = errors == 0
        
        return ValidationResult(checks=checks, passed=passed, errors=errors, warnings=warnings)


# Registry of all phases
PHASES: Dict[int, ValidationPhase] = {
    0: Phase0Prerequisites(),
    1: Phase1CoreFunctionality(),
    2: Phase2FileSystem(),
    3: Phase3APIContracts(),
    4: Phase4Integration(),
    5: Phase5Deployment(),
    6: Phase6BusinessRules(),
}


def run_phase(phase_num: int, db_path: Optional[str] = None, **kwargs) -> ValidationResult:
    """Run a specific validation phase."""
    if phase_num not in PHASES:
        return ValidationResult(
            checks=[ValidationCheck(
                name="phase_not_found",
                status="failed",
                message=f"Phase {phase_num} not found. Available phases: {list(PHASES.keys())}"
            )],
            passed=False,
            errors=1
        )
    
    phase = PHASES[phase_num]
    print_step(phase.phase_num, len(PHASES), f"{phase.name}: {phase.description}")
    
    return phase.run(db_path=db_path, **kwargs)


def run_all_phases(db_path: Optional[str] = None, skip_deployment: bool = True, **kwargs) -> Dict[str, Any]:
    """Run all validation phases."""
    results: Dict[str, Any] = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "phases": {},
        "summary": {
            "total_phases": len(PHASES),
            "passed": 0,
            "failed": 0,
            "warnings": 0,
            "errors": 0,
        }
    }
    
    for phase_num in sorted(PHASES.keys()):
        phase = PHASES[phase_num]
        
        # Skip deployment phases if requested
        if skip_deployment and phase.requires_deployment():
            results["phases"][f"phase_{phase_num}"] = {
                "status": "skipped",
                "name": phase.name,
                "reason": "Deployment phases skipped (use --include-deployment to run)"
            }
            continue
        
        result = phase.run(db_path=db_path, **kwargs)
        
        phase_result = {
            "status": "passed" if result.passed else "failed",
            "name": phase.name,
            "checks": len(result.checks),
            "errors": result.errors,
            "warnings": result.warnings,
            "details": [
                {
                    "name": c.name,
                    "status": c.status,
                    "message": c.message,
                    "details": c.details,
                }
                for c in result.checks
            ]
        }
        
        results["phases"][f"phase_{phase_num}"] = phase_result
        
        # Update summary
        if result.passed:
            results["summary"]["passed"] += 1
        else:
            results["summary"]["failed"] += 1
        
        results["summary"]["warnings"] += result.warnings
        results["summary"]["errors"] += result.errors
    
    return results


def print_results(results: Dict[str, Any], json_output: bool = False):
    """Print validation results."""
    if json_output:
        print(json.dumps(results, indent=2))
        return
    
    # Print summary
    try:
        print(f"\n{Colors.BOLD}{'='*60}{Colors.RESET}")
        print(f"{Colors.BOLD}Validation Summary{Colors.RESET}")
        print(f"{'='*60}\n")
    except UnicodeEncodeError:
        print("\n" + "="*60)
        print("Validation Summary")
        print("="*60 + "\n")
    
    summary = results["summary"]
    print(f"Total phases: {summary['total_phases']}")
    print(f"Passed: {summary['passed']}")
    print(f"Failed: {summary['failed']}")
    print(f"Warnings: {summary['warnings']}")
    print(f"Errors: {summary['errors']}\n")
    
    # Print phase results
    for phase_key, phase_result in results["phases"].items():
        if phase_result.get("status") == "skipped":
            print(f"  [SKIP] {phase_result.get('name', phase_key)}: {phase_result.get('reason', 'Skipped')}")
            continue
        
        status = phase_result.get("status", "unknown")
        phase_name = phase_result.get("name", phase_key)
        checks_count = phase_result.get("checks", 0)
        errors_count = phase_result.get("errors", 0)
        warnings_count = phase_result.get("warnings", 0)
        
        # Use ASCII-safe status indicators
        try:
            if status == "passed":
                status_str = f"{Colors.GREEN}[PASS]{Colors.RESET}"
            else:
                status_str = f"{Colors.RED}[FAIL]{Colors.RESET}"
        except (UnicodeEncodeError, UnicodeError):
            status_str = "[PASS]" if status == "passed" else "[FAIL]"
        
        try:
            print(f"  {status_str} {phase_name}: {checks_count} checks, {errors_count} errors, {warnings_count} warnings")
        except UnicodeEncodeError:
            print(f"  {status_str} {phase_name}: {checks_count} checks, {errors_count} errors, {warnings_count} warnings")
        
        # Print failed checks
        for check in phase_result.get("details", []):
            if check.get("status") == "failed":
                try:
                    print(f"    [FAIL] {check.get('name', 'unknown')}: {check.get('message', '')}")
                except UnicodeEncodeError:
                    print(f"    [FAIL] {check.get('name', 'unknown')}: {check.get('message', '')}")


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Comprehensive system validation script"
    )
    parser.add_argument(
        "--phase",
        type=int,
        help="Run specific phase (0-6)"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Run all phases"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON"
    )
    parser.add_argument(
        "--db-path",
        default="acq.db",
        help="Path to SQLite database (default: acq.db)"
    )
    parser.add_argument(
        "--include-deployment",
        action="store_true",
        help="Include deployment phases (4-5) when running --all"
    )
    parser.add_argument(
        "--console-url",
        default="http://localhost:8000",
        help="Console URL for integration tests (default: http://localhost:8000)"
    )
    parser.add_argument(
        "--public-url",
        default="http://localhost:8001",
        help="Public API URL for integration tests (default: http://localhost:8001)"
    )
    
    args = parser.parse_args()
    
    if args.phase is not None:
        # Run specific phase
        result = run_phase(args.phase, db_path=args.db_path, console_url=args.console_url, public_url=args.public_url)
        results = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "phases": {
                f"phase_{args.phase}": {
                    "status": "passed" if result.passed else "failed",
                    "checks": len(result.checks),
                    "errors": result.errors,
                    "warnings": result.warnings,
                    "details": [
                        {
                            "name": c.name,
                            "status": c.status,
                            "message": c.message,
                            "details": c.details,
                        }
                        for c in result.checks
                    ]
                }
            },
            "summary": {
                "total_phases": 1,
                "passed": 1 if result.passed else 0,
                "failed": 0 if result.passed else 1,
                "warnings": result.warnings,
                "errors": result.errors,
            }
        }
        
        if not args.json:
            # Print checks
            for check in result.checks:
                print_check(check)
            print(f"\nPhase {args.phase}: {'PASSED' if result.passed else 'FAILED'}")
        
        print_results(results, json_output=args.json)
        return 0 if result.passed else 1
    
    elif args.all:
        # Run all phases
        results = run_all_phases(
            db_path=args.db_path,
            skip_deployment=not args.include_deployment,
            console_url=args.console_url,
            public_url=args.public_url
        )
        print_results(results, json_output=args.json)
        
        all_passed = results["summary"]["failed"] == 0
        return 0 if all_passed else 1
    
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
