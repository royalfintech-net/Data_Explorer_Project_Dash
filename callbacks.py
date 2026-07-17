"""
callbacks.py — All Dash callbacks (upload display, read/analyze, chart creation).

Chart flow: pick a chart type (dropdown) → choose that chart's columns and
options → Create Chart renders it. Changing the chart type afterwards
re-renders using the new type's own column selections.
"""

import io
import math
import traceback

import pandas as pd
import plotly.graph_objects as go
from dash import dcc, html, dash_table, Input, Output, State, no_update

from config import COLORS, CHART_COLORS, PLOTLY_TEMPLATE, card_style
from utils import parse_upload, try_parse_datetime, coerce_datetime_columns


def register_callbacks(app):
    """Register every callback with the given Dash *app*.

    Called once from app.py at import time so Dash discovers the callbacks.
    """

    # ── Show filename after upload ────────────────────────────────────────
    @app.callback(
        Output("file-name", "children"),
        Input("upload-data", "filename"),
    )
    def show_filename(filename):
        if filename is None:
            return ""
        return html.Div(
            [
                html.Span("📄 ", style={"marginRight": "6px"}),
                html.Span(filename, style={"fontWeight": "500"}),
            ],
            style={
                "color": COLORS["accent2"],
                "fontSize": "13px",
                "display": "flex",
                "alignItems": "center",
            },
        )

    # ── Read & Analyze ────────────────────────────────────────────────────
    @app.callback(
        Output("store-data", "data"),
        Output("store-columns", "data"),
        Output("status-msg", "children"),
        Output("schema-section", "children"),
        Output("chart-controls", "children"),
        Output("data-preview", "children"),
        Output("charts-section", "children", allow_duplicate=True),
        Input("btn-read", "n_clicks"),
        State("upload-data", "contents"),
        State("upload-data", "filename"),
        prevent_initial_call=True,
    )
    def read_file(n_clicks, contents, filename):
        if contents is None:
            return (
                no_update, no_update,
                html.Div("⚠ No file uploaded yet.", style={
                    "color": COLORS["danger"], "marginBottom": "16px", "fontSize": "14px",
                }),
                no_update, no_update, no_update, no_update,
            )

        try:
            df = parse_upload(contents, filename)
        except Exception:
            return (
                no_update, no_update,
                html.Div(
                    f"⚠ Error reading file: {traceback.format_exc(limit=1)}",
                    style={"color": COLORS["danger"], "marginBottom": "16px",
                           "fontSize": "13px", "whiteSpace": "pre-wrap"},
                ),
                no_update, no_update, no_update, no_update,
            )

        df = coerce_datetime_columns(df)

        numeric_cols = df.select_dtypes(include="number").columns.tolist()
        all_cols = df.columns.tolist()

        schema_card = _build_schema_card(df, all_cols)
        controls = _build_chart_controls(all_cols, numeric_cols)
        preview = _build_preview_table(df)

        status = html.Div(
            f"✓ Successfully loaded {filename}  —  {len(df)} rows × {len(all_cols)} columns",
            style={"color": COLORS["accent2"], "marginBottom": "16px",
                   "fontSize": "14px", "fontWeight": "500"},
        )

        return (
            df.to_json(date_format="iso", orient="split"),
            {"all": all_cols, "numeric": numeric_cols},
            status,
            schema_card,
            controls,
            preview,
            html.Div(),  # clear any chart from a previous file
        )

    # ── Show only the active chart type's options ─────────────────────────
    @app.callback(
        Output("opts-line", "style"),
        Output("opts-bar", "style"),
        Output("opts-pie", "style"),
        Input("chart-type", "value"),
        prevent_initial_call=True,
    )
    def switch_options(chart_type):
        show, hide = {"display": "block"}, {"display": "none"}
        return (
            show if chart_type == "line" else hide,
            show if chart_type == "bar" else hide,
            show if chart_type == "pie" else hide,
        )  # nothing selected yet → all three stay hidden

    # ── Create / switch chart ─────────────────────────────────────────────
    @app.callback(
        Output("charts-section", "children"),
        Input("btn-chart", "n_clicks"),
        Input("chart-type", "value"),
        State("store-data", "data"),
        State("dd-line-x", "value"),
        State("dd-line-y", "value"),
        State("rd-line-style", "value"),
        State("dd-bar-x", "value"),
        State("dd-bar-y", "value"),
        State("dd-bar-agg", "value"),
        State("dd-bar-topn", "value"),
        State("rd-bar-orient", "value"),
        State("dd-pie", "value"),
        State("dd-pie-value", "value"),
        State("dd-pie-topn", "value"),
        State("chk-pie-donut", "value"),
        prevent_initial_call=True,
    )
    def create_chart(n_clicks, chart_type, json_data,
                     line_x, line_y, line_style,
                     bar_x, bar_y, bar_agg, bar_topn, bar_orient,
                     pie_col, pie_value, pie_topn, pie_donut):
        # Dash fires this once when the freshly rendered controls mount, and
        # again on tab switches. Render nothing until the user has explicitly
        # created a chart at least once (n_clicks resets with each new upload).
        if not n_clicks:
            return no_update
        if json_data is None:
            return _chart_warning("No data loaded — upload a file and click Read & Analyze first.")
        if not chart_type:
            return _chart_warning("Select a chart type first.")

        df = pd.read_json(io.StringIO(json_data), orient="split")

        if chart_type == "line":
            line_y = [line_y] if isinstance(line_y, str) else list(line_y or [])
            if not (line_x and line_y):
                return _chart_warning("Select an X-axis and at least one Y column for the line chart.")
            fig = _make_line_chart(df, line_x, line_y, style=line_style or "markers")

        elif chart_type == "bar":
            bar_y = [bar_y] if isinstance(bar_y, str) else list(bar_y or [])
            bar_y = [c for c in bar_y if c != bar_x]
            if not bar_x:
                return _chart_warning("Select a category column for the bar chart.")
            if bar_agg != "count" and not bar_y:
                return _chart_warning("Select at least one value column (or set aggregation to Count).")
            fig = _make_bar_chart(df, bar_x, bar_y, agg=bar_agg or "sum",
                                  top_n=bar_topn if bar_topn is not None else 25,
                                  orientation=bar_orient or "v")

        else:  # pie
            if not pie_col:
                return _chart_warning("Select a slice column for the pie chart.")
            fig = _make_pie_chart(df, pie_col, value_col=pie_value,
                                  top_n=pie_topn or 11,
                                  donut=bool(pie_donut))

        return html.Div(children=[
            html.H3("④ Chart", style={
                "marginBottom": "6px", "fontWeight": "600", "fontSize": "17px",
            }),
            html.Div(
                "Switch the chart type in ③ any time — the chart updates instantly.",
                style={"color": COLORS["muted"], "fontSize": "13px", "marginBottom": "14px"},
            ),
            html.Div(style=card_style(), children=[
                dcc.Graph(figure=fig, config={"displayModeBar": True, "displaylogo": False}),
            ]),
        ])


