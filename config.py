"""
config.py — Theme tokens, chart palette, Plotly template, and style helpers.
"""

import plotly.graph_objects as go

# ── Color palette ─────────────────────────────────────────────────────────────
COLORS = {
    "bg":       "#0B0F19",
    "surface":  "#131825",
    "surface2": "#1A2035",
    "border":   "#252D44",
    "accent":   "#6C63FF",
    "accent2":  "#00D9A3",
    "accent3":  "#FF6B8A",
    "text":     "#E8ECF4",
    "muted":    "#7B8AB8",
    "danger":   "#FF4D6A",
}

# ── Chart color sequence ──────────────────────────────────────────────────────
CHART_COLORS = [
    "#6C63FF", "#00D9A3", "#FF6B8A", "#FFB84D", "#4DC9F6",
    "#9B59B6", "#1ABC9C", "#E74C3C", "#3498DB", "#F39C12",
]

# ── Plotly layout template ────────────────────────────────────────────────────
PLOTLY_TEMPLATE = dict(
    layout=go.Layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="DM Sans, sans-serif", color=COLORS["text"], size=13),
        xaxis=dict(gridcolor="#1E2740", zerolinecolor="#1E2740"),
        yaxis=dict(gridcolor="#1E2740", zerolinecolor="#1E2740"),
        margin=dict(l=50, r=30, t=50, b=50),
        colorway=CHART_COLORS,
        legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(size=11)),
    )
)


# ── Reusable style helpers ────────────────────────────────────────────────────
def card_style(extra=None):
    """Return a dark-themed card dict; merge *extra* overrides if given."""
    base = {
        "background": COLORS["surface"],
        "border": f"1px solid {COLORS['border']}",
        "borderRadius": "14px",
        "padding": "28px",
        "marginBottom": "24px",
    }
    if extra:
        base.update(extra)
    return base