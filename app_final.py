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
# PESTAÑA 2: HOJA DE PRODUCCIÓN (BLOQUE 1)
# ---------------------------------------------------------------------
with tab2:
    st.markdown("<h3 style='text-align: center;'>Hoja de Producción</h3>", unsafe_allow_html=True)
    
    # --- CABECERA DE 5 CAMPOS ---
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

    st.markdown("---")
    st.markdown("#### BLOQUE 1: Actividades")

    # --- TABLA DEL BLOQUE 1 ---
    def crear_tabla_actividades():
        # En Streamlit usamos nombres directos para las progresivas
        columnas = ["ACT.", "NOMBRE DE LA ACTIVIDAD", "UND.", "CANT.", "PROGRESIVA DEL", "PROGRESIVA AL", "LADO", "FASE"]
        df = pd.DataFrame(columns=columnas)
        # Añadimos 5 filas vacías por defecto para que sea fácil empezar a llenar
        for _ in range(5):
            df.loc[len(df)] = ["", "", "", None, "", "", "", ""]
        return df

    # Configuramos la columna CANT. para que solo acepte números
    columnas_act = {
        "CANT.": st.column_config.NumberColumn("CANT.", format="%.2f")
    }

    with st.form("form_produccion", clear_on_submit=True):
        st.markdown("**(Llena las filas necesarias. Usa el '+' para agregar más filas o la papelera para borrarlas)**")
        df_actividades = st.data_editor(
            crear_tabla_actividades(), 
            num_rows="dynamic", 
            use_container_width=True, 
            hide_index=True, 
            column_config=columnas_act
        )

        st.markdown("<br>", unsafe_allow_html=True)
        enviado_prod = st.form_submit_button("Guardar Hoja de Producción", use_container_width=True, type="primary")

    if enviado_prod:
        # Validación de campos obligatorios en cabecera
        if not jefe_grupo_prod or not tramo_prod or not frente_prod:
            st.error("⚠️ Faltan campos obligatorios en la cabecera (Jefe, Tramo o Frente).")
        else:
            # Rellenar nulos y filtrar filas que el usuario dejó totalmente vacías
            df_actividades = df_actividades.fillna("")
            df_actividades = df_actividades[df_actividades["NOMBRE DE LA ACTIVIDAD"] != ""]

            fecha_str = fecha_prod.strftime("%d/%m/%Y")
            bloque_final = []
            
            # --- CONSTRUCCIÓN DEL FORMATO PARA EXCEL ---
            # 1. Cabecera general
            bloque_final.append(["", "FECHA:", fecha_str, "", "", "", "", ""])
            bloque_final.append(["", "TURNO:", turno_prod, "", "", "", "", ""])
            bloque_final.append(["", "JEFE DE GRUPO:", jefe_grupo_prod, "", "", "", "", ""])
            bloque_final.append(["", "TRAMO:", tramo_prod, "", "", "", "", ""])
            bloque_final.append(["", "FRENTE:", frente_prod, "", "", "", "", ""])
            bloque_final.append(["", "", "", "", "", "", "", ""]) # Espacio en blanco
            
            # 2. Reconstrucción de la cabecera de la tabla (2 filas para simular celdas combinadas)
            bloque_final.append(["ACT.", "NOMBRE DE LA ACTIVIDAD", "UND.", "CANT.", "PROGRESIVA", "", "LADO", "FASE"])
            bloque_final.append(["", "", "", "", "DEL", "AL", "", ""])
            
            # 3. Datos insertados por el usuario
            if not df_actividades.empty:
                bloque_final.extend(df_actividades.values.tolist())
            else:
                bloque_final.append(["", "", "", "", "", "", "", ""]) # Fila vacía si no enviaron nada
            
            bloque_final.append(["", "", "", "", "", "", "", ""]) # Espacio final

            try:
                # Enviar datos brutos
                respuesta = hoja_costos.append_rows(bloque_final, value_input_option='USER_ENTERED')
                
                # Calcular filas para el formato visual
                rango_actualizado = respuesta.get('updates', {}).get('updatedRange', '')
                celda_inicio = rango_actualizado.split('!')[1].split(':')[0] 
                fila_inicio = int(''.join(filter(str.isdigit, celda_inicio))) 
                fila_fin = fila_inicio + len(bloque_final) - 2

                # --- APLICACIÓN DE FORMATO EXACTO AL DE TU IMAGEN ---
                # Formato Cabecera de 5 campos (Alineado a la derecha en col B, datos en col C)
                hoja_costos.format(f"B{fila_inicio}:B{fila_inicio+4}", {"textFormat": {"bold": True}, "horizontalAlignment": "RIGHT"})
                hoja_costos.format(f"C{fila_inicio}:C{fila_inicio+4}", {"textFormat": {"bold": True}, "horizontalAlignment": "LEFT"})

                # Cálculo de filas de la cabecera de la tabla
                fila_titulos_1 = fila_inicio + 6
                fila_titulos_2 = fila_inicio + 7
                
                # Combinar "PROGRESIVA" (Columnas E y F)
                hoja_costos.merge_cells(f"E{fila_titulos_1}:F{fila_titulos_1}")
                
                # Combinar verticalmente las demás columnas para que no queden partidas en 2 filas
                hoja_costos.merge_cells(f"A{fila_titulos_1}:A{fila_titulos_2}") # ACT.
                hoja_costos.merge_cells(f"B{fila_titulos_1}:B{fila_titulos_2}") # NOMBRE DE LA ACTIVIDAD
                hoja_costos.merge_cells(f"C{fila_titulos_1}:C{fila_titulos_2}") # UND.
                hoja_costos.merge_cells(f"D{fila_titulos_1}:D{fila_titulos_2}") # CANT.
                hoja_costos.merge_cells(f"G{fila_titulos_1}:G{fila_titulos_2}") # LADO
                hoja_costos.merge_cells(f"H{fila_titulos_1}:H{fila_titulos_2}") # FASE
                
                # Centrar y poner en negrita toda la cabecera de la tabla
                hoja_costos.format(f"A{fila_titulos_1}:H{fila_titulos_2}", {
                    "textFormat": {"bold": True},
                    "horizontalAlignment": "CENTER",
                    "verticalAlignment": "MIDDLE"
                })
                
                # Pintar de verde claro el área de datos ingresados
                if not df_actividades.empty:
                    hoja_costos.format(f"A{fila_titulos_2+1}:H{fila_fin}", {
                        "backgroundColor": {"red": 0.65, "green": 0.88, "blue": 0.58}
                    })

                st.success("✅ ¡Bloque 1 enviado y formateado con éxito!")
            except Exception as e:
                st.error(f"❌ Falló la conexión al enviar o dar formato. Error: {e}")

st.markdown("<br><hr><p style='text-align: center; color: gray; font-size: 12px;'><b>EngiLab</b> © 2026</p>", unsafe_allow_html=True)
