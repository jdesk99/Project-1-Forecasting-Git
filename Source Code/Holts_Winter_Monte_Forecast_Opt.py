import numpy as np
import pandas as pd
from pathlib import Path

# ============================================================
# 0. Load dependencies and input data
#    - If this still fails, you can replace this chunk with a direct 
#      df = pd.read_excel("path/to/90_Days_Winning_HW_Forecast.xlsx") 
#      pointing to a local copy of the file

BASE_DIR = Path(__file__).resolve().parent.parent
FILENAME = "90_Days_Winning_HW_Forecast.xlsx"
preferred = BASE_DIR / "datafiles" / "raw" / FILENAME
try:
    df = pd.read_excel(preferred if preferred.exists() else next(BASE_DIR.rglob(FILENAME)))
except StopIteration:
    raise FileNotFoundError(f"Could not find {FILENAME} under {BASE_DIR}. Place it in datafiles/raw/ or anywhere in the project tree.")

# ============================================================





# ============================================================
# Project 1: Demand Forecasting & Inventory Optimization
# Code analysis begins here with forecast arrays and problem size
# ============================================================

# Holt–Winters (multiplicative) forecast that will become means in normal curve distribution
forecast = df['Forecast'] 
forecast_np = forecast.to_numpy()
n_days = len(df)

# ============================================================
# 1. Inventory policy inputs (R,Q)
# ============================================================

LEAD_TIME   = 5         #supplier lead_time in days
SERVICE_Z   = 1.65      #(95% service target)
HOLD_COST   = 1.00      # Cost per unit per day
ORDER_COST  = 50.0      # fixed cost per purchase order

average_daily_demand = forecast.mean()
log_residual_stdev = df['stdev'].values[0]

# Per-day forecasts over the lead time window
lead_time_daily_forecast = forecast_np[:LEAD_TIME]

#Sum of daily forecasts across the lead time window
lead_time_expected_demand = lead_time_daily_forecast.sum()

# Lead-time demand variance under proportional (multiplicative) Normal errors:
lead_time_demand_variance = (log_residual_stdev ** 2) * np.sum(lead_time_daily_forecast ** 2)
lead_time_demand_stdev = float(np.sqrt(lead_time_demand_variance))


# Safety stock, Reorder point (R) policy, and Q (EOQ approximation):
safety_stock = int(round(SERVICE_Z * lead_time_demand_stdev))
R            = int(round(lead_time_expected_demand + safety_stock))
Q = int(round(np.sqrt((2 * ORDER_COST * average_daily_demand) / HOLD_COST)))


print('\nInventory Policy Inputs')
print(f'Lead Time: {LEAD_TIME}')
print(f'Service Level: 95%')
print(f'Our Holding Cost: {HOLD_COST}')
print(f'Our Ordering Cost: {ORDER_COST}\n')

print(f'Mean Demand: {average_daily_demand:.2f}')
print(f'Safety Stock: {safety_stock}')
print(f'Reorder Point R: {R}')
print(f'Order Quantity Q: {Q}\n')



# ============================================================
# 2. Single-scenario simulator (continuous-review R,Q)
#    - State: on-hand stock, deliveries (days-until-arrival), orders placed
#    - Each day:
#        1) Advance deliveries and receive any that hit 0 days
#        2) Sell up to available stock; track stockouts and holding cost
#        3) If inventory position (on-hand + pipeline) ≤ R, place a PO of size Q
#    - Notes: Demand is integer; receipts arrive after fixed LEAD_TIME
# ============================================================

