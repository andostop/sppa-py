from flask import Flask, render_template, request, redirect, url_for, session
import pandas as pd
import joblib
from datetime import datetime
import re
import random


app = Flask(__name__)
app.secret_key = 'chef_ia_premium_key'
EXCEL_PATH = 'Database_ChefIA.xlsx'

# =========================
# CARGA DE MODELOS
# =========================

IA_ACTIVA = False
RL_ACTIVO = False
INGREDIENTES_ACTIVO = False

# IA nutricional
try:
    modelo = joblib.load('modelo_chef.pkl')
    scaler = joblib.load('scaler_chef.pkl')
    features_modelo = joblib.load('features_chef.pkl')
    IA_ACTIVA = True
    print("Modelo IA principal cargado")
except Exception as e:
    IA_ACTIVA = False
    print("No se cargó modelo IA:", e)

# IA presupuesto
try:
    modelo_presupuesto = joblib.load('modelo_presupuesto_rl.pkl')
    RL_ACTIVO = True
    print("Modelo presupuesto cargado")
except Exception as e:
    RL_ACTIVO = False
    print("No se cargó modelo presupuesto:", e)

try:
    modelo_presupuesto = joblib.load('modelo_presupuesto_rl.pkl')
    RL_ACTIVO = True
    print("Modelo RL cargado correctamente")
except Exception as e:
    RL_ACTIVO = False
    print("Modelo presupuesto no cargado:", e)

# =========================
# IA INGREDIENTES
# =========================

try:
    modelo_ingredientes = joblib.load(
        'modelo_ingredientes.pkl'
    )

    INGREDIENTES_ACTIVO = True

    print("Modelo ingredientes cargado")

except Exception as e:

    INGREDIENTES_ACTIVO = False

    print("No se cargó modelo ingredientes:", e)

# =========================
# UTILIDADES
# =========================

def get_db():
    return pd.read_excel(EXCEL_PATH, sheet_name=None)

def save_db(data):
    with pd.ExcelWriter(EXCEL_PATH) as writer:
        for sheet, df in data.items():
            df.to_excel(writer, sheet_name=sheet, index=False)

def calcular_imc(peso, altura):
    try:
        imc = float(peso) / (float(altura) ** 2)
        return round(imc, 2)
    except:
        return 0

def interpretar_imc(imc):
    if imc < 18.5:
        return "Bajo Peso", "#3b82f6"
    elif 18.5 <= imc < 25:
        return "Normal", "#10b981"
    elif 25 <= imc < 30:
        return "Sobrepeso", "#f59e0b"
    else:
        return "Obesidad", "#ef4444"

def calcular_costo_plato(insumos_str, df_insumos):
    try:
        ids_lista = [int(n) for n in re.findall(r'\d+', str(insumos_str))]
        precios = df_insumos[df_insumos['id_insumo'].isin(ids_lista)]['precio_porcion']
        return round(precios.sum(), 2)
    except:
        return 0.0

def tiene_ingredientes_necesarios(
    plato_ids,
    user_ids
):

    try:

        ids_plato = set(
            int(x)
            for x in re.findall(
                r'\d+',
                str(plato_ids)
            )
        )

        ids_user = set(
            int(x)
            for x in re.findall(
                r'\d+',
                str(user_ids)
            )
        )

        if len(ids_plato) == 0:
            return False

        coincidencias = ids_plato.intersection(
            ids_user
        )

        porcentaje = (
            len(coincidencias)
            / len(ids_plato)
        )

        # mínimo 40% de ingredientes
        return porcentaje >= 0.4

    except:
        return False
    
def contar_coincidencias(plato_ids, user_ids):

    try:

        ids_plato = set(
            int(x)
            for x in re.findall(r'\d+', str(plato_ids))
        )

        ids_user = set(
            int(x)
            for x in re.findall(r'\d+', str(user_ids))
        )

        return len(
            ids_plato.intersection(ids_user)
        )

    except:
        return 0

# =========================
# IA ORIGINAL
# =========================

