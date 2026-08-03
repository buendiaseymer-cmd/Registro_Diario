import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import datetime
import json
import pandas as pd

# ---- CONFIGURACIÓN DE LA PÁGINA ----
st.set_page_config(page_title="Control Diario y Costos", layout="centered", page_icon="🏗️")

# ---- SISTEMA DE LOGIN ----
def verificar_autenticacion():
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if st.session_state.authenticated:
        return True

    st.markdown("<h2 style='text-align: center;'>🔐 Acceso restringido</h2>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center;'>Ingrese la contraseña general para continuar</p>", unsafe_allow_html=True)

    with st.form("login_form"):
        password = st.text_input("Contraseña", type="password")
        submit = st.form_submit_button("Ingresar", use_container_width=True)

        if submit:
            try:
                correct_password = st.secrets["general_password"]
            except:
                st.error("❌ No se encontró la contraseña en los secretos. Configura 'general_password' en .streamlit/secrets.toml")
                return False

            if password == correct_password:
                st.session_state.authenticated = True
                st.success("✅ Acceso concedido")
                st.rerun()
            else:
                st.error("❌ Contraseña incorrecta")
    return False

if not verificar_autenticacion():
    st.stop()

# ---- CONEXIÓN A GOOGLE SHEETS ----
@st.cache_resource
def conectar_google_sheets():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    if "google_credentials" in st.secrets:
        creds_dict = json.loads(st.secrets["google_credentials"])
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    else:
        creds = ServiceAccountCredentials.from_json_keyfile_name("credenciales.json", scope)
    cliente = gspread.authorize(creds)
    return cliente

try:
    cliente = conectar_google_sheets()
    hoja_reporte = cliente.open("Registro_Diario_Equipos").sheet1
    hoja_costos = cliente.open("Costos Diarios").worksheet("Costos_Diarios")
except Exception as e:
    st.error("❌ Error conectando a Google Sheets. Verifica los nombres de los archivos.")
    st.stop()

# ==========================================
# 1. FUNCIÓN DE CARGA DESDE GOOGLE SHEETS
# ==========================================
@st.cache_data(ttl=600)
def cargar_bd_personal_sheets():
    try:
        hoja_personal = cliente.open("Base_Personal").sheet1
        datos = hoja_personal.get_all_values()
        if len(datos) > 1:
            df = pd.DataFrame(datos[1:], columns=datos[0])
            lista = (df["DNI"].astype(str) + " - " + df["NOMBRE"]).tolist()
            return lista
        else:
            return ["00000000 - SIN BASE DE DATOS"]
    except Exception as e:
        return ["00000000 - ERROR AL CARGAR DESDE SHEETS"]

# ==========================================
# 2. BOTÓN DE ACTUALIZACIÓN MANUAL (SIDEBAR)
# ==========================================
with st.sidebar:
    st.markdown("### ⚙️ Sistema")
    if st.button("🔄 Actualizar Base de Datos", use_container_width=True):
        st.cache_data.clear()
        if "lista_personal" in st.session_state:
            del st.session_state["lista_personal"]
        st.rerun()

# ==========================================
# 3. ASIGNACIÓN A LA MEMORIA DE LA SESIÓN
# ==========================================
if "lista_personal" not in st.session_state:
    st.session_state["lista_personal"] = cargar_bd_personal_sheets()

st.markdown("""
    <style>
    input[type="text"], textarea { text-transform: uppercase; }
    div[data-testid="stHorizontalBlock"] { flex-direction: row !important; flex-wrap: nowrap !important; }
    div[data-testid="column"] { width: 100% !important; flex: 1 1 0% !important; min-width: 0 !important; padding: 0 5px !important; }
    
    /* Oculta manijas de arrastre de columna (varios intentos de selector) */
    [class*="drag-handle"],
    [class*="draggable-handle"],
    .dvn-scroller .draggable-handle,
    div[data-testid="stDataEditor"] [role="columnheader"] [draggable="true"] {
        display: none !important;
    }
    
    /* Oculta el botón de tres puntos (acciones de columna) */
    button[data-testid="column-menu-trigger"],
    button[data-testid="stDataEditorColumnActions"],
    [data-testid="column-header-menu"] button {
        display: none !important;
    }
    </style>
""", unsafe_allow_html=True)

