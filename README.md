# Institutional Proxy Voting Divergence Analysis
### SEC EDGAR N-PX Filings · 2025 (First Mandatory Structured Year)

**Business question:** Do Vanguard, BlackRock, and State Street vote differently on executive pay, board governance, and ESG proposals — and can voting behaviour be predicted from proposal characteristics?

---

## Dataset

| Institution | Coverage | Filings | Votes | Dissent rate |
|---|---|---|---|---|
| BlackRock | iShares Trust — 10 fund families | 10 | 1,011,315 | 4.37% |
| State Street | SSIT + SPDR Index Shares Funds | 7 | 556,525 | 5.10% |
| Vanguard | Index Funds + World Fund | 32 | 308,230 | 8.05% |
| **Total** | **3 institutions · 49 filings** | **49** | **1,876,070** | **5.19%** |

2025 is the **first year** the SEC required machine-readable structured XML for N-PX filings.  
All data streamed directly from SEC EDGAR using ReadableStream chunk parsing — no full-file download required.

---

## Key Findings

### Institutional Divergence

At 1.88 M votes the three institutions show **divergence, not convergence**:

- **Vanguard (8.05%)** is the most activist — nearly 2× BlackRock's rate. The World Fund contributes elevated Director Elections and Corporate Governance opposition.
- **State Street (5.10%)** sits in the middle, consistent across SSIT and SPDR fund families.
- **BlackRock (4.37%)** shows the lowest overall dissent despite the largest vote count.

### Executive Pay

| Institution | Say-on-pay against rate |
|---|---|
| BlackRock | 4.2% |
| State Street | 1.7% |
| Vanguard | 5.4% |

Vanguard is the toughest on executive compensation. State Street is largely aligned with management on pay.

### Climate & ESG Activism

| Category | Combined dissent | Notes |
|---|---|---|
| Human Rights / Workforce | **92.78%** | Near-universal activist position |
| Environment / Climate | **91.14%** | All three institutions oppose management on climate |
| Diversity, Equity & Inclusion | **84.95%** | Strong support for DEI shareholder resolutions |
| Other Social Issues | 39.48% | Selective engagement |
| Shareholder Rights | 22.05% | Targeted opposition to anti-shareholder defenses |
| Director Elections | 5.13% | Targeted withholding from specific directors |
| Corporate Governance | 4.67% | Mostly aligned with management |

State Street leads documented climate activism: 91.5% dissent across 294 tagged climate proposals.  
Vanguard voted against management on all 17 tagged climate proposals (100%).

### Predictive Model

A logistic regression trained on **98,941 votes** (pre-expansion baseline, 80/20 split) with 29 features:

| Metric | Value |
|---|---|
| ROC-AUC | **0.798** |
| Accuracy | 95.6% |
| Features | 29 |

**Top predictors of dissent:**
- Say-on-pay proposals → strongly *reduce* dissent probability (coefficient −0.984): institutions almost always side with management on executive pay.
- Director elections → *increase* dissent (+0.655): targeted withholding is common across all three institutions.
- Climate, Human Rights, and DEI categories → all strongly predict dissent against management.

---

## How It Works

All voting data is fetched and parsed entirely in-browser against live SEC EDGAR endpoints:

1. **ReadableStream parser** — processes complete `<inf:proxyTable>` / `<proxyTable>` blocks from chunked HTTP responses, accumulating running aggregates without storing individual votes.
2. **Dual-schema support** — BlackRock and State Street use the `inf:` XML namespace; Vanguard uses a default namespace with a different vote nesting structure (`<voteRecord>`).
3. **GitHub push** — aggregated JSON pushed to this repo via the GitHub Contents API.

---

## Project Structure

```
proxy-voting-analysis/
├── index.html               ← Live GitHub Pages dashboard (Chart.js 4.4)
├── model_metrics.json       ← Logistic regression performance stats
├── dashboard_data.json      ← Per-institution vote aggregates
└── scripts/
    └── phase1_fetch_parse.py    ← Earlier SQLite-based prototype (Colab)
```

## Methodology

- **Dissent definition:** `howVoted ≠ managementRecommendation` (both non-empty). Captures votes where the institution sides with a shareholder proposal against the board, or withholds from a management-sponsored proposal.
- **Model:** Logistic regression with one-hot encoded institution identity, proposal category, and meeting month. Trained on the pre-expansion 98,941-vote dataset; AUC and accuracy reported on 20% held-out test set.
- **Limitation:** BlackRock category tags (`inf:categoryType`) exist in the 2025 iShares Trust XML but ESG-tagged proposals (Climate, Human Rights, DEI) are extremely rare relative to the 1 M+ total — those categories are not shown in the per-institution breakdown.

---

*Data: SEC EDGAR public N-PX filings (2025) · Analysis: Kamran Ali · 2025*
