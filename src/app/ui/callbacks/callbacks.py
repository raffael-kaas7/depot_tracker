"""
Callbacks for the Depot Tracker application
"""
from dash import Output, Input, callback_context, dash_table, html, dcc
import dash_bootstrap_components as dbc
import pandas as pd
import numpy as np
import datetime as dt
from zoneinfo import ZoneInfo
import plotly.express as px

from app.services.depot_service import DepotService
from app.services.dividend_service import DividendService
from app.api.comdirect_api import ComdirectAPI
from app.services.data_service import DataManager
from app.ui.components.layout import create_summary_row
from app.ui.components.charts import create_allocation_pie_chart, create_historical_depot_chart, create_combined_historical_chart
from config.settings import get_settings


def register_callbacks(app):
    """Register all callbacks with the app"""
    
    settings = get_settings()
    
    # Initialize APIs and services (same as original app.py)
    DEPOT_1_NAME = settings.DEPOT_1_NAME
    DEPOT_2_NAME = settings.DEPOT_2_NAME
    
    api_cd_1 = ComdirectAPI(
        username=settings.USERNAME_1,
        pw=settings.PASSWORD_1,
        depot_name=DEPOT_1_NAME,
        session_id="comdirect-active-depot",
        request_id="000001",
    )
    api_cd_2 = ComdirectAPI(
        username=settings.USERNAME_2,
        pw=settings.PASSWORD_2,
        depot_name=DEPOT_2_NAME,
        session_id="comdirect-dividend-depot",
        request_id="000002",
    )
    
    # Raw Data handling objects
    data_cd_1 = DataManager(depot_name=api_cd_1.get_name())
    data_cd_2 = DataManager(depot_name=api_cd_2.get_name())
    
    # Service objects for specific KPIs
    service_cd_1 = DepotService(data_cd_1)
    service_cd_2 = DepotService(data_cd_2)
    
    # Dividend service for cross-depot dividend calculations
    dividend_service = DividendService([service_cd_1, service_cd_2])
    
    # Register services in global registry for scheduler access
    from app.services.service_registry import registry
    registry.register_services(data_cd_1, data_cd_2, service_cd_1, service_cd_2)
    
    BERLIN_TZ = ZoneInfo("Europe/Berlin")
    
    # ---------------------------
    # Sidebar section switching
    # ---------------------------
    @app.callback(
        Output("assets-section", "style"),
        Output("allocation-section", "style"),
        Output("dividends-section", "style"), 
        Output("nav-assets", "active"),
        Output("nav-allocation", "active"),
        Output("nav-dividends", "active"),
        Input("nav-assets", "n_clicks"),
        Input("nav-allocation", "n_clicks"),
        Input("nav-dividends", "n_clicks"),
    )
    def switch_sections(n_assets, n_allocation, n_divs):
        # default to assets on initial load
        ctx = callback_context
        which = "assets"
        if ctx.triggered:
            trigger_id = ctx.triggered[0]["prop_id"]
            if trigger_id.startswith("nav-assets"):
                which = "assets"
            elif trigger_id.startswith("nav-allocation"):
                which = "allocation"
            elif trigger_id.startswith("nav-dividends"):
                which = "dividends"
        
        if which == "assets":
            return {"display": "block"}, {"display": "none"}, {"display": "none"}, True, False, False
        elif which == "allocation":
            return {"display": "none"}, {"display": "block"}, {"display": "none"}, False, True, False
        else:  # dividends
            return {"display": "none"}, {"display": "none"}, {"display": "block"}, False, False, True
    
    # ---------------------------
    # Sync buttons (separate fns)
    # ---------------------------
    @app.callback(
        Output("auth-status-cd1", "children"),
        Input("auth-button-cd1", "n_clicks"),
        prevent_initial_call=True,
    )
    def sync_depot_1(n_clicks):
        try:
            # authenticate and update data
            api_cd_1.authenticate()
            data_cd_1.update_data()
            return dbc.Alert("Depot 1: Authentication & sync successful.", color="success", className="mt-2 py-2")
        except Exception as e:
            return dbc.Alert(f"Depot 1: Authentication failed — {e}", color="danger", className="mt-2 py-2")
    
    @app.callback(
        Output("auth-status-cd2", "children"),
        Input("auth-button-cd2", "n_clicks"),
        prevent_initial_call=True,
    )
    def sync_depot_2(n_clicks):
        try:
            # authenticate and update data
            api_cd_2.authenticate()
            data_cd_2.update_data()
            return dbc.Alert("Depot 2: Authentication & sync successful.", color="success", className="mt-2 py-2")
        except Exception as e:
            return dbc.Alert(f"Depot 2: Authentication failed — {e}", color="danger", className="mt-2 py-2")
    
    # Helper functions
    def momentum_display(x: float) -> str:
        if x is None or pd.isna(x): return "—"
        if x >= 0.10: arrow = "▲"
        elif x >= 0.03: arrow = "↗"
        elif x <= -0.10: arrow = "▼"
        elif x <= -0.03: arrow = "↘"
        else: arrow = "→"
        return f"{arrow}"
    
    def process_depot(positions: pd.DataFrame, title: str, summary=True):
        if positions is None or positions.empty:
            return html.Div([html.H4(title), dbc.Alert("No positions to display. Authenticate and sync depots first (Sync Depot 1, Sync Depot 2)", color="secondary")])

        # totals
        total_purchase_value = positions["purchase_value"].sum()
        total_value = positions["current_value"].sum()
        capital_gain = total_value - total_purchase_value
        performance = ((total_value - total_purchase_value) / total_purchase_value) * 100 if total_purchase_value else 0

        # momentum
        if "momentum_3m" not in positions.columns:
            positions["momentum_3m"] = np.nan
        positions["momentum_3m_disp"] = positions["momentum_3m"].map(momentum_display)

        # render table with compact column headers for better space usage
        show_cols = [
            ("name","Name"), ("count","Quantity"),
            ("purchase_price","Price"), ("current_price","Price Now"),
            ("purchase_value","Invested €"), ("current_value","Curr. Value"),
            ("performance_%","Performance %"), ("absolute_gain_loss","Abs. Diff"),
            ("percentage_in_depot","Allocation %"),
            ("total_dividends","Tot. Dividends"), ("momentum_3m_disp","3M-Mom")
        ]
        cols = [c for c,_ in show_cols if c in positions.columns]
        
        # Create column definitions with English/US number formatting
        table_columns = []
        for c, n in show_cols:
            if c in positions.columns:
                column_def = {"name": n, "id": c}
                
                # Add number formatting for different column types
                if c in ["purchase_price", "current_price", "purchase_value", "current_value", "absolute_gain_loss", "total_dividends"]:
                    # Currency formatting with English/US locale (, for thousands, . for decimals)
                    column_def.update({
                        "type": "numeric",
                        "format": {"specifier": ",.2f"}
                    })
                elif c in ["performance_%", "percentage_in_depot"]:
                    # Percentage formatting
                    column_def.update({
                        "type": "numeric", 
                        "format": {"specifier": ",.2f"}
                    })
                elif c == "count":
                    # Integer formatting for quantities
                    column_def.update({
                        "type": "numeric",
                        "format": {"specifier": ",.0f"}
                    })
                
                table_columns.append(column_def)
        
        table = dash_table.DataTable(
            columns=table_columns,
            data=positions[cols].to_dict("records"),
            sort_action="native",
            sort_by=[{"column_id": "percentage_in_depot", "direction": "desc"}] if "percentage_in_depot" in cols else [],
            style_table={"overflowX": "auto", "borderRadius": "5px"},
            style_data_conditional=[
                {"if": {"column_id": "performance_%", "filter_query": "{performance_%} < 0"}, "color": "#ff6b6b"},
                {"if": {"column_id": "performance_%", "filter_query": "{performance_%} >= 0"}, "color": "#1dd1a1"},
                {"if": {"column_id": "absolute_gain_loss", "filter_query": "{absolute_gain_loss} < 0"}, "color": "#ff6b6b"},
                {"if": {"column_id": "absolute_gain_loss", "filter_query": "{absolute_gain_loss} >= 0"}, "color": "#1dd1a1"},
                {"if": {"column_id": "momentum_3m_disp", "filter_query": "{momentum_3m} >= 0.10"}, "color": "#1dd1a1"},
                {"if": {"column_id": "momentum_3m_disp", "filter_query": "{momentum_3m} >= 0.03 && {momentum_3m} < 0.10"}, "color": "#10ac84"},
                {"if": {"column_id": "momentum_3m_disp", "filter_query": "{momentum_3m} > -0.03 && {momentum_3m} < 0.03"}, "color": "#c8d6e5"},
                {"if": {"column_id": "momentum_3m_disp", "filter_query": "{momentum_3m} <= -0.03 && {momentum_3m} > -0.10"}, "color": "#ff9f43"},
                {"if": {"column_id": "momentum_3m_disp", "filter_query": "{momentum_3m} <= -0.10"}, "color": "#ff6b6b"},
            ],
        )

        if not summary:
            return html.Div([html.H4(title), table])

        summary_div = create_summary_row([
            {"icon": "💰", "label": "Current Value", "value": f"{total_value:,.0f} €", "color": "light"},
            {"icon": "💲", "label": "Capital Gain", "value": f"{capital_gain:,.0f} €", "color": "#1dd1a1" if performance > 0 else "#ff6b6b"},
            {"icon": "📈", "label": "Performance", "value": f"{performance:.1f} %", "color": "#1dd1a1" if performance > 0 else "#ff6b6b"},
            {"icon": "🏷️", "label": "Invested Capital", "value": f"{total_purchase_value:,.0f} €", "color": "light"},
        ])

        return html.Div([html.H4(title), summary_div, table, html.Br()])
    
    # ---------------------------
    # Assets: positions table(s)
    # ---------------------------
    @app.callback(
        Output("depot-table", "children"),
        Input("table-switch", "value"),
    )
    def render_depot_table(table_mode):
        try:
            pos1 = service_cd_1.get_positions()
        except Exception:
            pos1 = pd.DataFrame()
        try:
            pos2 = service_cd_2.get_positions()
        except Exception:
            pos2 = pd.DataFrame()

        if pos1 is None: pos1 = pd.DataFrame()
        if pos2 is None: pos2 = pd.DataFrame()

        # allocation for combined
        all_pos = pd.concat([pos1, pos2], ignore_index=True) if not pos1.empty or not pos2.empty else pd.DataFrame()
        if not all_pos.empty and "current_value" in all_pos.columns:
            total_current_value = all_pos["current_value"].sum()
            if total_current_value:
                all_pos["percentage_in_depot"] = (all_pos["current_value"] / total_current_value * 100).round(2)

        if table_mode == True:  # separated
            return html.Div([
                process_depot(pos1, DEPOT_1_NAME or "Depot 1"),
                process_depot(pos2, DEPOT_2_NAME or "Depot 2"),
            ])
        else:
            return html.Div([
                process_depot(all_pos, f"{DEPOT_1_NAME} + {DEPOT_2_NAME}", summary=True)
            ])

    # ---------------------------
    # Dividends
    # ---------------------------
    @app.callback(
        Output("dividend-chart", "figure"),
        Output("dividend-summary", "children"),
        Input("dividend-chart", "id"),  # Trigger the callback when the chart is loaded
    )
    def show_dividend_chart(_):
        # Get chart data from service
        chart_data = dividend_service.get_monthly_chart_data()
        stats = dividend_service.get_dividend_statistics()
        
        if not chart_data["monthly_data"]:
            fig = px.bar(pd.DataFrame({"month_name": [], "amount": [], "year": []}), 
                        x="month_name", y="amount", color="year")
            return fig, html.Div("No dividend data available.", className="text-muted")

        # Create chart
        monthly_df = pd.DataFrame(chart_data["monthly_data"])
        fig = px.bar(monthly_df, x="month_name", y="amount", color="year", barmode="group",
                     labels={"amount": "Dividends in €", "month_name": "Month", "year": "Year"},
                     height=450)
        fig.update_layout(paper_bgcolor="#0b1e25", plot_bgcolor="#0b1e25", font_color="#e5e5e5", font_size=14,
                          margin=dict(l=20, r=20, t=40, b=20))

        # Create summary using statistics from service
        summary = html.Div([
            html.Div(f"All time Dividends: {stats['total']:.0f} €", 
                     style={"margin-bottom": "10px", "font-weight": "bold"}),
            html.Div(f"Monthly Average (Last 12 Months): {stats['avg_12_months']:.0f} €", 
                    style={"margin-bottom": "20px", "font-weight": "bold"}),
            *[
                html.Div(
                    [
                        html.Span(
                            f"📅 {int(year)}: {amt:.0f} €" + 
                            (f" (+{change:.1f}%)" if change and change > 0 else 
                             f" ({change:.1f}%)" if change and change < 0 else ""),
                            style={"margin-right": "30px"}
                        )
                        for year, amt, change in stats['year_changes'][i:i+3]
                    ],
                    style={"margin-bottom": "5px",}
                )
                for i in range(0, len(stats['year_changes']), 3)
            ]
        ], style={"text-align": "left", "list-style-type": "none", "padding": "0"})
        return fig, summary

    # RAW dividend table — ALWAYS visible
    @app.callback(
        Output("dividend-table-container", "children"),
        Input("dividend-chart", "id"),  # Trigger the callback when the chart is loaded
    )
    def render_dividend_table(_):
        dividends = dividend_service.get_all_dividends()
        
        if not dividends:
            return dbc.Alert("No dividend data available.", color="secondary")

        df = pd.DataFrame(dividends)
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df = df.dropna(subset=["date"]).sort_values("date", ascending=False)
        
        # Format date column to show only date (YYYY-MM-DD) without time
        df["date"] = df["date"].dt.strftime("%Y-%m-%d")

        table = dash_table.DataTable(
            columns=[{"name":"Date","id":"date"},{"name":"Company","id":"company"},{"name":"Net amount (€)","id":"amount"}],
            data=df.to_dict("records"),
            style_table={"overflowX":"auto"},
            page_size=12, sort_action="native", filter_action="native",
        )
        return table

    # ---------------------------
    # Allocation section callbacks
    # ---------------------------
    
    def _get_combined_positions():
        """Helper function to get combined positions from both depots."""
        # Update prices for both depots
        data_cd_1.update_prices()
        data_cd_2.update_prices()
        
        # Get positions from both services (already processed and enriched)
        positions_cd_1 = service_cd_1.get_positions()
        positions_cd_2 = service_cd_2.get_positions()
        
        # Combine the positions
        if not positions_cd_1.empty and not positions_cd_2.empty:
            combined = pd.concat([positions_cd_1, positions_cd_2], ignore_index=True)
        elif not positions_cd_1.empty:
            combined = positions_cd_1
        elif not positions_cd_2.empty:
            combined = positions_cd_2
        else:
            combined = pd.DataFrame()
        
        return combined

    @app.callback(
        Output("asset-class-pie", "figure"),
        Input("allocation-section", "id"),  # Trigger when allocation section is accessed
    )
    def update_asset_class_pie(_):
        combined_positions = _get_combined_positions()
        return create_allocation_pie_chart(combined_positions, 'asset_class', 'Asset Class')

    @app.callback(
        Output("sector-pie", "figure"),
        Input("allocation-section", "id"),
    )
    def update_sector_pie(_):
        combined_positions = _get_combined_positions()
        return create_allocation_pie_chart(combined_positions, 'sector', 'Sector')

    @app.callback(
        Output("region-pie", "figure"),
        Input("allocation-section", "id"),
    )
    def update_region_pie(_):
        combined_positions = _get_combined_positions()
        return create_allocation_pie_chart(combined_positions, 'region', 'Region')

    @app.callback(
        Output("risk-pie", "figure"),
        Input("allocation-section", "id"),
    )
    def update_risk_pie(_):
        combined_positions = _get_combined_positions()
        return create_allocation_pie_chart(combined_positions, 'risk_estimation', 'Pers. Risk Estimation')

    @app.callback(
        Output("historical-charts-container", "children"),
        Input("table-switch", "value"),  # React to table mode changes
        Input("assets-section", "id"),   # Also trigger when assets section is accessed
    )
    def update_historical_charts(table_mode, _):
        """Update the historical charts based on table mode (separated vs combined)."""
        # Get snapshot data for both depots
        depot_1_snapshots = data_cd_1.get_snapshot_data()
        depot_2_snapshots = data_cd_2.get_snapshot_data()
        
        # Prepare data structure
        snapshots_data = {}
        if depot_1_snapshots:
            snapshots_data[DEPOT_1_NAME] = depot_1_snapshots
        if depot_2_snapshots:
            snapshots_data[DEPOT_2_NAME] = depot_2_snapshots
        
        if not snapshots_data:
            return dbc.Alert("No historical data available. Data will appear after synchronization.", 
                           color="secondary", className="mt-3")
        
        # Check table mode: True = Separated Depots, False = Combined View
        if table_mode:  # Separated view - show individual charts
            charts = []
            
            # Create individual charts for each depot
            if DEPOT_1_NAME in snapshots_data:
                fig1 = create_historical_depot_chart(
                    {DEPOT_1_NAME: snapshots_data[DEPOT_1_NAME]}, 
                    f"{DEPOT_1_NAME}",
                    show_invested_capital=True  # Include invested capital (toggleable via legend)
                )
                charts.append(
                    dbc.Col([
                        dcc.Graph(figure=fig1, className="mb-3")
                    ], lg=6, md=12)
                )
            
            if DEPOT_2_NAME in snapshots_data:
                fig2 = create_historical_depot_chart(
                    {DEPOT_2_NAME: snapshots_data[DEPOT_2_NAME]}, 
                    f"{DEPOT_2_NAME}",
                    show_invested_capital=True  # Include invested capital (toggleable via legend)
                )
                charts.append(
                    dbc.Col([
                        dcc.Graph(figure=fig2, className="mb-3")
                    ], lg=6, md=12)
                )
            
            return dbc.Row(charts, className="g-3")
            
        else:  # Combined view - show single combined chart
            fig_combined = create_combined_historical_chart(
                snapshots_data, 
                "Combined Portfolio - Historical Performance",
                show_invested_capital=True  # Include invested capital (toggleable via legend)
            )
            
            return dbc.Row([
                dbc.Col([
                    dcc.Graph(figure=fig_combined, className="mb-3")
                ], width=12)
            ])