def score_ia(usuario, plato):
    try:
        if 'modelo' not in globals() or 'scaler' not in globals() or 'features_modelo' not in globals():
            return 0

        imc = float(usuario['peso_kg']) / (float(usuario['altura_m']) ** 2)

        data = {
            'imc': imc,
            'edad': usuario.get('edad', 25),
            'presupuesto_dia': usuario.get('presupuesto_dia', 50),
            'calorias_totales': plato.get('calorias_totales', 500),
            'tiempo_preparacion_min': plato.get('tiempo_preparacion_min', 30),

            'sexo_M': 1 if usuario.get('sexo') == 'M' else 0,
            'sexo_F': 1 if usuario.get('sexo') == 'F' else 0,

            'horario_Desayuno': 1 if str(plato.get('horario', '')).lower() == 'desayuno' else 0,
            'horario_Almuerzo': 1 if str(plato.get('horario', '')).lower() == 'almuerzo' else 0,
            'horario_Cena': 1 if str(plato.get('horario', '')).lower() == 'cena' else 0,

            'region_tipica_Costa': 1 if str(plato.get('region_tipica', '')).lower() == 'costa' else 0,
            'region_tipica_Sierra': 1 if str(plato.get('region_tipica', '')).lower() == 'sierra' else 0,
            'region_tipica_Selva': 1 if str(plato.get('region_tipica', '')).lower() == 'selva' else 0,

            'dificultad_Baja': 1 if str(plato.get('dificultad', '')).lower() == 'baja' else 0,
            'dificultad_Media': 1 if str(plato.get('dificultad', '')).lower() == 'media' else 0,
            'dificultad_Alta': 1 if str(plato.get('dificultad', '')).lower() == 'alta' else 0,
        }

        fila = [data.get(f, 0) for f in features_modelo]
        X = scaler.transform([fila])

        return float(modelo.predict(X)[0])

    except Exception as e:
        print("score_ia:", e)
        return 0

# =========================
# IA PRESUPUESTO
# =========================

def score_presupuesto(usuario, plato):
    if not RL_ACTIVO:
        return 0

    try:
        presupuesto = int(float(usuario['presupuesto_dia']))
        region = str(usuario['ubicacion_actual']).strip()
        horario = str(plato['horario']).strip()
        id_plato = int(plato['id_comida'])

        key = (presupuesto, region, horario)

        if key in modelo_presupuesto:
            return modelo_presupuesto[key].get(id_plato, 0)

        return 0

    except:
        return 0

# =========================
# IA INGREDIENTES
# =========================

def score_ingredientes(usuario, plato):

    if not INGREDIENTES_ACTIVO:
        return 0

    try:

        ingredientes = str(
            usuario.get(
                'insumos_disponibles',
                ''
            )
        )

        horario = str(
            plato['horario']
        ).strip()

        key = (
            ingredientes,
            horario
        )

        id_plato = int(
            plato['id_comida']
        )

        if key in modelo_ingredientes:

            return modelo_ingredientes[key].get(
                id_plato,
                0
            )

        return 0

    except Exception as e:

        print(
            "score_ingredientes:",
            e
        )

        return 0

# =========================
# LOGIN
# =========================

@app.route('/')
def login():
    return render_template('login.html')

@app.route('/auth', methods=['POST'])
def auth():
    nombre = request.form.get('usuario').strip()
    BD = get_db()

    if nombre in BD['USUARIOS']['nombre'].values:
        session['usuario'] = nombre
        return redirect(url_for('dashboard'))

    alergias_list = BD['ALERGIAS'].to_dict('records')

    insumos_list = BD['INSUMOS'][['id_insumo', 'nombre']] \
    .dropna() \
    .to_dict('records')

    return render_template(
        'registro_perfil.html',
        nombre=nombre,
        alergias=alergias_list,
        insumos=insumos_list
    )

# =========================
# REGISTRO
# =========================

@app.route('/completar_registro', methods=['POST'])
def completar_registro():
    nombre = request.form.get('nombre')
    BD = get_db()

    nuevo_id = 1 if BD['USUARIOS'].empty else int(BD['USUARIOS']['id_usuario'].max() + 1)

    nueva_fila = {
        'id_usuario': nuevo_id,
        'nombre': nombre,
        'peso_kg': float(request.form.get('peso')),
        'altura_m': float(request.form.get('altura')),
        'ubicacion_actual': request.form.get('region'),
        'alergias_id': int(request.form.get('alergia')),
        'preferencia_dieta': 'Equilibrada',
        'edad': 25,
        'sexo': request.form.get('sexo', 'M'),
        'presupuesto_dia': float(request.form.get('presupuesto', 50)),
        'insumos_disponibles': request.form.get('insumos_ids', '')
    }

    BD['USUARIOS'] = pd.concat([BD['USUARIOS'], pd.DataFrame([nueva_fila])], ignore_index=True)
    save_db(BD)

    session['usuario'] = nombre

    return redirect(url_for('dashboard'))

# =========================
# EDITAR PERFIL
# =========================

