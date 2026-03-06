"""Demonstrate content personalization for landing pages.

This script shows how the enhanced StubContentAdapter generates
personalized content based on client data.
"""

import sys
import os
import io

# Fix Windows console encoding issues
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# Add src to path (run from project root)
_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(_root, "src"))

from ae.models import Client, Page, BusinessModel, Trade, ClientStatus
from ae.adapters.content_stub import StubContentAdapter
from ae.enums import PageStatus
from datetime import datetime

def demonstrate_content():
    """Demonstrate personalized content generation."""
    
    adapter = StubContentAdapter()
    
    print("=" * 80)
    print("LANDING PAGE CONTENT PERSONALIZATION DEMONSTRATION")
    print("=" * 80)
    print()
    
    # Scenario 1: Minimal client data (before personalization)
    print("SCENARIO 1: Minimal Client Data (Generic Content)")
    print("-" * 80)
    client_minimal = Client(
        client_id="test-spa-minimal",
        client_name="Test Spa",
        trade=Trade.massage,
        business_model=BusinessModel.fixed_price,
        geo_city="chiang mai",
        service_area=["Chiang Mai"],
        primary_phone="+66-80-000-0000",
        lead_email="test@example.com",
        status=ClientStatus.draft,
    )
    
    page = Page(
        page_id="test-page-minimal",
        client_id="test-spa-minimal",
        template_id="service_lp",
        template_version="1.0",
        page_slug="test-minimal",
        page_url="/test-minimal",
        page_status=PageStatus.draft,
        content_version=1,
        locale="en",
    )
    
    context = {
        "client": client_minimal,
        "page": page,
        "db_path": "acq.db",
    }
    
    payload_minimal = adapter.build("test-page-minimal", context)
    
    print(f"Headline: {payload_minimal['headline']}")
    print(f"Subheadline: {payload_minimal['subheadline']}")
    print(f"CTA Primary: {payload_minimal['cta_primary']}")
    print(f"CTA Secondary: {payload_minimal['cta_secondary']}")
    print(f"Amenities: {payload_minimal['sections'][0]['items']}")
    testimonials_str = str(payload_minimal['sections'][1]['items'])
    print(f"Testimonials: {testimonials_str}")
    print(f"FAQ: {payload_minimal['sections'][2]['items']}")
    print()
    
    # Scenario 2: Full client data (highly personalized)
    print("SCENARIO 2: Full Client Data (Highly Personalized)")
    print("-" * 80)
    client_full = Client(
        client_id="test-spa-full",
        client_name="Premium Massage & Wellness Spa",
        trade=Trade.massage,
        business_model=BusinessModel.fixed_price,
        geo_city="chiang mai",
        service_area=["Chiang Mai City", "Chiang Mai Old Town", "Nimman"],
        primary_phone="+66-80-123-4567",
        lead_email="info@premiumspa.com",
        status=ClientStatus.live,
        hours="Mon-Fri 9am-8pm, Sat-Sun 10am-6pm",
        license_badges=["Licensed", "Insured", "Certified Therapist"],
        price_anchor="Starting from ฿800",
        service_config_json={
            "default_available_slots": 2,  # Low availability for urgency
        },
    )
    
    page_full = Page(
        page_id="test-page-full",
        client_id="test-spa-full",
        template_id="service_lp",
        template_version="1.0",
        page_slug="test-full",
        page_url="/test-full",
        page_status=PageStatus.draft,
        content_version=1,
        locale="en",
    )
    
    context_full = {
        "client": client_full,
        "page": page_full,
        "db_path": "acq.db",
    }
    
    payload_full = adapter.build("test-page-full", context_full)
    
    print(f"Headline: {payload_full['headline']}")
    print(f"Subheadline: {payload_full['subheadline']}")
    print(f"CTA Primary: {payload_full['cta_primary']}")
    print(f"CTA Secondary: {payload_full['cta_secondary']}")
    print(f"Amenities: {payload_full['sections'][0]['items']}")
    testimonials_str = str(payload_full['sections'][1]['items'])
    print(f"Testimonials: {testimonials_str}")
    print(f"FAQ: {payload_full['sections'][2]['items']}")
    print(f"Default Available Slots: {payload_full.get('default_available_slots', 'Not set')}")
    print()
    
    # Scenario 3: Custom content override
    print("SCENARIO 3: Custom Content Override via service_config_json")
    print("-" * 80)
    client_custom = Client(
        client_id="test-spa-custom",
        client_name="Luxury Spa Retreat",
        trade=Trade.massage,
        business_model=BusinessModel.fixed_price,
        geo_city="bangkok",
        service_area=["Sukhumvit", "Siam"],
        primary_phone="+66-80-999-8888",
        lead_email="luxury@spa.com",
        status=ClientStatus.live,
        hours="Daily 10am-10pm",
        license_badges=["5-Star Rated", "Award Winning"],
        price_anchor="From ฿1,500",
        service_config_json={
            "custom_headline": "Experience Ultimate Relaxation at Luxury Spa Retreat",
            "custom_subheadline": "Open daily 10am-10pm. Book your premium wellness experience today.",
            "custom_amenities": [
                "5-Star Luxury Facilities",
                "Award-Winning Therapists",
                "Premium Essential Oils",
                "Private Treatment Rooms"
            ],
            "custom_testimonials": [
                "Rated 5★ by 1,000+ guests",
                "Best Spa in Sukhumvit 2024",
                "Same-day appointments available"
            ],
            "custom_faq": [
                "What makes your spa different?",
                "Do you offer couples packages?",
                "Can I book same-day appointments?"
            ],
            "custom_cta_primary": "Reserve Your Session",
            "custom_cta_secondary": "View Premium Packages",
            "default_available_slots": 1,  # Very limited
        },
    )
    
    page_custom = Page(
        page_id="test-page-custom",
        client_id="test-spa-custom",
        template_id="service_lp",
        template_version="1.0",
        page_slug="test-custom",
        page_url="/test-custom",
        page_status=PageStatus.draft,
        content_version=1,
        locale="en",
    )
    
    context_custom = {
        "client": client_custom,
        "page": page_custom,
        "db_path": "acq.db",
    }
    
    payload_custom = adapter.build("test-page-custom", context_custom)
    
    print(f"Headline: {payload_custom['headline']}")
    print(f"Subheadline: {payload_custom['subheadline']}")
    print(f"CTA Primary: {payload_custom['cta_primary']}")
    print(f"CTA Secondary: {payload_custom['cta_secondary']}")
    print(f"Amenities: {payload_custom['sections'][0]['items']}")
    testimonials_str = str(payload_custom['sections'][1]['items'])
    print(f"Testimonials: {testimonials_str}")
    print(f"FAQ: {payload_custom['sections'][2]['items']}")
    print(f"Default Available Slots: {payload_custom.get('default_available_slots', 'Not set')}")
    print()
    
    # Scenario 4: Trade template (quote-based)
    print("SCENARIO 4: Trade Template (Quote-Based Business)")
    print("-" * 80)
    client_trade = Client(
        client_id="test-plumber",
        client_name="Reliable Plumbing Services",
        trade=Trade.plumber,
        business_model=BusinessModel.quote_based,
        geo_city="bangkok",
        service_area=["Bangkok Central", "Sukhumvit", "Silom"],
        primary_phone="+66-80-111-2222",
        lead_email="info@reliableplumbing.com",
        status=ClientStatus.live,
        hours="Mon-Sat 7am-7pm, Emergency 24/7",
        license_badges=["Licensed", "Insured", "10+ Years Experience"],
        price_anchor="Free quotes",
    )
    
    page_trade = Page(
        page_id="test-page-trade",
        client_id="test-plumber",
        template_id="trade_lp",
        template_version="1.0",
        page_slug="test-trade",
        page_url="/test-trade",
        page_status=PageStatus.draft,
        content_version=1,
        locale="en",
    )
    
    context_trade = {
        "client": client_trade,
        "page": page_trade,
        "db_path": "acq.db",
    }
    
    payload_trade = adapter.build("test-page-trade", context_trade)
    
    print(f"Headline: {payload_trade['headline']}")
    print(f"Subheadline: {payload_trade['subheadline']}")
    print(f"CTA Primary: {payload_trade['cta_primary']}")
    print(f"CTA Secondary: {payload_trade['cta_secondary']}")
    print(f"Benefits: {payload_trade['sections'][0]['items']}")
    proof_str = str(payload_trade['sections'][1]['items'])
    print(f"Proof: {proof_str}")
    print(f"FAQ: {payload_trade['sections'][2]['items']}")
    print()
    
    # Scenario 5: Availability urgency demonstration
    print("SCENARIO 5: Availability Urgency Messages")
    print("-" * 80)
    availability_scenarios = [
        (0, "Fully booked"),
        (1, "Only 1 slot left!"),
        (2, "Only 2 slots left"),
        (3, "Only 3 slots left"),
        (4, None),  # No message for 4+
        (None, None),  # No availability data
    ]
    
    for slots, expected_msg in availability_scenarios:
        slots_str = "none" if slots is None else str(slots)
        client_avail = Client(
            client_id=f"test-spa-avail-{slots_str}",
            client_name="Test Spa",
            trade=Trade.massage,
            business_model=BusinessModel.fixed_price,
            geo_city="chiang mai",
            service_area=["Chiang Mai"],
            primary_phone="+66-80-000-0000",
            lead_email="test@example.com",
            status=ClientStatus.draft,
            service_config_json={
                "default_available_slots": slots,
            } if slots is not None else {},
        )
        
        page_avail = Page(
            page_id=f"test-page-avail-{slots_str}",
            client_id=f"test-spa-avail-{slots_str}",
            template_id="service_lp",
            template_version="1.0",
            page_slug=f"test-avail-{slots_str}",
            page_url=f"/test-avail-{slots_str}",
            page_status=PageStatus.draft,
            content_version=1,
            locale="en",
        )
        
        context_avail = {
            "client": client_avail,
            "page": page_avail,
            "db_path": "acq.db",
        }
        
        payload_avail = adapter.build(f"test-page-avail-{slots_str}", context_avail)
        
        slots_display = "Not set" if slots is None else str(slots)
        subheadline = payload_avail['subheadline']
        has_urgency = "Limited availability" in subheadline or "slots" in subheadline.lower()
        
        print(f"Available Slots: {slots_display}")
        print(f"  Subheadline: {subheadline}")
        print(f"  Has Urgency Message: {has_urgency}")
        print()
    
    print("=" * 80)
    print("DEMONSTRATION COMPLETE")
    print("=" * 80)
    print()
    print("Key Takeaways:")
    print("1. Content adapts based on available client data")
    print("2. Custom content in service_config_json overrides defaults")
    print("3. Availability messages create urgency when slots ≤ 3")
    print("4. License badges and service areas personalize trust signals")
    print("5. Hours information enhances subheadlines")
    print("6. Price anchors set pricing expectations")


if __name__ == "__main__":
    demonstrate_content()
