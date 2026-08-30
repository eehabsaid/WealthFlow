"""
Certificate-domain forecast logic for NetWorthService.

Everything needed by certificate_forecast_payload() lives here, split by
phase: certificate_forecast_context.py (shared state) ->
certificate_forecast_metrics.py (phase 1) ->
certificate_forecast_recommendations*.py (phase 2) ->
certificate_forecast_action.py (phase 3). See the parent package's
__init__.py docstring for the full call-order explanation.
"""
