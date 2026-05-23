# F1 circuit database — corners, straights, reference lap records
TRACKS = {
    "monza": {
        "name": "Monza — Italian GP",
        "length_km": 5.793,
        "laps": 53,
        "corners": [
            {"name": "Prima Variante",   "radius": 45,  "count": 1},
            {"name": "Seconda Variante", "radius": 40,  "count": 1},
            {"name": "Lesmo 1",          "radius": 90,  "count": 1},
            {"name": "Lesmo 2",          "radius": 85,  "count": 1},
            {"name": "Ascari complex",   "radius": 65,  "count": 2},
            {"name": "Parabolica",       "radius": 105, "count": 1},
        ],
        "straights": [
            {"name": "Start/Finish",     "length_m": 450},
            {"name": "Back straight",    "length_m": 1100},
            {"name": "Curva Grande exit","length_m": 780},
        ],
        "downforce_bias": "low",
        "lap_record_s": 78.667,   # Barrichello, 2004
    },
    "monaco": {
        "name": "Monaco — Monaco GP",
        "length_km": 3.337,
        "laps": 78,
        "corners": [
            {"name": "Sainte Dévote",  "radius": 15, "count": 1},
            {"name": "Massenet",       "radius": 28, "count": 1},
            {"name": "Casino",         "radius": 22, "count": 1},
            {"name": "Mirabeau",       "radius": 20, "count": 1},
            {"name": "Loews (hairpin)","radius": 12, "count": 1},
            {"name": "Portier",        "radius": 25, "count": 1},
            {"name": "Nouvelle",       "radius": 30, "count": 1},
            {"name": "Piscine",        "radius": 20, "count": 2},
            {"name": "Rascasse",       "radius": 15, "count": 1},
            {"name": "Anthony Noghès", "radius": 18, "count": 1},
        ],
        "straights": [
            {"name": "Tunnel exit",    "length_m": 200},
            {"name": "Pit straight",   "length_m": 280},
        ],
        "downforce_bias": "high",
        "lap_record_s": 71.382,   # Hamilton, 2021
    },
    "silverstone": {
        "name": "Silverstone — British GP",
        "length_km": 5.891,
        "laps": 52,
        "corners": [
            {"name": "Copse",                    "radius": 120, "count": 1},
            {"name": "Maggotts-Becketts-Chapel", "radius": 80,  "count": 3},
            {"name": "Stowe",                    "radius": 95,  "count": 1},
            {"name": "Club",                     "radius": 100, "count": 1},
            {"name": "Abbey",                    "radius": 80,  "count": 1},
            {"name": "Village",                  "radius": 40,  "count": 1},
            {"name": "The Loop",                 "radius": 30,  "count": 1},
            {"name": "Luffield",                 "radius": 35,  "count": 1},
        ],
        "straights": [
            {"name": "Hangar Straight",     "length_m": 870},
            {"name": "Wellington Straight", "length_m": 620},
            {"name": "National Straight",   "length_m": 500},
        ],
        "downforce_bias": "medium",
        "lap_record_s": 87.097,   # Verstappen, 2020
    },
    "spa": {
        "name": "Spa-Francorchamps — Belgian GP",
        "length_km": 7.004,
        "laps": 44,
        "corners": [
            {"name": "La Source",          "radius": 20,  "count": 1},
            {"name": "Eau Rouge/Raidillon","radius": 35,  "count": 1},
            {"name": "Les Combes",         "radius": 50,  "count": 2},
            {"name": "Malmedy",            "radius": 45,  "count": 1},
            {"name": "Pouhon",             "radius": 130, "count": 1},
            {"name": "Campus",             "radius": 55,  "count": 2},
            {"name": "Stavelot",           "radius": 60,  "count": 1},
            {"name": "Blanchimont",        "radius": 220, "count": 1},
            {"name": "Bus Stop chicane",   "radius": 20,  "count": 1},
        ],
        "straights": [
            {"name": "Kemmel Straight",    "length_m": 870},
            {"name": "Pit Straight",       "length_m": 750},
        ],
        "downforce_bias": "medium-low",
        "lap_record_s": 105.841,  # Bottas, 2018
    },
    "suzuka": {
        "name": "Suzuka — Japanese GP",
        "length_km": 5.807,
        "laps": 53,
        "corners": [
            {"name": "Turn 1-2",       "radius": 80,  "count": 2},
            {"name": "Esses",          "radius": 55,  "count": 3},
            {"name": "Dunlop curve",   "radius": 70,  "count": 1},
            {"name": "Hairpin",        "radius": 18,  "count": 1},
            {"name": "Spoon curve",    "radius": 95,  "count": 1},
            {"name": "130R",           "radius": 130, "count": 1},
            {"name": "Chicane",        "radius": 25,  "count": 2},
            {"name": "Casio triangle", "radius": 20,  "count": 1},
        ],
        "straights": [
            {"name": "Main straight",  "length_m": 640},
            {"name": "Back straight",  "length_m": 660},
        ],
        "downforce_bias": "medium-high",
        "lap_record_s": 88.064,   # Hamilton, 2019
    },
}
