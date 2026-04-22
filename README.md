# Broker Portfolio CSV Analyzer

> *"Local, secure portfolio and spending analyzer for Trading212 and Revolut. Built with Streamlit, it transforms raw CSV history exports into powerful visual insights — detailing trade win rates, money-weighted returns, dividends, interest, P&L efficiency, and granular per-company breakdowns that the native apps don't show you."*

![Main Dashboard](assets/photo.png)

A high-performance **Streamlit** web application for visualizing your **Trading212** and **Revolut** portfolios (plus Trading212 debit card activity). Upload one or more CSV files — mix brokers freely — pick a date range, and instantly unlock institutional-grade P&L breakdowns, yield tracking, MWRR return analysis, and a deep per-company comparison — all wrapped in a premium dark UI.

> **Supported brokers:** Trading212 (full feature set) · Revolut Stocks (USD sub-portfolio — see note below)

---

## 🚀 The "Missing" Broker Insights

While the native Trading212 and Revolut apps are excellent for execution, their analytics are basic. This dashboard extracts and visualizes the raw data hidden within your export files to give you:

- **True Win Rates** — Know exactly how many sell trades resulted in a profit vs. a loss, and visualize your win-ratio per ticker.
- **Money-Weighted Return (MWRR)** — See your actual portfolio IRR adjusted for the exact timing and size of every deposit and withdrawal — the same metric professional fund managers use.
- **Hidden Fees & Taxes** — See the exact aggregated total of FX fees, stamp duties, and hidden costs you've paid across your trading career.
- **Algorithmic P&L Correlation** — Scatter plot visualization of Trade Volume vs. Total Trades vs. Net P&L to see if overtrading is hurting your returns.
- **Aggregated Net Deposits** — Flawless tracking of In/Out flows, automatically deducting your stock market withdrawals *and* your card spending.
- **Card Spending Analytics** — Beautiful categorizations of your Trading212 Visa/Mastercard debit expenses, top merchants, and spending velocity.

---

## 📊 Comprehensive Feature Breakdown

### 🏦 1. Main Dashboard & Portfolio Tracking

![Main Dashboard](assets/photo.png)
![Portfolio Growth Chart](assets/CHART.png)

- **Portfolio Return Hero Card** — The MWRR annualized return *(requires ≥ 180 days)* is displayed prominently at the top of every dashboard view. For shorter windows, the total return % is shown instead.
- **MWRR Metric Row** — Four dedicated cards: Annualized Return, Total Return, Terminal Portfolio Value, and Capital Deployed.
- **Total Portfolio Value Tracker** — A stacked area chart combining Net Deposits, Cumulative P&L, Dividends, and Interest — with the live MWRR Return % overlaid on a secondary axis as a dotted teal line.

---

### 📈 2. Portfolio Return (MWRR)

![MWRR Return Chart](assets/MWRR.png)

This section surfaces the **Money-Weighted Rate of Return** — a time-adjusted performance metric that accounts for the exact dollar amount and date of every cash flow into and out of the portfolio.

#### How It's Calculated

The MWRR is mathematically equivalent to the **Internal Rate of Return (IRR)** of the portfolio's cash flows. It solves for an annualized rate `r` such that the net present value of all cash flows equals zero:

```
NPV = Σ [ Cash_Flow_i / (1 + r)^(t_i in years) ] + Terminal_Value / (1 + r)^T = 0
```

Where:
- **Deposits** → negative cash flows (money flowing **into** the portfolio)
- **Withdrawals & card spend** → positive cash flows (money flowing **out**)
- **Terminal Value** = Net Deposits + Realized P&L + Dividends + Interest *(realized gains only — no live price feed)*
- **`r`** = annualized MWRR (the result)

The solver uses a **multi-start Newton-Raphson** algorithm (three seed guesses) with a **bisection fallback**, operating in annualized rate space `[-99%, +1000%]` to prevent the numerical divergence that occurs when compounding short-period daily rates.

> ⚠️ **Realized-only caveat:** Because the app has no live market price feed, the terminal value is built from *realized* gains only. Unrealized gains on currently-held positions are not captured. This is clearly marked in all tooltips.

> 📅 **Annualized MWRR** is only shown when the selected date range is **≥ 180 days**. For shorter windows, only the Total Return % is displayed to avoid misleading annualizations.

#### What the Chart Shows

The dedicated MWRR chart has two panels:

| Panel | Content |
|---|---|
| **Top** | Cumulative Return % curve with gradient fill and a final annotation stamp |
| **Bottom** | Daily gains delta bars (green for positive days, red for negative) |

Rich hover tooltips on the top curve show, for every date: Return %, Terminal Value, Capital Deployed, and Total Gains.

#### Per-Company Return Contribution

Every company in your portfolio is assigned a **Return Contribution %** — representing how large a share of the total realized portfolio P&L it is responsible for:

```
Return Contribution (ticker) = Net P&L (ticker) / Total Portfolio Net P&L × 100%
```

