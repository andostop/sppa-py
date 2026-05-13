import pandas as pd
import numpy as np
import joblib
import random
import re
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
archivo = os.path.join(BASE_DIR, "Database_ChefIA.xlsx")

print("Leyendo:", archivo)

bd = pd.read_excel(archivo, sheet_name=None)

usuarios = bd["USUARIOS"]
comidas = bd["COMIDAS"]
insumos = bd["INSUMOS"]

Q = {}

alpha = 0.1
gamma = 0.9
epsilon = 0.2
episodios = 3000

def costo_plato(insumos_ids):
    try:
        ids = [int(x) for x in re.findall(r'\d+', str(insumos_ids))]
        return insumos[insumos["id_insumo"].isin(ids)]["precio_porcion"].sum()
    except:
        return 0

def estado(usuario, momento):
    imc = usuario["peso_kg"] / (usuario["altura_m"] ** 2)
    return (
        round(imc),
        usuario["presupuesto_dia"],
        usuario["ubicacion_actual"],
        momento
    )

def recompensa(usuario, plato):
    r = 0

    costo = costo_plato(plato["insumos_base_ids"])

    if costo <= usuario["presupuesto_dia"]:
        r += 40
    else:
        r -= 30

    if plato["calorias_totales"] < 600:
        r += 30

    if str(plato["region_tipica"]).lower() == str(usuario["ubicacion_actual"]).lower():
        r += 20

    return r

for ep in range(episodios):

    user = usuarios.sample(1).iloc[0]
    momento = random.choice(["Desayuno","Almuerzo","Cena","Snack"])

    disponibles = comidas[
        comidas["horario"].str.lower() == momento.lower()
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

    if random.random() < epsilon:
        accion = random.choice(acciones)
    else:
        accion = max(Q[s], key=Q[s].get)

    plato = comidas[comidas["id_comida"] == accion].iloc[0]

    r = recompensa(user, plato)

    valor_actual = Q[s][accion]
    nuevo_valor = valor_actual + alpha * (r - valor_actual)

    Q[s][accion] = nuevo_valor

joblib.dump(Q, "modelo_presupuesto_rl.pkl")

print("modelo entrenado")