# ══════════════════════════════════════════════════════════════════════════════
# Private helpers — build sub-components returned by callbacks
# ══════════════════════════════════════════════════════════════════════════════

def _chart_warning(msg):
    return html.Div(f"⚠ {msg}", style={
        "color": COLORS["danger"], "fontSize": "14px", "marginBottom": "16px",
    })


def _label_style():
    return {
        "fontSize": "12px", "fontWeight": "600", "color": COLORS["muted"],
        "marginBottom": "6px", "display": "block",
        "textTransform": "uppercase", "letterSpacing": "0.5px",
    }


# ── Schema card ───────────────────────────────────────────────────────────────
def _build_schema_card(df, all_cols):
    schema_rows = []
    for col in all_cols:
        non_null = int(df[col].notna().sum())
        sample = str(df[col].dropna().iloc[0]) if non_null > 0 else "—"
        if len(sample) > 40:
            sample = sample[:40] + "…"
        schema_rows.append({
            "Column": col,
            "Type": str(df[col].dtype),
            "Non-Null": non_null,
            "Nulls": int(df[col].isna().sum()),
            "Unique": int(df[col].nunique()),
            "Sample": sample,
        })

    return html.Div(style=card_style(), children=[
        html.H3("② Data Schema", style={
            "marginTop": "0", "marginBottom": "6px",
            "fontWeight": "600", "fontSize": "17px",
        }),
        html.Div(f"{len(df)} rows  ×  {len(all_cols)} columns", style={
            "color": COLORS["muted"], "fontSize": "13px", "marginBottom": "16px",
        }),
        dash_table.DataTable(
            data=schema_rows,
            columns=[{"name": c, "id": c} for c in schema_rows[0].keys()],
            style_table={"overflowX": "auto"},
            style_header={
                "backgroundColor": COLORS["surface2"],
                "color": COLORS["text"],
                "fontWeight": "600", "fontSize": "12px",
                "textTransform": "uppercase", "letterSpacing": "0.5px",
                "border": "none",
                "borderBottom": f"2px solid {COLORS['border']}",
            },
            style_cell={
                "backgroundColor": COLORS["surface"],
                "color": COLORS["text"],
                "border": "none",
                "borderBottom": f"1px solid {COLORS['border']}",
                "fontSize": "13px", "padding": "10px 14px",
                "fontFamily": "'DM Sans', sans-serif",
            },
            style_data_conditional=[{
                "if": {"column_id": "Type"},
                "color": COLORS["accent"],
                "fontFamily": "'DM Mono', monospace",
                "fontSize": "12px",
            }],
        ),
    ])