@app.route('/editar_perfil')
def editar_perfil():
    if 'usuario' not in session:
        return redirect(url_for('login'))

    BD = get_db()
    user_row = BD['USUARIOS'][BD['USUARIOS']['nombre'] == session['usuario']]

    if user_row.empty:
        return "Usuario no encontrado", 404

    user = user_row.iloc[0]
    alergias_list = BD['ALERGIAS'].to_dict('records')

    insumos_list = BD['INSUMOS'][['id_insumo', 'nombre']] \
        .dropna() \
        .to_dict('records')

    return render_template(
        'editar_perfil.html',
        user=user,
        alergias=alergias_list,
        insumos=insumos_list
    )

@app.route('/actualizar_perfil', methods=['POST'])
def actualizar_perfil():
    try:
        if 'usuario' not in session:
            return redirect(url_for('login'))

        BD = get_db()

        user_idx = BD['USUARIOS'].index[
            BD['USUARIOS']['nombre'] == session['usuario']
        ]

        if len(user_idx) == 0:
            return "Usuario no encontrado", 404

        idx = user_idx[0]

        BD['USUARIOS']['peso_kg'] = BD['USUARIOS']['peso_kg'].astype(float)
        BD['USUARIOS']['altura_m'] = BD['USUARIOS']['altura_m'].astype(float)
        BD['USUARIOS']['presupuesto_dia'] = BD['USUARIOS']['presupuesto_dia'].astype(float)

        BD['USUARIOS'].at[idx, 'peso_kg'] = float(request.form.get('peso', 0))
        BD['USUARIOS'].at[idx, 'altura_m'] = float(request.form.get('altura', 0))
        BD['USUARIOS'].at[idx, 'ubicacion_actual'] = request.form.get('region', '')
        BD['USUARIOS'].at[idx, 'alergias_id'] = int(request.form.get('alergia', 0))
        BD['USUARIOS'].at[idx, 'sexo'] = request.form.get('sexo', 'M')
        BD['USUARIOS'].at[idx, 'presupuesto_dia'] = float(request.form.get('presupuesto', 50))
        BD['USUARIOS'].at[idx, 'insumos_disponibles'] = request.form.get('insumos_ids', '')

        save_db(BD)

        return redirect(url_for('dashboard'))

    except Exception as e:
        return f"Error actualizando perfil: {e}", 500

# =========================
# DASHBOARD
# =========================

@app.route('/dashboard')
def dashboard():
    if 'usuario' not in session:
        return redirect(url_for('login'))

    BD = get_db()

    user = BD['USUARIOS'][BD['USUARIOS']['nombre'] == session['usuario']].iloc[0]
    id_usuario = user['id_usuario']

    imc_valor = calcular_imc(user['peso_kg'], user['altura_m'])
    imc_cat, imc_color = interpretar_imc(imc_valor)

    alergia_row = BD['ALERGIAS'][BD['ALERGIAS']['id_alergia'] == user['alergias_id']]
    alergia_nombre = alergia_row.iloc[0]['nombre_alergia'] if not alergia_row.empty else "Ninguna"

    hist = BD['HISTORIAL_Y_PREFERENCIAS']
    reg = hist[hist['id_usuario'] == id_usuario].copy()

    ultima = "Aún no has comido nada"

    if not reg.empty:
        id_c = reg.iloc[-1]['id_comida']
        plato_row = BD['COMIDAS'][BD['COMIDAS']['id_comida'] == id_c]

        if not plato_row.empty:
            ultima = plato_row.iloc[0]['nombre_plato']

    lineas_tiempo = {}
    momentos = ['desayuno', 'almuerzo', 'cena', 'snack']

    if 'tipo_comida' not in reg.columns:
        reg['tipo_comida'] = ""
    else:
        reg['tipo_comida'] = reg['tipo_comida'].astype(str).replace('nan', '')

    if 'eleccion_tipo' not in reg.columns:
        reg['eleccion_tipo'] = ""
    else:
        reg['eleccion_tipo'] = reg['eleccion_tipo'].astype(str).replace('nan', '')

    for m in momentos:
        df_m = reg[reg['tipo_comida'].astype(str).str.lower() == m].tail(7)

        puntos = []

        for _, fila in df_m.iterrows():
            tipo = str(fila.get('eleccion_tipo', '')).lower()

            if tipo == 'principal':
                color = "#2ECC71"
            elif tipo == 'secundario':
                color = "#F1C40F"
            else:
                color = "#FF4B4B"

            puntos.append({
                'plato': fila.get('nombre_comida', 'Plato'),
                'color': color
            })

        lineas_tiempo[m] = puntos

    return render_template(
        'dashboard.html',
        user=user,
        ultima=ultima,
        imc=imc_valor,
        imc_cat=imc_cat,
        imc_color=imc_color,
        alergia=alergia_nombre,
        fecha=datetime.now().strftime('%A, %d de %B'),
        lineas=lineas_tiempo
    )

