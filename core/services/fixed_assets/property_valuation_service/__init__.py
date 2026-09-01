"""property_valuation_service package.

Split from the former single-file ``property_valuation_service.py``
(400 lines) into a one-class-per-file strategy-pattern package. Sibling
contents:

- base.py                          -- ``PropertyValuationResult`` dataclass, ``BasePropertyValuationProvider`` abstract base
- configured_market_rate_provider.py -- ``ConfiguredMarketRateProvider`` (rate-map + bilingual location matching)
- external_api_provider.py         -- ``ExternalApiPropertyValuationProvider`` (HTTP-based external estimator)
- service.py                       -- ``PropertyValuationService`` (orchestrator; public entry point)

Only ``PropertyValuationService`` is re-exported here; it is the sole
name external callers import from this package.
"""

from .service import PropertyValuationService

__all__ = ["PropertyValuationService"]