# ── Chart controls card ──────────────────────────────────────────────────────
def _dropdown_block(label, dd_id, options, value=None, placeholder="Select column…"):
    return html.Div(
        style={"marginBottom": "12px"},
        children=[
            html.Label(label, style=_label_style()),
            dcc.Dropdown(
                id=dd_id,
                options=options if options and isinstance(options[0], dict)
                else [{"label": c, "value": c} for c in options],
                value=value,
                placeholder=placeholder,
                clearable=False,
                style={"fontSize": "13px"},
                className="dash-dropdown",
            ),
        ],
    )


def _column_list_style():
    return {
        "maxHeight": "160px", "overflowY": "auto",
        "border": f"1px solid {COLORS['border']}",
        "borderRadius": "8px", "padding": "8px 12px",
        "background": COLORS["surface"],
    }


def _column_item_styles():
    return dict(
        labelStyle={"display": "block", "fontSize": "13px",
                    "color": COLORS["text"], "cursor": "pointer",
                    "marginBottom": "6px"},
        inputStyle={"marginRight": "8px"},
    )


def _checklist_block(label, chk_id, options):
    """A scrollable list of checkboxes — used for multi-column selection."""
    return html.Div(
        style={"marginBottom": "12px"},
        children=[
            html.Label(label, style=_label_style()),
            html.Div(
                style=_column_list_style(),
                children=[dcc.Checklist(
                    id=chk_id,
                    options=[{"label": f" {c}", "value": c} for c in options],
                    value=[],
                    **_column_item_styles(),
                )],
            ),
        ],
    )


def _radio_list_block(label, rd_id, options):
    """A scrollable list of radio buttons — used for single-column selection."""
    return html.Div(
        style={"marginBottom": "12px"},
        children=[
            html.Label(label, style=_label_style()),
            html.Div(
                style=_column_list_style(),
                children=[dcc.RadioItems(
                    id=rd_id,
                    options=[{"label": f" {c}", "value": c} for c in options],
                    value=None,
                    **_column_item_styles(),
                )],
            ),
        ],
    )


