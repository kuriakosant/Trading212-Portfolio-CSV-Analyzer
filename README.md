# Trading212 Portfolio CSV Analyzer

![App Screenshot](assets/photo.png)

A powerful **Streamlit** web app for analyzing your Trading212 portfolio exports.  
Upload one or more CSV files, pick a date range, and instantly get P&L breakdowns, dividend growth charts, interest tracking, and a deep per-company comparison — all in a premium dark UI.

---

## Features

| Tab | What it shows |
|---|---|
| **📈 P&L Timeline** | Cumulative P&L area chart + period bars, switchable between **Daily / Weekly / Monthly / Quarterly** resolution. Hover any point to see exact P&L, win rate, and trade count for that period. |
| **📅 Monthly** | Side-by-side grouped bars for Profit, Loss, Net P&L, Dividends, and Interest — one column per month. |
| **🏆 Tickers** | Horizontal bar chart of your best and worst performing tickers + sortable/searchable full breakdown table. |
| **🏢 Companies** | Deep per-company stats: total buy & sell trades, volume, gross profit, gross loss, net P&L, win rate, best/worst single trade, average win/loss. Interactive bubble chart (trades vs P&L vs volume) and a drill-down timeline for any selected company. Multi-company comparison mode. |
| **💵 Dividends** | Cumulative step-line growth chart + per-payment bars grouped by ticker. Full payment log with withholding tax column. |
| **🏦 Interest** | Separate EUR and USD cumulative interest growth lines. Full interest/lending payment log. |
| **🔄 Trades** | Searchable & filterable table of every buy/sell transaction. Export to CSV. |
| **💳 Card Spending** | *(Optional)* Card debit transactions grouped by merchant category. |

### Summary Metric Cards
Two rows of live-updating metric cards at the top of every page:
- **Trading P&L** — Total Profit · Total Loss · Net P&L · Win Rate · Buy Count
- **Passive Income & Cash** — Dividends · Withholding Tax · EUR Interest · USD Interest · Cashback · Net Deposited

---

## Installation

### Prerequisites
- Python 3.9+
- A Trading212 Invest or ISA account (CSV export)

### Setup

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

## Exporting your CSV from Trading212

1. Open the **Trading212** app (mobile or web)
2. Tap **Menu → History**
3. Tap the **download / export icon** (top right)
4. Select your date range *(max 365 days per export)*
5. Tap **Export** — the CSV downloads to your device

> **Tip:** For multi-year history, export one year at a time and upload all files together — the app merges and de-duplicates them automatically.

---

## How to use

1. **Upload CSVs** — drag-and-drop one or more files using the sidebar uploader
2. **Set a date range** — use a quick preset (This Month, Last 3 Months, This Year…) or pick custom dates
3. **Explore** — navigate the tabs to view charts, tables, and breakdowns
4. **Filter** — use the search boxes and action filters in the Trades and Companies tabs
5. **Export** — download any filtered table as a CSV using the export buttons

---

## Project structure

```
Trading212-Portfolio-CSV-Analyzer/
├── app.py              # Streamlit UI — all pages, tabs, and layout
├── analyzer.py         # CSV parser, action classifier, P&L calculations, timeline resampling
├── charts.py           # Plotly chart generation (dark theme)
├── requirements.txt    # Python dependencies
├── .gitignore          # Excludes all *.csv files — your data stays private
└── assets/
    └── photo.png       # Hero screenshot (add your own)
```

---

## Data privacy

- **No data leaves your machine.** The app runs 100% locally.
- **CSV files are gitignored** (`*.csv`, `*.CSV`) — you cannot accidentally commit your financial data to GitHub.
- No analytics, no telemetry, no external API calls.

---

## Dependencies

| Package | Purpose |
|---|---|
| `streamlit` | Web app framework |
| `pandas` | CSV parsing, date filtering, aggregation |
| `plotly` | Interactive charts |
| `numpy` | Numerical operations |

---

## Supported action types

The app correctly classifies every row type in Trading212 exports:

| Action | Category |
|---|---|
| Market buy / Limit buy | `buy` |
| Market sell / Limit sell | `sell` — P&L from `Result` column |
| Dividend (Dividend) | `dividend` |
| Interest on cash / Lending interest | `interest` |
| Deposit | `deposit` |
| Withdrawal | `withdrawal` |
| Currency conversion | `fx_conversion` |
| Card debit / Card credit | `card_debit` / `card_credit` |
| Spending cashback | `cashback` |

---

## License

MIT — free to use and modify.
