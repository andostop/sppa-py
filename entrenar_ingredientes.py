import pandas as pd
import joblib
import random
import re
import os

# =========================
# CARGAR EXCEL
# =========================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

archivo = os.path.join(
    BASE_DIR,
    "Database_ChefIA.xlsx"
)

print("Leyendo:", archivo)

bd = pd.read_excel(archivo, sheet_name=None)

usuarios = bd["USUARIOS"]
comidas = bd["COMIDAS"]

# =========================
# Q TABLE
# =========================

Q = {}

alpha = 0.1
epsilon = 0.2
episodios = 4000

# =========================
# UTILIDADES
# =========================

def extraer_ids(texto):

    try:
        return set(
            int(x)
            for x in re.findall(r'\d+', str(texto))
        )
    except:
        return set()

# =========================
# ESTADO
# =========================

def estado(usuario, momento):

    ingredientes = str(
        usuario.get(
            "insumos_disponibles",
            ""
        )
    )

    return (
        ingredientes,
        momento
    )

# =========================
# RECOMPENSA
# =========================

def recompensa(usuario, plato):

    try:

        user_ids = extraer_ids(
            usuario.get(
                "insumos_disponibles",
                ""
            )
        )

        plato_ids = extraer_ids(
            plato.get(
                "insumos_base_ids",
                ""
            )
        )

        if len(plato_ids) == 0:
            return -50

        coincidencias = user_ids.intersection(plato_ids)

        porcentaje = len(coincidencias) / len(plato_ids)

        # recompensa principal
        r = porcentaje * 100

        # bonus si tiene casi todo
        if porcentaje >= 0.8:
            r += 50

        elif porcentaje >= 0.5:
            r += 20

        # castigo si no tiene nada
        if porcentaje == 0:
            r -= 80

        return r

    except:
        return -20

# =========================
# ENTRENAMIENTO
# =========================

for ep in range(episodios):

    user = usuarios.sample(1).iloc[0]

    momento = random.choice([
        "Desayuno",
        "Almuerzo",
        "Cena",
        "Snack"
    ])

    disponibles = comidas[
        comidas["horario"].str.lower()
        == momento.lower()
    ]

    if disponibles.empty:
        continue

    s = estado(user, momento)

    if s not in Q:
        Q[s] = {}

    acciones = disponibles["id_comida"].tolist()

    for a in acciones:

        if a not in Q[s]:
            Q[s][a] = 0

    # exploración
    if random.random() < epsilon:
        accion = random.choice(acciones)

    else:
        accion = max(
            Q[s],
            key=Q[s].get
        )

    plato = comidas[
        comidas["id_comida"] == accion
    ].iloc[0]

    r = recompensa(user, plato)

    valor_actual = Q[s][accion]

    nuevo_valor = valor_actual + (
        alpha * (r - valor_actual)
    )

    Q[s][accion] = nuevo_valor

# =========================
# GUARDAR MODELO
# =========================

joblib.dump(
    Q,
    "modelo_ingredientes.pkl"
)

print("modelo ingredientes entrenado")