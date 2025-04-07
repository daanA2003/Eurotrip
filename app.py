from dash import Dash
from layout import serve_layout
from callbacks import register_callbacks

app = Dash(__name__, suppress_callback_exceptions=True)
app.title = "Eurotrip Etappeplanner"
app.layout = serve_layout  # Of gebruik: app.layout = serve_layout()

register_callbacks(app)

if __name__ == "__main__":
    app.run(debug=True)