st.components.v1.html("""
<script>
const observer = new MutationObserver(() => {
    // Eliminar manijas de arrastre
    document.querySelectorAll('[draggable="true"]').forEach(el => {
        if (el.closest('[data-testid="stDataEditor"]') && el.getAttribute('role') === 'columnheader') {
            el.setAttribute('draggable', 'false');
            el.style.cursor = 'default';
        }
    });
    // Ocultar botones de menú de columna (tres puntos)
    document.querySelectorAll('button').forEach(btn => {
        if (btn.innerText === '⋮' || btn.getAttribute('data-testid')?.includes('column-menu')) {
            btn.style.display = 'none';
        }
    });
});
observer.observe(document.body, { childList: true, subtree: true });
</script>
""", height=0)

# =====================================================================
# CREACIÓN DE LAS PESTAÑAS
# =====================================================================
tab1, tab2 = st.tabs(["📝 PARTE OPERADOR", "📈 HOJA DE PRODUCCIÓN"])

# ---------------------------------------------------------------------
# PESTAÑA 1: Ficha Diaria Original
# ---------------------------------------------------------------------
with tab1:
    st.markdown("<h3 style='text-align: center;'>Parte Diario de Operador</h3>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; font-size: 14px;'>Los campos con <span style='color: red;'>*</span> son obligatorios</p>", unsafe_allow_html=True)

    with st.form("ficha_diaria", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1: fecha = st.date_input("FECHA *", datetime.date.today())
        with col2: guardia_turno = st.selectbox("TURNO *", ["Día", "Noche"])

        col1, col2 = st.columns(2)
        with col1: operador = st.text_input("OPERADOR *").upper()
        with col2: frente_trabajo = st.text_input("FRENTE/TRABAJO *", placeholder="EJ. T-11").upper()

        col1, col2, col3 = st.columns(3)
        with col1: codigo_interno = st.text_input("CÓDIGO *", placeholder="EJ. VOL-16").upper()
        with col2: codigo_equipo = st.text_input("CÓDIGO (SAP)", placeholder="EJ. PE90/A277").upper()
        with col3: fase = st.text_input("FASE *", placeholder="EJ. EMER").upper()

        col1, col2 = st.columns(2)
        with col1: inicio_horometro = st.number_input("INICIO HOR. *", min_value=0.0, format="%.2f")
        with col2: final_horometro = st.number_input("FINAL HOR. *", min_value=0.0, format="%.2f")

        actividad = st.text_area("ACTIVIDAD/COMENTARIO").upper()
        enviado_reporte = st.form_submit_button("Guardar Ficha Diaria", use_container_width=True, type="primary")

    if enviado_reporte:
        if not operador or not frente_trabajo or not codigo_interno or not fase:
            st.error("⚠️ Faltan campos obligatorios.")
        elif final_horometro < inicio_horometro:
            st.error("⚠️ El horómetro final no puede ser menor al inicial.")
        else:
            total_horas = round(final_horometro - inicio_horometro, 2)
            fecha_str = fecha.strftime("%d/%m/%Y")

            fila_nueva = [codigo_interno, codigo_equipo, operador, fecha_str, guardia_turno,
                          inicio_horometro, final_horometro, actividad, total_horas, fase, "", frente_trabajo, ""]
            with st.spinner("⏳ Guardando ficha diaria, por favor espere..."):
                try:
                    hoja_reporte.append_row(fila_nueva, value_input_option='USER_ENTERED')
                    st.success("✅ ¡Ficha guardada con éxito!")
                    st.toast("Ficha diaria guardada", icon="✅")
                except Exception as e:
                    st.error(f"❌ Falló al enviar. Detalle del error: {e}")

# ---------------------------------------------------------------------
# PESTAÑA 2: HOJA DE PRODUCCIÓN (AUTO-NUMERADA)
# ---------------------------------------------------------------------
with tab2:
    st.markdown("<h3 style='text-align: center;'>Hoja de Producción</h3>", unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)
    with col1:
        fecha_prod = st.date_input("FECHA *", datetime.date.today(), key="fecha_prod")
    with col2:
        turno_prod = st.selectbox("TURNO *", ["DÍA", "NOCHE"], key="turno_prod")
    with col3:
        jefe_grupo_prod = st.text_input("JEFE DE GRUPO *", key="jefe_prod").upper()

    col4, col5 = st.columns(2)
    with col4:
        tramo_prod = st.text_input("TRAMO *", key="tramo_prod").upper()
    with col5:
        frente_prod = st.text_input("FRENTE DE TRABAJO *", key="frente_prod").upper()

    st.markdown("<br>", unsafe_allow_html=True)
    st.info("💡 **Preparación para el Tareo (Bloque 2):** Si un trabajador no está en la lista desplegable, agrégalo aquí antes de empezar a llenar las tablas.")

    with st.expander("➕ Agregar personal no registrado"):
        col_d, col_n, col_b = st.columns([2, 3, 1])
        with col_d:
            nuevo_dni = st.text_input("DNI Nuevo", key="tab2_dni")
        with col_n:
            nuevo_nombre = st.text_input("Nombre Nuevo", key="tab2_nombre").upper()
        with col_b:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("Añadir a la lista", use_container_width=True, key="btn_agregar_tab2"):
                if nuevo_dni and nuevo_nombre:
                    nuevo_registro = f"{nuevo_dni} - {nuevo_nombre}"
                    if nuevo_registro not in st.session_state["lista_personal"]:
                        st.session_state["lista_personal"].insert(0, nuevo_registro)
                        st.success(f"✅ {nuevo_nombre} agregado temporalmente para este registro.")
                        st.rerun()
                else:
                    st.warning("Escribe DNI y Nombre")

    st.markdown("<br>", unsafe_allow_html=True)

    with st.form("form_produccion", clear_on_submit=True):

        # Columnas de horas fijas (pinned=True)
        columnas_base_horas = {
            "ACT.1": st.column_config.NumberColumn("ACT.1", pinned=True),
            "ACT.2": st.column_config.NumberColumn("ACT.2", pinned=True),
            "ACT.3": st.column_config.NumberColumn("ACT.3", pinned=True),
            "ACT.4": st.column_config.NumberColumn("ACT.4", pinned=True),
            "ACT.5": st.column_config.NumberColumn("ACT.5", pinned=True),
        }

        st.markdown("#### Actividades")

        def crear_tabla_actividades():
            columnas = ["NOMBRE DE LA ACTIVIDAD", "UND.", "CANT.", "PROGRESIVA DEL", "PROGRESIVA AL", "LADO", "FASE"]
            df = pd.DataFrame(columns=columnas)
            for _ in range(3):
                df.loc[len(df)] = ["", "", None, "", "", "", ""]
            df.index = [1, 2, 3]
            return df

        columnas_act = {
            "_index": st.column_config.Column("ACT.", pinned=True, disabled=True),
            "NOMBRE DE LA ACTIVIDAD": st.column_config.Column(pinned=True),
            "UND.": st.column_config.Column("UND.", pinned=True),
            "CANT.": st.column_config.NumberColumn("CANT.", format="%.2f", pinned=True),
            "PROGRESIVA DEL": st.column_config.Column("PROGRESIVA DEL", pinned=True),
            "PROGRESIVA AL": st.column_config.Column("PROGRESIVA AL", pinned=True),
            "LADO": st.column_config.Column("LADO", pinned=True),
            "FASE": st.column_config.Column("FASE", pinned=True),
        }

        orden_columnas_act = [
            "_index",
            "NOMBRE DE LA ACTIVIDAD",
            "UND.",
            "CANT.",
            "PROGRESIVA DEL",
            "PROGRESIVA AL",
            "LADO",
            "FASE"
        ]

        df_actividades = st.data_editor(
            crear_tabla_actividades(),
            num_rows="dynamic",
            use_container_width=True,
            column_config=columnas_act,
            column_order=orden_columnas_act
        )

        st.markdown("---")
        st.markdown("#### Tareo de Personal")

        def crear_tabla_tareo():
            columnas = ["TAREO PERSONAL", "CARGO", "ACT.1", "ACT.2", "ACT.3", "ACT.4", "ACT.5"]
            df = pd.DataFrame(columns=columnas)
            for _ in range(3):
                df.loc[len(df)] = ["", "", None, None, None, None, None]
            df.index = [1, 2, 3]
            return df

        columnas_tareo = {
            "_index": st.column_config.Column("N°", pinned=True, disabled=True),
            "TAREO PERSONAL": st.column_config.SelectboxColumn(
                "TAREO PERSONAL",
                help="Haz doble clic y escribe el DNI o Nombre para buscar",
                options=st.session_state["lista_personal"],
                required=True,
                pinned=True
            ),
            "CARGO": st.column_config.Column("CARGO", pinned=True),
            **columnas_base_horas
        }

        orden_tareo = ["_index", "TAREO PERSONAL", "CARGO", "ACT.1", "ACT.2", "ACT.3", "ACT.4", "ACT.5"]

        df_tareo = st.data_editor(
            crear_tabla_tareo(),
            num_rows="dynamic",
            use_container_width=True,
            column_config=columnas_tareo,
            column_order=orden_tareo
        )

        st.markdown("---")
        st.markdown("#### Equipos")

        def crear_tabla_equipos():
            columnas = ["DESCRIPCION DE EQUIPOS", "CODIGO/PLACA", "ACT.1", "ACT.2", "ACT.3", "ACT.4", "ACT.5"]
            df = pd.DataFrame(columns=columnas)
            for _ in range(3):
                df.loc[len(df)] = ["", "", None, None, None, None, None]
            df.index = [1, 2, 3]
            return df

        columnas_equipos = {
            "_index": st.column_config.Column("N°", pinned=True, disabled=True),
            "DESCRIPCION DE EQUIPOS": st.column_config.Column(pinned=True),
            "CODIGO/PLACA": st.column_config.Column("CODIGO/PLACA", pinned=True),
            **columnas_base_horas
        }

        orden_equipos = ["_index", "DESCRIPCION DE EQUIPOS", "CODIGO/PLACA", "ACT.1", "ACT.2", "ACT.3", "ACT.4", "ACT.5"]

        df_equipos = st.data_editor(
            crear_tabla_equipos(),
            num_rows="dynamic",
            use_container_width=True,
            column_config=columnas_equipos,
            column_order=orden_equipos
        )

        st.markdown("---")
        st.markdown("#### Materiales (metrado)")

        def crear_tabla_materiales():
            columnas = ["DESCRIPCION DE LOS MATERIALES", "UNIDAD", "ACT.1", "ACT.2", "ACT.3", "ACT.4", "ACT.5"]
            df = pd.DataFrame(columns=columnas)
            for _ in range(3):
                df.loc[len(df)] = ["", "", None, None, None, None, None]
            df.index = [1, 2, 3]
            return df

        columnas_materiales = {
            "_index": st.column_config.Column("N°", pinned=True, disabled=True),
            "DESCRIPCION DE LOS MATERIALES": st.column_config.Column(pinned=True),
            "UNIDAD": st.column_config.Column("UNIDAD", pinned=True),
            **columnas_base_horas
        }

        orden_materiales = ["_index", "DESCRIPCION DE LOS MATERIALES", "UNIDAD", "ACT.1", "ACT.2", "ACT.3", "ACT.4", "ACT.5"]

        df_materiales = st.data_editor(
            crear_tabla_materiales(),
            num_rows="dynamic",
            use_container_width=True,
            column_config=columnas_materiales,
            column_order=orden_materiales
        )

        st.markdown("---")
        observaciones = st.text_area("OBSERVACIONES / COMENTARIOS ADICIONALES", key="obs_produccion").upper()

        st.markdown("<br>", unsafe_allow_html=True)
        enviado_prod = st.form_submit_button("Guardar Hoja de Producción", use_container_width=True, type="primary")

    # ==========================================
    # --- LÓGICA DE GUARDADO ---
    # ==========================================
    if enviado_prod:
        if not jefe_grupo_prod or not tramo_prod or not frente_prod:
            st.error("⚠️ Faltan campos obligatorios en la cabecera (Jefe, Tramo o Frente).")
        else:
            df_actividades = df_actividades.fillna("")
            df_actividades = df_actividades[df_actividades["NOMBRE DE LA ACTIVIDAD"] != ""]
            df_tareo = df_tareo.fillna("")
            df_tareo = df_tareo[df_tareo["TAREO PERSONAL"] != ""]
            df_equipos = df_equipos.fillna("")
            df_equipos = df_equipos[df_equipos["DESCRIPCION DE EQUIPOS"] != ""]
            df_materiales = df_materiales.fillna("")
            df_materiales = df_materiales[df_materiales["DESCRIPCION DE LOS MATERIALES"] != ""]

            fecha_str = fecha_prod.strftime("%d/%m/%Y")
            bloque_final = []
            
            bloque_final.append(["", "FECHA:", fecha_str, "", "", "", "", "", ""])
            bloque_final.append(["", "TURNO:", turno_prod, "", "", "", "", "", ""])
            bloque_final.append(["", "JEFE DE GRUPO:", jefe_grupo_prod, "", "", "", "", "", ""])
            bloque_final.append(["", "TRAMO:", tramo_prod, "", "", "", "", "", ""])
            bloque_final.append(["", "FRENTE:", frente_prod, "", "", "", "", "", ""])
            bloque_final.append(["", "", "", "", "", "", "", "", ""])
            
            bloque_final.append(["ACT.", "NOMBRE DE LA ACTIVIDAD", "UND.", "CANT.", "PROGRESIVA", "", "LADO", "FASE", ""])
            bloque_final.append(["", "", "", "", "DEL", "AL", "", "", ""])
            
            if not df_actividades.empty:
                df_actividades.reset_index(drop=True, inplace=True)
                for i, row in df_actividades.iterrows():
                    num_act = str(i + 1)
                    fila_limpia = [num_act] + [float(x) if isinstance(x, (int, float)) else str(x) for x in row]
                    fila_limpia.append("")
                    bloque_final.append(fila_limpia)
            else:
                bloque_final.append(["", "", "", "", "", "", "", "", ""])
            
            bloque_final.append(["", "", "", "", "", "", "", "", ""])
            len_b1 = len(bloque_final)

            def mostrar_num(n): return n if n > 0 else ""

            bloque_final.append(["N°", "TAREO PERSONAL", "CARGO", "HORAS TRABAJADAS POR ACTIVIDAD", "", "", "", "", "TOTAL HORAS"])
            bloque_final.append(["", "", "", "ACT.1", "ACT.2", "ACT.3", "ACT.4", "ACT.5", ""])
            
            suma_total_horas_personal = 0.0
            filas_datos_b2 = 0

            if not df_tareo.empty:
                df_tareo.reset_index(drop=True, inplace=True)
                for i, row in df_tareo.iterrows():
                    num_fila = str(i + 1)
                    horas_limpias = []
                    for j in range(1, 6):
                        val = row.get(f"ACT.{j}", "")
                        try:
                            horas_limpias.append(float(val) if val != "" else 0.0)
                        except:
                            horas_limpias.append(0.0)
                    
                    total_fila = sum(horas_limpias)
                    suma_total_horas_personal += total_fila
                    filas_datos_b2 += 1
                    
                    bloque_final.append([
                        num_fila, str(row["TAREO PERSONAL"]), str(row["CARGO"]),
                        mostrar_num(horas_limpias[0]), mostrar_num(horas_limpias[1]),
                        mostrar_num(horas_limpias[2]), mostrar_num(horas_limpias[3]),
                        mostrar_num(horas_limpias[4]), mostrar_num(total_fila)
                    ])
            else:
                bloque_final.append(["", "", "", "", "", "", "", "", ""])
                filas_datos_b2 = 1
                
            bloque_final.append(["", "TOTAL", "", "", "", "", "", "", mostrar_num(suma_total_horas_personal)])
            bloque_final.append(["", "", "", "", "", "", "", "", ""])
            len_b2 = len(bloque_final)

            bloque_final.append(["N°", "DESCRIPCION DE EQUIPOS", "CODIGO/PLACA", "HORAS TRABAJADAS POR ACTIVIDAD", "", "", "", "", "TOTAL HORAS"])
            bloque_final.append(["", "", "", "ACT.1", "ACT.2", "ACT.3", "ACT.4", "ACT.5", ""])
            
            filas_datos_b3 = 0

            if not df_equipos.empty:
                df_equipos.reset_index(drop=True, inplace=True)
                for i, row in df_equipos.iterrows():
                    num_fila = str(i + 1)
                    horas_limpias = []
                    for j in range(1, 6):
                        val = row.get(f"ACT.{j}", "")
                        try:
                            horas_limpias.append(float(val) if val != "" else 0.0)
                        except:
                            horas_limpias.append(0.0)
                    
                    total_fila = sum(horas_limpias)
                    filas_datos_b3 += 1
                    
                    bloque_final.append([
                        num_fila, str(row["DESCRIPCION DE EQUIPOS"]), str(row["CODIGO/PLACA"]),
                        mostrar_num(horas_limpias[0]), mostrar_num(horas_limpias[1]),
                        mostrar_num(horas_limpias[2]), mostrar_num(horas_limpias[3]),
                        mostrar_num(horas_limpias[4]), mostrar_num(total_fila)
                    ])
            else:
                bloque_final.append(["", "", "", "", "", "", "", "", ""])
                filas_datos_b3 = 1
                
            bloque_final.append(["", "", "", "", "", "", "", "", ""])
            len_b3 = len(bloque_final)

            bloque_final.append(["N°", "DESCRIPCION DE LOS MATERIALES", "UNIDAD", "CANTIDAD DE MATERIALES USADOS", "", "", "", "", "TOTAL DE MATERIAL"])
            bloque_final.append(["", "", "", "ACT.1", "ACT.2", "ACT.3", "ACT.4", "ACT.5", ""])
            
            filas_datos_b3_1 = 0

            if not df_materiales.empty:
                df_materiales.reset_index(drop=True, inplace=True)
                for i, row in df_materiales.iterrows():
                    num_fila = str(i + 1)
                    cantidades_limpias = []
                    for j in range(1, 6):
                        val = row.get(f"ACT.{j}", "")
                        try:
                            cantidades_limpias.append(float(val) if val != "" else 0.0)
                        except:
                            cantidades_limpias.append(0.0)
                    
                    total_fila = sum(cantidades_limpias)
                    filas_datos_b3_1 += 1
                    
                    bloque_final.append([
                        num_fila, str(row["DESCRIPCION DE LOS MATERIALES"]), str(row["UNIDAD"]),
                        mostrar_num(cantidades_limpias[0]), mostrar_num(cantidades_limpias[1]),
                        mostrar_num(cantidades_limpias[2]), mostrar_num(cantidades_limpias[3]),
                        mostrar_num(cantidades_limpias[4]), mostrar_num(total_fila)
                    ])
            else:
                bloque_final.append(["", "", "", "", "", "", "", "", ""])
                filas_datos_b3_1 = 1
                
            # Observaciones siempre presente, con "--" si está vacía
            texto_obs = observaciones.strip() if observaciones.strip() else "--"
            bloque_final.append(["OBSERVACIONES:", "", "", "", "", "", "", "", ""])
            bloque_final.append([texto_obs, "", "", "", "", "", "", "", ""])
            bloque_final.append(["", "", "", "", "", "", "", "", ""])

            with st.spinner("⏳ Guardando hoja de producción, esto puede tardar unos segundos..."):
                try:
                    respuesta = hoja_costos.append_rows(bloque_final, value_input_option='USER_ENTERED')
                    
                    rango_actualizado = respuesta.get('updates', {}).get('updatedRange', '')
                    celda_inicio = rango_actualizado.split('!')[1].split(':')[0]
                    fila_inicio = int(''.join(filter(str.isdigit, celda_inicio)))
                    
                    hoja_costos.format(f"B{fila_inicio}:B{fila_inicio+4}", {"textFormat": {"bold": True}, "horizontalAlignment": "RIGHT"})
                    hoja_costos.format(f"C{fila_inicio}:C{fila_inicio+4}", {"textFormat": {"bold": True}, "horizontalAlignment": "LEFT"})

                    f_tit_b1_1 = fila_inicio + 6
                    f_tit_b1_2 = fila_inicio + 7
                    f_fin_b1 = f_tit_b1_2 + (len(df_actividades) if not df_actividades.empty else 1)
                    
                    hoja_costos.merge_cells(f"E{f_tit_b1_1}:F{f_tit_b1_1}")
                    for col in ["A", "B", "C", "D", "G", "H"]:
                        hoja_costos.merge_cells(f"{col}{f_tit_b1_1}:{col}{f_tit_b1_2}")
                    
                    hoja_costos.format(f"A{f_tit_b1_1}:H{f_tit_b1_2}", {"textFormat": {"bold": True}, "horizontalAlignment": "CENTER", "verticalAlignment": "MIDDLE"})
                    hoja_costos.format(f"A{f_tit_b1_2+1}:H{f_fin_b1}", {"backgroundColor": {"red": 0.65, "green": 0.88, "blue": 0.58}})

                    f_ini_b2 = fila_inicio + len_b1
                    f_fin_b2 = f_ini_b2 + 1 + filas_datos_b2
                    
                    hoja_costos.merge_cells(f"D{f_ini_b2}:H{f_ini_b2}")
                    for col in ["A", "B", "C", "I"]:
                        hoja_costos.merge_cells(f"{col}{f_ini_b2}:{col}{f_ini_b2+1}")
                    
                    hoja_costos.format(f"A{f_ini_b2}:I{f_ini_b2+1}", {"textFormat": {"bold": True}, "horizontalAlignment": "CENTER", "verticalAlignment": "MIDDLE"})
                    hoja_costos.format(f"A{f_ini_b2+2}:I{f_fin_b2}", {"backgroundColor": {"red": 0.65, "green": 0.88, "blue": 0.58}})
                    
                    hoja_costos.merge_cells(f"A{f_fin_b2+1}:H{f_fin_b2+1}")
                    hoja_costos.format(f"A{f_fin_b2+1}:I{f_fin_b2+1}", {"textFormat": {"bold": True}, "horizontalAlignment": "CENTER"})

                    f_ini_b3 = fila_inicio + len_b2
                    f_fin_b3 = f_ini_b3 + 1 + filas_datos_b3
                    
                    hoja_costos.merge_cells(f"D{f_ini_b3}:H{f_ini_b3}")
                    for col in ["A", "B", "C", "I"]:
                        hoja_costos.merge_cells(f"{col}{f_ini_b3}:{col}{f_ini_b3+1}")
                    
                    hoja_costos.format(f"A{f_ini_b3}:I{f_ini_b3+1}", {"textFormat": {"bold": True}, "horizontalAlignment": "CENTER", "verticalAlignment": "MIDDLE"})
                    hoja_costos.format(f"A{f_ini_b3+2}:I{f_fin_b3}", {"backgroundColor": {"red": 0.65, "green": 0.88, "blue": 0.58}})

                    f_ini_b3_1 = fila_inicio + len_b3
                    f_fin_b3_1 = f_ini_b3_1 + 1 + filas_datos_b3_1
                    
                    hoja_costos.merge_cells(f"D{f_ini_b3_1}:H{f_ini_b3_1}")
                    for col in ["A", "B", "C", "I"]:
                        hoja_costos.merge_cells(f"{col}{f_ini_b3_1}:{col}{f_ini_b3_1+1}")
                    
                    hoja_costos.format(f"A{f_ini_b3_1}:I{f_ini_b3_1+1}", {"textFormat": {"bold": True}, "horizontalAlignment": "CENTER", "verticalAlignment": "MIDDLE"})
                    hoja_costos.format(f"A{f_ini_b3_1+2}:I{f_fin_b3_1}", {"backgroundColor": {"red": 0.65, "green": 0.88, "blue": 0.58}})

                    fila_obs_label = f_fin_b3_1 + 1
                    fila_obs_text  = f_fin_b3_1 + 2
                    hoja_costos.merge_cells(f"A{fila_obs_label}:H{fila_obs_label}")
                    hoja_costos.format(f"A{fila_obs_label}", {"textFormat": {"bold": True}})
                    hoja_costos.merge_cells(f"A{fila_obs_text}:H{fila_obs_text}")
                    hoja_costos.format(f"A{fila_obs_text}:H{fila_obs_text}", {"wrapStrategy": "WRAP"})

                    st.success("✅ ¡Todos los bloques de Producción se guardaron y formatearon correctamente en Excel!")
                    st.toast("Hoja de producción guardada", icon="📈")
                except Exception as e:
                    st.error(f"❌ Falló la conexión al enviar o dar formato. Error: {e}")

st.markdown("<br><hr><p style='text-align: center; color: gray; font-size: 12px;'><b>EngiLab</b> © 2026</p>", unsafe_allow_html=True)
