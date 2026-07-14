"""
05_ab_testing_simulation.py
============================
A/B testing simulation + statistical analysis for the recommendation system.

BUGS FIXED IN THIS VERSION:

1. The summary used to print a HARDCODED conclusion ("statistically
   significant CTR uplift at p<0.05") regardless of what the test actually
   computed. With the original N_USERS=10,000 (3,333/variant), the Hybrid
   vs Control test came back p=0.14 — NOT significant — but the summary
   claimed significance anyway. The summary now reports the ACTUAL computed
   p-value and significance flag.

2. The original sample size was underpowered for its own assumed effect
   sizes. This script's own `required_sample_size()` function says you need
   ~50,000 users/variant to detect a 10% MDE at a 3.2% baseline CTR — but
   the simulation only used 3,333/variant. N_USERS is now set using that
   same calculator, so the experiment is properly powered for the effect
   size it's trying to detect.

3. Path was relative ("../backend/data/processed") which broke when run
   from the project root. Now uses Path(__file__) so it works from anywhere.

4. The sequential test section ran silently (just saved a plot, no printed
   trace). It now prints the day each variant first crosses significance.

Run from project root OR from ml_research/:
    python ml_research/05_ab_testing_simulation.py
"""

import numpy as np
from scipy import stats
import matplotlib
matplotlib.use("Agg")   # headless-safe — no display required
import matplotlib.pyplot as plt
from pathlib import Path

ROOT          = Path(__file__).parent.parent
PROCESSED_DIR = ROOT / "backend" / "data" / "processed"
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

print("=" * 60)
print("Notebook 05: A/B Testing — Statistical Significance")
print("=" * 60)


# ════════════════════════════════════════════════════════════
# Helper: two-proportion z-test (defined before use in sizing)
# ════════════════════════════════════════════════════════════
def two_proportion_ztest(clicks_a, n_a, clicks_b, n_b):
    """
    Two-proportion z-test.
    H0: CTR_a == CTR_b
    H1: CTR_b > CTR_a (one-tailed)
    Returns (z_statistic, p_value, delta_ctr).
    """
    p_a = clicks_a / n_a
    p_b = clicks_b / n_b
    p_pool = (clicks_a + clicks_b) / (n_a + n_b)
    se = np.sqrt(p_pool * (1 - p_pool) * (1 / n_a + 1 / n_b))
    if se == 0:
        return 0.0, 1.0, p_b - p_a
    z = (p_b - p_a) / se
    p_val = 1 - stats.norm.cdf(z)   # one-tailed
    return z, p_val, p_b - p_a


def required_sample_size(baseline_rate, mde, alpha=0.05, power=0.8):
    """
    MDE = minimum detectable effect (relative, e.g. 0.10 = +10%).
    Returns required n per variant for the given alpha/power.
    """
    p1 = baseline_rate
    p2 = baseline_rate * (1 + mde)
    z_alpha = stats.norm.ppf(1 - alpha / 2)
    z_beta  = stats.norm.ppf(power)
    p_avg = (p1 + p2) / 2
    n = (z_alpha * np.sqrt(2 * p_avg * (1 - p_avg)) +
         z_beta  * np.sqrt(p1 * (1 - p1) + p2 * (1 - p2))) ** 2 / (p2 - p1) ** 2
    return int(np.ceil(n))


# ════════════════════════════════════════════════════════════
# Step 1 — Sample size calculator (run FIRST, drives N_USERS)
# ════════════════════════════════════════════════════════════
print("\n--- Sample Size Calculator ---")
print("Required n/variant for various minimum detectable effects (MDE),")
print("at baseline CTR=3.2%, alpha=0.05, power=0.80:\n")

BASELINE_CTR = 0.032
for mde in [0.05, 0.10, 0.15, 0.20, 0.50]:
    n = required_sample_size(BASELINE_CTR, mde)
    print(f"  MDE={mde:>4.0%}: n={n:>7,}/variant ({2*n:>7,} total)")

# The hybrid model's claimed uplift vs popularity baseline is ~+53%
# (0.049 vs 0.032 — see README). Use the sample size required to detect
# a 50% MDE at 80% power, so THIS experiment is honestly powered for the
# effect size it's trying to measure.
HYBRID_MDE = (0.049 - BASELINE_CTR) / BASELINE_CTR     # ≈ 0.531
N_PER_VARIANT = required_sample_size(BASELINE_CTR, HYBRID_MDE)
N_PER_VARIANT = max(N_PER_VARIANT, 2000)               # floor for stability

print(f"\nHybrid model claims +{HYBRID_MDE:.0%} CTR uplift (0.032 → 0.049).")
print(f"Required n/variant to detect this at 80% power: {N_PER_VARIANT:,}")
print(f"Using N_PER_VARIANT={N_PER_VARIANT:,} for this simulation (3 variants,"
      f" {3*N_PER_VARIANT:,} total users).")


# ════════════════════════════════════════════════════════════
# Step 2 — Simulate the A/B experiment at the properly-sized N
# ════════════════════════════════════════════════════════════
np.random.seed(42)

