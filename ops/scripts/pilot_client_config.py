#!/usr/bin/env python3
"""Interactive script to configure a client for the pilot checklist.

This script guides you through client configuration step-by-step.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Ensure we can import ae modules
ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / 'src'
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ae import db as dbmod
from ae import repo
from ae.models import Client
from ae.enums import Trade, ClientStatus


def print_header(text: str):
    """Print a formatted header."""
    print("\n" + "=" * 60)
    print(f"  {text}")
    print("=" * 60 + "\n")


def print_step(step: int, total: int, text: str):
    """Print a step indicator."""
    print(f"[{step}/{total}] {text}")


def get_input(prompt: str, default: str = "", required: bool = True) -> str:
    """Get user input with optional default."""
    if default:
        full_prompt = f"{prompt} [{default}]: "
    else:
        full_prompt = f"{prompt}: "
    
    value = input(full_prompt).strip()
    if not value:
        if default:
            return default
        if required:
            print("  ⚠ This field is required. Please enter a value.")
            return get_input(prompt, default, required)
        return ""
    return value


def get_choice(prompt: str, choices: list[str], default: str = "") -> str:
    """Get user choice from a list."""
    print(f"\n{prompt}")
    for i, choice in enumerate(choices, 1):
        marker = " (default)" if choice == default else ""
        print(f"  {i}. {choice}{marker}")
    
    while True:
        try:
            response = input("\nEnter choice [1-{}]: ".format(len(choices))).strip()
            if not response and default:
                return default
            idx = int(response) - 1
            if 0 <= idx < len(choices):
                return choices[idx]
            print("  ⚠ Invalid choice. Please try again.")
        except ValueError:
            print("  ⚠ Please enter a number.")


def get_multi_input(prompt: str) -> list[str]:
    """Get multiple values (e.g., service areas)."""
    print(f"\n{prompt}")
    print("  (Enter one value per line, empty line to finish)")
    values = []
    while True:
        value = input(f"  Value {len(values) + 1}: ").strip()
        if not value:
            break
        values.append(value)
    return values if values else [get_input("At least one value required", required=True)]


def configure_client(db_path: str) -> bool:
    """Interactive client configuration."""
    print_header("Client Configuration - Pilot Checklist")
    
    # Check if DB exists
    if not os.path.exists(db_path):
        print(f"⚠ Database not found: {db_path}")
        init = input("Initialize database? [y/N]: ").strip().lower()
        if init == 'y':
            dbmod.init_db(db_path)
            print("✓ Database initialized")
        else:
            print("✗ Cannot proceed without database")
            return False
    
    # Step 1: Basic Information
    print_step(1, 5, "Basic Information")
    client_id = get_input("Client ID (slug, e.g., plumber-cm-oldtown)", required=True)
    
    # Check if client already exists
    existing = repo.get_client(db_path, client_id=client_id)
    if existing:
        print(f"\n⚠ Client '{client_id}' already exists:")
        print(f"  Name: {existing.client_name}")
        print(f"  Trade: {existing.trade}")
        overwrite = input("\nUpdate existing client? [y/N]: ").strip().lower()
        if overwrite != 'y':
            print("✗ Cancelled")
            return False
    
    client_name = get_input("Client Name", required=True)
    
    # Step 2: Trade Selection
    print_step(2, 5, "Trade Selection")
    trades = [t.value for t in Trade]
    trade_value = get_choice("Select Trade", trades, default=trades[0])
    trade = Trade(trade_value)
    
    # Step 3: Geographic Information
    print_step(3, 5, "Geographic Information")
    geo_country = get_input("Country Code (ISO, e.g., au, th, us)", default="th", required=True)
    geo_city = get_input("City Name", required=True)
    service_areas = get_multi_input("Service Areas")
    
    # Step 4: Contact Information
    print_step(4, 5, "Contact Information")
    primary_phone = get_input("Primary Phone (e.g., +66-80-000-0000)", required=True)
    lead_email = get_input("Lead Email", required=True)
    
    # Step 5: Optional Information
    print_step(5, 5, "Optional Information")
    hours = get_input("Business Hours", required=False)
    status = get_choice(
        "Status",
        [s.value for s in ClientStatus],
        default=ClientStatus.draft.value
    )
    
    # Create client
    print("\n" + "-" * 60)
    print("Creating client...")
    
    client = Client(
        client_id=client_id,
        client_name=client_name,
        trade=trade,
        geo_country=geo_country,
        geo_city=geo_city,
        service_area=service_areas,
        primary_phone=primary_phone,
        lead_email=lead_email,
        status=ClientStatus(status),
        hours=hours if hours else None,
        license_badges=[],
    )
    
    try:
        repo.upsert_client(db_path, client)
        print(f"✓ Client '{client_id}' created/updated successfully")
    except Exception as e:
        print(f"✗ Error creating client: {e}")
        return False
    
    # Initialize onboarding templates
    print("\n" + "-" * 60)
    print("Initializing onboarding templates...")
    try:
        templates = repo.ensure_default_onboarding_templates(db_path, client_id)
        print(f"✓ Onboarding templates initialized ({len(templates)} templates)")
    except Exception as e:
        print(f"⚠ Warning: Could not initialize templates: {e}")
    
    # Summary
    print("\n" + "=" * 60)
    print("  Client Configuration Complete!")
    print("=" * 60)
    print(f"\nClient ID: {client_id}")
    print(f"Name: {client_name}")
    print(f"Trade: {trade.value}")
    print(f"Location: {geo_city}, {geo_country}")
    print(f"Service Areas: {', '.join(service_areas)}")
    print(f"Status: {status}")
    
    print("\nNext Steps:")
    print("  1. Review onboarding templates: /console/onboarding?client_id=" + client_id)
    print("  2. Create landing page: python -m ae.cli create-page ...")
    print("  3. Set up chat channel (via console)")
    print("  4. Configure ads integration")
    
    return True


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Configure a client for pilot")
    parser.add_argument(
        "--db",
        default="acq.db",
        help="Database path (default: acq.db)"
    )
    
    args = parser.parse_args()
    
    success = configure_client(args.db)
    sys.exit(0 if success else 1)