This is visualized in the **🧩 Return Contribution by Position** waterfall chart in the Companies tab. Bars to the right (green) are drivers of growth; bars to the left (red) are detractors. The total portfolio MWRR is stamped in the top-right corner.

---

### 📅 3. Realized P&L Timeline

![P&L Timeline](assets/PNL.png)

- **Dynamic Resolution** — Daily, Weekly, Monthly, or Quarterly resolutions. The top area chart tracks cumulative P&L growth; bottom bars show period-by-period returns with win/loss counts.

---

### 🏢 4. Companies Deep-Dive

![Companies Market Overview](assets/Companies.png)

- **Net P&L Bar Chart** — All tickers ranked by realized gain/loss.
- **Trades vs. P&L Bubble Chart** — Interactive matrix of trade count vs. net P&L. Bubble size = capital deployed; color = win rate.
- **Return Contribution Waterfall** — Per-ticker share of total portfolio MWRR return growth.
- **Multi-Company Comparison** — Select 2–8 tickers to stack their cumulative P&L timelines.

### 🔍 5. Granular Company Drill-Down

![Company Drill-Down](assets/company-drill-down.png)

Select any stock to reveal:
- Stat cards: Net P&L, **Return Contribution %**, Gross Profit, Gross Loss, Win Rate, Best/Worst Trade, Avg Win/Loss, Buy count, Days Active.
- A full chronological buy/sell timeline with running cumulative P&L.
- A trade-by-trade log table, exportable as CSV.

### 💵 6. Dividends & Interest Tracking

![Dividends Tracker](assets/dividends.png)
![Interest Tracker](assets/INTEREST.png)

- **Step charts** showing every payment with running cumulative totals.
- EUR and USD interest streams tracked separately.
- Withholding tax isolated from gross dividends.

### 💳 7. Trading212 Card Spending Analyzer *(Trading212 only)*

![Card Spending Analytics](assets/spending.png)

Dynamically activates when card debit activity is detected. Revolut's Stocks CSV does not carry card/merchant data, so this page automatically hides itself when only Revolut files are uploaded.

- **Monthly Velocity** — Bar charts tracking your debit card burn rate.
- **Merchant Profiling** — Top 10 most frequented merchants.
- **Category Donut** — Spending breakdown by Visa/Mastercard categories.
- **Cashback Metrics** — Card rewards fully integrated into portfolio return totals.

---

## 💾 Installation & Setup

### Prerequisites

- Python 3.9+
- A Trading212 Invest/ISA account **or** a Revolut Stocks account (CSV export)

### Terminal Startup

```bash
# 1. Clone the repo
git clone https://github.com/kuriakosant/Trading212-Portfolio-CSV-Analyzer.git
cd Trading212-Portfolio-CSV-Analyzer

# 2. Create a virtual environment
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Launch the app
streamlit run app.py
```

Then open **http://localhost:8501** in your browser.

---

## 🗄 Exporting your CSV

### From Trading212

1. Open the **Trading212** app (mobile or web)
2. Go to **Menu → History**
3. Click the **download / export icon** (top right)
4. Select your date range *(max 365 days per export — upload multiple files for longer history)*
5. Tap **Export** — the CSV downloads to your device

### From Revolut

1. Open the **Revolut** app and switch to the **Stocks** product
2. Go to **Statements** (under the Stocks account menu)
3. Choose **Account statement** and the **CSV** format
4. Pick your date range and confirm — the CSV is emailed / downloaded

> **Heads up on Revolut:** The adapter analyzes Revolut as a **USD-only sub-portfolio**. EUR cash top-ups, EUR-denominated trades, and internal EUR↔USD conversions are filtered out at parse time so that P&L, FIFO cost basis, and all cash flows are expressed cleanly in USD end-to-end.

> **Tip:** For multi-year history, export one year at a time. The sidebar uploader accepts multiple CSV files concurrently — **mix Trading212 and Revolut files freely** — and will merge and de-duplicate them automatically (ID-based first, then content fingerprint).

---

## 🔒 Data Privacy & Security

- **No data leaves your machine.** The app runs completely locally on your own Python environment.
- **CSV files are git-ignored** in the source control config — you cannot accidentally commit your financial data to GitHub.
- **Zero Telemetry.** No external API calls, no analytics tracking, no server-side renders.

---

## 📦 Supported Action Types

The backend parsing engine cleanly isolates the following row types from both Trading212 and Revolut CSV exports:

| Category | Actions |
|---|---|
| `buy` | Market Buy, Limit Buy |
| `sell` | Market Sell, Limit Sell (with FIFO P&L for Revolut) |
| `dividend` | Dividend payment, Dividend tax correction |
| `interest` | Interest on cash, Lending interest (EUR & USD) |
| `deposit` | Deposit, Top-up |
| `withdrawal` | Withdrawal |
| `fx_conversion` | Currency conversion |
| `card_debit` | Debit card spending *(Trading212 only)* |
| `card_credit` | Card refunds / credits |
| `cashback` | Spending cashback rewards |
| `stock_split` | Stock split adjustments |

---

## License

MIT — free to use, modify, and distribute.
