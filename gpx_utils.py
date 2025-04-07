import os
import gpxpy
import numpy as np
from geopy.distance import geodesic
import pandas as pd

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

# Bereken de GPX-gegevens
gpx_path = os.path.join(os.path.dirname(__file__), "parcours.gpx")
x_data, y_data, lat_data, lon_data = parse_gpx(gpx_path)

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

# Extra configuratie
default_afstanden = [0]
default_grenzen = list(np.cumsum(default_afstanden))
teamleden = sorted(["Daan", "Kjartan", "Elise", "Nathan", "Sarah", "Ewald", "Robin", "Axelle"])