def run_one (demand, R, Q):
    stock       = R + Q     
    stockouts   = 0
    hold_cost   = 0
    order_count = 0
    deliveries  = []

    for d in demand:
        # 1) Advance pipeline: decrement days and receive any POs that reach 0
        if deliveries:
            deliveries = [t - 1 for t in deliveries]
            arrived = [t for t in deliveries if t == 0]
            if arrived:
                stock += Q * len(arrived)
                deliveries = [t for t in deliveries if t > 0]

        # 2) Satisfy demand up to available stock; shortfall counts as stockout
        sold        = min(stock, d)
        stock      -= sold
        stockouts  += d - sold
        hold_cost  += stock * HOLD_COST

        # 3) Continuous-review reorder rule:
        #    Inventory position = on-hand + pipeline (each PO contributes Q)
        inventory_position = stock + Q * len(deliveries)
        if inventory_position <= R:
            deliveries.append(LEAD_TIME)
            order_count     += 1

    # KPI calculations:
    service_level = 1 - stockouts / demand.sum()
    avg_order_cost = (order_count * ORDER_COST) / n_days
    avg_hold_cost  = hold_cost / n_days
    avg_total_cost = avg_hold_cost + avg_order_cost
    return service_level, stockouts, avg_hold_cost, order_count, avg_order_cost, avg_total_cost


# ============================================================
# 3. Monte Carlo simulation — 10,000 scenarios
#    - Sample daily demand with random draws: N(mean = forecast_t, sd = sigma_log * forecast_t)
#    - Clip at 0 and round to integers to represent unit demand
#    - Run 'run_one' for each scenario and record KPIs and costs
# ============================================================

N_SIMS      = 10000

rng       = np.random.default_rng(42)
records     = []

for s in range(N_SIMS):
    raw_demand_path = rng.normal(forecast_np, log_residual_stdev * forecast_np)
    demand_path = np.rint(np.clip(raw_demand_path, 0, None)).astype(int)
    service_level, oos, h, po, avg_order_cost, avg_total_cost = run_one(demand_path, R, Q)
    records.append((service_level, oos, h, po, avg_order_cost, avg_total_cost))

results = pd.DataFrame(
    records,
    columns=['service_level','stockouts','avg_hold_cost','order_count','avg_order_cost','avg_total_cost']
)
print('\nMonte Carlo Summary (10,000 scenarios)\n')
print(results.agg(['mean','std']))


# Baseline ordering summary (for the baseline R,Q)
orders_per_day = results['order_count'].mean() / n_days
orders_per_year = orders_per_day * 365
ordering_cost_per_year = orders_per_year * ORDER_COST
print(f"\nBaseline policy: ~{orders_per_year:.0f} POs/year  |  ordering $/year ≈ ${ordering_cost_per_year:,.0f}")


# ============================================================
# 4. Grid search over (R, Q)
#    - Build candidate grids around baseline R and Q
#    - For each pair, simulate N_GRID_SIMS demand paths; compute mean service and costs
#    - Keep pairs meeting target_service; rank by total cost (tie-break: higher service)
# ============================================================

print("\nRunning R-Q grid search (this may take ~3-4 minutes)…")
TOP_N = 10

# 1) Defining candidate grids centered on baseline (R, Q)
R_grid = range (R-20, R+20)           
Q_grid = range (Q-20, Q+20)          
N_GRID_SIMS = 100                         
rng = np.random.default_rng(0)             # fresh seed for grid

grid_rows = []
for r in R_grid:
    for q in Q_grid:
        # Initialize Monte Carlo totals for this (r, q)
        service_total = 0
        hold_total    = 0
        order_total   = 0
        for s in range(N_GRID_SIMS):
            draws = rng.normal(forecast_np, log_residual_stdev * forecast_np)
            demand = np.rint(np.clip(draws, 0, None)).astype(int)
            service, oos, h, po, avg_order_cost, avg_total_cost = run_one(demand, r, q)
            service_total += service
            hold_total    += h
            order_total   += po
        mean_service = service_total / N_GRID_SIMS
        mean_hold    = hold_total / N_GRID_SIMS
        mean_orders = order_total / N_GRID_SIMS
        mean_order_cost = mean_orders * ORDER_COST / n_days
        mean_total_cost = mean_hold + mean_order_cost
        grid_rows.append((r, q, mean_service, mean_hold, mean_order_cost, mean_total_cost))

grid_df = pd.DataFrame(
    grid_rows,
    columns=['R','Q','service_lvl','avg_hold_$','avg_order_$','avg_total_$']
)

