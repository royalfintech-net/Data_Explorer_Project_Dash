"""
Flask-Dash Data Visualizer — entry point.
Upload CSV/Excel files → inspect schema → visualize with Plotly charts.

Theme/styles live in config.py, page structure in layout.py, and all
callbacks in callbacks.py.
"""

import dash
from flask import Flask

from layout import build_layout
from callbacks import register_callbacks

# ── Flask server ──────────────────────────────────────────────────────────────
server = Flask(__name__)

# ── Dash app ──────────────────────────────────────────────────────────────────
app = dash.Dash(
    __name__,
    server=server,
    suppress_callback_exceptions=True,
    title="DataLens · Visual Explorer",
    update_title=None,
)

app.layout = build_layout()
register_callbacks(app)

# ── Run ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8050)