def _radio_block(label, rd_id, options, value):
    return html.Div(
        style={"marginBottom": "12px"},
        children=[
            html.Label(label, style=_label_style()),
            dcc.RadioItems(
                id=rd_id,
                options=options,
                value=value,
                labelStyle={"marginRight": "16px", "fontSize": "13px",
                            "color": COLORS["text"], "cursor": "pointer"},
                inputStyle={"marginRight": "6px"},
            ),
        ],
    )


def _options_grid(children):
    return html.Div(
        style={"display": "grid", "gridTemplateColumns": "1fr 1fr 1fr",
               "gap": "0 20px", "marginTop": "16px"},
        children=children,
    )


def _build_chart_controls(all_cols, numeric_cols):
    # Per-type option panels. All rendered up front (hidden until their chart
    # type is picked) so every control keeps a stable id for create_chart.
    # No column is pre-selected — the user chooses explicitly.
    opts_line = html.Div(id="opts-line", style={"display": "none"}, children=[
        _options_grid([
            _radio_list_block("X-Axis (time / sequence)", "dd-line-x", all_cols),
            _checklist_block("Y-Axis columns (numeric)", "dd-line-y", numeric_cols),
            _radio_block("Style", "rd-line-style", [
                {"label": "Lines + markers", "value": "markers"},
                {"label": "Lines", "value": "lines"},
                {"label": "Area", "value": "area"},
            ], "markers"),
        ]),
    ])

    opts_bar = html.Div(id="opts-bar", style={"display": "none"}, children=[
        _options_grid([
            _radio_list_block("Category (X-Axis)", "dd-bar-x", all_cols),
            _checklist_block("Value columns (Y-Axis, numeric)", "dd-bar-y", numeric_cols),
            html.Div([
                _dropdown_block("Aggregation", "dd-bar-agg", [
                    {"label": "Sum per category", "value": "sum"},
                    {"label": "Average per category", "value": "mean"},
                    {"label": "Count rows", "value": "count"},
                    {"label": "Raw values (no grouping)", "value": "none"},
                ], "sum", placeholder=None),
                _dropdown_block("Show", "dd-bar-topn", [
                    {"label": "Top 10", "value": 10},
                    {"label": "Top 25", "value": 25},
                    {"label": "Top 50", "value": 50},
                    {"label": "All categories", "value": 0},
                ], 25, placeholder=None),
                _radio_block("Orientation", "rd-bar-orient", [
                    {"label": "Vertical", "value": "v"},
                    {"label": "Horizontal", "value": "h"},
                ], "v"),
            ]),
        ]),
    ])

    opts_pie = html.Div(id="opts-pie", style={"display": "none"}, children=[
        _options_grid([
            _radio_list_block("Slice Column (categorical)", "dd-pie", all_cols),
            _dropdown_block("Slice Size", "dd-pie-value",
                            [{"label": "Count of rows", "value": "__count__"}]
                            + [{"label": f"Sum of {c}", "value": c} for c in numeric_cols],
                            "__count__", placeholder=None),
            html.Div([
                _dropdown_block("Slices", "dd-pie-topn", [
                    {"label": "Top 6 + Other", "value": 6},
                    {"label": "Top 11 + Other", "value": 11},
                    {"label": "Top 16 + Other", "value": 16},
                ], 11, placeholder=None),
                html.Div(style={"marginBottom": "12px"}, children=[
                    html.Label("Style", style=_label_style()),
                    dcc.Checklist(
                        id="chk-pie-donut",
                        options=[{"label": " Donut hole", "value": "donut"}],
                        value=["donut"],
                        labelStyle={"fontSize": "13px", "color": COLORS["text"],
                                    "cursor": "pointer"},
                    ),
                ]),
            ]),
        ]),
    ])

    return html.Div(style=card_style(), children=[
        html.H3("③ Configure Chart", style={
            "marginTop": "0", "marginBottom": "6px",
            "fontWeight": "600", "fontSize": "17px",
        }),
        html.Div(
            "Pick a chart type, choose its columns and options, then Create Chart.",
            style={"color": COLORS["muted"], "fontSize": "13px", "marginBottom": "16px"},
        ),
        html.Div(style={"maxWidth": "320px"}, children=[
            _dropdown_block("Chart Type", "chart-type", [
                {"label": "📈 Line Chart", "value": "line"},
                {"label": "📊 Bar Chart", "value": "bar"},
                {"label": "🥧 Pie Chart", "value": "pie"},
            ], placeholder="Select a chart type…"),
        ]),
        opts_line,
        opts_bar,
        opts_pie,
        html.Button(
            "Create Chart", id="btn-chart", n_clicks=0,
            style={
                "marginTop": "8px", "padding": "10px 28px",
                "background": f"linear-gradient(135deg, {COLORS['accent2']}, #00B88C)",
                "color": "#fff", "border": "none", "borderRadius": "8px",
                "fontWeight": "600", "fontSize": "14px", "cursor": "pointer",
                "fontFamily": "'DM Sans', sans-serif",
            },
        ),
    ])


