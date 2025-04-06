import dash
from dash import dcc, html, Output, Input, State, ctx
import plotly.graph_objs as go
import gpxpy
from geopy.distance import geodesic
import numpy as np
import re
import datetime
import pandas as pd
import os
import csv


DATA_FOLDER = os.path.join(os.path.dirname(__file__), "data")




def list_csv_files():
    if not os.path.exists(DATA_FOLDER):
        os.makedirs(DATA_FOLDER)
    return sorted([f for f in os.listdir(DATA_FOLDER) if f.endswith(".csv")])


def load_data_from_csv(filename):
    path = os.path.join(DATA_FOLDER, filename)
    if not os.path.exists(path):
        return {}, {}, {}, []

    team_data = {}
    tempo_data = {}
    opmerking_data = {}
    grenzen = []

    with open(path, newline='') as f:
        reader = csv.reader(f)
        headers = next(reader)

        for row in reader:
            if not row:
                continue
            if row[0] == "_GRENZEN":
                grenzen = [float(x) for x in row[1:] if x]
            elif row[0].startswith("Etappe"):
                etappe = row[0]
                team_data[etappe] = row[4] if len(row) > 4 else ''
                tempo_data[etappe] = row[5] if len(row) > 5 else ''
                opmerking_data[etappe] = row[6] if len(row) > 6 else ''

    return team_data, tempo_data, opmerking_data, grenzen




