import dash
from dash import dcc, html, Output, Input, State, ctx
import plotly.graph_objs as go
import re
import numpy as np
import pandas as pd
from data_utils import list_csv_files, load_data_from_csv, save_data_to_csv
from gpx_utils import x_data, y_data, lat_data, lon_data, segmenteer_route, calc_etappes, tempo_str_to_min, team_kleuren, teamleden

def register_callbacks(app):

    @app.callback(
        Output("show-new-file-modal", "data"),
        Input("open-new-file-modal", "n_clicks"),
        Input("confirm-new-file", "n_clicks"),
        Input("cancel-new-file", "n_clicks"),
        prevent_initial_call=True
    )
    def toggle_modal(open_click, confirm_click, cancel_click):
        triggered_id = ctx.triggered_id

        if triggered_id == "open-new-file-modal":
            return True
        return False

    @app.callback(
        Output("new-file-modal", "style"),
        Input("show-new-file-modal", "data")
    )
    def show_hide_modal(show):
        if show:
            return {"display": "block", "position": "fixed", "top": "0", "left": "0", "width": "100%", "height": "100%", "backgroundColor": "rgba(0,0,0,0.4)", "zIndex": "1000"}
        return {"display": "none"}

    @app.callback(
        Output("hoogtegrafiek", "figure"),
        Input("grens-store", "data"),
        Input("team-store", "data")
    )
    def update_figure(grenzen, team_data):
        team_data = team_data or {}
        fig = go.Figure()

        grenzen = [0] + sorted(grenzen) + [x_data[-1]]
        legend_shown = set()

        for i in range(len(grenzen) - 1):
            start = grenzen[i]
            end = grenzen[i + 1]
            mask = (np.array(x_data) >= start) & (np.array(x_data) <= end)

            etappe_id = f"Etappe {i + 1}"
            naam = team_data.get(etappe_id)
            kleur = team_kleuren.get(naam, "black")

            showlegend = kleur != "black" and naam not in legend_shown
            if showlegend:
                legend_shown.add(naam)

            fig.add_trace(go.Scatter(
                x=np.array(x_data)[mask],
                y=np.array(y_data)[mask],
                mode='lines',
                line=dict(color=kleur, width=3),
                name=naam if naam else "Niet toegewezen",
                showlegend=showlegend,
                legendgroup=naam if naam else "onbekend"
            ))

        shapes = []
        annotations = []
        for gx in sorted(grenzen[1:-1]):
            shapes.append({
                "type": "line",
                "x0": gx,
                "x1": gx,
                "y0": min(y_data),
                "y1": max(y_data),
                "line": {"color": "grey", "width": 2, "dash": "dot"},
                "editable": True
            })

            annotations.append(dict(
                x=gx,
                y=max(y_data) + 70,
                text=f"{gx:.1f} km",
                textangle=270,
                showarrow=False,
                font=dict(size=10, color="black"),
                xanchor="center"
            ))

        fig.update_layout(
            height=600,
            xaxis_title="Afstand (km)",
            yaxis_title="Hoogte (m)",
            shapes=shapes,
            annotations=annotations,
            margin=dict(t=40, r=10, l=10, b=40),
            title="Hoogtegrafiek",
            legend=dict(
                x=1,
                y=0.87,
                xanchor="right",
                yanchor="top",
                bgcolor="rgba(255,255,255,0.7)",
                bordercolor="lightgrey",
                borderwidth=1
            )
        )

        return fig




    @app.callback(
        Output("etappe-resultaten", "children"),
        Input("grens-store", "data"),
        Input("team-store", "data"),
        Input("tempo-store", "data"),
        Input("opmerking-store", "data")
    )
    def update_tabel(grenzen, team_data, tempo_data, opmerkingen):
        resultaten = calc_etappes(x_data, y_data, grenzen)
        team_data = team_data or {}
        tempo_data = tempo_data or {}
        opmerkingen = opmerkingen or {}

        def cell_style():
            return {"padding": "8px", "border": "1px solid #ddd"}

        header_style = {
            "backgroundColor": "#0074D9",
            "color": "white",
            "padding": "8px",
            "border": "1px solid #ddd",
            "textAlign": "left"
        }

        rows = []
        totaal_min = 0

        for r in resultaten:
            etappe = r['Etappe']
            afstand = r['Afstand (km)']
            tempo_str = tempo_data.get(etappe, "")
            tempo_min = tempo_str_to_min(tempo_str) if tempo_str else None

            tijd = tempo_min * afstand if tempo_min else None
            totaal_min += tijd if tijd else 0

            tijd_str = f"{int(tijd // 60)}:{int(tijd % 60):02d}" if tijd else ""
            cum_str = f"{int(totaal_min // 60)}:{int(totaal_min % 60):02d}" if tijd else ""

            rows.append(html.Tr([
                html.Td(etappe, style=cell_style()),
                html.Td(afstand, style=cell_style()),
                html.Td(r['Stijging (m)'], style=cell_style()),
                html.Td(r['Daling (m)'], style=cell_style()),
                html.Td(dcc.Dropdown(
                    options=[
                        {
                            "label": html.Span([
                                html.Span(style={
                                    "display": "inline-block",
                                    "width": "10px",
                                    "height": "10px",
                                    "borderRadius": "50%",
                                    "backgroundColor": team_kleuren.get(naam, "black"),
                                    "marginRight": "6px"
                                }),
                                naam
                            ]),
                            "value": naam
                        }
                        for naam in teamleden
                    ],
                    value=team_data.get(etappe),
                    id={"type": "team-input", "index": etappe},
                    style={"width": "100%"},
                    clearable=True
                ), style=cell_style()),
                html.Td(dcc.Input(
                    type="text",
                    placeholder="m:ss",
                    value=tempo_data.get(etappe, ""),
                    id={"type": "tempo-input", "index": etappe},
                    debounce=True,
                    style={"width": "90px"}
                ), style=cell_style()),
                html.Td(tijd_str, style=cell_style()),
                html.Td(cum_str, style=cell_style()),
                html.Td(dcc.Input(
                    type="text",
                    placeholder="Opmerking...",
                    value=opmerkingen.get(etappe, ""),
                    id={"type": "opmerking-input", "index": etappe},
                    debounce=True,
                    style={"width": "100%"}
                ), style=cell_style())
            ]))

        return html.Table([
            html.Thead(html.Tr([
                html.Th("Etappe", style=header_style),
                html.Th("Afstand (km)", style=header_style),
                html.Th("Stijging (m)", style=header_style),
                html.Th("Daling (m)", style=header_style),
                html.Th("Teamlid (Team 2)", style=header_style),
                html.Th("Tempo (min/km)", style=header_style),
                html.Th("Tijd", style=header_style),
                html.Th("Cumulatief", style=header_style),
                html.Th("Opmerking", style=header_style)
            ])),
            html.Tbody(rows)
        ], style={"width": "100%", "borderCollapse": "collapse"})

    @app.callback(
        Output("kaart-plot", "figure"),
        Input("grens-store", "data"),
        Input("team-store", "data")
    )
    def update_kaart(grenzen, team_data):
        df = segmenteer_route(lat_data, lon_data, grenzen, x_data)
        fig = go.Figure()

        for etappe_id in sorted(df["etappe"].unique()):
            etappe_data = df[df["etappe"] == etappe_id]
            etappe_naam = f"Etappe {etappe_id}"
            naam = team_data.get(etappe_naam)
            kleur = team_kleuren.get(naam, "black")

            fig.add_trace(go.Scattermapbox(
                lat=etappe_data["lat"],
                lon=etappe_data["lon"],
                mode="lines",
                line=dict(color=kleur, width=4),
                name=etappe_naam if naam else "Niet toegewezen",
                hoverinfo="skip"
            ))

        fig.update_layout(
            mapbox=dict(
                style="open-street-map",
                center=dict(lat=np.mean(lat_data), lon=np.mean(lon_data)),
                zoom=6
            ),
            margin=dict(t=0, b=0, l=0, r=0),
            showlegend=False
        )

        return fig

    @app.callback(
        Output("team-store", "data"),
        Output("tempo-store", "data"),
        Output("opmerking-store", "data"),
        Output("selected-file", "data"),
        Output("grens-store", "data"),
        Output("file-selector", "options"),
        Output("file-selector", "value"),
        Input("file-selector", "value"),
        Input("confirm-new-file", "n_clicks"),
        Input("hoogtegrafiek", "relayoutData"),
        Input("add-line", "n_clicks"),
        Input("remove-line", "n_clicks"),
        Input({"type": "team-input", "index": dash.ALL}, "value"),
        Input({"type": "tempo-input", "index": dash.ALL}, "value"),
        Input({"type": "opmerking-input", "index": dash.ALL}, "value"),
        State({"type": "team-input", "index": dash.ALL}, "id"),
        State({"type": "tempo-input", "index": dash.ALL}, "id"),
        State({"type": "opmerking-input", "index": dash.ALL}, "id"),
        State("team-store", "data"),
        State("tempo-store", "data"),
        State("opmerking-store", "data"),
        State("selected-file", "data"),
        State("modal-filename", "value"),
        State("grens-store", "data"),
        prevent_initial_call=True
    )
    def unified_handler(
        file_select, new_clicks,
        relayout_data, add_clicks, remove_clicks,
        team_vals, tempo_vals, opm_vals,
        team_ids, tempo_ids, opm_ids,
        current_team, current_tempo, current_opm,
        selected_file, new_name, huidige_grenzen
    ):
        triggered = ctx.triggered_id
        grenzen = huidige_grenzen.copy() if huidige_grenzen else []

        if triggered == "confirm-new-file" and new_name:
            filename = new_name.strip()
            if not filename.endswith(".csv"):
                filename += ".csv"
            save_data_to_csv([], {}, {}, {}, [], filename)
            all_files = list_csv_files()
            return {}, {}, {}, filename, [], [{"label": f, "value": f} for f in all_files], filename

        elif triggered == "file-selector" and file_select:
            t, p, o, g = load_data_from_csv(file_select)
            all_files = list_csv_files()
            return (
                t,
                p,
                o,
                file_select,
                g or [],
                [{"label": f, "value": f} for f in all_files],
                file_select
            )

        if triggered == "hoogtegrafiek" and relayout_data:
            for key, value in relayout_data.items():
                match = re.match(r"shapes\[(\d+)\]\.x0", key)
                if match:
                    idx = int(match.group(1))
                    if 0 <= idx < len(grenzen):
                        grenzen[idx] = round(value, 2)
        elif triggered == "add-line":
            laatste_grens = grenzen[-1] if grenzen else 0
            einde = x_data[-1]
            nieuw = round(laatste_grens + (einde - laatste_grens) * 0.9, 2)
            if nieuw < einde:
                grenzen.append(nieuw)
        elif triggered == "remove-line" and len(grenzen) > 0:
            grenzen.pop()

        current_team = current_team or {}
        current_tempo = current_tempo or {}
        current_opm = current_opm or {}

        for v, i in zip(team_vals, team_ids):
            current_team[i["index"]] = v
        for v, i in zip(tempo_vals, tempo_ids):
            current_tempo[i["index"]] = v
        for v, i in zip(opm_vals, opm_ids):
            current_opm[i["index"]] = v

        resultaten = calc_etappes(x_data, y_data, grenzen)
        save_data_to_csv(resultaten, current_team, current_tempo, current_opm, grenzen, selected_file)

        all_files = list_csv_files()
        return (
            current_team,
            current_tempo,
            current_opm,
            selected_file,
            sorted(grenzen),
            [{"label": f, "value": f} for f in all_files],
            selected_file
        )
