from __future__ import annotations
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from .interfaces import PublisherAdapter, PublishResult
from ..page_themes import get_theme

def _escape(s: Optional[str]) -> str:
    if s is None:
        return ""
    return (
        str(s)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#39;")
    )

def _li(items: List[str]) -> str:
    return "\n".join(
        [
            f'<li class="lp-li"><span class="lp-check">✓</span><span>{_escape(x)}</span></li>'
            for x in items
        ]
    )


def _faq_accordion(items: List[Any]) -> str:
    """Render FAQ items as <details>/<summary> accordion. Supports {"q","a"} dicts or legacy str."""
    parts = []
    for item in items:
        if isinstance(item, dict) and "q" in item:
            q = _escape(item.get("q", ""))
            a = _escape(item.get("a", ""))
        else:
            q = _escape(item) if item is not None else ""
            a = ""
        if not q:
            continue
        answer_html = f'<p class="lp-faq-answer pt-2">{a}</p>' if a else ""
        parts.append(f'<details class="lp-faq-item"><summary class="lp-faq-summary">{q}</summary>{answer_html}</details>')
    return "\n      ".join(parts)


def _review_aggregate(items: List[dict]) -> str:
    """Compute aggregate rating summary for reviews section header."""
    if not items:
        return ""
    ratings = [
        r.get("rating", 5) for r in items
        if isinstance(r.get("rating"), (int, float)) and 1 <= r.get("rating", 5) <= 5
    ]
    avg = sum(ratings) / len(ratings) if ratings else 5.0
    avg_rounded = round(avg, 1)
    count = len(items)
    source = "Google" if any(r.get("source") == "google" for r in items) else "customer"
    return f"{avg_rounded}★ from {count} {source} review{'s' if count != 1 else ''}"


def _review_card(item: dict) -> str:
    """Render a single review as a blockquote card."""
    quote = _escape(item.get("quote", ""))
    author = _escape(item.get("author_name", ""))
    rating = item.get("rating")
    rating_val = rating if isinstance(rating, int) and 1 <= rating <= 5 else 5
    stars = "★" * rating_val + "☆" * (5 - rating_val)
    source = item.get("source")
    source_label = "Reviewed on Google" if source == "google" else (f"Reviewed on {_escape(str(source))}" if source else "")
    source_html = f'<span class="lp-review-source">{source_label}</span>' if source_label else ""
    return f'''<blockquote class="lp-review-card">
        <p class="lp-review-quote">{quote}</p>
        <div class="lp-review-meta">
          <span class="lp-review-stars">{stars}</span>
          <cite class="lp-review-author">{author}</cite>
          {source_html}
        </div>
      </blockquote>'''


