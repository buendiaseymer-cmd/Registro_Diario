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
# PESTAÑA 2: HOJA DE PRODUCCIÓN (CON COLUMNAS FIJAS)
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

    with st.form("form_produccion", clear_on_submit=True):
        
        # --- CONFIGURACIÓN BASE PARA COLUMNAS DE HORAS/CANTIDADES ---
        columnas_base_horas = {
            "ACT.1": st.column_config.NumberColumn("ACT.1"),
            "ACT.2": st.column_config.NumberColumn("ACT.2"),
            "ACT.3": st.column_config.NumberColumn("ACT.3"),
            "ACT.4": st.column_config.NumberColumn("ACT.4"),
            "ACT.5": st.column_config.NumberColumn("ACT.5"),
        }

        # ==========================================
        # BLOQUE 1: ACTIVIDADES
        # ==========================================
        st.markdown("---")
        st.markdown("#### BLOQUE 1: Actividades")

        def crear_tabla_actividades():
            columnas = ["ACT.", "NOMBRE DE LA ACTIVIDAD", "UND.", "CANT.", "PROGRESIVA DEL", "PROGRESIVA AL", "LADO", "FASE"]
            df = pd.DataFrame(columns=columnas)
            for _ in range(3):
                df.loc[len(df)] = ["", "", "", None, "", "", "", ""]
            return df

        columnas_act = {
            "ACT.": st.column_config.Column(pinned=True),
            "NOMBRE DE LA ACTIVIDAD": st.column_config.Column(pinned=True),
            "CANT.": st.column_config.NumberColumn("CANT.", format="%.2f")
        }

        df_actividades = st.data_editor(
            crear_tabla_actividades(), 
            num_rows="dynamic", use_container_width=True, hide_index=True, column_config=columnas_act
        )

        # ==========================================
        # BLOQUE 2: TAREO DE PERSONAL
        # ==========================================
        st.markdown("---")
        st.markdown("#### BLOQUE 2: Tareo de Personal")
        
        def crear_tabla_tareo():
            columnas = ["N°", "TAREO PERSONAL", "CARGO", "ACT.1", "ACT.2", "ACT.3", "ACT.4", "ACT.5"]
            df = pd.DataFrame(columns=columnas)
            for _ in range(3):
                df.loc[len(df)] = ["", "", "", None, None, None, None, None]
            return df

        columnas_tareo = {
            "N°": st.column_config.Column(pinned=True),
            "TAREO PERSONAL": st.column_config.Column(pinned=True),
            **columnas_base_horas
        }

        df_tareo = st.data_editor(
            crear_tabla_tareo(), 
            num_rows="dynamic", use_container_width=True, hide_index=True, column_config=columnas_tareo
        )

        # ==========================================
        # BLOQUE 3: EQUIPOS
        # ==========================================
        st.markdown("---")
        st.markdown("#### BLOQUE 3: Equipos")

        def crear_tabla_equipos():
            columnas = ["N°", "DESCRIPCION DE EQUIPOS", "CODIGO/PLACA", "ACT.1", "ACT.2", "ACT.3", "ACT.4", "ACT.5"]
            df = pd.DataFrame(columns=columnas)
            for _ in range(3):
                df.loc[len(df)] = ["", "", "", None, None, None, None, None]
            return df

        columnas_equipos = {
            "N°": st.column_config.Column(pinned=True),
            "DESCRIPCION DE EQUIPOS": st.column_config.Column(pinned=True),
            **columnas_base_horas
        }

        df_equipos = st.data_editor(
            crear_tabla_equipos(), 
            num_rows="dynamic", use_container_width=True, hide_index=True, column_config=columnas_equipos
        )

        # ==========================================
        # BLOQUE 3.1: MATERIALES (METRADO)
        # ==========================================
        st.markdown("---")
        st.markdown("#### BLOQUE 3.1: Materiales (metrado)")

        def crear_tabla_materiales():
            columnas = ["N°", "DESCRIPCION DE LOS MATERIALES", "UNIDAD", "ACT.1", "ACT.2", "ACT.3", "ACT.4", "ACT.5"]
            df = pd.DataFrame(columns=columnas)
            for _ in range(3):
                df.loc[len(df)] = ["", "", "", None, None, None, None, None]
            return df

        columnas_materiales = {
            "N°": st.column_config.Column(pinned=True),
            "DESCRIPCION DE LOS MATERIALES": st.column_config.Column(pinned=True),
            **columnas_base_horas
        }

        df_materiales = st.data_editor(
            crear_tabla_materiales(), 
            num_rows="dynamic", use_container_width=True, hide_index=True, column_config=columnas_materiales
        )

        st.markdown("<br>", unsafe_allow_html=True)
        enviado_prod = st.form_submit_button("Guardar Hoja de Producción", use_container_width=True, type="primary")

    if enviado_prod:
        if not jefe_grupo_prod or not tramo_prod or not frente_prod:
            st.error("⚠️ Faltan campos obligatorios en la cabecera (Jefe, Tramo o Frente).")
        else:
            # Limpieza de todos los bloques
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
            
            # --- CONSTRUCCIÓN DEL EXCEL ---
            bloque_final.append(["", "FECHA:", fecha_str, "", "", "", "", "", ""])
            bloque_final.append(["", "TURNO:", turno_prod, "", "", "", "", "", ""])
            bloque_final.append(["", "JEFE DE GRUPO:", jefe_grupo_prod, "", "", "", "", "", ""])
            bloque_final.append(["", "TRAMO:", tramo_prod, "", "", "", "", "", ""])
            bloque_final.append(["", "FRENTE:", frente_prod, "", "", "", "", "", ""])
            bloque_final.append(["", "", "", "", "", "", "", "", ""]) 
            
            # --- DATOS BLOQUE 1 ---
            bloque_final.append(["ACT.", "NOMBRE DE LA ACTIVIDAD", "UND.", "CANT.", "PROGRESIVA", "", "LADO", "FASE", ""])
            bloque_final.append(["", "", "", "", "DEL", "AL", "", "", ""])
            
            if not df_actividades.empty:
                for row in df_actividades.values.tolist():
                    fila_limpia = [float(x) if isinstance(x, (int, float)) else str(x) for x in row]
                    fila_limpia.append("") 
                    bloque_final.append(fila_limpia)
            else:
                bloque_final.append(["", "", "", "", "", "", "", "", ""]) 
            
            bloque_final.append(["", "", "", "", "", "", "", "", ""]) 
            len_b1 = len(bloque_final) 

            # Función de ayuda para números (oculta ceros)
            def mostrar_num(n): return n if n > 0 else ""

            # --- DATOS BLOQUE 2 ---
            bloque_final.append(["N°", "TAREO PERSONAL", "CARGO", "HORAS TRABAJADAS POR ACTIVIDAD", "", "", "", "", "TOTAL HORAS"])
            bloque_final.append(["", "", "", "ACT.1", "ACT.2", "ACT.3", "ACT.4", "ACT.5", ""])
            
            suma_total_horas_personal = 0.0
            filas_datos_b2 = 0

            if not df_tareo.empty:
                for index, row in df_tareo.iterrows():
                    horas_limpias = []
                    for i in range(1, 6):
                        val = row.get(f"ACT.{i}", "")
                        try:
                            horas_limpias.append(float(val) if val != "" else 0.0)
                        except:
                            horas_limpias.append(0.0)
                    
                    total_fila = sum(horas_limpias)
                    suma_total_horas_personal += total_fila
                    filas_datos_b2 += 1
                    
                    bloque_final.append([
                        str(row["N°"]), str(row["TAREO PERSONAL"]), str(row["CARGO"]), 
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

            # --- DATOS BLOQUE 3 ---
            bloque_final.append(["N°", "DESCRIPCION DE EQUIPOS", "CODIGO/PLACA", "HORAS TRABAJADAS POR ACTIVIDAD", "", "", "", "", "TOTAL HORAS"])
            bloque_final.append(["", "", "", "ACT.1", "ACT.2", "ACT.3", "ACT.4", "ACT.5", ""])
            
            filas_datos_b3 = 0

            if not df_equipos.empty:
                for index, row in df_equipos.iterrows():
                    horas_limpias = []
                    for i in range(1, 6):
                        val = row.get(f"ACT.{i}", "")
                        try:
                            horas_limpias.append(float(val) if val != "" else 0.0)
                        except:
                            horas_limpias.append(0.0)
                    
                    total_fila = sum(horas_limpias)
                    filas_datos_b3 += 1
                    
                    bloque_final.append([
                        str(row["N°"]), str(row["DESCRIPCION DE EQUIPOS"]), str(row["CODIGO/PLACA"]), 
                        mostrar_num(horas_limpias[0]), mostrar_num(horas_limpias[1]), 
                        mostrar_num(horas_limpias[2]), mostrar_num(horas_limpias[3]), 
                        mostrar_num(horas_limpias[4]), mostrar_num(total_fila)
                    ])
            else:
                bloque_final.append(["", "", "", "", "", "", "", "", ""])
                filas_datos_b3 = 1
                
            bloque_final.append(["", "", "", "", "", "", "", "", ""]) 
            len_b3 = len(bloque_final)

            # --- DATOS BLOQUE 3.1 ---
            bloque_final.append(["N°", "DESCRIPCION DE LOS MATERIALES", "UNIDAD", "CANTIDAD DE MATERIALES USADOS", "", "", "", "", "TOTAL DE MATERIAL"])
            bloque_final.append(["", "", "", "ACT.1", "ACT.2", "ACT.3", "ACT.4", "ACT.5", ""])
            
            filas_datos_b3_1 = 0

            if not df_materiales.empty:
                for index, row in df_materiales.iterrows():
                    cantidades_limpias = []
                    for i in range(1, 6):
                        val = row.get(f"ACT.{i}", "")
                        try:
                            cantidades_limpias.append(float(val) if val != "" else 0.0)
                        except:
                            cantidades_limpias.append(0.0)
                    
                    total_fila = sum(cantidades_limpias)
                    filas_datos_b3_1 += 1
                    
                    bloque_final.append([
                        str(row["N°"]), str(row["DESCRIPCION DE LOS MATERIALES"]), str(row["UNIDAD"]), 
                        mostrar_num(cantidades_limpias[0]), mostrar_num(cantidades_limpias[1]), 
                        mostrar_num(cantidades_limpias[2]), mostrar_num(cantidades_limpias[3]), 
                        mostrar_num(cantidades_limpias[4]), mostrar_num(total_fila)
                    ])
            else:
                bloque_final.append(["", "", "", "", "", "", "", "", ""])
                filas_datos_b3_1 = 1
                
            bloque_final.append(["", "", "", "", "", "", "", "", ""]) # Espacio final

            # --- ENVÍO Y FORMATO A EXCEL ---
            try:
                # 1. Insertar datos
                respuesta = hoja_costos.append_rows(bloque_final, value_input_option='USER_ENTERED')
                
                # 2. Calcular coordenadas base
                rango_actualizado = respuesta.get('updates', {}).get('updatedRange', '')
                celda_inicio = rango_actualizado.split('!')[1].split(':')[0] 
                fila_inicio = int(''.join(filter(str.isdigit, celda_inicio))) 
                
                # --- FORMATO CABECERA ---
                hoja_costos.format(f"B{fila_inicio}:B{fila_inicio+4}", {"textFormat": {"bold": True}, "horizontalAlignment": "RIGHT"})
                hoja_costos.format(f"C{fila_inicio}:C{fila_inicio+4}", {"textFormat": {"bold": True}, "horizontalAlignment": "LEFT"})

                # --- FORMATO BLOQUE 1 ---
                f_tit_b1_1 = fila_inicio + 6
                f_tit_b1_2 = fila_inicio + 7
                f_fin_b1 = f_tit_b1_2 + (len(df_actividades) if not df_actividades.empty else 1)
                
                hoja_costos.merge_cells(f"E{f_tit_b1_1}:F{f_tit_b1_1}") # PROGRESIVA
                for col in ["A", "B", "C", "D", "G", "H"]:
                    hoja_costos.merge_cells(f"{col}{f_tit_b1_1}:{col}{f_tit_b1_2}")
                
                hoja_costos.format(f"A{f_tit_b1_1}:H{f_tit_b1_2}", {"textFormat": {"bold": True}, "horizontalAlignment": "CENTER", "verticalAlignment": "MIDDLE"})
                hoja_costos.format(f"A{f_tit_b1_2+1}:H{f_fin_b1}", {"backgroundColor": {"red": 0.65, "green": 0.88, "blue": 0.58}})

                # --- FORMATO BLOQUE 2 ---
                f_ini_b2 = fila_inicio + len_b1
                f_fin_b2 = f_ini_b2 + 1 + filas_datos_b2
                
                hoja_costos.merge_cells(f"D{f_ini_b2}:H{f_ini_b2}") 
                for col in ["A", "B", "C", "I"]:
                    hoja_costos.merge_cells(f"{col}{f_ini_b2}:{col}{f_ini_b2+1}")
                
                hoja_costos.format(f"A{f_ini_b2}:I{f_ini_b2+1}", {"textFormat": {"bold": True}, "horizontalAlignment": "CENTER", "verticalAlignment": "MIDDLE"})
                hoja_costos.format(f"A{f_ini_b2+2}:I{f_fin_b2}", {"backgroundColor": {"red": 0.65, "green": 0.88, "blue": 0.58}})
                
                hoja_costos.merge_cells(f"A{f_fin_b2+1}:H{f_fin_b2+1}")
                hoja_costos.format(f"A{f_fin_b2+1}:I{f_fin_b2+1}", {"textFormat": {"bold": True}, "horizontalAlignment": "CENTER"})

                # --- FORMATO BLOQUE 3 ---
                f_ini_b3 = fila_inicio + len_b2
                f_fin_b3 = f_ini_b3 + 1 + filas_datos_b3
                
                hoja_costos.merge_cells(f"D{f_ini_b3}:H{f_ini_b3}") 
                for col in ["A", "B", "C", "I"]:
                    hoja_costos.merge_cells(f"{col}{f_ini_b3}:{col}{f_ini_b3+1}")
                
                hoja_costos.format(f"A{f_ini_b3}:I{f_ini_b3+1}", {"textFormat": {"bold": True}, "horizontalAlignment": "CENTER", "verticalAlignment": "MIDDLE"})
                hoja_costos.format(f"A{f_ini_b3+2}:I{f_fin_b3}", {"backgroundColor": {"red": 0.65, "green": 0.88, "blue": 0.58}})

                # --- FORMATO BLOQUE 3.1 ---
                f_ini_b3_1 = fila_inicio + len_b3
                f_fin_b3_1 = f_ini_b3_1 + 1 + filas_datos_b3_1
                
                hoja_costos.merge_cells(f"D{f_ini_b3_1}:H{f_ini_b3_1}") 
                for col in ["A", "B", "C", "I"]:
                    hoja_costos.merge_cells(f"{col}{f_ini_b3_1}:{col}{f_ini_b3_1+1}")
                
                hoja_costos.format(f"A{f_ini_b3_1}:I{f_ini_b3_1+1}", {"textFormat": {"bold": True}, "horizontalAlignment": "CENTER", "verticalAlignment": "MIDDLE"})
                hoja_costos.format(f"A{f_ini_b3_1+2}:I{f_fin_b3_1}", {"backgroundColor": {"red": 0.65, "green": 0.88, "blue": 0.58}})

                st.success("✅ ¡Todos los bloques de Producción se guardaron y formatearon correctamente en Excel!")
            except Exception as e:
                st.error(f"❌ Falló la conexión al enviar o dar formato. Error: {e}")

st.markdown("<br><hr><p style='text-align: center; color: gray; font-size: 12px;'><b>EngiLab</b> © 2026</p>", unsafe_allow_html=True)