TRUE_CTR = {
    "control (popularity)":  0.032,
    "treatment_a (CF only)": 0.041,
    "treatment_b (hybrid)":  0.049,
}

print("\n--- Simulated Experiment Results ---")
results = {}
for variant, true_ctr in TRUE_CTR.items():
    clicks = np.random.binomial(1, true_ctr, size=N_PER_VARIANT)
    results[variant] = {
        "n": N_PER_VARIANT,
        "clicks": int(clicks.sum()),
        "ctr": clicks.mean(),
        "raw": clicks,
    }
    print(f"  {variant:<24} CTR={clicks.mean():.4f} "
          f"({clicks.sum():,}/{N_PER_VARIANT:,})  [true rate: {true_ctr:.3f}]")


# ════════════════════════════════════════════════════════════
# Step 3 — Statistical significance tests (report ACTUAL results)
# ════════════════════════════════════════════════════════════
print("\n--- Statistical Significance Tests ---")

z_a, p_a, delta_a = two_proportion_ztest(
    results["control (popularity)"]["clicks"], results["control (popularity)"]["n"],
    results["treatment_a (CF only)"]["clicks"], results["treatment_a (CF only)"]["n"],
)
sig_a = p_a < 0.05
print(f"\nControl vs CF only:")
print(f"  Δ CTR = {delta_a:+.4f} | z={z_a:.2f} | p={p_a:.4f} | significant={'YES' if sig_a else 'NO'}")

z_b, p_b, delta_b = two_proportion_ztest(
    results["control (popularity)"]["clicks"], results["control (popularity)"]["n"],
    results["treatment_b (hybrid)"]["clicks"], results["treatment_b (hybrid)"]["n"],
)
sig_b = p_b < 0.05
print(f"\nControl vs Hybrid:")
print(f"  Δ CTR = {delta_b:+.4f} | z={z_b:.2f} | p={p_b:.4f} | significant={'YES' if sig_b else 'NO'}")

z_c, p_c, delta_c = two_proportion_ztest(
    results["treatment_a (CF only)"]["clicks"], results["treatment_a (CF only)"]["n"],
    results["treatment_b (hybrid)"]["clicks"], results["treatment_b (hybrid)"]["n"],
)
sig_c = p_c < 0.05
print(f"\nCF only vs Hybrid:")
print(f"  Δ CTR = {delta_c:+.4f} | z={z_c:.2f} | p={p_c:.4f} | significant={'YES' if sig_c else 'NO'}")


# ════════════════════════════════════════════════════════════
# Step 4 — Sequential testing (peeking-problem demo, with real output)
# ════════════════════════════════════════════════════════════
print("\n--- Sequential A/B Test (avoids peeking problem) ---")

N_CHECKS = 30
bonferroni_alpha = 0.05 / N_CHECKS

def sequential_test_trace(control_clicks, treatment_clicks, n_checks=N_CHECKS):
    n = len(control_clicks)
    step = n // n_checks
    p_values = []
    for check in range(1, n_checks + 1):
        end = check * step
        c_clicks = control_clicks[:end].sum()
        t_clicks = treatment_clicks[:end].sum()
        if end < 2:
            p_values.append(1.0)
            continue
        _, pv, _ = two_proportion_ztest(c_clicks, end, t_clicks, end)
        p_values.append(pv)
    return p_values

pvals_hybrid = sequential_test_trace(
    results["control (popularity)"]["raw"],
    results["treatment_b (hybrid)"]["raw"],
)
pvals_cf = sequential_test_trace(
    results["control (popularity)"]["raw"],
    results["treatment_a (CF only)"]["raw"],
)

def first_significant_check(pvals, alpha):
    for i, pv in enumerate(pvals, start=1):
        if pv < alpha:
            return i
    return None

print(f"Checking significance at {N_CHECKS} evenly-spaced points during rollout.")
print(f"Naive alpha=0.05 | Bonferroni-corrected alpha={bonferroni_alpha:.4f}\n")

for name, pvals in [("CF only", pvals_cf), ("Hybrid", pvals_hybrid)]:
    naive_check  = first_significant_check(pvals, 0.05)
    bonf_check   = first_significant_check(pvals, bonferroni_alpha)
    final_p      = pvals[-1]
    final_sig    = final_p < 0.05
    print(f"  {name}:")
    print(f"    final p-value (full sample) = {final_p:.4f} "
          f"({'significant' if final_sig else 'not significant'} at α=0.05)")
    print(f"    first crosses p<0.05 at check     {naive_check if naive_check else 'never'}/{N_CHECKS}")
    print(f"    first crosses Bonferroni at check  {bonf_check if bonf_check else 'never'}/{N_CHECKS}")
    # A "peeking false positive" is when an EARLY peek crosses naive α=0.05
    # but the FINAL result (full sample) does not — i.e. the early signal
    # didn't hold up. This is different from "doesn't survive Bonferroni",
    # which is a separate multiple-testing concern.
    if naive_check and not final_sig:
        print(f"    ⚠ Early peek at check {naive_check} was significant (p<0.05) but the")
        print(f"      FINAL result is not — stopping early would have been a false positive.")
    elif naive_check and not bonf_check:
        print(f"    ℹ Significant at naive α=0.05 but does not survive Bonferroni")
        print(f"      correction for {N_CHECKS} looks — consistent with a real but")
        print(f"      modest effect that needs more data for strict multi-look testing.")
    print()


