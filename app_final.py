import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import datetime
import json
import pandas as pd

st.set_page_config(page_title="Control Diario y Costos", layout="centered", page_icon="🏗️")

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

st.markdown("""
    <style>
    input[type="text"], textarea { text-transform: uppercase; }
    div[data-testid="stHorizontalBlock"] { flex-direction: row !important; flex-wrap: nowrap !important; }
    div[data-testid="column"] { width: 100% !important; flex: 1 1 0% !important; min-width: 0 !important; padding: 0 5px !important; }
    </style>
""", unsafe_allow_html=True)

# =====================================================================
# CREACIÓN DE LAS PESTAÑAS (TABS)
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
        with col2: codigo_equipo = st.text_input("CÓDIGO (SAP) *", placeholder="EJ. PE90/A277").upper()
        with col3: fase = st.text_input("FASE *", placeholder="EJ. EMER").upper()

        col1, col2 = st.columns(2)
        with col1: inicio_horometro = st.number_input("INICIO HOR. *", min_value=0.0, format="%.2f")
        with col2: final_horometro = st.number_input("FINAL HOR. *", min_value=0.0, format="%.2f")

        actividad = st.text_area("ACTIVIDAD/COMENTARIO").upper()
        enviado_reporte = st.form_submit_button("Guardar Ficha Diaria", use_container_width=True, type="primary")

    if enviado_reporte:
        if not operador or not frente_trabajo or not codigo_interno or not codigo_equipo or not fase:
            st.error("⚠️ Faltan campos obligatorios.")
        elif final_horometro < inicio_horometro:
            st.error("⚠️ El horómetro final no puede ser menor al inicial.")
        else:
            total_horas = round(final_horometro - inicio_horometro, 2)
            fecha_str = fecha.strftime("%d/%m/%y")
            # En Pestaña 1 también aplicamos USER_ENTERED para que total_horas y horómetros sean números
            fila_nueva = [codigo_interno, codigo_equipo, operador, fecha_str, guardia_turno, 
                          inicio_horometro, final_horometro, actividad, total_horas, fase, "", frente_trabajo, ""]
            try:
                hoja_reporte.append_row(fila_nueva, value_input_option='USER_ENTERED')
                st.success("✅ ¡Ficha guardada con éxito!")
            except Exception as e:
                st.error("❌ Falló la conexión al enviar. Reintenta.")

