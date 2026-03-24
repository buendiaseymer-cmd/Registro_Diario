import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import datetime
import json

# 1. LA CONFIGURACIÓN DE PÁGINA SIEMPRE VA PRIMERO
st.set_page_config(page_title="Ficha Diaria", layout="centered")

# 2. CACHÉ DE CONEXIÓN: Evita bloqueos de Google y hace la app 10x más rápida
@st.cache_resource
def conectar_google_sheets():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    if "google_credentials" in st.secrets:
        creds_dict = json.loads(st.secrets["google_credentials"])
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    else:
        creds = ServiceAccountCredentials.from_json_keyfile_name("credenciales.json", scope)
    
    cliente = gspread.authorize(creds)
    return cliente.open("Registro_Diario_Equipos").sheet1

# Llamamos a la función optimizada
hoja = conectar_google_sheets()

# 3. ESTILOS CSS
st.markdown("""
    <style>
    /* Texto en MAYÚSCULAS */
    input[type="text"], textarea {
        text-transform: uppercase;
    }
    
    /* FORZAR columnas horizontales en celulares */
    div[data-testid="stHorizontalBlock"] {
        flex-direction: row !important;
        flex-wrap: nowrap !important;
    }
    /* Ajustar el ancho para que no se desborden */
    div[data-testid="column"] {
        width: 100% !important;
        flex: 1 1 0% !important;
        min-width: 0 !important;
        padding: 0 5px !important;
    }
    </style>
""", unsafe_allow_html=True)

st.markdown("<h3 style='text-align: center;'>Ficha de Control Diario</h3>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; font-size: 14px;'>Los campos marcados con <span style='color: red;'>*</span> son obligatorios (Celdas amarillas)</p>", unsafe_allow_html=True)

# 4. INTERFAZ Y FORMULARIO
with st.form("ficha_diaria", clear_on_submit=True):
    
    col1, col2 = st.columns(2)
    with col1:
        fecha = st.date_input("FECHA *", datetime.date.today()) 
    with col2:
        guardia_turno = st.selectbox("TURNO *", ["Día", "Noche"])

    col1, col2 = st.columns(2)
    with col1:
        operador = st.text_input("OPERADOR *").upper()
    with col2:
        frente_trabajo = st.text_input("FRENTE/TRABAJO *", placeholder="EJ. T-11").upper()

    col1, col2, col3 = st.columns(3)
    with col1:
        codigo_interno = st.text_input("CÓDIGO *", placeholder="EJ. VOL-16").upper()
    with col2:
        codigo_equipo = st.text_input("CÓDIGO EQUIPO (SAP) *", placeholder="EJ. PE90/A277").upper()
    with col3:
        fase = st.text_input("FASE *", placeholder="EJ. EMER").upper()

    col1, col2 = st.columns(2)
    with col1:
        inicio_horometro = st.number_input("INICIO HORÓMETRO/KM. *", min_value=0.0, format="%.2f")
    with col2:
        final_horometro = st.number_input("FINAL HORÓMETRO/KM. *", min_value=0.0, format="%.2f")

    actividad = st.text_area("ACTIVIDAD/COMENTARIO (Observaciones)").upper()

    st.markdown("<br>", unsafe_allow_html=True)
    
    enviado = st.form_submit_button("Guardar Ficha Diaria", use_container_width=True, type="primary")

# 5. LÓGICA DE ENVÍO Y MANEJO DE ERRORES (Try/Except)
if enviado:
    if not operador or not frente_trabajo or not codigo_interno or not codigo_equipo or not fase:
        st.error("⚠️ Faltan campos obligatorios. Por favor, completa todos los campos con asterisco (*).")
    
    elif final_horometro < inicio_horometro:
        st.error("⚠️ Error: El horómetro final no puede ser menor al inicial.")
    
    else:
        total_horas = round(final_horometro - inicio_horometro, 2)
        fecha_str = fecha.strftime("%d/%m/%y")
        
        fila_nueva = [
            codigo_interno, codigo_equipo, operador, fecha_str, guardia_turno, 
            inicio_horometro, final_horometro, actividad, total_horas, 
            fase, "", frente_trabajo, ""
        ]
        
        # El bloque "try" intenta subir los datos. Si falla el internet, pasa al "except".
        try:
            hoja.append_row(fila_nueva)
            st.success("✅ ¡Ficha guardada con éxito en la base de datos!")
            st.info(f"⏱️ **Se registraron automáticamente: {total_horas} horas de trabajo.**")
        except Exception as e:
            st.error("❌ Falló la conexión al enviar los datos. Revisa tu internet y vuelve a presionar Guardar.")

# 6. FIRMA DEL AUTOR
st.markdown("<br><hr><p style='text-align: center; color: gray; font-size: 12px;'><b>cachi</b> © 2026</p>", unsafe_allow_html=True)