# ── Data preview table ────────────────────────────────────────────────────────
def _build_preview_table(df):
    preview_df = df.head(15)
    return html.Div(style=card_style(), children=[
        html.H3("Data Preview (first 15 rows)", style={
            "marginTop": "0", "marginBottom": "14px",
            "fontWeight": "600", "fontSize": "17px",
        }),
        dash_table.DataTable(
            data=preview_df.to_dict("records"),
            columns=[{"name": c, "id": c} for c in preview_df.columns],
            style_table={"overflowX": "auto"},
            page_size=15,
            style_header={
                "backgroundColor": COLORS["surface2"],
                "color": COLORS["text"],
                "fontWeight": "600", "fontSize": "12px",
                "border": "none",
                "borderBottom": f"2px solid {COLORS['border']}",
            },
            style_cell={
                "backgroundColor": COLORS["surface"],
                "color": COLORS["text"],
                "border": "none",
                "borderBottom": f"1px solid {COLORS['border']}",
                "fontSize": "12px", "padding": "8px 12px",
                "fontFamily": "'DM Sans', sans-serif",
                "maxWidth": "200px", "overflow": "hidden",
                "textOverflow": "ellipsis",
            },
        ),
    ])


# ── Chart builders ────────────────────────────────────────────────────────────
def _is_plottable_axis(series):
    return (
        pd.api.types.is_numeric_dtype(series)
        or pd.api.types.is_datetime64_any_dtype(series)
    )


def _make_line_chart(df, x_col, y_cols, style="markers"):
    x = df[x_col]
    # Dates arrive as ISO strings after the JSON round-trip through dcc.Store.
    if not _is_plottable_axis(x):
        parsed = try_parse_datetime(x)
        if parsed is not None:
            x = parsed
    # A line chart only makes sense with X in order; sort when X is sortable.
    if _is_plottable_axis(x):
        order = x.sort_values(na_position="last").index
        x = x.loc[order]
        df = df.loc[order]

    # Metrics on wildly different scales (e.g. market cap vs. price) drown
    # each other out on one axis — move outliers to a secondary right axis.
    medians = {c: float(df[c].abs().median() or 0) for c in y_cols}
    base = medians[y_cols[0]]
    right_cols = {
        c for c in y_cols[1:]
        if base > 0 and medians[c] > 0 and abs(math.log10(medians[c] / base)) >= 2
    }

    mode = "lines" if style in ("lines", "area") else "lines+markers"
    fig = go.Figure()
    for i, col in enumerate(y_cols):
        fig.add_trace(go.Scatter(
            x=x, y=df[col], mode=mode, name=col,
            yaxis="y2" if col in right_cols else "y",
            fill="tozeroy" if style == "area" else None,
            line=dict(width=2.5, color=CHART_COLORS[i % len(CHART_COLORS)]),
            marker=dict(size=5),
        ))

    title = "Line Chart"
    layout_extra = {}
    if right_cols:
        title = "Line Chart — dual axis (scales differ)"
        layout_extra["yaxis2"] = dict(
            title=", ".join(c for c in y_cols if c in right_cols),
            overlaying="y", side="right",
            showgrid=False, zeroline=False,
        )
        layout_extra["yaxis"] = dict(
            title=", ".join(c for c in y_cols if c not in right_cols),
        )
    fig.update_layout(
        title=dict(text=title, font=dict(size=16, color=COLORS["text"])),
        template=PLOTLY_TEMPLATE, hovermode="x unified", xaxis_title=x_col,
        **layout_extra,
    )
    return fig


