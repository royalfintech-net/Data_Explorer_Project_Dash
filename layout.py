"""
layout.py — Dash HTML layout definition.
"""

from dash import dcc, html

from config import COLORS, card_style


def build_layout():
    """Return the root Dash layout component."""
    return html.Div(
        style={
            "backgroundColor": COLORS["bg"],
            "minHeight": "100vh",
            "fontFamily": "'DM Sans', sans-serif",
            "color": COLORS["text"],
            "padding": "0",
        },
        children=[
            # ── Topbar ────────────────────────────────────────────────────
            _topbar(),
            # ── Main content ──────────────────────────────────────────────
            html.Div(
                style={"maxWidth": "1280px", "margin": "0 auto", "padding": "36px 40px"},
                children=[
                    _upload_card(),
                    html.Div(id="status-msg"),
                    html.Div(id="schema-section"),
                    html.Div(id="chart-controls"),
                    html.Div(id="charts-section"),
                    html.Div(id="data-preview"),
                ],
            ),
            # ── Hidden stores ─────────────────────────────────────────────
            dcc.Store(id="store-data"),
            dcc.Store(id="store-columns"),
        ],
    )


# ── Private layout builders ──────────────────────────────────────────────────

def _topbar():
    return html.Div(
        style={
            "background": f"linear-gradient(135deg, {COLORS['surface']} 0%, {COLORS['surface2']} 100%)",
            "borderBottom": f"1px solid {COLORS['border']}",
            "padding": "18px 40px",
            "display": "flex",
            "alignItems": "center",
            "justifyContent": "space-between",
        },
        children=[
            html.Div(
                style={"display": "flex", "alignItems": "center", "gap": "14px"},
                children=[
                    html.Div("◈", style={
                        "fontSize": "28px", "color": COLORS["accent"], "fontWeight": "700",
                    }),
                    html.Span("DataLens", style={
                        "fontSize": "22px", "fontWeight": "700", "letterSpacing": "-0.5px",
                    }),
                    html.Span("Visual Explorer", style={
                        "fontSize": "13px", "color": COLORS["muted"],
                        "marginLeft": "4px", "fontWeight": "400",
                    }),
                ],
            ),
            html.Span(
                "Upload → Inspect → Visualize",
                style={"color": COLORS["muted"], "fontSize": "13px"},
            ),
        ],
    )


def _upload_card():
    return html.Div(
        style=card_style(),
        children=[
            html.H3("① Upload your data", style={
                "marginTop": "0", "marginBottom": "16px",
                "fontWeight": "600", "fontSize": "17px",
            }),
            dcc.Upload(
                id="upload-data",
                children=html.Div(
                    [
                        html.Div("⬆", style={
                            "fontSize": "32px", "marginBottom": "8px",
                            "color": COLORS["accent"],
                        }),
                        html.Div("Drag & drop or click to select", style={
                            "fontWeight": "500", "marginBottom": "4px",
                        }),
                        html.Div("Supports .csv, .xlsx, .xls", style={
                            "fontSize": "12px", "color": COLORS["muted"],
                        }),
                    ],
                    style={"textAlign": "center"},
                ),
                style={
                    "border": f"2px dashed {COLORS['border']}",
                    "borderRadius": "12px",
                    "padding": "40px 20px",
                    "cursor": "pointer",
                    "transition": "border-color 0.2s",
                    "background": COLORS["surface2"],
                },
                multiple=False,
            ),
            html.Div(id="file-name", style={"marginTop": "12px"}),
            html.Button(
                "Read & Analyze",
                id="btn-read",
                n_clicks=0,
                style={
                    "marginTop": "16px",
                    "padding": "10px 28px",
                    "background": f"linear-gradient(135deg, {COLORS['accent']}, #8B83FF)",
                    "color": "#fff",
                    "border": "none",
                    "borderRadius": "8px",
                    "fontWeight": "600",
                    "fontSize": "14px",
                    "cursor": "pointer",
                    "fontFamily": "'DM Sans', sans-serif",
                },
            ),
        ],
    )