# ---------------------------------------------------------------------
# PESTAÑA 2: Módulo de Costos con Formato
# ---------------------------------------------------------------------
with tab2:
    st.markdown("<h3 style='text-align: center;'>Hoja de Producción</h3>", unsafe_allow_html=True)
    
    # --- NUEVOS CAMPOS DE CABECERA ---
    col1, col2 = st.columns(2)
    with col1:
        fecha_costos = st.date_input("FECHA DE REPORTE *", datetime.date.today(), key="fecha_costo")
        jefe_grupo = st.text_input("JEFE DE GRUPO *").upper()
    with col2:
        turno_costos = st.selectbox("TURNO *", ["DÍA", "NOCHE"], key="turno_costos")
        frente_costos = st.text_input("FRENTE / TRABAJO *", key="frente_costos").upper()

    base_mo = [["Jefe de Grupo", "hh"], ["Oficial", "hh"], ["Oficial Plantillero", "hh"], ["Ayudante", "hh"], ["Operario", "hh"], ["Op. Camion Micropavimentador", "hh"], ["Op. Caja Esparcidora", "hh"], ["Op. Retroexcavadora", "hh"], ["Op. Camion Baranda", "hh"], ["Op. Minicargador", "hh"], ["Op. Cisterna de Agua", "hh"], ["Op. Cisterna de Emulsion 5,000 gln", "hh"], ["Op. Rastrillero", "hh"], ["Op. Esquinero", "hh"], ["Op. Cargador Frontal", "hh"], ["Vigia Mype", "hh"], ["Vigilante Mype", "hh"]]
    base_eq = [["Minicargador", "HM"], ["Cisterna Estacionaria", "DM"], ["Cisterna de emulsion 5,000 gln", "DM"], ["Cisterna de agua de 4,000 gln cantera", "HM"], ["Camion Micropavimentador", "HM"], ["Compresora de Aire", "HM"], ["Retroexcavadora", "HM"], ["Cargador Frontral", "HM"], ["Camion Baranda de 4 tn", "DM"], ["Coaster de 24 pasajeros", "DM"]]
    base_mat = [["Emulsión", "-"], ["Emulsion Controlada", "gal"], ["Cemento", "bls"], ["Arena Chancada", "m3"], ["GETs de Equipos", "%"], ["Herramientas Manuales", "%"]]

    # --- TABLA REDUCIDA A 2 COLUMNAS ---
    def crear_tabla(datos_base):
        df = pd.DataFrame(datos_base, columns=["Descripción del recurso", "Und"])
        df["Cant"] = None
        df["Hr"] = None
        return df

    # Forzar columnas numéricas
    columnas_numericas = {
        "Cant": st.column_config.NumberColumn("Cant"),
        "Hr": st.column_config.NumberColumn("Hr")
    }

    with st.form("form_costos", clear_on_submit=True):
        st.markdown("**(Puedes editar los casilleros y usar el botón '+' abajo para agregar recursos nuevos)**")
        
        st.markdown("#### 👷‍♂️ Mano de Obra")
        df_mo = st.data_editor(crear_tabla(base_mo), num_rows="dynamic", use_container_width=True, hide_index=True, column_config=columnas_numericas)
        
        st.markdown("#### 🚜 Equipo")
        df_eq = st.data_editor(crear_tabla(base_eq), num_rows="dynamic", use_container_width=True, hide_index=True, column_config=columnas_numericas)
        
        st.markdown("#### 🧱 Materiales")
        df_mat = st.data_editor(crear_tabla(base_mat), num_rows="dynamic", use_container_width=True, hide_index=True, column_config=columnas_numericas)

        st.markdown("<br>", unsafe_allow_html=True)
        enviado_costos = st.form_submit_button("Guardar Formato", use_container_width=True, type="primary")

    if enviado_costos:
        # Validación rápida para los nuevos campos
        if not jefe_grupo or not frente_costos:
            st.error("⚠️ Faltan campos obligatorios en la cabecera (Jefe de Grupo o Frente).")
        else:
            # Reemplazar Nulos por strings vacíos
            df_mo = df_mo.fillna("")
            df_eq = df_eq.fillna("")
            df_mat = df_mat.fillna("")

            fecha_str = fecha_costos.strftime("%d/%m/%Y")
            bloque_final = []
            
            # --- NUEVA ESTRUCTURA DEL EXCEL ---
            # Cabecera de 4 filas ubicadas en las columnas C (Títulos) y D (Respuestas)
            bloque_final.append(["", "", "FECHA:", fecha_str])
            bloque_final.append(["", "", "JEFE DE GRUPO:", jefe_grupo])
            bloque_final.append(["", "", "FRENTE:", frente_costos])
            bloque_final.append(["", "", "TURNO:", turno_costos])
            bloque_final.append(["", "", "", ""]) # Espacio en blanco
            
            # Tablas (ahora son de 4 columnas de la A a la D)
            bloque_final.append(["Descripción del recurso", "Und", "Cant", "Hr"])
            bloque_final.append(["Mano de obra", "", "", ""])
            bloque_final.extend(df_mo.values.tolist())
            bloque_final.append(["Equipo", "", "", ""])
            bloque_final.extend(df_eq.values.tolist())
            bloque_final.append(["Materiales", "", "", ""])
            bloque_final.extend(df_mat.values.tolist())
            bloque_final.append(["", "", "", ""]) # Fila en blanco final

            try:
                # 1. Insertamos los datos
                respuesta = hoja_costos.append_rows(bloque_final, value_input_option='USER_ENTERED')
                
                # 2. Leemos la fila exacta de inicio
                rango_actualizado = respuesta.get('updates', {}).get('updatedRange', '')
                celda_inicio = rango_actualizado.split('!')[1].split(':')[0] 
                fila_inicio = int(''.join(filter(str.isdigit, celda_inicio))) 
                
                # 3. Recalculamos posiciones (ahora sumando la nueva cabecera de 5 filas)
                fila_fin = fila_inicio + len(bloque_final) - 1
                fila_eq = fila_inicio + 7 + len(df_mo)
                fila_mat = fila_eq + 1 + len(df_eq)

                # --- FORMATO VISUAL ---
                
                # Cabecera: Negritas para etiquetas en col C, centrado para datos en col D
                hoja_costos.format(f"C{fila_inicio}:C{fila_inicio+3}", {
                    "textFormat": {"bold": True},
                    "horizontalAlignment": "RIGHT"
                })
                hoja_costos.format(f"D{fila_inicio}:D{fila_inicio+3}", {
                    "horizontalAlignment": "CENTER",
                    "textFormat": {"bold": True}
                })

                # Títulos de las tablas en negrita
                hoja_costos.format(f"A{fila_inicio+5}:D{fila_inicio+5}", {"textFormat": {"bold": True}})
                hoja_costos.format(f"A{fila_inicio+6}", {"textFormat": {"bold": True}})
                hoja_costos.format(f"A{fila_eq}", {"textFormat": {"bold": True}})
                hoja_costos.format(f"A{fila_mat}", {"textFormat": {"bold": True}})
                
                # Bloque verde reajustado a las nuevas columnas C y D (Cant y Hr)
                hoja_costos.format(f"C{fila_inicio+6}:D{fila_fin-1}", {
                    "backgroundColor": {"red": 0.57, "green": 0.81, "blue": 0.31}
                })

                st.success("✅ ¡Bloque enviado y formato visual aplicado correctamente!")
            except Exception as e:
                st.error(f"❌ Falló la conexión al enviar o dar formato. Error: {e}")

st.markdown("<br><hr><p style='text-align: center; color: gray; font-size: 12px;'><b>EngiLab</b> © 2026</p>", unsafe_allow_html=True)
