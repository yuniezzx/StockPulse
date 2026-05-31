"""StockPulse compute engine.

Responsibilities (per docs/architecture.md §3):
- Tushare data ingestion (data ring 1)
- Indicators & adjustment (data ring 2)
- Screening, risk, evaluation, weights (data ring 3)
- Writing notifications outbox

Does NOT serve HTTP. The API gateway is pulse-api (TypeScript).
"""
