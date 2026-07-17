# ◈ DataLens — Visual Explorer

A dark-themed web app for exploring tabular data without writing code.
Upload a CSV or Excel file, inspect its schema, then build interactive
Plotly charts step by step: pick a chart type, choose the columns, tune
the options, and create the chart.

Built with [Dash](https://dash.plotly.com/) (Flask + Plotly + React) in Python.

## Features

- **File upload** — drag & drop or click to select `.csv`, `.xlsx`, or `.xls`
- **Schema inspection** — column types, non-null / null counts, unique
  values, and a sample value for every column, plus a 15-row data preview
- **Automatic date detection** — string columns that look like dates
  (common in CSVs) are converted to real datetimes
- **Guided chart builder** — select a chart type from a dropdown, then
  configure only what that chart needs:

  | Chart | Columns | Extra options |
  |-------|---------|---------------|
  | 📈 Line | X-axis (radio list), Y columns (checkboxes) | Lines + markers / lines / area |
  | 📊 Bar | Category (radio list), value columns (checkboxes) | Sum / average / count / raw · Top 10/25/50/all · vertical / horizontal |
  | 🥧 Pie | Slice column (radio list) | Slice size (row count or sum of a numeric column) · Top 6/11/16 + "Other" · donut toggle |

- **Chart smarts**
  - Line charts sort by X and re-parse ISO date strings, so series plot in order
  - When two Y metrics differ by ≥100× (e.g. market cap vs. price), the
    smaller series moves to a labeled secondary axis instead of flattening to zero
  - Bar charts aggregate repeated categories and cap to a Top-N so
    thousands of rows stay readable; horizontal mode auto-sizes for long labels
  - Pie charts roll everything beyond the Top-N into an "Other" slice
- **Switch chart types in place** — after creating a chart, changing the
  chart type re-renders instantly using that type's own column selections

## Getting started

Requires Python 3.10+.

```bash
# 1. Create and activate a virtual environment
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run the app
python app.py
```

Then open <http://localhost:8050> in your browser.

`LargestCompanies.csv` (≈5,900 public companies with rank, market cap,
price, and country) is included as a sample dataset to try out.

## Usage

1. **① Upload your data** — drop a file and click **Read & Analyze**
2. **② Data Schema** — review column types and null counts; a preview
   table shows the first 15 rows
3. **③ Configure Chart** — pick a chart type from the dropdown, select
   its columns (nothing is pre-selected), adjust the options, and click
   **Create Chart**
4. **④ Chart** — interact with the Plotly chart (hover, zoom, pan,
   export as PNG). Switch the chart type in ③ any time — the chart
   updates instantly once its columns are chosen

## Project structure

```
data_explorer_project/
├── app.py            # Entry point: Flask server + Dash app wiring
├── layout.py         # Page structure (topbar, upload card, section placeholders)
├── callbacks.py      # All interactivity: upload, schema, chart controls, chart builders
├── utils.py          # File parsing and datetime detection helpers
├── config.py         # Theme tokens, chart palette, Plotly template, style helpers
├── assets/
│   └── styles.css    # Fonts, scrollbars, and Dash 4 dropdown dark-theme overrides
├── requirements.txt
└── LargestCompanies.csv   # Sample dataset
```

How the pieces fit together:

- `app.py` creates the Flask server and Dash app, sets
  `app.layout = build_layout()` and calls `register_callbacks(app)`
- `layout.py` renders the static shell; the schema card, chart controls,
  and charts are filled in dynamically by callbacks after a file is read
- `callbacks.py` holds three callbacks — read & analyze, show/hide the
  active chart type's options, and create/switch the chart — plus the
  pure chart-builder functions (`_make_line_chart`, `_make_bar_chart`,
  `_make_pie_chart`)
- Parsed data is stored client-side in a `dcc.Store` as JSON, so the
  server stays stateless between callbacks

## Tech stack

| Layer | Library |
|-------|---------|
| Web framework | Flask 3 + Dash 4 |
| Charts | Plotly 6 |
| Data wrangling | pandas |
| Excel support | openpyxl |

## Notes & limitations

- Data lives in the browser session (`dcc.Store`); refreshing the page
  requires re-uploading
- Very large files are limited by browser memory — tested comfortably
  with ~6,000 rows
- Bar "sum per category" answers *"which category totals the most"*;
  use **Average per category** for per-item comparisons