# =========================
# RECOMENDAR
# =========================

@app.route('/recomendar', methods=['POST'])
def recomendar():
    try:
        momento = request.form.get('momento')
        BD = get_db()

        user = BD['USUARIOS'][BD['USUARIOS']['nombre'] == session['usuario']].iloc[0]

        id_usuario = user['id_usuario']
        presupuesto_user = float(user['presupuesto_dia'])
        region_usuario = str(user.get('ubicacion_actual', "")).strip().lower()

        historial = BD['HISTORIAL_Y_PREFERENCIAS']

        ultimas_comidas_df = historial[historial['id_usuario'] == id_usuario].tail()

        lista_bloqueo = ultimas_comidas_df['id_comida'].astype(str).str.replace('.0', '').tolist()

        conteo_vistos = historial[historial['id_usuario'] == id_usuario]['id_comida'].value_counts().to_dict()

        df_comidas = BD['COMIDAS'].copy()

        def es_plato_seguro_interno(insumos_str, al_user):
            try:
                if int(float(al_user)) == 0:
                    return True

                if pd.isna(insumos_str) or str(insumos_str).strip() == "":
                    return False

                ids_plato = [int(n) for n in re.findall(r'\d+', str(insumos_str))]

                alergias_plato = BD['INSUMOS'][
                    BD['INSUMOS']['id_insumo'].isin(ids_plato)
                ]['alergeno_asociado'].dropna()

                return int(float(al_user)) not in [
                    int(float(a)) for a in alergias_plato if int(float(a)) > 0
                ]

            except:
                return False

        aptos = df_comidas[df_comidas['horario'].str.strip().str.lower() == momento.lower()].copy()

        aptos = aptos[aptos['insumos_base_ids'].apply(
            lambda x: es_plato_seguro_interno(x, user['alergias_id'])
        )].copy()

        # ====================================
        # COINCIDENCIA DE INGREDIENTES
        # ====================================

        aptos['coincide_ingredientes'] = aptos[
            'insumos_base_ids'
        ].apply(
            lambda x: tiene_ingredientes_necesarios(
                x,
                user.get(
                    'insumos_disponibles',
                    ''
                )
            )
        )

        aptos['id_str'] = aptos['id_comida'].astype(str).str.replace('.0', '').str.strip()

        aptos = aptos[~aptos['id_str'].isin(lista_bloqueo)].copy()

        aptos['costo_estimado'] = aptos['insumos_base_ids'].apply(
            lambda x: calcular_costo_plato(x, BD['INSUMOS'])
        )

        

        def motor_ia(fila):
            puntos = 0
            id_p = fila['id_comida']
            cals = float(fila.get('calorias_totales', 500))

            if float(user['peso_kg']) / (float(user['altura_m']) ** 2) > 25 and cals < 450:
                puntos += 50

            if str(fila.get('region_tipica', "")).strip().lower() == region_usuario:
                puntos += 70

            veces_visto_usuario = conteo_vistos.get(id_p, 0)
            puntos -= (veces_visto_usuario * 45)

           
            puntos += score_ia(user, fila)
            puntos += score_presupuesto(user, fila)
            puntos += score_ingredientes(user, fila)

            # =========================
            # PRIORIDAD INGREDIENTES
            # =========================

            coincidencias = contar_coincidencias(
                fila['insumos_base_ids'],
                user.get('insumos_disponibles', '')
            )

            # MUCHOS puntos por coincidencia
            puntos += coincidencias * 120

            puntos += random.randint(0, 30)

            return puntos

        aptos['puntuacion'] = aptos.apply(motor_ia, axis=1)

        baratos = aptos[aptos['costo_estimado'] <= presupuesto_user].sort_values(by='puntuacion', ascending=False)
        caros = aptos[aptos['costo_estimado'] > presupuesto_user].sort_values(by='puntuacion', ascending=False)

        pool_final = pd.concat([baratos, caros])

        p_data = pool_final.iloc[0].to_dict()
        p_data['sobrepasa_presupuesto'] = p_data['costo_estimado'] > presupuesto_user
        p_data['tipo_sug'] = 'principal'

        secundarias = []

        otros_df = pool_final.copy()

        # quitar principal
        otros_df = otros_df.iloc[1:]

        # primero compatibles
        otros_df = otros_df.sort_values(
            by='coincide_ingredientes',
            ascending=False
        )

        # ====================================
        # ASEGURAR SIEMPRE 3 SECUNDARIOS
        # ====================================

        if len(otros_df) < 3:

            faltan = 3 - len(otros_df)

            extras = pool_final.copy()

            # quitar principal
            extras = extras.iloc[1:]

            # repetir algunos
            extras = extras.head(faltan)

            otros_df = pd.concat(
                [otros_df, extras],
                ignore_index=True
            )

        # tomar máximo 3
        otros_df = otros_df.head(3)

        if not otros_df.empty:
            id_plato_saludable = otros_df['calorias_totales'].idxmin()

            for idx, row in otros_df.iterrows():
                item = row.to_dict()
                item['es_saludable'] = (idx == id_plato_saludable)
                item['sobrepasa_presupuesto'] = item['costo_estimado'] > presupuesto_user
                item['tipo_sug'] = 'secundario'
                item['color_ingrediente'] = (
                    'verde'
                    if item['coincide_ingredientes']
                    else 'naranja'
                )

                item['texto_ingrediente'] = (
                '✓ Tienes los ingredientes'
                if item['coincide_ingredientes']
                else 'No tienes suficientes ingredientes'
)

                secundarias.append(item)

        return render_template(
            'recomendacion.html',
            p=p_data,
            s=secundarias,
            momento=momento,
            presupuesto=presupuesto_user
        )

    except Exception as e:
        return f"Error en la recomendación: {e}", 500

