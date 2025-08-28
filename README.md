# Project 1 — Demand Forecasting & Inventory Optimization

Optimize a continuous-review **(R, Q)** inventory policy using **Holt–Winters forecasting** and **Monte Carlo simulation**.

---

## Goal
Balance high service levels (≥95%) with lower total inventory costs by simulating demand variability and testing policy options.

---

## Method
1. Forecast 91 days of demand with Holt–Winters (multiplicative).
2. Model demand uncertainty using proportional Normal noise:
   - μₜ = forecast mean
   - σₜ = σ_log · μₜ  (σ_log from training residuals)
3. Simulate 10,000 scenarios of daily demand.
4. Evaluate baseline policy (R, Q).
5. Grid search around baseline to find the cost-optimal policy that meets service ≥95%.
6. Validate the best policy with another 10,000 runs.

---

## Results
- **Baseline** (R=92, Q=42)  
  Service ≈ 96.8% · Cost ≈ $50.9/day · ≈149 POs/year  

- **Optimized** (R=86, Q=49)  
  Service ≈ 95.0% · Cost ≈ $46.3/day · ≈125 POs/year  

- **Savings:** ≈ $419 over 91 days (≈$1.7K annualized)  

---

## How to Run
```bash
pip install -r requirements.txt
python "Source Code/Holts_Winter_Monte_Forecast_Opt.py"