def save_data_to_csv(resultaten, team_data, tempo_data, opmerkingen,grenzen, filename):
    path = os.path.join(DATA_FOLDER, filename)
    with open(path, mode='w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["Etappe", "Afstand", "Stijging", "Daling", "Teamlid", "Tempo", "Opmerking"])
        for r in resultaten:
            etappe = r['Etappe']
            writer.writerow([
                etappe,
                r['Afstand (km)'],
                r['Stijging (m)'],
                r['Daling (m)'],
                team_data.get(etappe, ''),
                tempo_data.get(etappe, ''),
                opmerkingen.get(etappe, '')
            ])
        writer.writerow([])
        writer.writerow(["_GRENZEN"] + grenzen)




# === Kleuren per teamlid ===
team_kleuren = {
    "Axelle": "#E91E63",
    "Daan": "#2196F3",
    "Elise": "#9C27B0",
    "Ewald": "#4CAF50",
    "Kjartan": "#FFC107",
    "Nathan": "#FF5722",
    "Robin": "#3F51B5",
    "Sarah": "#00BCD4"
}


# === GPX inladen ===
def parse_gpx(gpx_path):
    with open(gpx_path, 'r') as gpx_file:
        gpx = gpxpy.parse(gpx_file)

    latitudes, longitudes, hoogtes, afstanden = [], [], [], []
    totale_afstand = 0

    punten = []
    for track in gpx.tracks:
        for segment in track.segments:
            punten.extend(segment.points)

    for i, p in enumerate(punten):
        lat, lon, ele = p.latitude, p.longitude, p.elevation
        latitudes.append(lat)
        longitudes.append(lon)
        hoogtes.append(ele)
        if i == 0:
            afstanden.append(0)
        else:
            prev = punten[i - 1]
            dist = geodesic((prev.latitude, prev.longitude), (lat, lon)).meters
            totale_afstand += dist
            afstanden.append(totale_afstand / 1000)

    return afstanden, hoogtes, latitudes, longitudes

# === Data voorbereiden ===
gpx_path = gpx_path = os.path.join(os.path.dirname(__file__),"parcours.gpx")
x_data, y_data, lat_data, lon_data = parse_gpx(gpx_path)


default_afstanden = [0]
default_grenzen = list(np.cumsum(default_afstanden))
teamleden = sorted(["Daan", "Kjartan", "Elise", "Nathan", "Sarah", "Ewald", "Robin", "Axelle"])


def segmenteer_route(lat, lon, grenspunten, afstanden):
    df = pd.DataFrame({
        "lat": lat,
        "lon": lon,
        "afstand": afstanden
    })

    df["etappe"] = 0
    grenzen = [0] + sorted(grenspunten) + [afstanden[-1]]

    for i in range(len(grenzen) - 1):
        start = grenzen[i]
        einde = grenzen[i + 1]
        mask = (df["afstand"] >= start) & (df["afstand"] <= einde)
        df.loc[mask, "etappe"] = i + 1

    return df


# === Etappeberekening ===
def calc_etappes(x, y, grenspunten):
    resultaten = []
    grenzen = [0] + sorted(grenspunten) + [x[-1]]

    for i in range(len(grenzen) - 1):
        start = grenzen[i]
        einde = grenzen[i + 1]

        mask = (np.array(x) >= start) & (np.array(x) <= einde)
        segment_x = np.array(x)[mask]
        segment_y = np.array(y)[mask]

        if len(segment_x) < 2:
            continue

        afstand = segment_x[-1] - segment_x[0]
        hoogteverschillen = np.diff(segment_y)
        stijging = np.sum(hoogteverschillen[hoogteverschillen > 0])
        daling = -np.sum(hoogteverschillen[hoogteverschillen < 0])

        resultaten.append({
            'Etappe': f'Etappe {i + 1}',
            'Afstand (km)': round(afstand, 2),
            'Stijging (m)': round(stijging, 1),
            'Daling (m)': round(daling, 1)
        })

    return resultaten



# Tempo converter
def tempo_str_to_min(t_str):
    try:
        parts = t_str.strip().split(":")
        return int(parts[0]) + int(parts[1]) / 60
    except:
        return None
    


def serve_layout():
    init_team, init_tempo, init_opmerking, init_grenzen = load_data_from_csv("etappes_data.csv")

    # Kleiner grijs vlak enkel rond de elementen
    return html.Div(
        style={
            "maxWidth": "1100px",
            "margin": "40px auto",
            "padding": "40px",
            "backgroundColor": "#f0f0f0",
            "borderRadius": "8px"
        },
        children=[
            html.H2(
                "Eurotrip Etappeplanner",
                style={
                    "textAlign": "center",
                    "marginBottom": "30px"
                }
            ),

            # Bovenste container: twee boxen naast elkaar
            html.Div([
                html.Div([
                    html.H4("Bestand selecteren", style={"marginBottom": "10px"}),
                    dcc.Dropdown(
                        id="file-selector",
                        options=[],  # ← opties worden later gezet via callback
                        value="etappes_data.csv",
                        clearable=False,
                        style={"width": "100%"}
                    )
                ], style={
                    "border": "1px solid #ccc",
                    "borderRadius": "5px",
                    "padding": "15px",
                    "backgroundColor": "#ffffff",
                    "flex": "1"
                }),
                html.Div([
                    html.H4("Nieuw bestand"),
                    html.Button(
                        "📄 Start nieuw bestand",
                        id="open-new-file-modal",
                        n_clicks=0,
                        style={"width": "100%"}
                    )
                ], style={
                    "border": "1px solid #ccc",
                    "borderRadius": "5px",
                    "padding": "15px",
                    "backgroundColor": "#ffffff",
                    "flex": "1"
                }),
            ], style={
                "display": "flex",
                "gap": "20px",
                "maxWidth": "800px",
                "margin": "0 auto",
                "marginBottom": "40px"
            }),

            # Popup trigger
            dcc.Store(id="show-new-file-modal", data=False),
            html.Div(
                id="new-file-modal",
                style={"display": "none"},
                children=[
                    html.Div([
                        html.H4("Nieuwe bestandsnaam"),
                        dcc.Input(
                            id="modal-filename",
                            type="text",
                            placeholder="bijv. etappes_daan",
                            style={"width": "100%", "marginBottom": "10px"}
                        ),
                        html.Button("Aanmaken", id="confirm-new-file", n_clicks=0),
                        html.Button(
                            "Annuleren",
                            id="cancel-new-file",
                            n_clicks=0,
                            style={"marginLeft": "10px"}
                        )
                    ], style={
                        "backgroundColor": "white",
                        "padding": "20px",
                        "border": "1px solid #ccc",
                        "borderRadius": "8px",
                        "width": "300px",
                        "margin": "100px auto",
                        "boxShadow": "0 4px 6px rgba(0,0,0,0.1)",
                        "textAlign": "center"
                    })
                ]
            ),

            # Store en data
            dcc.Store(id="selected-file", data="etappes_data.csv"),
            dcc.Store(id="grens-store", data=init_grenzen or default_grenzen),
            dcc.Store(id="team-store", data=init_team),
            dcc.Store(id="tempo-store", data=init_tempo),
            dcc.Store(id="opmerking-store", data=init_opmerking),

            # Box met etappelijnbeheer en grafiek
            html.Div([
                html.H4("Etappelijn beheer", style={"marginBottom": "5px"}),
                html.P("Voeg toe en verwijder met onderstaande knoppen. Je kan de lijnen verschuiven door erop te klikken en te slepen. De tabel onder de grafiek wortd zo automatsich geüpdatet.",  # noqa: E501
                       style={"marginBottom": "15px", "fontStyle": "italic"}),
                html.Div([
                    html.Button(
                        "➕ Voeg etappelijn toe",
                        id="add-line",
                        n_clicks=0,
                        style={"marginRight": "10px"}
                    ),
                    html.Button(
                        "➖ Verwijder laatste etappelijn",
                        id="remove-line",
                        n_clicks=0
                    )
                ], style={"textAlign": "center", "marginTop": "10px"}),

                dcc.Graph(
                    id="hoogtegrafiek",
                    config={"editable": True},
                    style={"width": "100%", "height": "600px", "marginTop": "20px"}
                ),
            ], style={
                "border": "1px solid #ccc",
                "borderRadius": "5px",
                "padding": "20px",
                "marginBottom": "40px",
                "maxWidth": "1000px",
                "margin": "0 auto",
                "backgroundColor": "#ffffff"
            }),

            # Tabel met titel
            html.H4("Etappe Resultaten", style={"textAlign": "center", "marginBottom": "15px"}),
            html.Div(
                id="etappe-resultaten",
                style={
                    "maxHeight": "500px",
                    "overflowY": "scroll",
                    "border": "1px solid #ccc",
                    "padding": "10px",
                    "marginBottom": "40px",
                    "backgroundColor": "#f9f9f9",
                    "borderRadius": "5px",
                    "maxWidth": "1000px",
                    "margin": "0 auto"
                }
            ),

            # Kaart
            html.H3("Kaartweergave", style={"textAlign": "center", "marginBottom": "15px"}),
            dcc.Graph(
                id="kaart-plot",
                style={
                    "height": "600px",
                    "width": "100%",
                    "maxWidth": "1000px",
                    "margin": "0 auto"
                }
            ),
        ]
    )

# === App layout ===
app = dash.Dash(__name__, suppress_callback_exceptions=True)

app.title = "Eurotrip Etappeplanner"

app.layout = serve_layout
# === Callback: grensbeheer ===



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


# === Callback: grafiek ===
@app.callback(
    Output("hoogtegrafiek", "figure"),
    Input("grens-store", "data"),
    Input("team-store", "data")
)
def update_figure(grenzen, team_data):
    team_data = team_data or {}
    fig = go.Figure()

    grenzen = [0] + sorted(grenzen) + [x_data[-1]]
    for i in range(len(grenzen) - 1):
        start = grenzen[i]
        end = grenzen[i + 1]
        mask = (np.array(x_data) >= start) & (np.array(x_data) <= end)

        etappe_id = f"Etappe {i + 1}"
        naam = team_data.get(etappe_id)
        kleur = team_kleuren.get(naam, "black")

        fig.add_trace(go.Scatter(
            x=np.array(x_data)[mask],
            y=np.array(y_data)[mask],
            mode='lines',
            line=dict(color=kleur, width=3),
            name=etappe_id if naam else "Niet toegewezen"
        ))

    # Voeg grenslijnen toe
    shapes = []
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

    fig.update_layout(
        height=600,
        xaxis_title="Afstand (km)",
        yaxis_title="Hoogte (m)",
        shapes=shapes,
        margin=dict(t=40, r=10, l=10, b=40),
        showlegend=False,
        title="Hoogtegrafiek"
    )

    return fig


# === Callback: tabel met alle velden ===
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









# === Opslag voor team, tempo en opmerkingen ===
@app.callback(
    Output("team-store", "data"),
    Output("tempo-store", "data"),
    Output("opmerking-store", "data"),
    Output("selected-file", "data"),
    Output("grens-store", "data"),
    Output("file-selector", "options"),  # <== toegevoegde output
    Output("file-selector", "value"),    # <== toegevoegde output

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

    # Nieuw bestand starten
    if triggered == "confirm-new-file" and new_name:

        filename = new_name.strip()
        if not filename.endswith(".csv"):
            filename += ".csv"
        save_data_to_csv([], {}, {}, {}, [], filename)
        all_files = list_csv_files()
        return {}, {}, {}, filename, [], [{"label": f, "value": f} for f in all_files], filename


    # Ander bestand gekozen
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


    # Etappelijnen beheren
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

    # Team/tempo/opmerkingen bijwerken
    current_team = current_team or {}
    current_tempo = current_tempo or {}
    current_opm = current_opm or {}

    for v, i in zip(team_vals, team_ids):
        current_team[i["index"]] = v
    for v, i in zip(tempo_vals, tempo_ids):
        current_tempo[i["index"]] = v
    for v, i in zip(opm_vals, opm_ids):
        current_opm[i["index"]] = v

    # Altijd opslaan bij wijziging
        # Altijd opslaan bij wijziging
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





if __name__ == "__main__":
    app.run(debug=True)