# =========================
# RECETA
# =========================

@app.route('/receta/<int:id_p>')
def receta(id_p):
    BD = get_db()

    tipo_procedencia = request.args.get('tipo', 'principal')

    df = BD['COMIDAS']
    plato_row = df[df['id_comida'] == id_p]

    if plato_row.empty:
        return f"Plato con ID {id_p} no encontrado", 404

    plato = plato_row.iloc[0]

    return render_template('receta.html', plato=plato, tipo=tipo_procedencia)

# =========================
# REGISTRAR CONSUMO
# =========================

@app.route('/registrar_consumo', methods=['POST'])
def registrar_consumo():
    try:
        BD = get_db()

        if 'usuario' not in session:
            return redirect(url_for('login'))

        user_row = BD['USUARIOS'][BD['USUARIOS']['nombre'] == session['usuario']]

        if user_row.empty:
            return "Usuario no encontrado", 404

        user_row = user_row.iloc[0]
        u_id = user_row['id_usuario']

        id_elegido = request.form.get('id_comida')
        tipo_sug_limpio = str(request.form.get('tipo_sug', 'principal')).strip().lower()

        if not id_elegido:
            return "No se recibió id_comida", 400

        id_elegido = int(id_elegido)

        df_comidas = BD['COMIDAS']
        datos_plato = df_comidas[df_comidas['id_comida'] == id_elegido]

        if datos_plato.empty:
            return "Plato no existe", 404

        datos_plato = datos_plato.iloc[0]

        nombre_real = datos_plato.get('nombre_plato', 'Plato')
        horario_real = str(datos_plato.get('horario', '')).strip().lower()

        historial = BD['HISTORIAL_Y_PREFERENCIAS']

        nuevo_id_reg = 1 if historial.empty else int(historial['id_registro'].max() + 1)

        nuevo_reg = {
            'id_registro': nuevo_id_reg,
            'id_usuario': u_id,
            'id_comida': id_elegido,
            'tipo_comida': horario_real,
            'eleccion_tipo': tipo_sug_limpio,
            'nombre_comida': nombre_real,
            'fecha_consumo': datetime.now().strftime('%Y-%m-%d'),
            'puntos_satisfaccion': 10
        }

        BD['HISTORIAL_Y_PREFERENCIAS'] = pd.concat(
            [historial, pd.DataFrame([nuevo_reg])],
            ignore_index=True
        )

        idx_user = BD['USUARIOS'].index[BD['USUARIOS']['id_usuario'] == u_id][0]

        BD['USUARIOS'].at[idx_user, 'id_ultima_comida'] = id_elegido

        save_db(BD)

        return redirect(url_for('dashboard'))

    except Exception as e:
        return f"Error interno: {e}", 500

# =========================
# LOGOUT
# =========================

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# =========================
# RUN
# =========================

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
