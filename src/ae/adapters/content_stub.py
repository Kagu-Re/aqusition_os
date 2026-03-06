from __future__ import annotations
from typing import Any, Dict, List, Optional
from .interfaces import ContentAdapter
from ..trade_templates import get_trade_template_or_fallback, format_price_anchor
from ..enums import Trade
from ..page_themes import get_theme


def _extract_hours_short(hours: Optional[str]) -> Optional[str]:
    """Extract short hours format for subheadline.
    
    Examples:
    - "Mon-Fri 9am-6pm" -> "Mon-Fri 9am-6pm"
    - "Monday to Friday: 9:00 AM - 6:00 PM" -> "Mon-Fri 9am-6pm"
    """
    if not hours:
        return None
    # Simple pass-through for now - can be enhanced with parsing logic
    return hours.strip() if hours else None


def _format_availability_message(available_slots: Optional[int]) -> Optional[str]:
    """Format availability message based on slot count.
    
    Returns:
    - None if slots >= 4 or None
    - "Only X slots left" for 1-3 slots
    - "Fully booked" for 0 slots
    """
    if available_slots is None:
        return None
    if available_slots == 0:
        return "Fully booked"
    if available_slots == 1:
        return "Only 1 slot left!"
    if available_slots <= 3:
        return f"Only {available_slots} slots left"
    return None


def _normalize_faq_item(item: Any) -> Dict[str, str]:
    """Convert FAQ item to {"q": "...", "a": "..."}."""
    if isinstance(item, dict) and "q" in item:
        return {"q": str(item.get("q", "")), "a": str(item.get("a", ""))}
    return {"q": str(item), "a": ""}


