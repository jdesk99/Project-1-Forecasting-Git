# Project 1 — Demand Forecasting & Inventory Optimization

Business problem: achieve a 95% service level while minimizing inventory cost for a single SKU. Given business inputs (lead time, holding and order costs, service target) and historical demand, we evaluated five forecasting models (winner: Holt–Winters, multiplicative) and used the winner to forecast and optimize a continuous‑review (R, Q) policy, then validated results with Monte Carlo simulation.

---

## Overview
- Goal: Minimize total inventory cost while achieving ≥95% service.
- Scope: 5 years of daily demand (single SKU), weekly HW forecast disaggregated to daily, grid-search optimization, 10k-run validation.
- Live page: https://jdesk99.github.io/Project-1-Forecasting-Git/
- Project brief: `docs/brief.html`

---

## Results
- Baseline (R=92, Q=42): ≈96.8% service · ≈$50.94/day · ≈149 POs/year
- Optimized (R=86, Q=49): ≈95.0% service · ≈$46.32/day · ≈125 POs/year
- Savings: ≈$419 over 91 days (≈$1,684/year) and ≈24 fewer POs/year

---

## Methodology
- Forecast: Holt–Winters (multiplicative) selected via MAE on holdout; weekly forecast disaggregated to daily by day‑of‑week factors.
- Uncertainty: Proportional Normal noise with σ estimated from HW residuals (σ · μₜ).
- Simulation: 10,000 demand paths for baseline and best‑policy validation.
- Optimization: Grid search around baseline (R, Q); pick min total cost/day subject to service ≥95%.
- Policy model: Continuous‑review (R, Q) with fixed lead time and costs.

### Assumptions
- Lead time: 5 days
- Service target: 95% (Z=1.65)
- Holding cost: $1/unit/day
- Order (setup) cost: $50/PO

---

## Next Steps
- Sensitivity analysis on lead time, costs, and service targets
- Multi‑SKU extension (shared capacity constraints)
- Backorders vs lost‑sales toggle
- CSV export of grid and validation summaries

---

## Outputs
- Console: 
  - Baseline Monte Carlo summary (10k sims)
  - Grid-search Top N (feasible ≥95% service)
  - Best policy metrics and POs/year
  - Validation comparison and annualized savings
- Visuals: Key figures in `Data Files/images/` (e.g., 7‑day smoothing) are showcased on the landing page `docs/index.html`.

---

## Repository Structure
- Data: `Data Files/Raw/` (source Excel), `Data Files/Processed/` (model selection), `Data Files/images/` (charts)
- Code: `Source Code/Holts_Winter_Monte_Forecast_Opt.py`
- Docs: `docs/index.html` (landing), `docs/brief.html` (brief)
- Env: `requirements.txt`, `LICENSE` (MIT)

---

## Data & Modeling Assets
- Raw demand and forecast: `Data Files/Raw/90_Days_Winning_HW_Forecast.xlsx`
- Model selection workbook (MAE): `Data Files/Processed/Model Selection.xlsx`
- Visual artifacts (Tableau/exports): `Data Files/images/`

---

## How to Run
Requirements
- Python 3.10+
- `numpy`, `pandas`, `openpyxl`

Install
```bash
pip install -r requirements.txt
```

Run
```bash
python "Source Code/Holts_Winter_Monte_Forecast_Opt.py"
```

Input file
- The script auto-locates `90_Days_Winning_HW_Forecast.xlsx` anywhere under the repo; place it in `Data Files/Raw/` if missing.
- Loader logic lives near the top of the script and falls back to a recursive search if the preferred path is absent.

Runtime
- Grid search runs in ~3–4 minutes on a typical laptop. The script prints baseline summaries, grid-search Top N, best policy metrics, and a final validation comparison with annualized savings.

---

## Repro Notes
- Defaults for lead time, costs, and Z are set near the top of `Source Code/Holts_Winter_Monte_Forecast_Opt.py`:

```python
LEAD_TIME   = 5        # days
SERVICE_Z   = 1.65     # ~95% service
HOLD_COST   = 1.00     # $/unit/day
ORDER_COST  = 50.0     # $/PO
```

- The input Excel must include columns used by the script (e.g., `Forecast` and a residual `stdev`).
- Re-run the script to regenerate baseline, search, and validation summaries.

---

## License
MIT — see `LICENSE`.