class TailwindStaticSitePublisher(PublisherAdapter):
    """Static site publisher (owned CSS).

    v0.3.1: ships a local CSS asset into the exported site (no CDN).
    - CSS source-of-truth is `src/ae/assets/tailwind_compiled.css`.
    - You can regenerate it via `npm run build:css` (requires Node).
    """

    def __init__(self, out_dir: str = "exports/static_site", css_asset_rel: str = "assets/styles.css"):
        self.out_dir = Path(out_dir)
        self.css_asset_rel = css_asset_rel
        self._repo_css = Path(__file__).resolve().parents[1] / "assets" / "tailwind_compiled.css"

    def publish(self, page_id: str, payload: Dict[str, Any], context: Dict[str, Any]) -> PublishResult:
        try:
            self.out_dir.mkdir(parents=True, exist_ok=True)
            page_dir = self.out_dir / page_id
            assets_dir = page_dir / "assets"
            assets_dir.mkdir(parents=True, exist_ok=True)

            # Copy CSS asset into site export
            css_out = assets_dir / "styles.css"
            if self._repo_css.exists():
                css_out.write_text(self._repo_css.read_text(encoding="utf-8"), encoding="utf-8")
            else:
                # Create empty CSS file if source doesn't exist
                css_out.write_text("/* CSS asset placeholder */", encoding="utf-8")

            template_style = get_theme(payload.get("template_style"))
            headline = _escape(payload.get("headline"))
            sub = _escape(payload.get("subheadline"))
            cta1 = _escape(payload.get("cta_primary") or "View Packages")
            hero_image_url = payload.get("hero_image_url")
            gallery_images = payload.get("gallery_images") or []
            if not isinstance(gallery_images, list):
                gallery_images = []

            hero_block = ""
            if hero_image_url:
                hero_src = _escape(hero_image_url)
                hero_block = f'<div class="lp-hero-image rounded-xl overflow-hidden shadow-lg"><img src="{hero_src}" alt="Hero" class="w-full h-56 md:h-80 object-cover" loading="eager" /></div>'

            gallery_block = ""
            if gallery_images:
                gallery_items = "\n            ".join(
                    f'<div><img src="{_escape(url)}" alt="Gallery" class="w-full h-32 object-cover rounded-lg" loading="lazy" /></div>'
                    for url in gallery_images[:6]
                )
                gallery_block = f'''
    <!-- Gallery Section -->
    <section class="lp-section lp-section-alt">
      <div class="lp-container py-10 md:py-14">
        <div class="lp-card lp-card-elevated">
          <h2 class="lp-heading-2 mb-6">Gallery</h2>
          <div class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
            {gallery_items}
          </div>
        </div>
      </div>
    </section>'''

            sections = payload.get("sections") or []
            template_type = payload.get("template_type", "trade")
            
            # Support both trade and service templates
            if template_type == "service":
                # Service template sections: amenities, testimonials, faq
                section1 = next((s for s in sections if s.get("type") == "amenities"), None) or {}
                section2 = next((s for s in sections if s.get("type") == "testimonials"), None) or {}
                section1_title = "Amenities"
                section2_title = "Why Choose Us"
            else:
                # Trade template sections: benefits, proof, faq
                section1 = next((s for s in sections if s.get("type") == "benefits"), None) or {}
                section2 = next((s for s in sections if s.get("type") == "proof"), None) or {}
                section1_title = "Benefits"
                section2_title = "Proof"
            
            faq_section = next((s for s in sections if s.get("type") == "faq"), None) or {}
            faq_items = faq_section.get("items") or []

            reviews_section = next((s for s in sections if s.get("type") == "reviews"), None) or {}
            reviews_items = reviews_section.get("items") or []
            
            # Get API base URL from context or use default
            # For local dev server, routes are at root level (/v1/*), not /api/v1/*
            # So we use http://localhost:8000 (without /api) for local dev
            api_base = os.getenv("AE_PUBLIC_API_URL", "http://localhost:8000")
            # Remove /api suffix if present for local dev server compatibility
            if api_base.endswith("/api"):
                api_base = api_base[:-4]
            db_param = context.get("db_path", "acq.db")
            
            # Get client_id from context
            client = context.get("client")
            client_id = client.client_id if client else None
            
            # Get currency from client location (default to THB for Thailand)
            currency_symbol = "฿"  # Thai Baht symbol
            currency_code = "THB"
            if client:
                geo_country = getattr(client, "geo_country", "").upper()
                if geo_country == "AU":
                    currency_symbol = "A$"
                    currency_code = "AUD"
                elif geo_country == "US":
                    currency_symbol = "$"
                    currency_code = "USD"
                elif geo_country in ["TH", "THA"]:
                    currency_symbol = "฿"
                    currency_code = "THB"
            
            # Escape values for JavaScript (use JSON encoding for safety)
            import json
            
            # Format page_id for use in HTML (for CSS path)
            page_id_html = page_id
            page_id_js = json.dumps(page_id)
            api_base_js = json.dumps(api_base)
            db_param_js = json.dumps(str(db_param))
            client_id_js = json.dumps(client_id) if client_id else "null"
            currency_symbol_js = json.dumps(currency_symbol)
            currency_code_js = json.dumps(currency_code)
            
            # Package-related variables (for fixed-price clients)
            show_packages = payload.get("show_packages", False)
            client_id_for_packages = payload.get("client_id")
            show_packages_js = "true" if show_packages else "false"
            has_packages_section = bool(show_packages and client_id_for_packages)
            hero_cta_href = "#packages-section" if has_packages_section else "#contact"
            hero_cta_text = cta1 if has_packages_section else "Contact Us"
            client_id_for_packages_js = json.dumps(client_id_for_packages) if client_id_for_packages else "null"
            
            # Tracking JavaScript (embedded before </body>)
            tracking_js = f"""  <script>
    // Acquisition Engine Tracking
    (function() {{
      const PAGE_ID = {page_id_js};
      const API_BASE = {api_base_js};
      const DB_PARAM = {db_param_js};
      
      // Extract UTM parameters from URL
      function getUTMParams() {{
        const params = new URLSearchParams(window.location.search);
        return {{
          utm_source: params.get('utm_source') || null,
          utm_medium: params.get('utm_medium') || null,
          utm_campaign: params.get('utm_campaign') || null,
          utm_content: params.get('utm_content') || null,
          utm_term: params.get('utm_term') || null
        }};
      }}
      
      // Send event to API
      function trackEvent(eventName, params) {{
        const payload = {{
          page_id: PAGE_ID,
          event_name: eventName,
          params: {{
            ...getUTMParams(),
            ...(params || {{}}),
            timestamp: new Date().toISOString(),
            url: window.location.href,
            referrer: document.referrer || null
          }}
        }};
        
        // Use fetch with keepalive for reliability (works better with CORS than sendBeacon)
        fetch(API_BASE + '/v1/event?db=' + encodeURIComponent(DB_PARAM), {{
          method: 'POST',
          headers: {{
            'Content-Type': 'application/json'
          }},
          body: JSON.stringify(payload),
          keepalive: true,
          mode: 'cors'
        }}).catch(function(err) {{
          // Silently fail - don't break page if tracking fails
          console.debug('Event tracking failed:', err);
        }});
      }}
      
      // Chat redirect functionality
      let chatUrl = null;
      let chatChannel = null;
      const CLIENT_ID = {client_id_js};
      
      // Fetch chat channel info on page load
      if (CLIENT_ID) {{
        fetch(API_BASE + '/v1/chat/channel?client_id=' + encodeURIComponent(CLIENT_ID) + '&db=' + encodeURIComponent(DB_PARAM))
          .then(function(response) {{
            if (response.ok) {{
              return response.json();
            }}
            return null;
          }})
          .then(function(data) {{
            if (data) {{
              chatUrl = data.chat_url;
              chatChannel = data;  // Store full channel info for deep links
            }}
          }})
          .catch(function(err) {{
            console.debug('Failed to fetch chat channel:', err);
          }});
      }}
      
      // Track CTA clicks: View Packages scrolls to packages, Contact Us redirects to chat
      document.addEventListener('click', function(e) {{
        const target = e.target.closest('a[href="#packages-section"], a[href="#contact"]');
        if (target) {{
          if (target.href.includes('#packages-section')) {{
            // View Packages: anchor scroll (native behavior), track only
            trackEvent('view_packages_click');
          }} else if (target.href.includes('#contact')) {{
            // Contact Us: redirect to chat with intent_contact for Telegram
            trackEvent('contact_click');
            if (chatUrl) {{
              e.preventDefault();
              let contactUrl = chatUrl;
              if (chatChannel && chatChannel.provider === 'telegram') {{
                contactUrl = chatUrl + (chatUrl.includes('?') ? '&' : '?') + 'start=intent_contact';
              }}
              setTimeout(function() {{
                window.location.href = contactUrl;
              }}, 100);
            }}
          }}
        }}
      }});
      
      // Track form submissions (if forms exist)
      document.addEventListener('submit', function(e) {{
        trackEvent('quote_submit');
      }});
      
      // Track thank you page view (if on thank you page)
      if (window.location.hash === '#thank-you' || window.location.pathname.includes('thank-you')) {{
        trackEvent('thank_you_view');
      }}
      
      // Service Packages functionality (for fixed-price clients)
      const SHOW_PACKAGES = {show_packages_js};
      const CLIENT_ID_FOR_PACKAGES = {client_id_for_packages_js};
      const PAGE_ID_FOR_PACKAGES = {page_id_js};
      const CURRENCY_SYMBOL = {currency_symbol_js};
      
      if (SHOW_PACKAGES && CLIENT_ID_FOR_PACKAGES) {{
        // Fetch service packages (include page_id to filter by service_focus)
        const packagesUrl = API_BASE + '/v1/service-packages?client_id=' + encodeURIComponent(CLIENT_ID_FOR_PACKAGES) + '&active=true&db=' + encodeURIComponent(DB_PARAM) + (PAGE_ID_FOR_PACKAGES ? '&page_id=' + encodeURIComponent(PAGE_ID_FOR_PACKAGES) : '');
        // #region agent log
        fetch('http://127.0.0.1:7246/ingest/08671b8a-c159-4401-922a-06bd2d4229ab',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{location:'publisher_tailwind_static.py:271',message:'packages fetch started',data:{{url:packagesUrl}},timestamp:Date.now(),runId:'run1',hypothesisId:'F'}})}}).catch(()=>{{}});
        // #endregion
        fetch(packagesUrl)
          .then(function(response) {{
            if (!response.ok) return null;
            return response.json();
          }})
          .then(function(data) {{
            if (!data || !data.items || data.items.length === 0) {{
              const packagesSection = document.getElementById('packages-section');
              if (packagesSection) packagesSection.style.display = 'none';
              return;
            }}
            
            const container = document.getElementById('packages-container');
            if (!container) return;
            
            // #region agent log
            const existingButtonCount = container.querySelectorAll('button').length;
            fetch('http://127.0.0.1:7246/ingest/08671b8a-c159-4401-922a-06bd2d4229ab',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{location:'publisher_tailwind_static.py:287',message:'packages rendering started',data:{{packageCount:data.items.length,existingButtons:existingButtonCount}},timestamp:Date.now(),runId:'run1',hypothesisId:'F'}})}}).catch(()=>{{}});
            // #endregion
            
            container.innerHTML = '';
            
            data.items.forEach(function(pkg, index) {{
              const duration = pkg.duration_min || 60;
              const hours = Math.floor(duration / 60);
              const minutes = duration % 60;
              const durationText = hours > 0 
                ? (minutes > 0 ? hours + 'h ' + minutes + 'm' : hours + 'h')
                : minutes + 'm';
              
              const addons = (pkg.addons || []).length > 0
                ? '<ul class="lp-ul lp-text-muted text-sm mt-2"><li class="lp-li">' + pkg.addons.join('</li><li class="lp-li">') + '</li></ul>'
                : '';
              
              // Availability display logic
              const availableSlots = pkg.available_slots !== undefined ? pkg.available_slots : null;
              let availabilityBadge = '';
              let availabilityClass = '';
              let isDisabled = false;
              let buttonText = 'Select Package';
              
              if (availableSlots !== null) {{
                if (availableSlots === 0) {{
                  availabilityBadge = '<div class="text-xs font-semibold text-red-400 mb-2">Fully booked</div>';
                  availabilityClass = 'opacity-60';
                  isDisabled = true;
                  buttonText = 'Fully Booked';
                }} else if (availableSlots === 1) {{
                  availabilityBadge = '<div class="text-xs font-semibold text-red-400 mb-2">Only 1 slot left!</div>';
                  buttonText = 'Book Now - Only 1 Left';
                }} else if (availableSlots <= 3) {{
                  availabilityBadge = '<div class="text-xs font-semibold text-orange-400 mb-2">Only ' + availableSlots + ' slots left</div>';
                  buttonText = 'Book Now - Only ' + availableSlots + ' Left';
                }} else {{
                  availabilityBadge = '<div class="text-xs font-semibold text-green-400 mb-2">Available</div>';
                }}
              }}
              
              const card = document.createElement('div');
              card.className = 'lp-feature-block p-6 cursor-pointer ' + availabilityClass;
              const packageNameEscaped = (pkg.name || '').replace(/'/g, "\\'").replace(/"/g, '&quot;');
              const packageIdEscaped = (pkg.package_id || '').replace(/'/g, "\\'");
              const buttonDisabledAttr = isDisabled ? ' disabled' : '';
              card.innerHTML = `
                <h3 class="lp-heading-3 mb-2">${{packageNameEscaped}}</h3>
                <div class="text-2xl font-bold mb-2" style="color: var(--ae-text)">${{CURRENCY_SYMBOL}}${{pkg.price.toFixed(0)}}</div>
                <div class="lp-text-muted text-sm mb-3">Duration: ${{durationText}}</div>
                ${{availabilityBadge}}
                ${{addons}}
                <button 
                  class="lp-btn lp-btn-primary w-full mt-4" 
                  data-package-id="${{packageIdEscaped}}"
                  data-package-name="${{packageNameEscaped}}"
                  data-package-price="${{pkg.price}}"
                  ${{buttonDisabledAttr}}
                >
                  ${{buttonText}}
                </button>
              `;
              // Add click handler using addEventListener (safer than onclick)
              const button = card.querySelector('button');
              if (button && !isDisabled) {{
                // #region agent log
                const listenerId = 'pkg_' + pkg.package_id + '_' + Date.now();
                fetch('http://127.0.0.1:7246/ingest/08671b8a-c159-4401-922a-06bd2d4229ab',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{location:'publisher_tailwind_static.py:347',message:'adding button listener',data:{{packageId:pkg.package_id,packageName:pkg.name,listenerId:listenerId,index:index}},timestamp:Date.now(),runId:'run1',hypothesisId:'F'}})}}).catch(()=>{{}});
                // #endregion
                button.addEventListener('click', function(e) {{
                  // #region agent log
                  fetch('http://127.0.0.1:7246/ingest/08671b8a-c159-4401-922a-06bd2d4229ab',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{location:'publisher_tailwind_static.py:349',message:'button click event fired',data:{{packageId:button.getAttribute('data-package-id'),listenerId:listenerId,eventTarget:e.target.tagName,currentTarget:e.currentTarget.tagName}},timestamp:Date.now(),runId:'run1',hypothesisId:'F'}})}}).catch(()=>{{}});
                  // #endregion
                  e.stopPropagation(); // Prevent event bubbling
                  selectPackage(
                    button.getAttribute('data-package-id'),
                    button.getAttribute('data-package-name'),
                    parseFloat(button.getAttribute('data-package-price'))
                  );
                }}, true); // Use capture phase to catch early
              }}
              container.appendChild(card);
            }});
          }})
          .catch(function(err) {{
            console.debug('Failed to load packages:', err);
            const packagesSection = document.getElementById('packages-section');
            if (packagesSection) packagesSection.style.display = 'none';
          }});
        
        // Package selection handler
        let isRedirecting = false;  // Prevent multiple redirects
        let lastRedirectTime = 0;  // Track last redirect time
        let lastRedirectedPackageId = null;  // Track which package was redirected
        window.selectPackage = function(packageId, packageName, price) {{
          // #region agent log
          const callStack = new Error().stack;
          fetch('http://127.0.0.1:7246/ingest/08671b8a-c159-4401-922a-06bd2d4229ab',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{location:'publisher_tailwind_static.py:369',message:'selectPackage called',data:{{packageId:packageId,packageName:packageName,price:price,isRedirecting:isRedirecting,timeSinceLast:Date.now()-lastRedirectTime,lastRedirectedPackage:lastRedirectedPackageId,callStack:callStack.substring(0,200)}},timestamp:Date.now(),runId:'run1',hypothesisId:'F'}})}}).catch(()=>{{}});
          // #endregion
          // Prevent multiple rapid calls (within 5 seconds) or if same package was already redirected
          const now = Date.now();
          if (isRedirecting || (now - lastRedirectTime < 5000) || lastRedirectedPackageId === packageId) {{
            // #region agent log
            fetch('http://127.0.0.1:7246/ingest/08671b8a-c159-4401-922a-06bd2d4229ab',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{location:'publisher_tailwind_static.py:373',message:'selectPackage blocked',data:{{packageId:packageId,isRedirecting:isRedirecting,timeSinceLast:now-lastRedirectTime,lastRedirectedPackage:lastRedirectedPackageId}},timestamp:Date.now(),runId:'run1',hypothesisId:'F'}})}}).catch(()=>{{}});
            // #endregion
            console.debug('Package selection ignored - redirect already in progress, too soon, or same package already redirected');
            return;
          }}
          isRedirecting = true;
          lastRedirectTime = now;
          lastRedirectedPackageId = packageId;
          
          // Track package selection
          trackEvent('package_selected', {{
            package_id: packageId,
            package_name: packageName,
            package_price: price
          }});
          
          // Create lead with package selection
          const utmParams = getUTMParams();
          const leadPayload = {{
            source: 'landing_page',
            page_id: PAGE_ID,
            client_id: CLIENT_ID_FOR_PACKAGES,
            message: 'Package selected: ' + packageName,
            utm: utmParams,
            meta: {{
              package_id: packageId,
              package_name: packageName,
              package_price: price
            }}
          }};
          
          // Send lead (non-blocking)
          fetch(API_BASE + '/lead?db=' + encodeURIComponent(DB_PARAM), {{
            method: 'POST',
            headers: {{ 'Content-Type': 'application/json' }},
            body: JSON.stringify(leadPayload),
            keepalive: true,
            mode: 'cors'
          }}).catch(function(err) {{
            console.debug('Lead creation failed:', err);
          }});
          
          // Redirect to chat or show booking form
          if (chatChannel && chatChannel.provider === 'telegram') {{
            // Telegram deep link: t.me/bot?start=package_pkg123
            const botUsername = chatChannel.handle.replace('@', '');
            const deepLink = 'https://t.me/' + botUsername + '?start=package_' + encodeURIComponent(packageId);
            // #region agent log
            fetch('http://127.0.0.1:7246/ingest/08671b8a-c159-4401-922a-06bd2d4229ab',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{location:'publisher_tailwind_static.py:417',message:'redirecting to Telegram deep link',data:{{packageId:packageId,deepLink:deepLink}},timestamp:Date.now(),runId:'run1',hypothesisId:'F'}})}}).catch(()=>{{}});
            // #endregion
            // Use window.open with _self to replace current page and prevent history issues
            // Also add a flag to prevent multiple redirects even if function is called again
            if (!window._telegramRedirectInProgress) {{
              window._telegramRedirectInProgress = true;
              // Use replace instead of assign to prevent back button from triggering old deep links
              setTimeout(function() {{
                window.location.replace(deepLink);
              }}, 200);
            }}
          }} else if (chatUrl) {{
            setTimeout(function() {{
              window.location.href = chatUrl + '?package=' + encodeURIComponent(packageId);
            }}, 200);
          }} else {{
            // Fallback: show booking form or redirect to phone
            alert('Package selected: ' + packageName + ' (' + CURRENCY_SYMBOL + price.toFixed(0) + ')\\n\\nRedirecting to booking...');
            isRedirecting = false;  // Reset flag if no redirect happens
          }}
        }};
      }}
    }})();
  </script>"""

            # Footer and contact: professional, client-facing
            client = context.get("client")
            client_name = (_escape(client.client_name) if client and getattr(client, "client_name", None) else "") or headline or "Landing Page"
            year = datetime.now().year

            # Contact strip data (hero)
            contact_phone = getattr(client, "primary_phone", None) or "" if client else ""
            contact_hours = getattr(client, "hours", None) or ""
            if not contact_hours and client:
                from ..trade_templates import get_trade_template_or_fallback
                tpl = get_trade_template_or_fallback(getattr(client, "trade", None)) if client else None
                contact_hours = tpl.default_hours if tpl else ""
            contact_area = (client.service_area[0] if client and getattr(client, "service_area", None) and len(client.service_area) > 0 else "") or ""
            has_contact = bool(contact_phone or contact_hours or contact_area)
            contact_block = ""
            if has_contact:
                parts = []
                if contact_phone:
                    tel = contact_phone.replace(" ", "").replace("-", "")
                    parts.append(f'<a href="tel:{_escape(tel)}" class="lp-contact-link">{_escape(contact_phone)}</a>')
                if contact_hours:
                    parts.append(f'<span class="lp-contact-item">Open {_escape(contact_hours)}</span>')
                if contact_area:
                    parts.append(f'<span class="lp-contact-item">{_escape(contact_area)} & surrounds</span>')
                contact_block = f'<div class="lp-hero-contact" aria-label="Contact info"><div class="lp-hero-contact-inner">{"".join(p for p in parts)}</div></div>'

            html = f"""<!doctype html>
<html lang="en" data-theme="{template_style}">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{headline or "Landing Page"}</title>
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
  <link href="https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,400;0,9..40,500;0,9..40,600;0,9..40,700;1,9..40,400&display=swap" rel="stylesheet" />
  <link rel="stylesheet" href="/pages/{page_id}/assets/styles.css" />
</head>
<body>
  <main class="lp-page">
    <!-- Hero Section -->
    <section class="lp-hero-section">
      <div class="lp-container py-12 md:py-16">
        <div class="lp-hero-card">
          <div class="flex flex-col gap-8">
            {hero_block}
            <header class="flex flex-col gap-4 text-center md:text-left">
              <h1 class="lp-heading-1">{headline}</h1>
              <p class="lp-text-muted max-w-2xl mx-auto md:mx-0 text-lg">{sub}</p>
              {contact_block}
            </header>

            <div class="flex flex-wrap gap-4 justify-center md:justify-start">
              <a href="{hero_cta_href}" class="lp-btn lp-btn-primary lp-btn-lg">{hero_cta_text}</a>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- Features Section -->
    <section class="lp-section lp-section-alt">
      <div class="lp-container py-10 md:py-14">
        <div class="lp-card lp-card-elevated">
          <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div class="lp-feature-block">
              <h2 class="lp-heading-2 mb-4">{section1_title}</h2>
              <ul class="lp-ul space-y-2">
                {_li(section1.get("items") or [])}
              </ul>
            </div>
            <div class="lp-feature-block">
              <h2 class="lp-heading-2 mb-4">{section2_title}</h2>
              <ul class="lp-ul space-y-2">
                {_li(section2.get("items") or [])}
              </ul>
            </div>
          </div>
        </div>
      </div>
    </section>
{f'''    <!-- What Customers Say -->
    <section class="lp-section">
      <div class="lp-container py-10 md:py-14">
        <div class="lp-card lp-card-elevated">
          <h2 class="lp-heading-2 mb-2">What Customers Say</h2>
          <p class="lp-review-aggregate mb-6">{_review_aggregate(reviews_items)}</p>
          <div class="lp-reviews-scroll" role="region" aria-label="Customer reviews">
{chr(10).join("            <div class=\"lp-review-slide\">" + _review_card(r) + "</div>" for r in reviews_items)}
          </div>
        </div>
      </div>
    </section>''' if reviews_items else ''}
{gallery_block}

    <!-- Packages Section -->
    {f'''<section id="packages-section" class="lp-section">
      <div class="lp-container py-10 md:py-14">
        <div class="lp-card lp-card-elevated">
          <div class="flex flex-col gap-6">
            <header class="text-center md:text-left">
              <h2 class="lp-heading-2 mb-2">Choose Your Service Package</h2>
              <p class="lp-text-muted">Select the perfect package for your needs</p>
            </header>
            <div id="packages-container" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              <div class="text-center p-8 lp-text-muted">
                <p>Loading packages...</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>''' if show_packages and client_id_for_packages else ''}

{f'''    <!-- FAQ Section -->
    <section class="lp-section lp-section-alt">
      <div class="lp-container py-10 md:py-14">
        <div class="lp-card lp-card-elevated">
          <h2 class="lp-heading-2 mb-6">FAQ</h2>
          <div class="space-y-2">
      {_faq_accordion(faq_items)}
          </div>
        </div>
      </div>
    </section>
''' if faq_items else ''}

    <!-- Footer Section -->
    <footer id="contact" class="lp-footer">
      <div class="lp-container py-8">
        <div class="text-center">
          <p class="lp-footer-text">
            © {year} {client_name}. All rights reserved.
          </p>
        </div>
      </div>
    </footer>

    <!-- Sticky CTA Bar (mobile) -->
    <div class="lp-sticky-cta" aria-label="Contact us">
      <div class="lp-sticky-cta-inner">
        <a href="#contact" class="lp-btn lp-btn-primary lp-btn-lg lp-sticky-cta-btn">Contact Us</a>
      </div>
    </div>
  </main>
{tracking_js}
</body>
</html>
"""

            out_path = page_dir / "index.html"
            out_path.write_text(html, encoding="utf-8")
            return PublishResult(ok=True, destination="tailwind_static", artifact_path=str(out_path))
        except Exception as e:
            return PublishResult(ok=False, destination="tailwind_static", errors=[str(e)])