def _make_bar_chart(df, x_col, y_cols, agg="sum", top_n=25, orientation="v"):
    if agg == "count":
        plot_df = df.groupby(x_col, dropna=False, sort=False).size().reset_index(name="count")
        y_cols = ["count"]
        title = "Bar Chart — row count per category"
    elif agg in ("sum", "mean") and df[x_col].duplicated().any():
        plot_df = df.groupby(x_col, dropna=False, sort=False)[y_cols].agg(agg).reset_index()
        title = f"Bar Chart — {'sum' if agg == 'sum' else 'average'} per category"
    else:
        plot_df = df
        title = "Bar Chart"

    if top_n and len(plot_df) > top_n:
        plot_df = plot_df.nlargest(top_n, y_cols[0])
        title += f" (top {top_n} by {y_cols[0]})"

    horizontal = orientation == "h"
    if horizontal:
        plot_df = plot_df.iloc[::-1]  # largest bar at the top

    fig = go.Figure()
    for i, col in enumerate(y_cols):
        fig.add_trace(go.Bar(
            x=plot_df[col] if horizontal else plot_df[x_col],
            y=plot_df[x_col] if horizontal else plot_df[col],
            orientation="h" if horizontal else "v",
            name=col,
            marker_color=CHART_COLORS[i % len(CHART_COLORS)], opacity=0.88,
        ))
    fig.update_layout(
        title=dict(text=title, font=dict(size=16, color=COLORS["text"])),
        template=PLOTLY_TEMPLATE, barmode="group",
        xaxis_title=y_cols[0] if horizontal and len(y_cols) == 1 else (None if horizontal else x_col),
        yaxis_title=x_col if horizontal else None,
        height=max(450, 26 * len(plot_df) + 140) if horizontal else None,
    )
    return fig


def _make_pie_chart(df, pie_col, value_col=None, top_n=11, donut=True):
    if value_col and value_col != "__count__":
        counts = (
            df.groupby(pie_col, dropna=False)[value_col]
            .sum().sort_values(ascending=False)
        )
        title = f"Pie Chart — sum of {value_col} by {pie_col}"
    else:
        counts = df[pie_col].value_counts()
        title = f"Pie Chart — count by {pie_col}"

    top = counts.head(top_n)
    labels = top.index.astype(str).tolist()
    values = [float(v) for v in top.values]
    remainder = float(counts.iloc[top_n:].sum())
    if remainder > 0:
        labels.append(f"Other ({len(counts) - len(top)} values)")
        values.append(remainder)

    fig = go.Figure(data=[go.Pie(
        labels=labels, values=values,
        hole=0.45 if donut else 0,
        marker=dict(colors=CHART_COLORS),
        textinfo="label+percent", textfont=dict(size=12),
    )])
    fig.update_layout(
        title=dict(text=title, font=dict(size=16, color=COLORS["text"])),
        template=PLOTLY_TEMPLATE,
    )
    return fig
