import dash
from dash import dcc, html
from data_utils import load_data_from_csv
from gpx_utils import default_grenzen

def serve_layout():
    init_team, init_tempo, init_opmerking, init_grenzen = load_data_from_csv("etappes_data.csv")

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
                html.P("Voeg toe en verwijder met onderstaande knoppen. Je kan de lijnen verschuiven door erop te klikken en te slepen. De tabel onder de grafiek wordt zo automatisch geüpdatet.",
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
