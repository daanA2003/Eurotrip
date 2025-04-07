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

def save_data_to_csv(resultaten, team_data, tempo_data, opmerkingen, grenzen, filename):
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