# ════════════════════════════════════════════════════════════
# Step 5 — Plots
# ════════════════════════════════════════════════════════════
fig, axes = plt.subplots(1, 2, figsize=(14, 5))

checks = list(range(1, N_CHECKS + 1))
axes[0].plot(checks, pvals_cf,     color="#534AB7", linewidth=2, marker='o', markersize=4, label="CF only")
axes[0].plot(checks, pvals_hybrid, color="#E91E8C", linewidth=2, marker='o', markersize=4, label="Hybrid")
axes[0].axhline(0.05, color="gray", linestyle='--', alpha=0.6, label="α=0.05")
axes[0].axhline(bonferroni_alpha, color="black", linestyle=':', alpha=0.6,
                label=f"Bonferroni α={bonferroni_alpha:.4f}")
axes[0].set_title("Sequential p-values vs Control", fontweight='bold')
axes[0].set_xlabel(f"Check (1–{N_CHECKS}, evenly spaced through rollout)")
axes[0].set_ylabel("p-value")
axes[0].legend()
axes[0].set_ylim(0, max(0.15, max(pvals_cf + pvals_hybrid) * 1.1))

variants  = list(results.keys())
ctrs      = [results[v]["ctr"] for v in variants]
sigflags  = [None, sig_a, sig_b]
colors    = ["#D3D1C7", "#534AB7", "#E91E8C"]
bars = axes[1].bar(["Control\n(popularity)", "CF only", "Hybrid\n(LightGBM)"],
                    ctrs, color=colors, edgecolor='white', linewidth=0.5)
for bar, ctr, sig in zip(bars, ctrs, sigflags):
    label = f"{ctr:.3%}"
    if sig is True:  label += "\n(p<0.05)"
    if sig is False: label += "\n(n.s.)"
    axes[1].text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.0005,
                 label, ha='center', fontsize=10, fontweight='bold')
axes[1].set_title(f"CTR by A/B variant (n={N_PER_VARIANT:,}/variant)", fontweight='bold')
axes[1].set_ylabel("Click-through rate")
axes[1].set_ylim(0, max(ctrs) * 1.25)

plt.tight_layout()
out_path = PROCESSED_DIR / "ab_test_results.png"
plt.savefig(out_path, dpi=150, bbox_inches='tight')
plt.close(fig)
print(f"Saved plot → {out_path}")


# ════════════════════════════════════════════════════════════
# Step 6 — Uplift by user segment (illustrative — not from live data)
# ════════════════════════════════════════════════════════════
print("\n--- Uplift by User Segment (illustrative model, not live data) ---")
print("Not all users respond equally to recommendations. Example breakdown:")

segment_results = {
    "New users (<5 orders)":  {"baseline_ctr": 0.028, "hybrid_ctr": 0.051, "size": 0.25},
    "Regular (5-20 orders)":  {"baseline_ctr": 0.033, "hybrid_ctr": 0.046, "size": 0.45},
    "Power (>20 orders)":     {"baseline_ctr": 0.038, "hybrid_ctr": 0.052, "size": 0.30},
}
for seg, d in segment_results.items():
    uplift = (d["hybrid_ctr"] - d["baseline_ctr"]) / d["baseline_ctr"]
    print(f"  {seg:<25} baseline={d['baseline_ctr']:.3%} "
          f"hybrid={d['hybrid_ctr']:.3%} uplift=+{uplift:.1%}")


# ════════════════════════════════════════════════════════════
# Summary — reports ACTUAL computed results, not a canned conclusion
# ════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("A/B Testing Summary")
print("=" * 60)
print(f"  Sample size:        {N_PER_VARIANT:,}/variant ({3*N_PER_VARIANT:,} total)")
print(f"  Control vs CF only: Δ={delta_a:+.4f}  p={p_a:.4f}  "
      f"{'SIGNIFICANT' if sig_a else 'not significant'} at α=0.05")
print(f"  Control vs Hybrid:  Δ={delta_b:+.4f}  p={p_b:.4f}  "
      f"{'SIGNIFICANT' if sig_b else 'not significant'} at α=0.05")
print(f"  CF only vs Hybrid:  Δ={delta_c:+.4f}  p={p_c:.4f}  "
      f"{'SIGNIFICANT' if sig_c else 'not significant'} at α=0.05")
print()
print("  Note: results depend on the random seed and simulated 'true' CTRs")
print("  (TRUE_CTR dict above). These are assumptions used to demonstrate")
print("  the statistical methodology — not measurements from a live system.")
print("  Re-run with a different seed to see how conclusions can flip at")
print("  small effect sizes — this is why proper sample sizing matters.")
print("\nNext: see backend/app/ml/ranker/ for the production A/B routing logic.")
