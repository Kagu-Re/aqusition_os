"""Adapter layer.

Adapters are integration boundaries. The control plane (policies/registries/queue/logs)
must not depend on vendor SDKs directly.

Interfaces:
- ContentAdapter: builds content payload for a page (copy, images, components)
- PublisherAdapter: publishes a page payload to a destination (Framer/Webflow/WP/etc.)
- AnalyticsAdapter: reads conversion/event signals for reporting or optimization

v0.2.0 ships with stub implementations for local simulation.
"""

# v0.2.1: config-driven adapter selection + framer stub publisher