class StubContentAdapter(ContentAdapter):
    """Deterministic content builder for local simulation."""

    def build(self, page_id: str, context: Dict[str, Any]) -> Dict[str, Any]:
        client = context.get("client")
        page = context.get("page")
        template_id = getattr(page, "template_id", None) if page else None
        
        # Extract page-specific fields
        service_focus = getattr(page, "service_focus", None) if page else None
        
        # Extract all available client fields
        trade = getattr(client, "trade", "trade")
        city = getattr(client, "geo_city", "city")
        client_name = getattr(client, "client_name", None)
        service_area = getattr(client, "service_area", [])
        hours = getattr(client, "hours", None)
        license_badges = getattr(client, "license_badges", [])
        price_anchor = getattr(client, "price_anchor", None)
        geo_country = getattr(client, "geo_country", "TH") or "TH"
        service_config_json = getattr(client, "service_config_json", {}) or {}
        
        # Load trade template for defaults
        try:
            if isinstance(trade, Trade) or (hasattr(trade, 'value') and hasattr(trade, 'name')):
                trade_template = get_trade_template_or_fallback(trade)
            else:
                trade_template = None
        except (AttributeError, TypeError, ValueError):
            trade_template = None
        
        # Fallback price_anchor when client has none (avoids literal {price_anchor} in output)
        if not price_anchor and trade_template:
            price_anchor = format_price_anchor(trade_template, geo_country)

        # Fallback hours when client has none (avoids literal {hours} in FAQ)
        effective_hours = hours or (trade_template.default_hours if trade_template else None)
        
        def _dedupe_price_anchor(text: str) -> str:
            """Fix 'Starting from Starting from X' -> 'Starting from X' when price_anchor already includes it."""
            return text.replace("Starting from Starting from", "Starting from")

        # Helper function to replace placeholders in template patterns
        def replace_placeholders(text: str) -> str:
            result = text
            if "{service_area[0]}" in result and service_area:
                result = result.replace("{service_area[0]}", service_area[0])
            if "{price_anchor}" in result and price_anchor:
                result = result.replace("{price_anchor}", price_anchor)
            if "{hours}" in result and effective_hours:
                result = result.replace("{hours}", effective_hours)
            if "{client_name}" in result and client_name:
                result = result.replace("{client_name}", client_name)
            return result
        
        # Get business model (check enum value)
        business_model = getattr(client, "business_model", None)
        business_model_value = business_model.value if business_model and hasattr(business_model, "value") else None
        
        # Service template: optimized for fixed-price service businesses
        if template_id == "service_lp":
            # Check for custom content in service_config_json
            custom_headline = service_config_json.get("custom_headline")
            custom_subheadline = service_config_json.get("custom_subheadline")
            custom_amenities = service_config_json.get("custom_amenities")
            custom_testimonials = service_config_json.get("custom_testimonials")
            custom_faq = service_config_json.get("custom_faq")
            
            # Build personalized headline based on service_focus
            if custom_headline:
                headline = custom_headline
            elif service_focus == "premium":
                if client_name:
                    trade_str = str(trade).replace("Trade.", "").replace("trade.", "").title()
                    headline = f"{client_name} — Premium {trade_str} Services"
                else:
                    trade_str = str(trade).replace("Trade.", "").replace("trade.", "").title()
                    headline = f"Premium {trade_str} Services in {str(city).title()}"
            elif service_focus == "express":
                if client_name:
                    headline = f"{client_name} — Express Booking"
                else:
                    trade_str = str(trade).replace("Trade.", "").replace("trade.", "").title()
                    headline = f"Express {trade_str} Services in {str(city).title()}"
            elif client_name:
                if service_area:
                    headline = f"{client_name} in {service_area[0]}"
                else:
                    headline = f"{client_name} — Premium {str(trade).title()} Services in {str(city).title()}"
            else:
                headline = f"Premium {str(trade).title()} Services in {str(city).title()}"
            
            # Build personalized subheadline based on service_focus
            if custom_subheadline:
                subheadline = custom_subheadline
            else:
                parts = []
                hours_short = _extract_hours_short(effective_hours)
                if hours_short:
                    parts.append(f"Open {hours_short}.")
                
                # Service focus-specific messaging
                if service_focus == "premium":
                    parts.append("Luxury experience. Premium quality. Exceptional service.")
                elif service_focus == "express":
                    parts.append("Fast booking. Quick service. Same-day availability.")
                else:
                    parts.append("Book your appointment today. Transparent pricing.")
                
                # Check for low availability (from service_config_json or calculated)
                default_available_slots = service_config_json.get("default_available_slots")
                if default_available_slots is not None and default_available_slots <= 3:
                    avail_msg = _format_availability_message(default_available_slots)
                    if avail_msg:
                        parts.append(f"Limited availability - {avail_msg.lower()}.")
                
                if service_focus not in ["premium", "express"]:
                    parts.append("Professional service.")
                
                subheadline = " ".join(parts) if parts else "Book your appointment today. Transparent pricing. Professional service."
            
            # Build personalized amenities based on service_focus
            if custom_amenities:
                amenities = custom_amenities if isinstance(custom_amenities, list) else []
            else:
                amenities = []
                # Try to use template defaults first
                if trade_template and trade_template.default_amenities:
                    # Use template amenities as base
                    amenities = trade_template.default_amenities.copy()
                else:
                    # Fallback to hardcoded logic
                    # Add license badges as trust signals
                    if license_badges:
                        if len(license_badges) >= 2:
                            amenities.append("Licensed & Insured")
                        else:
                            for badge in license_badges[:2]:
                                amenities.append(f"Certified {badge}")
                    # Add service area context
                    if service_area:
                        if len(service_area) == 1:
                            amenities.append(f"Serving {service_area[0]}")
                        else:
                            amenities.append(f"Serving {service_area[0]} and surrounding areas")
                
                # Service focus-specific amenities (add to template defaults)
                if service_focus == "premium":
                    focus_amenities = ["Premium Facilities", "Luxury Experience", "Expert Therapists", "VIP Treatment"]
                elif service_focus == "express":
                    focus_amenities = ["Fast Booking", "Quick Service", "Same-Day Availability", "Convenient Scheduling"]
                else:
                    focus_amenities = ["Professional Staff", "Clean Facilities", "Flexible Booking", "Satisfaction Guaranteed"]
                
                # Add focus-specific amenities (if not already in template defaults)
                for amenity in focus_amenities:
                    if amenity not in amenities and len(amenities) < 6:
                        amenities.append(amenity)
            
            # Build personalized testimonials/proof based on service_focus
            if custom_testimonials:
                testimonials = custom_testimonials if isinstance(custom_testimonials, list) else []
            else:
                testimonials = []
                # Try to use template defaults first
                if trade_template and trade_template.default_testimonials_patterns:
                    # Use template patterns with placeholder replacement
                    for pattern in trade_template.default_testimonials_patterns[:3]:
                        replaced = replace_placeholders(pattern)
                        if replaced not in testimonials:
                            testimonials.append(replaced)
                else:
                    # Fallback to hardcoded logic
                    # Add price anchor if available (don't add "Starting from" if already in price_anchor)
                    if price_anchor:
                        if price_anchor.lower().startswith("starting from"):
                            testimonials.append(price_anchor)
                        else:
                            testimonials.append(f"Starting from {price_anchor}")
                    # Add service area specificity
                    if service_area:
                        testimonials.append(f"Serving {service_area[0]} and surrounding areas")
                
                # Service focus-specific proof points (add to template defaults)
                if service_focus == "premium":
                    focus_proof = ["5★ luxury rating", "Premium clientele", "Exclusive packages available"]
                elif service_focus == "express":
                    focus_proof = ["Fast booking process", "Quick service turnaround", "Same-day appointments"]
                else:
                    focus_proof = ["4.9★ average rating", "500+ happy customers", "Same-day booking available"]
                
                def _already_covered(proof: str, existing: List[str]) -> bool:
                    """True if proof is redundant with existing items (avoids duplicate ratings)."""
                    for ex in existing:
                        if proof in ex or ex in proof:
                            return True
                        # Skip adding "4.9★ average rating" if we already have similar
                        if "★" in proof and "★" in ex and ("rating" in proof or "rating" in ex):
                            return True
                    return False

                # Add focus-specific proof points (if not already in template defaults)
                for proof in focus_proof:
                    if proof not in testimonials and not _already_covered(proof, testimonials) and len(testimonials) < 5:
                        testimonials.append(proof)
            
            # Build personalized FAQ (Q&A pairs for accordion)
            if custom_faq:
                faq = []
                for item in (custom_faq if isinstance(custom_faq, list) else []):
                    normalized = _normalize_faq_item(item)
                    normalized["q"] = replace_placeholders(normalized["q"])
                    normalized["a"] = replace_placeholders(normalized["a"]) if normalized["a"] else ""
                    faq.append(normalized)
            else:
                faq = []
                # Prefer default_faq_qa when present
                if trade_template and getattr(trade_template, "default_faq_qa", None):
                    for pair in trade_template.default_faq_qa:
                        if isinstance(pair, dict) and "q" in pair:
                            faq.append({
                                "q": replace_placeholders(str(pair.get("q", ""))),
                                "a": replace_placeholders(str(pair.get("a", ""))),
                            })
                elif trade_template and trade_template.default_faq_patterns:
                    # Fallback: questions only (legacy)
                    for pattern in trade_template.default_faq_patterns:
                        faq.append({"q": replace_placeholders(pattern), "a": ""})
                else:
                    if effective_hours:
                        faq.append({"q": "What are your operating hours?", "a": f"We're open {effective_hours}."})
                    if service_area:
                        faq.append({"q": "What areas do you serve?", "a": f"We serve {service_area[0]} and surrounding areas." if service_area else ""})

            # Fix price anchor duplication (e.g. "Starting from Starting from ฿800" -> "Starting from ฿800")
            testimonials = [_dedupe_price_anchor(t) if isinstance(t, str) else t for t in testimonials]
            
            # Build personalized CTAs based on service_focus
            # Use custom CTAs if provided, otherwise use template defaults, then service_focus-specific defaults
            custom_cta_primary = service_config_json.get("custom_cta_primary")
            custom_cta_secondary = service_config_json.get("custom_cta_secondary")
            
            if service_focus == "premium":
                cta_primary = custom_cta_primary or (trade_template.default_cta_primary if trade_template else "View Premium Packages")
                cta_secondary = custom_cta_secondary or (trade_template.default_cta_secondary if trade_template else "Book Premium Service")
                # Override with service_focus-specific if template doesn't have premium-specific defaults
                if not custom_cta_primary and (not trade_template or "Premium" not in cta_primary):
                    cta_primary = "View Premium Packages"
                if not custom_cta_secondary and (not trade_template or "Premium" not in cta_secondary):
                    cta_secondary = "Book Premium Service"
            elif service_focus == "express":
                cta_primary = custom_cta_primary or (trade_template.default_cta_primary if trade_template else "Book Now")
                cta_secondary = custom_cta_secondary or (trade_template.default_cta_secondary if trade_template else "Quick Booking")
                # Override with service_focus-specific defaults
                if not custom_cta_primary:
                    cta_primary = "Book Now"
                if not custom_cta_secondary:
                    cta_secondary = "Quick Booking"
            else:
                cta_primary = custom_cta_primary or (trade_template.default_cta_primary if trade_template else "View Packages")
                cta_secondary = custom_cta_secondary or (trade_template.default_cta_secondary if trade_template else "Book Now")
            
            # Extract reviews (GBP placeholder); validate and limit to 5
            reviews_raw = service_config_json.get("reviews") or []
            reviews = [r for r in reviews_raw if isinstance(r, dict) and r.get("quote")][:5]

            sections = [
                {"type": "amenities", "items": amenities},
                {"type": "testimonials", "items": testimonials},
            ]
            if reviews:
                sections.append({"type": "reviews", "items": reviews})
            sections.append({"type": "faq", "items": faq})

            payload = {
                "page_id": page_id,
                "headline": headline,
                "subheadline": subheadline,
                "cta_primary": cta_primary,
                "cta_secondary": cta_secondary,
                "sections": sections,
                "template_type": "service",
            }
            
            # Always show packages for service template
            if business_model_value == "fixed_price":
                payload["business_model"] = "fixed_price"
                payload["client_id"] = getattr(client, "client_id", None)
                payload["show_packages"] = True
                # Include availability context if available
                default_available_slots = service_config_json.get("default_available_slots")
                if default_available_slots is not None:
                    payload["default_available_slots"] = default_available_slots
        else:
            # Trade template: quote-based businesses
            # Check for custom content
            custom_headline = service_config_json.get("custom_headline")
            custom_subheadline = service_config_json.get("custom_subheadline")
            
            # Build personalized headline
            if custom_headline:
                headline = custom_headline
            elif client_name:
                headline = f"{client_name} — {str(trade).title()} in {str(city).title()}"
            else:
                headline = f"{str(trade).title()} in {str(city).title()} — Fast, Clean, Verified"
            
            # Build personalized subheadline
            if custom_subheadline:
                subheadline = custom_subheadline
            else:
                parts = []
                hours_short = _extract_hours_short(effective_hours)
                if hours_short:
                    parts.append(f"Open {hours_short}.")
                parts.append("Same-week availability. Transparent pricing. No spam calls.")
                subheadline = " ".join(parts)
            
            # Build personalized benefits
            benefits = []
            if license_badges:
                benefits.extend(license_badges[:4])
            generic_benefits = ["Licensed", "Insured", "On-time", "Warranty"]
            for gen in generic_benefits:
                if gen not in benefits and len(benefits) < 4:
                    benefits.append(gen)
            
            # Build personalized proof
            proof = []
            if price_anchor:
                if price_anchor.lower().startswith("starting from") or price_anchor.lower().startswith("from"):
                    proof.append(price_anchor)
                else:
                    proof.append(f"Starting from {price_anchor}")
            if service_area:
                proof.append(f"Serving {service_area[0]}")
            generic_proof = ["4.8★ average rating", "300+ jobs completed"]
            for gen in generic_proof:
                if gen not in proof and len(proof) < 2:
                    proof.append(gen)
            
            # Build personalized FAQ (Q&A pairs for accordion)
            custom_faq = service_config_json.get("custom_faq")
            if custom_faq:
                faq = []
                for item in (custom_faq if isinstance(custom_faq, list) else []):
                    normalized = _normalize_faq_item(item)
                    normalized["q"] = replace_placeholders(normalized["q"])
                    normalized["a"] = replace_placeholders(normalized["a"]) if normalized["a"] else ""
                    faq.append(normalized)
            else:
                faq = []
                if trade_template and getattr(trade_template, "default_faq_qa", None):
                    for pair in trade_template.default_faq_qa:
                        if isinstance(pair, dict) and "q" in pair:
                            faq.append({
                                "q": replace_placeholders(str(pair.get("q", ""))),
                                "a": replace_placeholders(str(pair.get("a", ""))),
                            })
                elif trade_template and trade_template.default_faq_patterns:
                    for pattern in trade_template.default_faq_patterns:
                        faq.append({"q": replace_placeholders(pattern), "a": ""})
                else:
                    if effective_hours:
                        faq.append({"q": "What are your operating hours?", "a": f"We're open {effective_hours}."})
                    if service_area:
                        faq.append({"q": "What areas do you serve?", "a": f"We serve {service_area[0]} and surrounding areas." if service_area else ""})

            # Fix price anchor duplication
            proof = [_dedupe_price_anchor(p) if isinstance(p, str) else p for p in proof]
            
            # Extract reviews (GBP placeholder); validate and limit to 5
            reviews_raw = service_config_json.get("reviews") or []
            reviews = [r for r in reviews_raw if isinstance(r, dict) and r.get("quote")][:5]

            sections = [
                {"type": "benefits", "items": benefits},
                {"type": "proof", "items": proof},
            ]
            if reviews:
                sections.append({"type": "reviews", "items": reviews})
            sections.append({"type": "faq", "items": faq})

            payload = {
                "page_id": page_id,
                "headline": headline,
                "subheadline": subheadline,
                "cta_primary": service_config_json.get("custom_cta_primary") or "Book now",
                "cta_secondary": service_config_json.get("custom_cta_secondary") or "Get a quote",
                "sections": sections,
                "template_type": "trade",
            }
            
            # Add service package metadata for fixed-price clients (even on trade template)
            if business_model_value == "fixed_price":
                payload["business_model"] = "fixed_price"
                payload["client_id"] = getattr(client, "client_id", None)
                payload["show_packages"] = True
                # Include availability context if available
                default_available_slots = service_config_json.get("default_available_slots")
                if default_available_slots is not None:
                    payload["default_available_slots"] = default_available_slots

        # Media: client override or trade template defaults
        hero_url = service_config_json.get("custom_hero_image_url") or (
            trade_template.default_hero_image_url if trade_template else None
        )
        gallery = service_config_json.get("custom_gallery_images") or (
            (trade_template.default_gallery_images or []) if trade_template else []
        )
        payload["hero_image_url"] = hero_url if hero_url else None
        payload["gallery_images"] = gallery if isinstance(gallery, list) else []

        # Theme: client override via service_config_json
        template_style = service_config_json.get("template_style")
        payload["template_style"] = get_theme(template_style)

        return payload