# 2) Keep pairs that achieve at least the target fill rate (e.g., >= 95%)
target_service = 0.95
candidates = grid_df[grid_df["service_lvl"] >= target_service]

# 3) Rank feasible pairs by lowest total cost/day (tie-break: higher service)
if candidates.empty:
    print(f"No (R, Q) pair met the {target_service:.0%} fill-rate target. Try widening the search grid or lowering the target.")
    raise SystemExit(0)

# Sort by total cost (asc), tie-break by higher service level (desc)
sorted_cands = candidates.sort_values(["avg_total_$","service_lvl"], ascending=[True, False])
best = sorted_cands.iloc[0]

# Show only the top-N rows for readability
print(f"\nGrid-search result (≥{target_service:.0%} service constraint) — Top {TOP_N}")
topN = sorted_cands.head(TOP_N)
print(topN.to_string(index=False))

print("\nBest policy is  R = {0},  Q = {1}"
      "\n   service level = {2:.2%}"
      "\n   holding cost  = ${3:.2f} / day"
      "\n   ordering cost = ${4:.2f} / day"
      "\n   total cost    = ${5:.2f} / day"
      .format(int(best.R), int(best.Q), best.service_lvl, best['avg_hold_$'], best['avg_order_$'], best['avg_total_$']))
best_orders_per_day = best['avg_order_$'] / ORDER_COST
print(f"   ≈{best_orders_per_day * 365:.0f} POs / year")


# ============================================================
# 5. Validate best policy with 10,000 Monte Carlo runs
#    - Re-simulate the best (R, Q) policy with same N_SIMS as baseline
#    - Compare service level, holding $, ordering $, and total $ vs baseline
#    - Report savings per day and annualized ($/year), plus POs/year
# ============================================================
R_best, Q_best = int(best.R), int(best.Q)

# Re-simulate with same N_SIMS as baseline for apples-to-apples
rng = np.random.default_rng(123)
val_records = []
for _ in range(N_SIMS):
    draws = rng.normal(forecast_np, log_residual_stdev * forecast_np)
    dpath = np.rint(np.clip(draws, 0, None)).astype(int)
    val_records.append(run_one(dpath, R_best, Q_best))

val = pd.DataFrame(
    val_records,
    columns=['service_level','stockouts','avg_hold_cost','order_count','avg_order_cost','avg_total_cost']
)

# Baseline and candidate means
base = results.agg('mean')
cand = val.agg('mean')

# Day-level savings
hold_sav_day  = base['avg_hold_cost']  - cand['avg_hold_cost']
order_sav_day = base['avg_order_cost'] - cand['avg_order_cost']
total_sav_day = base['avg_total_cost'] - cand['avg_total_cost']

# Year-level savings
hold_sav_year  = hold_sav_day  * 365
order_sav_year = order_sav_day * 365
total_sav_year = total_sav_day * 365

# Orders/year comparison
orders_per_year_best = (val['order_count'].mean() / n_days) * 365

print("\n=== Final Cost Impact Summary (validated with 10,000 sims) ===")
print(f"Baseline (R={R}, Q={Q}) — service ≈ {base['service_level']:.2%}, total ≈ ${base['avg_total_cost']:.2f}/day")
print(f"Best policy (R={R_best}, Q={Q_best}) — service ≈ {cand['service_level']:.2%}, total ≈ ${cand['avg_total_cost']:.2f}/day")
print("\nSavings")
print(f"  Total: ${total_sav_day:.2f}/day  →  ≈ ${total_sav_year:,.0f}/year")
print(f"    • Holding: ${hold_sav_day:.2f}/day  →  ≈ ${hold_sav_year:,.0f}/year")
print(f"    • Ordering: ${order_sav_day:.2f}/day →  ≈ ${order_sav_year:,.0f}/year")
print(f"\nPOs/year: baseline ≈ {orders_per_year:.0f} → best ≈ {orders_per_year_best:.0f}")