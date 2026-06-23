import streamlit as st
import pandas as pd
import plotly.express as px
from streamlit_option_menu import option_menu
from datetime import datetime, date
import os
from sqlalchemy import create_engine
import cloudinary
import cloudinary.uploader

import io
import json

# ------------------------------------------------
# CONFIG APP
# ------------------------------------------------

st.set_page_config(
    page_title="OWD Venier",
    page_icon="📋",
    layout="wide"
)

if "form_id" not in st.session_state:

    st.session_state.form_id = 0

# ------------------------------------------------
# POSTGRESQL
# ------------------------------------------------

DATABASE_URL = os.getenv("DATABASE_URL")

if DATABASE_URL:
    engine = create_engine(DATABASE_URL)
else:
    engine = None

cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET"),
    secure=True
)

# =========================================================
# LEER TABLAS
# =========================================================

def leer_sql(tabla):

    try:

        return pd.read_sql(
            f'SELECT * FROM "{tabla}"',
            engine
        )

    except Exception as e:

        print(f"Error leyendo {tabla}: {e}")

        return pd.DataFrame()


# ------------------------------------------------
# GUARDAR TABLAS MAESTRAS
# ------------------------------------------------

def guardar_sql(df, tabla):

    st.cache_data.clear()

    df.to_sql(
        tabla,
        engine,
        if_exists="replace",
        index=False
    )


# ------------------------------------------------
# AGREGAR RESPUESTAS
# ------------------------------------------------

def agregar_respuestas_sql(df):

    st.cache_data.clear()

    df.to_sql(
        "RESPUESTAS",
        engine,
        if_exists="append",
        index=False
    )


# ------------------------------------------------
# ELIMINAR AUDITORÍA
# ------------------------------------------------

def eliminar_auditoria_sql(id_auditoria):

    with engine.begin() as conn:

        conn.exec_driver_sql(
            """
            DELETE FROM "RESPUESTAS"
            WHERE "ID_AUDITORIA" = %s
            """,
            (str(id_auditoria),)
        )

# ------------------------------------------------
# ACTUALIZAR PDA
# ------------------------------------------------

def actualizar_pda_sql(
    id_auditoria,
    plan_accion,
    responsable,
    fecha_limite,
    estado,
    evidencia
):

    with engine.begin() as conn:

        conn.exec_driver_sql(
            """
            UPDATE "RESPUESTAS"
            SET
                "PLAN_ACCION" = %s,
                "RESPONSABLE" = %s,
                "FECHA_LIMITE" = %s,
                "ESTADO" = %s,
                "EVIDENCIA" = %s
            WHERE
                "ID_AUDITORIA" = %s
                AND "PREGUNTA" = 'Requiere Plan de Acción'
            """,
            (
                plan_accion,
                responsable,
                str(fecha_limite),
                estado,
                evidencia,
                str(id_auditoria)
            )
        )

# ------------------------------------------------
# SUBIR IMAGEN A CLOUDINARY
# # ------------------------------------------------

def subir_imagen_cloudinary(
    archivo,
    carpeta="owd_venier"
):

    resultado = cloudinary.uploader.upload(
        archivo,
        folder=carpeta,
        resource_type="image"
    )

    return resultado["secure_url"]

# ------------------------------------------------
# LEER EXCEL
# ------------------------------------------------

df_procesos = leer_sql("PROCESOS")
df_auditores = leer_sql("AUDITORES")
df_localidades = leer_sql("LOCALIDADES")
df_auditados = leer_sql("AUDITADOS")
df_motivos = leer_sql("MOTIVOS")
df_sectores = leer_sql("SECTORES")
df_areas = leer_sql("AREAS")
df_empresas = leer_sql("EMPRESAS")
df_pilares = leer_sql("PILARES")

# ------------------------------------------------
# LISTAS
# ------------------------------------------------

lista_pilares = [""] + sorted(
    df_pilares[
        df_pilares["PILAR"]
        .astype(str)
        .str.upper()
        != "GENERAL"
    ]["PILAR"]
    .dropna()
    .astype(str)
    .tolist()
)

lista_auditores = (
    df_auditores.iloc[:, 0]
    .dropna()
    .astype(str)
    .tolist()
)

lista_localidades = [""] + (
    df_localidades.iloc[:, 0]
    .dropna()
    .astype(str)
    .tolist()
)

lista_auditados = [""] + (
    df_auditados["Auditados"]
    .dropna()
    .astype(str)
    .tolist()
)

lista_motivos = [""] + (
    df_motivos.iloc[:, 0]
    .dropna()
    .astype(str)
    .tolist()
)

lista_sectores = [""] + (
    df_sectores.iloc[:, 0]
    .dropna()
    .astype(str)
    .tolist()
)

lista_areas = [""] + (
    df_areas.iloc[:, 0]
    .dropna()
    .astype(str)
    .tolist()
)

lista_empresas = [""] + (
    df_empresas.iloc[:, 0]
    .dropna()
    .astype(str)
    .tolist()
)

# ------------------------------------------------
# SIDEBAR
# ------------------------------------------------
st.sidebar.image(
    "Logo Grupo Venier.png",
    use_container_width=True
)

with st.sidebar:

    seleccion = option_menu(
        menu_title="OWD Venier",
        options=[
            "Nueva Auditoría",
            "Dashboard",
            "Planes de Acción",
            "Historial",
            "Maestros",
            "Calendario"
        ],
        icons=[
            "clipboard-check",
            "bar-chart",
            "exclamation-triangle",
            "clock-history",
            "gear",
            "calendar"
        ],
        default_index=0
    )

    # ================================================
    # AUTORÍA - Agregar esto abajo de todo
    # ================================================
    
    st.markdown("---")  # Línea separadora
    st.markdown(
        """
        <div style='text-align: center; color: gray; font-size: 12px; padding: 10px;'>
            By Pato Frangi
        </div>
        """,
        unsafe_allow_html=True
    )

# =========================================================
# NUEVA AUDITORÍA
# =========================================================

modo_edicion = False

if "editar_id" in st.session_state:

    modo_edicion = True

    id_editar = st.session_state["editar_id"]

    df_edicion = leer_sql("RESPUESTAS")

    df_edicion = df_edicion[
        df_edicion["ID_AUDITORIA"].astype(str)
        == str(id_editar)
    ]

    if not df_edicion.empty:

        info_edicion = df_edicion.iloc[0]

if seleccion == "Nueva Auditoría":

    st.title("📝 Nueva Auditoría")

    # ------------------------------------------------
    # ALERTAS DE PDA
    # ------------------------------------------------

    from datetime import datetime

    try:

        df_alertas = leer_sql("RESPUESTAS")

        df_alertas = df_alertas[
            (df_alertas["PREGUNTA"] == "Requiere Plan de Acción")
            &
            (df_alertas["RESPUESTA"] == "Si")
            &
            (df_alertas["ESTADO"] != "Completado")
        ]

        if not df_alertas.empty:

            hoy = datetime.now().date()

            resumen_responsables = {}

            for _, fila in df_alertas.iterrows():

                fecha_limite = pd.to_datetime(
                    fila["FECHA_LIMITE"],
                    errors="coerce"
                )

                if pd.isna(fecha_limite):
                    continue

                dias = (
                    fecha_limite.date() - hoy
                ).days

                responsable = str(
                    fila["RESPONSABLE"]
                ).strip()

                if responsable == "":
                    responsable = "Sin Responsable"

                if responsable not in resumen_responsables:

                    resumen_responsables[responsable] = {
                        "total": 0,
                        "vencidos": 0
                    }

                resumen_responsables[responsable]["total"] += 1

                if dias < 0:

                    resumen_responsables[responsable]["vencidos"] += 1

            if resumen_responsables:

                st.warning(
                    f"🚨 Hay {sum(d['total'] for d in resumen_responsables.values())} Planes de Acción pendientes"
                )

                with st.expander(
                    "Ver detalle por Responsable",
                    expanded=True
                ):

                    for responsable, datos in sorted(
                        resumen_responsables.items(),
                        key=lambda x: x[1]["vencidos"],
                        reverse=True
                    ):

                        icono = "🔴" if datos["vencidos"] > 0 else "🟡"

                        st.markdown(
                            f"""
            **{icono} {responsable}**

            • PDA pendientes: **{datos['total']}**  
            • PDA vencidos: **{datos['vencidos']}**
            """
                        )

                        st.divider()

    except:
        pass

    # ------------------------------------------------
    # AUDITORÍA
    # ------------------------------------------------

    st.subheader("👤 Auditoría")

    fecha = st.date_input("Fecha")

    auditor = st.multiselect(
        "Auditor",
        lista_auditores,
        key=f"{st.session_state.form_id}_auditor"
    )

    st.divider()

    # ------------------------------------------------
    # DATOS OPERATIVOS
    # ------------------------------------------------

    st.subheader("🏢 Datos Operativos")

    empresa = st.selectbox(
        "Empresa",
        lista_empresas,
        index=0,
        key=f"{st.session_state.form_id}_empresa"
    )

    if empresa != "":

        lista_auditados_filtrados = [""] + sorted(
            df_auditados[
                df_auditados["Empresa"]
                .astype(str)
                .str.strip()
                .str.upper()
                ==
                str(empresa)
                .strip()
                .upper()
            ]["Auditados"]
            .dropna()
            .astype(str)
            .tolist()
        )

    else:

        lista_auditados_filtrados = [""] + sorted(
            df_auditados["Auditados"]
            .dropna()
            .astype(str)
            .tolist()
        )

    auditado = st.selectbox(
        "Auditado",
        lista_auditados_filtrados,
        index=0,
        key=f"{st.session_state.form_id}_auditado"
    )

    sector = st.selectbox(
        "Sector",
        lista_sectores,
        index=0,
        key=f"{st.session_state.form_id}_sector"
    )

    area = st.selectbox(
        "Área",
        lista_areas,
        index=0,
        key=f"{st.session_state.form_id}_area"
    )

    if empresa != "":

        lista_localidades_filtradas = [""] + sorted(
            df_localidades[
                df_localidades["Empresa"]
                .astype(str)
                .str.strip()
                .str.upper()
                ==
                str(empresa)
                .strip()
                .upper()
            ]["Localidades"]
            .dropna()
            .astype(str)
            .tolist()
        )

    else:

        lista_localidades_filtradas = [""] + sorted(
            df_localidades["Localidades"]
            .dropna()
            .astype(str)
            .tolist()
        )

    localidad = st.selectbox(
        "Localidad",
        lista_localidades_filtradas,
        index=0
    )

    motivo = st.selectbox(
        "Motivo",
        lista_motivos,
        index=0,
        key=f"{st.session_state.form_id}_motivo"
    )

    pilar = st.selectbox(
        "Pilar",
        lista_pilares,
        index=0,
        key=f"{st.session_state.form_id}_pilar"
    )

    # ------------------------------------------------
    # FILTRAR PROCESOS
    # ------------------------------------------------

    if pilar != "":

        lista_procesos_filtrados = [""] + sorted(
            df_procesos[
                df_procesos["PILAR"] == pilar
                ]["PROCESO"]
                .dropna()
                .astype(str)
                .tolist()
            )

    else:

        lista_procesos_filtrados = [""]

    proceso = st.selectbox(
        "Proceso",
        lista_procesos_filtrados,
        index=0
    )

    st.divider()

    # ------------------------------------------------
    # LEER PREGUNTAS
    # ------------------------------------------------

    df_preguntas = leer_sql("PREGUNTAS")

    respuestas = {}

    # ------------------------------------------------
    # MOSTRAR PREGUNTAS
    # ------------------------------------------------

    if proceso != "":

        proceso_id = df_procesos[
            df_procesos["PROCESO"] == proceso
        ]["ID"].values[0]

        preguntas_proceso = df_preguntas[
            (
                (df_preguntas["PROCESO_ID"] == proceso_id)
                |
                (df_preguntas["SECCION"] == "Preguntas Generales")
            )
            &                (df_preguntas["ACTIVA"] == "Si")
        ]

        secciones = preguntas_proceso[
            "SECCION"
        ].unique()

        for seccion in secciones:

            st.subheader(f"📂 {seccion}")

            preguntas_seccion = preguntas_proceso[
            preguntas_proceso["SECCION"] == seccion
            ]

            for _, fila in preguntas_seccion.iterrows():

                pregunta_id = fila["ID"]
                pregunta = fila["PREGUNTA"]
                tipo = str(fila["TIPO"]).upper()

                visible_si = str(
                    fila["VISIBLE_SI"]
                )

                mostrar = True

                # ------------------------------------------------
                # VISIBILIDAD CONDICIONAL
                # ------------------------------------------------

                if visible_si != "nan":

                    try:

                        condicion = visible_si.replace(
                            " ",
                            ""
                        )

                        pregunta_condicional = (
                            condicion.split("=")[0]
                        )

                        valor_condicional = (
                            condicion.split("=")[1]
                        )

                        id_condicional = int(
                            pregunta_condicional.replace(
                                "P",
                                ""
                            )
                        )

                        respuesta_anterior = respuestas.get(
                            id_condicional
                        )

                        if (
                            str(respuesta_anterior)
                            != valor_condicional
                        ):
                            mostrar = False

                    except:

                        mostrar = False

                # ------------------------------------------------
                # MOSTRAR PREGUNTA
                # ------------------------------------------------

                if mostrar:

                    respuesta = None

                    # RADIO

                    if tipo == "RADIO":

                        opciones = [""] + (
                            str(fila["OPCIONES"])
                            .split("|")
                        )

                        respuesta = st.radio(
                            pregunta,
                            opciones,
                            horizontal=True,
                            index=0,
                            key=f"{st.session_state.form_id}_pregunta_{pregunta_id}"
                        )

                    # SELECT

                    elif tipo == "SELECT":

                        opciones = (
                            str(fila["OPCIONES"])
                            .split("|")
                        )

                        respuesta = st.selectbox(
                            pregunta,
                            [""] + opciones,
                            key=f"{st.session_state.form_id}_pregunta_{pregunta_id}"
                        )

                    # TEXTO

                    elif tipo == "TEXTO":

                        if pregunta == "Responsable":

                            respuesta = st.selectbox(
                                pregunta,
                                [""] + lista_auditores,
                                key=f"{st.session_state.form_id}_pregunta_{pregunta_id}"
                            )

                        else:

                            respuesta = st.text_area(
                                pregunta,
                                key=f"{st.session_state.form_id}_pregunta_{pregunta_id}"
                            )

                    # NUMERO

                    elif tipo == "NUMERO":

                        respuesta = st.number_input(
                            pregunta,
                            key=f"{st.session_state.form_id}_pregunta_{pregunta_id}"
                        )

                    # FECHA

                    elif tipo == "FECHA":

                        respuesta = st.date_input(
                            pregunta,
                            key=f"{st.session_state.form_id}_pregunta_{pregunta_id}"
                        )

                    # FOTO

                    elif tipo == "FOTO":

                        respuesta = st.camera_input(
                            pregunta,
                            key=f"{st.session_state.form_id}_pregunta_{pregunta_id}"
                        )

                    respuestas[pregunta_id] = respuesta

        st.divider()

        # ------------------------------------------------
        # OBSERVACIONES
        # ------------------------------------------------

        st.subheader("📝 Observaciones")

        observacion = st.text_area(
            "Observaciones Generales",
            height=120,
            placeholder="Ingrese comentarios, hallazgos o aclaraciones de la auditoría..."
        )

        st.divider()

        # ------------------------------------------------
        # FOTO GENERAL
        # ------------------------------------------------

        st.subheader("📷 Evidencia Fotográfica")

        col_foto1, col_foto2 = st.columns(2)

        foto_general = None
        foto_camara = None

        # --------------------------------------------
        # TOMAR FOTO
        # --------------------------------------------

        with col_foto1:

            st.markdown("### 📸 Tomar Foto")

            activar_camara = st.toggle(
                "Abrir cámara"
            )

            if activar_camara:

                foto_camara = st.camera_input(
                    "Capturar imagen"
                )

        # --------------------------------------------
        # CARGAR FOTO
        # --------------------------------------------

        with col_foto2:

            st.markdown("### 🖼️ Cargar Foto")

            archivo_galeria = st.file_uploader(
                "Seleccionar imagen",
                type=["png", "jpg", "jpeg"]
            )

        # --------------------------------------------
        # DEFINIR FOTO FINAL
        # --------------------------------------------

        if foto_camara is not None:

            foto_general = foto_camara

        elif archivo_galeria is not None:

            foto_general = archivo_galeria

        # --------------------------------------------
        # VISTA PREVIA
        # --------------------------------------------

        if foto_general is not None:

            st.divider()

            st.markdown("### 👁️ Vista previa")

            st.image(
                foto_general,
                use_container_width=True
            )

        st.divider()

        # ------------------------------------------------
        # BOTON GUARDAR
        # ------------------------------------------------

        guardar = st.button(
            "💾 Guardar Auditoría"
        )

        # ========================================================
        # GUARDAR
        # ========================================================

        if guardar:

            campos_faltantes = []

            if empresa == "":
                campos_faltantes.append("Empresa")

            if auditado == "":
                campos_faltantes.append("Auditado")

            if sector == "":
                campos_faltantes.append("Sector")

            if area == "":
                campos_faltantes.append("Área")

            if localidad == "":
                campos_faltantes.append("Localidad")

            if motivo == "":
                campos_faltantes.append("Motivo")

            if pilar == "":
                campos_faltantes.append("Pilar")

            if proceso == "":
                campos_faltantes.append("Proceso")

            if len(auditor) == 0:
                campos_faltantes.append("Auditor")

            # ------------------------------------------------
            # MOSTRAR ERROR
            # ------------------------------------------------

            if len(campos_faltantes) > 0:

                st.error(
                    "⚠️ Completar campos obligatorios: "
                    + ", ".join(campos_faltantes)
                )

            else:

                from datetime import datetime
                import os

                id_auditoria = datetime.now().strftime(
                    "%Y%m%d%H%M%S"
                )

                datos_auditoria = []

                # ------------------------------------------------
                # GUARDAR FOTO
                # ------------------------------------------------

                foto_path = ""

                if foto_general is not None:

                    foto_path = subir_imagen_cloudinary(
                        foto_general,
                        "auditorias"
                    )

                # ------------------------------------------------
                # CALCULO SCORE
                # ------------------------------------------------

                preguntas_excluidas = [
                    "Requiere Plan de Acción",
                    "Plan de Acción",
                    "Responsable",
                    "Fecha Limite"
                ]

                total_preguntas = 0
                total_si = 0

                # ------------------------------------------------
                # CAPTURAR DATOS DEL PDA
                # ------------------------------------------------

                plan_accion_valor = ""
                responsable_valor = ""
                fecha_limite_valor = ""

                for pregunta_id, respuesta in respuestas.items():

                    pregunta_info = df_preguntas[
                        df_preguntas["ID"] == pregunta_id
                    ]

                    if pregunta_info.empty:
                        continue

                    pregunta_texto = (
                        pregunta_info.iloc[0]["PREGUNTA"]
                    )

                    if pregunta_texto == "Plan de Acción":
                        plan_accion_valor = respuesta

                    elif pregunta_texto == "Responsable":
                        responsable_valor = respuesta

                    elif pregunta_texto == "Fecha Limite":
                        fecha_limite_valor = respuesta

                # ------------------------------------------------
                # RECORRER RESPUESTAS
                # ------------------------------------------------

                for pregunta_id, respuesta in respuestas.items():

                    pregunta_info = df_preguntas[
                        df_preguntas["ID"] == pregunta_id
                    ]

                    if pregunta_info.empty:
                        continue

                    pregunta_texto = (
                        pregunta_info.iloc[0]["PREGUNTA"]
                    )

                    seccion_pregunta = (
                        pregunta_info.iloc[0]["SECCION"]
                    )

                    score_pregunta = "None"

                    if pregunta_texto not in [
                        "Plan de Acción",
                        "Responsable",
                        "Fecha Limite"
                    ]:

                        if (
                            pregunta_texto not in [
                                "Requiere Plan de Acción"
                            ]
                            and str(respuesta) in ["Si", "No"]
                        ):

                            total_preguntas += 1

                            if str(respuesta) == "Si":

                                total_si += 1
                                score_pregunta = 100

                            else:

                                score_pregunta = 0

                        datos_auditoria.append({

                            "ID_AUDITORIA": id_auditoria,

                            "FECHA": fecha,

                            "AUDITOR": ", ".join(auditor),

                            "SECTOR": sector,

                            "AREA": area,

                            "EMPRESA": empresa,

                            "AUDITADO": auditado,

                            "LOCALIDAD": localidad,

                            "MOTIVO_OWD": motivo,

                            "PROCESO": proceso,

                            "PILAR": (
                                "GENERAL"
                                if seccion_pregunta == "Preguntas Generales"
                                else pilar
                            ),

                            "SECCION": seccion_pregunta,

                            "PREGUNTA": pregunta_texto,

                            "RESPUESTA": respuesta,

                            "OBSERVACION": observacion,

                            "SCORE": score_pregunta,

                            "FOTO": foto_path,

                            "PLAN_ACCION": (
                                plan_accion_valor
                                if pregunta_texto == "Requiere Plan de Acción"
                                and str(respuesta) == "Si"
                                else ""
                            ),

                            "RESPONSABLE": (
                                responsable_valor
                                if pregunta_texto == "Requiere Plan de Acción"
                                and str(respuesta) == "Si"
                                else ""
                            ),

                            "FECHA_LIMITE": (
                                fecha_limite_valor
                                if pregunta_texto == "Requiere Plan de Acción"
                                and str(respuesta) == "Si"
                                else ""
                            ),

                            "ESTADO": (
                                "Pendiente"
                                if pregunta_texto == "Requiere Plan de Acción"
                                and str(respuesta) == "Si"
                                else ""
                            )

                        })

                # ------------------------------------------------
                # SCORE FINAL
                # ------------------------------------------------

                if total_preguntas > 0:

                    score_final = round(
                        (total_si / total_preguntas) * 100,
                        2
                    )

                else:

                    score_final = 0

                # ------------------------------------------------
                # DATAFRAME FINAL
                # ------------------------------------------------

                df_guardado = pd.DataFrame(
                    datos_auditoria
                )

                # ------------------------------------------------
                # VALIDAR OBSERVACIONES OBLIGATORIAS
                # ------------------------------------------------

                observacion_obligatoria = False

                hay_desvios = False
                requiere_pda = False

                for pregunta_id, respuesta in respuestas.items():

                    pregunta_info = df_preguntas[
                        df_preguntas["ID"] == pregunta_id
                    ]

                    if pregunta_info.empty:
                        continue

                    pregunta_texto = (
                        pregunta_info.iloc[0]["PREGUNTA"]
                    )

                    # Detectar desvíos reales
                    if (
                        str(respuesta) == "No"
                        and pregunta_texto not in [
                            "Requiere Plan de Acción",
                            "Plan de Acción",
                            "Responsable",
                            "Fecha Limite"
                        ]
                    ):
                        hay_desvios = True

                    # Detectar si se abrió PDA
                    if (
                        pregunta_texto == "Requiere Plan de Acción"
                        and str(respuesta) == "Si"
                    ):
                        requiere_pda = True

                # Observación obligatoria solo si:
                # hay desvíos y NO se abrió PDA

                if hay_desvios and not requiere_pda:

                    if observacion.strip() == "":

                        st.error(
                            "⚠️ Debe completar Observaciones cuando existan desvíos y no se genere un Plan de Acción."
                        )

                        st.stop()

                # ------------------------------------------------
                # GUARDAR SQL
                # ------------------------------------------------

                agregar_respuestas_sql(
                    df_guardado
                )

                if score_final == 100:

                    st.success(
                        f"🏆 Excelente | SCORE FINAL: {score_final}%"
                    )

                elif score_final >= 85:

                    st.success(
                        f"✅ Muy Bien | SCORE FINAL: {score_final}%"
                    )

                else:

                    st.error(
                        f"🚨 Oportunidad de Mejora | SCORE FINAL: {score_final}%"
                    )

                st.balloons()

                import time
                time.sleep(3)

                st.session_state.form_id += 1

                st.rerun()

# =========================================================
# DASHBOARD
# =========================================================

elif seleccion == "Dashboard":

        st.title("📊 Dashboard OWD")

        # ------------------------------------------------
        # LEER RESPUESTAS
        # ------------------------------------------------

        try:

            df_dashboard = leer_sql(
                "RESPUESTAS"
            )

        except:

            st.warning(
                "⚠️ No existen auditorías cargadas"
            )

            st.stop()

        # ------------------------------------------------
        # VALIDAR DATOS
        # ------------------------------------------------

        if df_dashboard.empty:

            st.warning(
                "⚠️ No existen auditorías cargadas"
            )

            st.stop()

        # ------------------------------------------------
        # CONVERTIR FECHA
        # ------------------------------------------------

        df_dashboard["FECHA"] = pd.to_datetime(
            df_dashboard["FECHA"],
            errors="coerce"
        )

        df_dashboard["MES_FILTRO"] = (
            df_dashboard["FECHA"]
            .dt.strftime("%m-%Y")
        )

        col1, col2, col3 = st.columns(3)

        # ------------------------------------------------
        # FILTRO MES
        # ------------------------------------------------

        with col1:

            lista_meses = ["Todos"] + sorted(
                df_dashboard["MES_FILTRO"]
                .dropna()
                .unique()
                .tolist(),
                reverse=True
            )

            mes_seleccionado = st.selectbox(
                "📅 Filtrar por Mes",
                lista_meses,
                index=0
            )

        # ------------------------------------------------
        # FILTRO EMPRESA
        # ------------------------------------------------

        with col2:

            lista_empresas_dashboard = ["Todos"] + sorted(
                df_dashboard["EMPRESA"]
                .dropna()
                .astype(str)
                .unique()
                .tolist()
            )

            empresa_seleccionada = st.selectbox(
                "🏢 Filtrar por Empresa",
                lista_empresas_dashboard,
                index=0
            )

        # ------------------------------------------------
        # FILTRO AUDITADO
        # ------------------------------------------------

        with col3:

            df_auditados_filtro = df_dashboard.copy()

            if empresa_seleccionada != "Todos":

                df_auditados_filtro = df_auditados_filtro[
                    df_auditados_filtro["EMPRESA"]
                    == empresa_seleccionada
                ]

            lista_auditados_dashboard = ["Todos"] + sorted(
                df_auditados_filtro["AUDITADO"]
                .dropna()
                .astype(str)
                .unique()
                .tolist()
            )

            auditado_seleccionado = st.selectbox(
                "👤 Filtrar por Auditado",
                lista_auditados_dashboard,
                index=0
            )

        # ------------------------------------------------
        # APLICAR FILTROS
        # ------------------------------------------------

        df_dashboard_filtrado = df_dashboard.copy()

        # FILTRO MES

        if mes_seleccionado != "Todos":

            df_dashboard_filtrado = df_dashboard_filtrado[
                df_dashboard_filtrado["MES_FILTRO"]
                == mes_seleccionado
            ]

        # FILTRO EMPRESA

        if empresa_seleccionada != "Todos":

            df_dashboard_filtrado = df_dashboard_filtrado[
                df_dashboard_filtrado["EMPRESA"]
                == empresa_seleccionada
            ]

        # FILTRO AUDITADO

        if auditado_seleccionado != "Todos":

            df_dashboard_filtrado = df_dashboard_filtrado[
                df_dashboard_filtrado["AUDITADO"]
                == auditado_seleccionado
            ]

        # ------------------------------------------------
        # KPIs PRINCIPALES
        # ------------------------------------------------

        st.subheader("📌 Indicadores Generales")

        col1, col2, col3, col4 = st.columns(4)

        df_dashboard_filtrado["SCORE"] = pd.to_numeric(
            df_dashboard_filtrado["SCORE"],
            errors="coerce"
        )

        score_promedio = round(
            df_dashboard_filtrado["SCORE"].mean(),
            2
        )

        total_auditorias = (
            df_dashboard_filtrado["ID_AUDITORIA"]
            .nunique()
        )

        preguntas_excluidas = [
            "Plan de Acción",
            "Responsable",
            "Fecha Limite",
            "Requiere Plan de Acción"
        ]

        total_desvios = len(
            df_dashboard_filtrado[
                (df_dashboard_filtrado["RESPUESTA"] == "No")
                &
                (~df_dashboard_filtrado["PREGUNTA"].isin(
                    preguntas_excluidas
                ))
            ]
        )

        total_si = len(
            df_dashboard_filtrado[
                (df_dashboard_filtrado["RESPUESTA"] == "Si")
                &
                (~df_dashboard_filtrado["PREGUNTA"].isin(
                    preguntas_excluidas
                ))
            ]
        )

        with col1:

            st.metric(
                "🎯 Score Promedio",
                f"{score_promedio}%"
            )

        with col2:

            st.metric(
                "📋 Auditorías",
                total_auditorias
            )

        with col3:

            st.metric(
                "❌ Desvíos",
                total_desvios
            )

        with col4:

            st.metric(
                "✅ Cumplimientos",
                total_si
            )

        st.divider()

        # ------------------------------------------------
        # SCORE POR AUDITADO
        # ------------------------------------------------

        st.subheader("👤 Score por Auditado")

        score_auditado = (
            df_dashboard_filtrado
            .groupby("AUDITADO", as_index=False)
            .agg({
            "SCORE": "mean",
            "ID_AUDITORIA": "nunique"
            })
        )

        score_auditado.columns = [
            "AUDITADO",
            "SCORE",
            "CANTIDAD"
        ]

        score_auditado = score_auditado.sort_values(
            "SCORE",
            ascending=False
        )

        top_5 = score_auditado.head(5)

        bottom_5 = (
            score_auditado
            .sort_values("SCORE", ascending=True)
            .head(5)
        )

        col_mejores, col_peores = st.columns(2)

        # ------------------------------------------------
        # TOP 5 MEJORES
        # ------------------------------------------------

        with col_mejores:

            st.markdown("### 🏆 Top 5 Mejores")

            for _, fila in top_5.iterrows():

                st.markdown(
                    f"""
                    <div style="
                        padding:12px;
                        border-radius:10px;
                        background-color:#f5f7fa;
                        color:#000000;
                        margin-bottom:8px;
                        border:1px solid #dfe6ee;
                    ">

                    <b>👤 {fila['AUDITADO']}</b><br>

                    📋 Auditorías: {fila['CANTIDAD']}<br>

                    🎯 Score: <b>{round(fila['SCORE'],1)}%</b>

                    </div>
                    """,
                    unsafe_allow_html=True
                )


        # ------------------------------------------------
        # TOP 5 PEORES
        # ------------------------------------------------

        with col_peores:

            st.markdown("### ⚠️ Top 5 Peores")

            for _, fila in bottom_5.iterrows():

                st.markdown(
                    f"""
                    <div style="
                        padding:12px;
                        border-radius:10px;
                        background-color:#fff5f5;
                        color:#000000;
                        margin-bottom:8px;
                        border:1px solid #f0d0d0;
                    ">

                    <b>👤 {fila['AUDITADO']}</b><br>

                    📋 Auditorías: {fila['CANTIDAD']}<br>

                    🎯 Score: <b>{round(fila['SCORE'],1)}%</b>

                    </div>
                    """,
                    unsafe_allow_html=True
                )

        st.divider()

        # ------------------------------------------------
        # SCORE POR PILAR
        # ------------------------------------------------

        st.subheader("🏆 Score por Pilar")

        # ------------------------------------------------
        # LIMPIAR PILARES
        # ------------------------------------------------

        df_dashboard_filtrado["PILAR"] = (
            df_dashboard_filtrado["PILAR"]
            .astype(str)
            .str.strip()
            .str.upper()
        )

        # ------------------------------------------------
        # SCORE PILAR GENERAL
        # ------------------------------------------------

        df_pilar_general = df_dashboard_filtrado[
            df_dashboard_filtrado["PILAR"] == "GENERAL"
        ]

        if not df_pilar_general.empty:

            score_general = round(
                df_pilar_general["SCORE"].mean(),
                1
            )

            cantidad_general = (
                df_pilar_general["ID_AUDITORIA"]
                .nunique()
            )

            st.markdown(
                f"""
                <div style="
                    padding:15px;
                    border-radius:12px;
                    background-color:#f4f4f4;
                    color:#000000;
                    margin-bottom:15px;
                    border:1px solid #d9d9d9;
                ">

                <h4 style="margin:0;">
                🏆 PREGUNTAS GENERALES
                </h4>

                <p style="margin:5px 0 0 0;">
                📋 Cantidad: <b>{cantidad_general}</b>
                &nbsp;&nbsp;&nbsp;
                🎯 Score: <b>{score_general}%</b>
                </p>

                </div>
                """,
                unsafe_allow_html=True
            )

        # ------------------------------------------------
        # RESTO DE PILARES
        # ------------------------------------------------

        score_pilar = (
            df_dashboard_filtrado[
                df_dashboard_filtrado["PILAR"] != "GENERAL"
            ]
            .groupby("PILAR", as_index=False)
            .agg({
                "SCORE": "mean",
                "ID_AUDITORIA": "nunique"
            })
        )

        score_pilar.columns = [
            "PILAR",
            "SCORE",
            "CANTIDAD"
        ]

        score_pilar = score_pilar.sort_values(
            "SCORE",
            ascending=False
        )

        for _, fila in score_pilar.iterrows():

            st.markdown(
                f"""
                <div style="
                    padding:15px;
                    border-radius:12px;
                    background-color:#f5f7fa;
                    color:#000000;
                    margin-bottom:10px;
                    border:1px solid #dfe6ee;
                ">

                <h4 style="margin:0;">
                🏆 {fila['PILAR']}
                </h4>

                <p style="margin:5px 0 0 0;">
                📋 Cantidad: <b>{fila['CANTIDAD']}</b>
                &nbsp;&nbsp;&nbsp;
                🎯 Score: <b>{round(fila['SCORE'],1)}%</b>
                </p>

                </div>
                """,
                unsafe_allow_html=True
            )

        # ------------------------------------------------
        # SCORE POR PROCESO
        # ------------------------------------------------

        st.subheader("🏭 Score por Proceso")

        score_proceso = (
            df_dashboard_filtrado
            .groupby("PROCESO", as_index=False)
            .agg({
            "SCORE": "mean",
            "ID_AUDITORIA": "nunique"
            })
        )

        score_proceso.columns = [
            "PROCESO",
            "SCORE",
            "CANTIDAD"
        ]

        score_proceso = score_proceso.sort_values(
            "SCORE",
            ascending=False
        )

        top_5_procesos = score_proceso.head(5)

        bottom_5_procesos = (
            score_proceso
            .sort_values("SCORE", ascending=True)
            .head(5)
        )

        col1, col2 = st.columns(2)

        with col1:

            st.markdown("### 🏆 Top 5 Mejores Procesos")

            for _, fila in top_5_procesos.iterrows():

                st.markdown(
                    f"""
                    <div style="
                        padding:12px;
                        border-radius:10px;
                        background-color:#f5f7fa;
                        color:#000000;
                        margin-bottom:8px;
                        border:1px solid #dfe6ee;
                    ">
                    <b>🏭 {fila['PROCESO']}</b><br>
                    📋 Auditorías: {fila['CANTIDAD']}<br>
                    🎯 Score: <b>{round(fila['SCORE'],1)}%</b>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

        with col2:

            st.markdown("### ⚠️ Top 5 Peores Procesos")

            for _, fila in bottom_5_procesos.iterrows():

                st.markdown(
                    f"""
                    <div style="
                        padding:12px;
                        border-radius:10px;
                        background-color:#fff5f5;
                        color:#000000;
                        margin-bottom:8px;
                        border:1px solid #f0d0d0;
                    ">
                    <b>🏭 {fila['PROCESO']}</b><br>
                    📋 Auditorías: {fila['CANTIDAD']}<br>
                    🎯 Score: <b>{round(fila['SCORE'],1)}%</b>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

        st.divider()

        # ------------------------------------------------
        # SCORE POR LOCALIDAD
        # ------------------------------------------------

        st.subheader("📍 Score por Localidad")

        score_localidad = (
            df_dashboard_filtrado
            .groupby("LOCALIDAD", as_index=False)
            .agg({
                "SCORE": "mean",
                "ID_AUDITORIA": "nunique"
            })
        )

        score_localidad.columns = [
            "LOCALIDAD",
            "SCORE",
            "CANTIDAD"
        ]

        score_localidad = score_localidad.sort_values(
            "SCORE",
            ascending=False
        )

        top_5_localidades = score_localidad.head(5)

        bottom_5_localidades = (
            score_localidad
            .sort_values("SCORE", ascending=True)
            .head(5)
        )

        col1, col2 = st.columns(2)

        with col1:

            st.markdown("### 🏆 Top 5 Mejores Localidades")

            for _, fila in top_5_localidades.iterrows():

                st.markdown(
                    f"""
                    <div style="
                        padding:12px;
                        border-radius:10px;
                        background-color:#f5f7fa;
                        color:#000000;
                        margin-bottom:8px;
                        border:1px solid #dfe6ee;
                    ">
                    <b>📍 {fila['LOCALIDAD']}</b><br>
                    📋 Auditorías: {fila['CANTIDAD']}<br>
                    🎯 Score: <b>{round(fila['SCORE'],1)}%</b>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

        with col2:

            st.markdown("### ⚠️ Top 5 Peores Localidades")

            for _, fila in bottom_5_localidades.iterrows():

                st.markdown(
                    f"""
                    <div style="
                        padding:12px;
                        border-radius:10px;
                        background-color:#fff5f5;
                        color:#000000;
                        margin-bottom:8px;
                        border:1px solid #f0d0d0;
                    ">
                    <b>📍 {fila['LOCALIDAD']}</b><br>
                    📋 Auditorías: {fila['CANTIDAD']}<br>
                    🎯 Score: <b>{round(fila['SCORE'],1)}%</b>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

        st.divider()

        # ------------------------------------------------
        # PREGUNTAS MÁS INCUMPLIDAS
        # ------------------------------------------------

        st.subheader("❌ Preguntas Más Incumplidas TOP 5")

        preguntas_excluidas = [
            "Plan de Acción",
            "Responsable",
            "Fecha Limite",
            "Requiere Plan de Acción"
        ]

        df_incumplidas = df_dashboard_filtrado[
            (df_dashboard_filtrado["RESPUESTA"] == "No")
            &
            (~df_dashboard_filtrado["PREGUNTA"].isin(
                preguntas_excluidas
            ))
        ]

        ranking_preguntas = (
            df_incumplidas
            .groupby("PREGUNTA", as_index=False)
            .agg({
                "ID_AUDITORIA": "nunique"
            })
        )

        ranking_preguntas.columns = [
            "PREGUNTA",
            "CANTIDAD"
        ]

        ranking_preguntas = ranking_preguntas.sort_values(
            "CANTIDAD",
            ascending=False
        )
        ranking_preguntas = ranking_preguntas.head(5)

        for _, fila in ranking_preguntas.iterrows():

            st.markdown(
                f"""
                <div style="
                    padding:15px;
                    border-radius:12px;
                    background-color:#fff4f4;
                    color:#000000;
                    margin-bottom:10px;
                    border:1px solid #f5c2c2;
                ">

                <h4 style="margin:0;">
                ❌ {fila['PREGUNTA']}
                </h4>

                <p style="margin:5px 0 0 0;">
                🚨 Incumplimientos:
                <b>{fila['CANTIDAD']}</b>
                </p>

                </div>
                """,
                unsafe_allow_html=True
            )

        st.divider()

        # ------------------------------------------------
        # EVOLUCIÓN MENSUAL
        # ------------------------------------------------

        import plotly.express as px

        st.subheader("📈 Evolución Mensual del Score")

        # ------------------------------------------------
        # FILTRO PROCESO EVOLUCIÓN
        # ------------------------------------------------

        lista_procesos_evolucion = ["Todos"] + sorted(
            df_dashboard["PROCESO"]
            .dropna()
            .astype(str)
            .unique()
            .tolist()
        )

        proceso_evolucion = st.selectbox(
            "🏭 Filtrar Evolución por Proceso",
            lista_procesos_evolucion,
            index=0
        )

        df_dashboard["MES"] = (
            df_dashboard["FECHA"]
            .dt.strftime("%m-%Y")
        )

        df_dashboard["SCORE"] = pd.to_numeric(
            df_dashboard["SCORE"],
            errors="coerce"
        )

        # ------------------------------------------------
        # DATA PARA EVOLUCIÓN
        # SOLO FILTRA AUDITADO
        # ------------------------------------------------

        df_evolucion = df_dashboard.copy()

        # --------------------------------------------
        # FILTRO AUDITADO
        # --------------------------------------------

        if auditado_seleccionado != "Todos":

            df_evolucion = df_evolucion[
                df_evolucion["AUDITADO"]
                == auditado_seleccionado
            ]

        # --------------------------------------------
        # FILTRO PROCESO
        # --------------------------------------------

        if proceso_evolucion != "Todos":

            df_evolucion = df_evolucion[
                df_evolucion["PROCESO"]
                == proceso_evolucion
            ]

        evolucion = (
            df_evolucion
            .groupby("MES", as_index=False)["SCORE"]
            .mean()
        )

        evolucion = evolucion.sort_values(
            "MES"
        )

        evolucion["SCORE_TEXTO"] = (
            evolucion["SCORE"]
            .round(1)
            .astype(str) + "%"
        )

        fig = px.line(
            evolucion,
            x="MES",
            y="SCORE",
            markers=True,
            text="SCORE_TEXTO",
            title="📈 Evolución Mensual del Score"
        )

        fig.update_traces(
            textposition="top center"
        )

        fig.update_layout(
            xaxis_title="Mes",
            yaxis_title="Score (%)"
        )

        st.plotly_chart(
            fig,
            use_container_width=True
        )

        st.divider()

# =========================================================
# PLANES DE ACCIÓN
# =========================================================

elif seleccion == "Planes de Acción":

        st.title("🚨 Planes de Acción")

        # ------------------------------------------------
        # LEER RESPUESTAS
        # ------------------------------------------------

        try:

            df_planes = leer_sql(
                "RESPUESTAS"
            )

        except:

            st.warning(
                "⚠️ No existen auditorías cargadas"
            )

            st.stop()

        # ------------------------------------------------
        # KPIs
        # ------------------------------------------------

        st.subheader("📊 Indicadores")

        col1, col2, col3, col4 = st.columns(4)

        pendientes = len(
            df_planes[
                df_planes["ESTADO"] == "Pendiente"
            ]
        )

        en_proceso = len(
            df_planes[
                df_planes["ESTADO"] == "En Proceso"
            ]
        )

        completados = len(
            df_planes[
                df_planes["ESTADO"] == "Completado"
            ]
        )

        vencidos = len(
            df_planes[
                (
                    pd.to_datetime(
                        df_planes["FECHA_LIMITE"],
                        errors="coerce"
                    )
                    <
                    pd.Timestamp.now()
                )
                &
                (
                    df_planes["ESTADO"]
                    != "Completado"
                )
            ]
        )

        with col1:
            st.metric(
                "🔴 Pendientes",
                pendientes
            )

        with col2:
            st.metric(
                "🟡 En Proceso",
                en_proceso
            )

        with col3:
            st.metric(
                "🟢 Completados",
                completados
            )

        with col4:
            st.metric(
                "⏰ Vencidos",
                vencidos
            )

        st.divider()

        # ------------------------------------------------
        # ACCIONES CRITICAS
        # ------------------------------------------------

        st.subheader("🚨 Acciones Críticas")

        hoy = datetime.now().date()

        df_alertas = df_planes.copy()

        df_alertas["FECHA_LIMITE_DT"] = pd.to_datetime(
            df_alertas["FECHA_LIMITE"],
            errors="coerce"
        )

        df_alertas = df_alertas[
            df_alertas["ESTADO"] != "Completado"
        ]

        alertas = []

        for _, fila in df_alertas.iterrows():

            if pd.isna(fila["FECHA_LIMITE_DT"]):
                continue

            dias = (
                fila["FECHA_LIMITE_DT"].date()
                - hoy
            ).days

            if dias < 0:

                alertas.append({
                    "tipo": "vencido",
                    "texto":
                    f"🔴 {fila['AUDITADO']} | {fila['PROCESO']} | "
                    f"Vencido hace {abs(dias)} días"
                })

            elif dias <= 7:

                alertas.append({
                    "tipo": "proximo",
                    "texto":
                    f"🟡 {fila['AUDITADO']} | {fila['PROCESO']} | "
                    f"Vence en {dias} días"
                })

        if len(alertas) == 0:

            st.success(
                "✅ No existen acciones críticas"
            )

        else:

            texto_alertas = "\n\n".join(
                alerta["texto"]
                for alerta in alertas                    )

            st.warning(texto_alertas)

        st.divider()

        # ------------------------------------------------
        # FILTRAR PLANES DE ACCION
        # ------------------------------------------------

        df_planes = df_planes[
            (
                df_planes["PREGUNTA"]
                .astype(str)
                .str.strip()
                == "Requiere Plan de Acción"
            )
            &
            (
                df_planes["RESPUESTA"]
                .astype(str)
                .str.strip()
                == "Si"
            )
        ]

        # ------------------------------------------------
        # VALIDAR
        # ------------------------------------------------

        if df_planes.empty:

            st.success(
                "✅ No existen desvíos pendientes"
            )

            st.stop()

        # ------------------------------------------------
        # COLUMNAS AUXILIARES
        # ------------------------------------------------

        if "PLAN_ACCION" not in df_planes.columns:

            df_planes["PLAN_ACCION"] = ""

        if "RESPONSABLE" not in df_planes.columns:

            df_planes["RESPONSABLE"] = ""

        if "FECHA_LIMITE" not in df_planes.columns:

            df_planes["FECHA_LIMITE"] = ""

        if "ESTADO" not in df_planes.columns:

            df_planes["ESTADO"] = "Pendiente"

        if "EVIDENCIA" not in df_planes.columns:
            df_planes["EVIDENCIA"] = ""

        # ------------------------------------------------
        # FILTROS
        # ------------------------------------------------

        st.subheader("🔎 Filtros")

        col1, col2, col3, col4, col5 = st.columns(5)

        with col1:

            lista_empresas_pa = ["Todos"] + sorted(
                df_planes["EMPRESA"]
                .dropna()
                .astype(str)
                .unique()
                .tolist()
            )

            empresa_seleccionada = st.selectbox(
                "Empresa",
                lista_empresas_pa,
                index=0
            )

        with col2:

            if empresa_seleccionada != "Todos":

                lista_auditados = ["Todos"] + sorted(
                    df_planes[
                        df_planes["EMPRESA"]
                        == empresa_seleccionada
                    ]["AUDITADO"]
                    .dropna()
                    .astype(str)
                    .unique()
                    .tolist()
                )

            else:

                lista_auditados = ["Todos"] + sorted(
                    df_planes["AUDITADO"]
                    .dropna()
                    .astype(str)
                    .unique()
                    .tolist()
                )

            auditado_seleccionado = st.selectbox(
                "Auditado",
                lista_auditados
            )

        with col3:

            filtro_proceso = st.selectbox(
                "Proceso",
                ["Todos"] + sorted(
                    df_planes["PROCESO"]
                    .dropna()
                    .astype(str)
                    .unique()
                    .tolist()
                )
            )

        with col4:

            filtro_estado = st.selectbox(
                "Estado",
                ["Todos"] + sorted(
                    df_planes["ESTADO"]
                    .dropna()
                    .astype(str)
                    .unique()
                    .tolist()
                )
            )

        with col5:

            filtro_responsable = st.selectbox(
                "Responsable",
                ["Todos"] + sorted(
                    df_planes["RESPONSABLE"]
                    .dropna()
                    .astype(str)
                    .unique()
                    .tolist()
                )
            )

        df_planes_filtrado = df_planes.copy()

        # ------------------------------------------------
        # APLICAR FILTROS
        # ------------------------------------------------

        df_planes_filtrado = df_planes.copy()

        if empresa_seleccionada != "Todos":

            df_planes_filtrado = df_planes_filtrado[
                df_planes_filtrado["EMPRESA"]
                == empresa_seleccionada
            ]

        if auditado_seleccionado != "Todos":

            df_planes_filtrado = df_planes_filtrado[
                df_planes_filtrado["AUDITADO"]
                == auditado_seleccionado
            ]

        if filtro_proceso != "Todos":

            df_planes_filtrado = df_planes_filtrado[
                df_planes_filtrado["PROCESO"]
                == filtro_proceso
            ]

        if filtro_estado != "Todos":

            df_planes_filtrado = df_planes_filtrado[
                df_planes_filtrado["ESTADO"]
                == filtro_estado
            ]

        if filtro_responsable != "Todos":

            df_planes_filtrado = df_planes_filtrado[
                df_planes_filtrado["RESPONSABLE"]
                == filtro_responsable
            ]

        st.divider()

        # ------------------------------------------------
        # TABLA
        # ------------------------------------------------

        if "EVIDENCIA" not in df_planes_filtrado.columns:

            df_planes_filtrado["EVIDENCIA"] = ""

        df_planes_filtrado["TIENE EVIDENCIA"] = (
            df_planes_filtrado["EVIDENCIA"]
            .fillna("")
            .astype(str)
            .apply(
                lambda x: "📎 Sí"
                if str(x).strip() != ""
                else ""
            )
        )

        columnas_mostrar = [
            "SEMAFORO",
            "FECHA_LIMITE",
            "EMPRESA",
            "AUDITADO",
            "PROCESO",
            "PLAN_ACCION",
            "RESPONSABLE",
            "ESTADO",
            "TIENE EVIDENCIA"
        ]

        df_planes_filtrado["FECHA"] = pd.to_datetime(
            df_planes["FECHA"],
            errors="coerce"
        ).dt.strftime("%d-%m-%Y")

        df_planes["ESTADO"] = (
            df_planes["ESTADO"]
            .replace({
                "Pendiente": "🔴 Pendiente",
                "En Proceso": "🟡 En Proceso",
                "Completado": "🟢 Completado"
                })
        )

        # ------------------------------------------------
        # SEMAFORO
        # ------------------------------------------------

        def calcular_semaforo(fila):

            if fila["ESTADO"] == "Completado":
                return "✅ Completado"

            fecha = pd.to_datetime(
                fila["FECHA_LIMITE"],
                errors="coerce"
            )

            if pd.isna(fecha):
                return ""

            dias = (
                fecha.date()
                - datetime.now().date()
            ).days

            if dias < 0:
                return "🔴 Vencido"

            elif dias <= 7:
                return "🟡 Próximo"

            else:
                return "🟢 En fecha"


        df_planes_filtrado["SEMAFORO"] = (
            df_planes_filtrado
            .apply(
                calcular_semaforo,
                axis=1
            )
        )

        # ------------------------------------------------
        # ORDEN DE PRIORIDAD
        # ------------------------------------------------

        orden_prioridad = {
            "🔴 Vencido": 1,
            "🟡 Próximo": 2,
            "🟢 En fecha": 3,
            "✅ Completado": 4
        }

        df_planes_filtrado["PRIORIDAD"] = (
            df_planes_filtrado["SEMAFORO"]
            .map(orden_prioridad)
        )

        df_planes_filtrado = (
            df_planes_filtrado
            .sort_values(
                by=["PRIORIDAD", "FECHA_LIMITE"],
                ascending=[True, True]
            )
        )

        st.subheader("📋 Seguimiento")

        st.dataframe(
            df_planes_filtrado[columnas_mostrar],
            use_container_width=True
        )

        st.divider()

        # ------------------------------------------------
        # SELECCIONAR DESVÍO
        # ------------------------------------------------

        lista_desvios = (
            df_planes_filtrado["PREGUNTA"]
            .astype(str)
            .tolist()
        )

        df_planes_filtrado = df_planes_filtrado.reset_index()

        df_planes_filtrado["DESVIO_LABEL"] = (
            df_planes_filtrado["FECHA_LIMITE"].astype(str)
            + " | "
            + df_planes_filtrado["EMPRESA"].astype(str)
            + " | "
            + df_planes_filtrado["AUDITADO"].astype(str)
            + " | "
            + df_planes_filtrado["PROCESO"].astype(str)
        )

        lista_pda = [""] + (
            df_planes_filtrado["DESVIO_LABEL"]
            .tolist()
        )

        pda_seleccionado = st.selectbox(
            "Seleccionar PDA",
            lista_pda,
            index=0
        )

        if pda_seleccionado != "":

            fila = df_planes_filtrado[
                df_planes_filtrado["DESVIO_LABEL"]
                == pda_seleccionado
            ].iloc[0]

            st.subheader("✏️ Gestión PDA")

            # ------------------------------------------------
            # VALORES VACÍOS
            # ------------------------------------------------

            valor_plan = ""

            if pd.notna(fila["PLAN_ACCION"]):

                valor_plan = str(
                    fila["PLAN_ACCION"]
                )

            valor_responsable = ""

            if pd.notna(fila["RESPONSABLE"]):

                valor_responsable = str(
                fila["RESPONSABLE"]
                )

            ruta_evidencia_actual = ""

            if (
                "EVIDENCIA" in fila.index
                and pd.notna(fila["EVIDENCIA"])
            ):

                ruta_evidencia_actual = str(
                    fila["EVIDENCIA"]
                )

            from datetime import date

            valor_fecha = date.today()

            fecha_convertida = pd.to_datetime(
                fila["FECHA_LIMITE"],
                errors="coerce"
            )

            if pd.notna(fecha_convertida):

                valor_fecha = fecha_convertida.date()

            ruta_evidencia_actual = ""

            if (
                "EVIDENCIA" in fila.index
                and pd.notna(fila["EVIDENCIA"])
            ):
                ruta_evidencia_actual = str(
                    fila["EVIDENCIA"]
                )

            # ------------------------------------------------
            # CAMPOS
            # ------------------------------------------------

            plan_accion = st.text_area(
                "Plan de Acción",
                value=valor_plan
            )

            lista_responsables = [""] + lista_auditores

            responsable = st.selectbox(
                "Responsable",
                lista_responsables,
                index=(
                    lista_responsables.index(valor_responsable)
                    if valor_responsable in lista_responsables
                    else 0
                )
            )

            fecha_limite = st.date_input(
                "Fecha Límite",
                value=valor_fecha,
                format="DD/MM/YYYY"
            )

            evidencia = st.file_uploader(
                "📎 Evidencia de Cierre",
                type=["jpg", "jpeg", "png"],
                help="Obligatorio para completar el Plan de Acción",
                key=f"evidencia_{fila['ID_AUDITORIA']}"
            )

            eliminar_evidencia = False

            if ruta_evidencia_actual != "":

                try:

                    st.image(
                        ruta_evidencia_actual,
                        caption="Evidencia cargada",
                        width=650
                    )

                except:

                    st.warning(
                        "⚠️ La evidencia ya no está disponible."
                    )

                eliminar_evidencia = st.checkbox(
                    "🗑️ Eliminar evidencia actual"
                )

            if evidencia is not None:

                st.success(
                    f"Archivo cargado: {evidencia.name}"
                )

            valor_estado = "Pendiente"

            if pd.notna(fila["ESTADO"]):

                valor_estado = str(
                    fila["ESTADO"]
                )

            lista_estados = [
                "Pendiente",
                "En Proceso",
                "Completado"
            ]

            estado = st.selectbox(
                "Estado",
                lista_estados,
                index=(
                    lista_estados.index(valor_estado)
                    if valor_estado in lista_estados
                    else 0
                )
            )

            if st.button("💾 Guardar Plan"):

                if (
                    estado == "Completado"
                    and evidencia is None
                    and ruta_evidencia_actual == ""
                ):

                    st.error(
                        "⚠️ Debe adjuntar una evidencia para completar el Plan de Acción"
                    )

                    st.stop()

                import os

                ruta_evidencia = ruta_evidencia_actual

                if evidencia is not None:

                    ruta_evidencia = subir_imagen_cloudinary(
                        evidencia,
                        "evidencias_pda"
                    )

                if estado != "Completado":
                    ruta_evidencia = ""

                if eliminar_evidencia:

                    ruta_evidencia = ""

                    if estado == "Completado" and evidencia is None:

                        st.error(
                            "⚠️ Debe cargar una nueva evidencia o cambiar el estado."
                        )

                        st.stop()

                actualizar_pda_sql(
                    fila["ID_AUDITORIA"],
                    plan_accion,
                    responsable,
                    fecha_limite,
                    estado,
                    ruta_evidencia
                )

                st.success(
                    "✅ Plan guardado correctamente"
                )

                import time
                time.sleep(1.5)

                st.rerun()  

# =========================================================
# HISTORIAL
# =========================================================

elif seleccion == "Historial":

        st.title("📂 Historial de Auditorías")

        # ------------------------------------------------
        # LEER RESPUESTAS
        # ------------------------------------------------

        try:

            df_historial = leer_sql(
            "RESPUESTAS"
            )

        except:

            st.warning("No existen auditorías cargadas.")
            st.stop()

        # ------------------------------------------------
        # CONVERTIR SCORE
        # ------------------------------------------------

        df_historial["SCORE"] = pd.to_numeric(
            df_historial["SCORE"],
            errors="coerce"
        )

        # ------------------------------------------------
        # TABLA RESUMEN
        # ------------------------------------------------

        resumen = (
            df_historial
            .groupby("ID_AUDITORIA", as_index=False)
            .agg({
                "FECHA": "first",
                "AUDITADO": "first",
                "PILAR": "first",
                "PROCESO": "first",
                "SCORE": "mean"
            })
        )

        resumen = resumen[
            [
                "ID_AUDITORIA",
                "FECHA",
                "AUDITADO",
                "PILAR",
                "PROCESO",
                "SCORE"
            ]
        ]
        resumen["SCORE"] = (
            resumen["SCORE"]
            .round(1)
            .astype(str)
            + "%"
        )

        resumen = resumen.sort_values(
            "FECHA",
            ascending=False
        )
        resumen["FECHA"] = pd.to_datetime(
            resumen["FECHA"]
        ).dt.strftime("%d-%m-%Y")

        # ------------------------------------------------
        # FILTROS
        # ------------------------------------------------

        st.subheader("🔎 Filtros")

        col1, col2, col3, col4 = st.columns(4)

        # --------------------------------------------
        # FECHA
        # --------------------------------------------

        with col1:

            lista_fechas = [""] + sorted(
                resumen["FECHA"]
                .dropna()
                .astype(str)
                .unique()
                .tolist(),
                reverse=True
            )

            filtro_fecha = st.selectbox(
                "Fecha",
                lista_fechas
            )

        # --------------------------------------------
        # AUDITADO
        # --------------------------------------------

        with col2:

            lista_auditados = [""] + sorted(
                resumen["AUDITADO"]
                .dropna()
                .astype(str)
                .unique()
                .tolist()
            )

            filtro_auditado = st.selectbox(
                "Auditado",
                lista_auditados
            )

        # --------------------------------------------
        # PILAR
        # --------------------------------------------

        with col3:

            lista_pilares = [""] + sorted(
            resumen["PILAR"]
            .dropna()
            .astype(str)
            .unique()
            .tolist()
            )

            filtro_pilar = st.selectbox(
            "Pilar",
            lista_pilares
            )

        # --------------------------------------------
        # PROCESO
        # --------------------------------------------

        with col4:

            lista_procesos = [""] + sorted(
                resumen["PROCESO"]
                .dropna()
                .astype(str)
                .unique()
                .tolist()
            )

            filtro_proceso = st.selectbox(
                "Proceso",
                lista_procesos
            )

        # ------------------------------------------------
        # APLICAR FILTROS
        # ------------------------------------------------

        df_filtrado = resumen.copy()

        if filtro_fecha != "":

            df_filtrado = df_filtrado[
                df_filtrado["FECHA"].astype(str)
                == filtro_fecha
            ]

        if filtro_auditado != "":

            df_filtrado = df_filtrado[
                df_filtrado["AUDITADO"]
                == filtro_auditado
            ]

        if filtro_pilar != "":

            df_filtrado = df_filtrado[
                df_filtrado["PILAR"]
                == filtro_pilar
            ]

        if filtro_proceso != "":

            df_filtrado = df_filtrado[
                df_filtrado["PROCESO"]
                == filtro_proceso
            ]

        st.divider()

        st.subheader("📋 Auditorías")

        st.dataframe(
            df_filtrado,
            use_container_width=True
        )

        # ------------------------------------------------
        # EXPORTAR EXCEL
        # ------------------------------------------------

        ids_filtrados = (
            df_filtrado["ID_AUDITORIA"]
            .astype(str)
            .unique()
            .tolist()
        )

        detalle_export = df_historial[
            df_historial["ID_AUDITORIA"]
            .astype(str)
            .isin(ids_filtrados)
        ]

        buffer = io.BytesIO()

        with pd.ExcelWriter(
            buffer,
            engine="openpyxl"
        ) as writer:

            df_filtrado.to_excel(
                writer,
                sheet_name="Resumen",
                index=False
            )

            detalle_export.to_excel(
                writer,
                sheet_name="Detalle",
                index=False
            )

        buffer.seek(0)

        st.download_button(
            label="📥 Exportar Excel",
            data=buffer,
            file_name=f"OWD_Historial_{datetime.now().strftime('%Y%m%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

        st.divider()

        # ------------------------------------------------
        # SELECCIONAR AUDITORÍA
        # ------------------------------------------------

        auditoria_seleccionada = st.selectbox(
            "Seleccionar Auditoría",
            [""] + df_filtrado["ID_AUDITORIA"]
            .astype(str)
            .tolist()
        )

        # ------------------------------------------------
        # DETALLE AUDITORÍA
        # ------------------------------------------------

        if auditoria_seleccionada != "":

            detalle = df_historial[
                df_historial["ID_AUDITORIA"]
                .astype(str)
                == auditoria_seleccionada
            ]

            info = detalle.iloc[0]

            # ------------------------------------------------
            # BOTONES ACCIONES
            # ------------------------------------------------

            col_btn1, col_btn2 = st.columns(2)

            with col_btn1:

                editar = st.button(
                    "✏️ Editar Auditoría",
                    use_container_width=True
                )

            with col_btn2:

                eliminar = st.button(
                    "🗑️ Eliminar Auditoría",
                    use_container_width=True
                )

            # ------------------------------------------------
            # ELIMINAR AUDITORÍA
            # ------------------------------------------------

            if "confirmar_eliminacion" not in st.session_state:

                st.session_state.confirmar_eliminacion = False

            if eliminar:

                st.session_state.confirmar_eliminacion = True

            if st.session_state.confirmar_eliminacion:

                st.warning(
                    "⚠️ ¿Estás seguro que querés eliminar la auditoría?"
                )

                col_si, col_no = st.columns(2)

                with col_si:

                    if st.button(
                        "✅ Sí, eliminar definitivamente",
                        use_container_width=True
                    ):

                        eliminar_auditoria_sql(
                            auditoria_seleccionada
                        )

                        st.session_state.confirmar_eliminacion = False

                        st.success(
                            "✅ Auditoría eliminada"
                        )

                        st.rerun()

                with col_no:

                    if st.button(
                        "❌ Cancelar",
                        use_container_width=True
                    ):

                        st.session_state.confirmar_eliminacion = False

                        st.rerun()

            # ------------------------------------------------
            # MODO EDICIÓN
            # ------------------------------------------------

            if editar:

                st.session_state["editar_id"] = (
                    auditoria_seleccionada
                )

                st.session_state["modo_edicion"] = True

            if st.session_state.get("modo_edicion", False):

                st.divider()

                st.subheader("✏️ Editar Auditoría")

                df_edicion = leer_sql("RESPUESTAS")

                df_edicion = df_edicion[
                    df_edicion["ID_AUDITORIA"].astype(str)
                    == str(st.session_state["editar_id"])
                ]

                st.write(
                    "ID buscado:",
                    st.session_state["editar_id"]
                )

                st.write(
                    "Filas encontradas:",
                    len(df_edicion)
                )

                if df_edicion.empty:

                    st.error(
                        "No se encontraron datos para la auditoría seleccionada"
                    )

                    st.stop()

                fila = df_edicion.iloc[0]

                fecha_editada = st.date_input(
                    "Fecha",
                    value=pd.to_datetime(
                        fila["FECHA"]
                    ).date()
                )

                auditor_actual = str(fila["AUDITOR"])

                auditor_editado = st.selectbox(
                    "Auditor",
                    lista_auditores,
                    index=(
                        lista_auditores.index(auditor_actual)
                        if auditor_actual in lista_auditores
                        else 0
                    )
                )

                empresa_editada = st.selectbox(
                    "Empresa",
                    lista_empresas,
                    index=lista_empresas.index(
                        str(fila["EMPRESA"])
                    )
                )

                if empresa_editada != "":

                    lista_auditados_filtrados = [""] + sorted(
                        df_auditados[
                            df_auditados["Empresa"]
                            .astype(str)
                            .str.strip()
                            .str.upper()
                            ==
                            str(empresa_editada)
                            .strip()
                            .upper()
                        ]["Auditados"]
                        .dropna()
                        .astype(str)
                        .tolist()
                    )

                else:

                    lista_auditados_filtrados = lista_auditados

                auditado_editado = st.selectbox(
                    "Auditado",
                    lista_auditados_filtrados,
                    index=lista_auditados_filtrados.index(
                        str(fila["AUDITADO"])
                    )
                )

                if empresa_editada != "":

                    lista_localidades_filtradas = [""] + sorted(
                        df_localidades[
                            df_localidades["Empresa"]
                            .astype(str)
                            .str.strip()
                            .str.upper()
                            ==
                            str(empresa_editada)
                            .strip()
                            .upper()
                        ]["Localidades"]
                        .dropna()
                        .astype(str)
                        .tolist()
                    )

                else:

                    lista_localidades_filtradas = lista_localidades

                localidad_editada = st.selectbox(
                    "Localidad",
                    lista_localidades_filtradas,
                    index=lista_localidades_filtradas.index(
                        str(fila["LOCALIDAD"])
                    )
                )

                sector_editado = st.selectbox(
                    "Sector",
                    lista_sectores,
                    index=lista_sectores.index(
                        str(fila["SECTOR"])
                    )
                )

                area_editada = st.selectbox(
                    "Área",
                    lista_areas,
                    index=lista_areas.index(
                        str(fila["AREA"])
                    )
                )

                motivo_editado = st.selectbox(
                    "Motivo",
                    lista_motivos,
                    index=lista_motivos.index(
                        str(fila["MOTIVO_OWD"])
                    )
                )

                fila_pda = df_edicion[
                    df_edicion["PREGUNTA"]
                    == "Requiere Plan de Acción"
                ]

                valor_pda = "No"

                if (
                    not fila_pda.empty
                    and str(
                        fila_pda.iloc[0]["RESPUESTA"]
                    ) == "Si"
                ):
                    valor_pda = "Si"

                pda_editado = st.radio(
                    "Requiere Plan de Acción",
                    ["Si", "No"],
                    index=0 if valor_pda == "Si" else 1
                )

                plan_accion_editado = ""
                responsable_editado = ""
                fecha_limite_editada = None

                if pda_editado == "Si":

                    st.divider()

                    plan_accion_actual = ""

                    if not fila_pda.empty:

                        plan_accion_actual = str(
                            fila_pda.iloc[0]["PLAN_ACCION"]
                        )

                    plan_accion_editado = st.text_area(
                        "Plan de Acción",
                        value=plan_accion_actual
                    )

                    responsable_actual = ""

                    if not fila_pda.empty:

                        responsable_actual = str(
                            fila_pda.iloc[0]["RESPONSABLE"]
                        )

                    responsable_editado = st.selectbox(
                        "Responsable",
                        [""] + lista_auditores,
                        index=(
                            ([""] + lista_auditores).index(responsable_actual)
                            if responsable_actual in ([""] + lista_auditores)
                            else 0
                        )
                    )

                    fecha_actual = date.today()

                    if (
                        not fila_pda.empty
                        and pd.notna(fila_pda.iloc[0]["FECHA_LIMITE"])
                        and str(fila_pda.iloc[0]["FECHA_LIMITE"]) != ""
                    ):

                        fecha_actual = pd.to_datetime(
                            fila_pda.iloc[0]["FECHA_LIMITE"]
                        ).date()

                    fecha_limite_editada = st.date_input(
                        "Fecha Límite",
                        value=fecha_actual,
                        format="DD/MM/YYYY"
                    )

                st.divider()

                observacion_editada = st.text_area(
                    "📝 Observaciones",
                    value=(
                        str(fila["OBSERVACION"])
                        if pd.notna(fila["OBSERVACION"])
                        else ""
                    ),
                    height=120
                )

                st.subheader("📷 Foto")

                foto_actual = str(fila["FOTO"])

                if foto_actual and os.path.exists(foto_actual):

                    st.image(
                        foto_actual,
                        width=300
                    )

                nueva_foto = st.file_uploader(
                    "Reemplazar foto",
                    type=["jpg", "jpeg", "png"]
                )

                eliminar_foto = st.checkbox(
                        "🗑️ Eliminar foto actual"
                    )

                if st.button("💾 Guardar Cambios"):

                    df_original = leer_sql("RESPUESTAS")

                    mask = (
                        df_original["ID_AUDITORIA"].astype(str)
                        == str(st.session_state["editar_id"])
                    )

                    df_original.loc[mask, "FECHA"] = str(fecha_editada)
                    df_original.loc[mask, "AUDITOR"] = auditor_editado
                    df_original.loc[mask, "EMPRESA"] = empresa_editada
                    df_original.loc[mask, "AUDITADO"] = auditado_editado
                    df_original.loc[mask, "LOCALIDAD"] = localidad_editada
                    df_original.loc[mask, "SECTOR"] = sector_editado
                    df_original.loc[mask, "AREA"] = area_editada
                    df_original.loc[mask, "MOTIVO_OWD"] = motivo_editado
                    df_original.loc[mask,"OBSERVACION"] = observacion_editada

                    mask_pda = (
                        mask
                        &
                        (
                            df_original["PREGUNTA"]
                            .astype(str)
                            .str.strip()
                            .str.lower()
                            ==
                            "requiere plan de acción"
                        )
                    )

                    df_original.loc[
                        mask_pda,
                        "RESPUESTA"
                    ] = pda_editado

                    if pda_editado == "Si":

                        df_original.loc[
                            mask_pda,
                            "PLAN_ACCION"
                        ] = plan_accion_editado

                        df_original.loc[
                            mask_pda,
                            "RESPONSABLE"
                        ] = responsable_editado

                        df_original.loc[
                            mask_pda,
                            "FECHA_LIMITE"
                        ] = str(fecha_limite_editada)

                        estado_actual = df_original.loc[
                            mask_pda,
                            "ESTADO"
                        ]

                        if len(estado_actual) > 0:

                            if str(estado_actual.iloc[0]).strip() == "":

                                df_original.loc[
                                    mask_pda,
                                    "ESTADO"
                                ] = "Pendiente"

                    if pda_editado == "No":

                        df_original.loc[
                            mask_pda,
                            "PLAN_ACCION"
                        ] = ""

                        df_original.loc[
                            mask_pda,
                            "RESPONSABLE"
                        ] = ""

                        df_original.loc[
                            mask_pda,
                            "FECHA_LIMITE"
                        ] = ""

                        df_original.loc[
                            mask_pda,
                            "ESTADO"
                        ] = ""

                        # ----------------------------------
                        # LIMPIAR PREGUNTAS HIJAS DEL PDA
                        # ----------------------------------

                        mask_plan = (
                            mask
                            &
                            (
                                df_original["PREGUNTA"]
                                == "Plan de Acción"
                            )
                        )

                        mask_resp = (
                            mask
                            &
                            (
                                df_original["PREGUNTA"]
                                == "Responsable"
                            )
                        )

                        mask_fecha = (
                            mask
                            &
                            (
                                df_original["PREGUNTA"]
                                == "Fecha Limite"
                            )
                        )

                        df_original.loc[
                            mask_plan,
                            "RESPUESTA"
                        ] = ""

                        df_original.loc[
                            mask_resp,
                            "RESPUESTA"
                        ] = ""

                        df_original.loc[
                            mask_fecha,
                            "RESPUESTA"
                        ] = ""

                    import os

                    if nueva_foto is not None:

                        nueva_url = subir_imagen_cloudinary(
                            nueva_foto,
                            "auditorias"
                        )

                        df_original.loc[
                            mask,
                            "FOTO"
                        ] = nueva_url

                    if eliminar_foto:

                        df_original.loc[
                            mask,
                            "FOTO"
                        ] = ""

                    guardar_sql(
                        df_original,
                        "RESPUESTAS"
                    )

                    st.success(
                        "✅ Auditoría actualizada correctamente"
                    )

                    st.session_state["modo_edicion"] = False

                    st.rerun()
            # ------------------------------------------------
            # INFORMACIÓN GENERAL
            # ------------------------------------------------

            st.subheader("📝 Información General")

            col1, col2 = st.columns(2)

            with col1:

                st.write(f"📅 Fecha: {info['FECHA']}")
                st.write(f"👤 Auditado: {info['AUDITADO']}")
                st.write(f"🏢 Localidad: {info['LOCALIDAD']}")

            with col2:

                st.write(f"🏆 Pilar: {info['PILAR']}")
                st.write(f"🏭 Proceso: {info['PROCESO']}")
                
                detalle["SCORE"] = pd.to_numeric(
                    detalle["SCORE"],
                    errors="coerce"
                )

                score_real = round(
                    detalle["SCORE"].mean(),
                    1
                )

                st.write(f"🎯 Score: {score_real}%")

            st.divider()

            # ------------------------------------------------
            # OBSERVACIONES
            # ------------------------------------------------

            observacion = ""

            if (
                "OBSERVACION" in detalle.columns
                and detalle["OBSERVACION"].notna().any()
            ):

                observacion = str(
                    detalle["OBSERVACION"].iloc[0]
                )

            if observacion.strip() != "":

                st.subheader("📝 Observaciones")

                st.info(observacion)

                st.divider()

                # ------------------------------------------------
                # FOTO
                # ------------------------------------------------

                foto_path = ""

                fotos_validas = detalle[
                    detalle["FOTO"].notna()
                ]

                if not fotos_validas.empty:

                    foto_path = str(
                        fotos_validas.iloc[0]["FOTO"]
                    )

                if foto_path != "" and foto_path != "nan":

                    st.divider()

                    st.subheader("📷 Evidencia Fotográfica")

                    try:

                        st.image(
                            foto_path,
                            width=300
                        )

                    except:

                        st.warning(
                            "⚠️ No se pudo cargar la imagen."
                        )

            # ------------------------------------------------
            # RESPUESTAS
            # ------------------------------------------------

            st.subheader("📋 Respuestas")

            for _, fila in detalle.iterrows():

                pregunta = str(fila["PREGUNTA"])
                respuesta = str(fila["RESPUESTA"]).strip()

                # --------------------------------------------
                # OCULTAR PREGUNTAS PDA VACÍAS
                # --------------------------------------------

                if (
                    pregunta in [
                        "Plan de Acción",
                        "Responsable",
                        "Fecha Limite"
                    ]
                    and respuesta == ""
                ):
                    continue

                if pregunta == "Requiere Plan de Acción":

                    if respuesta == "Si":

                        emoji_respuesta = "❌"

                    elif respuesta == "No":

                        emoji_respuesta = "✅"

                    else:

                        emoji_respuesta = "📌"

                else:

                    if respuesta == "Si":

                        emoji_respuesta = "✅"

                    elif respuesta == "No":

                        emoji_respuesta = "❌"

                    else:

                        emoji_respuesta = "📌"

            # ------------------------------------------------
            # TARJETA RESPUESTA
            # ------------------------------------------------

                st.markdown(
                    f"""
                    <div style="
                        padding:12px;
                        border-radius:10px;
                        background-color:#f8f9fa;
                        margin-bottom:10px;
                        border:1px solid #dee2e6;
                    ">
                    <b>🏭 {fila['PROCESO']}</b><br><br>

                    <b>❓ {fila['PREGUNTA']}</b><br><br>

                    {emoji_respuesta} <b>Respuesta:</b>
                    {fila['RESPUESTA']}

                    </div>
                    """,
                    unsafe_allow_html=True
                )

            # ------------------------------------------------
            # DETALLE PLAN DE ACCIÓN
            # ------------------------------------------------

                if (
                    fila["PREGUNTA"] == "Requiere Plan de Acción"
                    and str(fila["RESPUESTA"]) == "Si"
                ):

                    st.warning(
                        f"""
                📋 Plan de Acción: {fila['PLAN_ACCION']}

                👤 Responsable: {fila['RESPONSABLE']}

                📅 Fecha Límite: {fila['FECHA_LIMITE']}

                🚦 Estado: {fila['ESTADO']}
                """
                    )

                    ruta_evidencia = str(
                        fila.get("EVIDENCIA", "")
                    )

                    if (
                        ruta_evidencia != ""
                        and os.path.exists(ruta_evidencia)
                    ):

                        st.image(
                            ruta_evidencia,
                            caption="📎 Evidencia de cierre",
                            width=250
                        )

# =========================================================
# MAESTROS
# =========================================================

elif seleccion == "Maestros":

        st.title("⚙️ Maestros")

        tablas = {
            "": "",
            "Auditores": "AUDITORES",
            "Auditados": "AUDITADOS",
            "Empresas": "EMPRESAS",
            "Localidades": "LOCALIDADES",
            "Sectores": "SECTORES",
            "Áreas": "AREAS",
            "Motivos": "MOTIVOS",
            "Pilares": "PILARES",
            "Procesos": "PROCESOS",
            "Preguntas": "PREGUNTAS"
        }

        opcion_tabla = st.selectbox(
            "Seleccionar módulo",
            list(tablas.keys()),
            index=0
        )

        if opcion_tabla != "":

            hoja_excel = tablas[opcion_tabla]

            # ------------------------------------------------
            # LEER HOJA
            # ------------------------------------------------

            df_admin = leer_sql(
                hoja_excel
            )

            st.subheader(f"📋 {opcion_tabla}")

            st.dataframe(
                df_admin,
                use_container_width=True
            )

            st.divider()

            # =========================================================
            # PROCESOS
            # =========================================================

            if hoja_excel == "PROCESOS":

                st.subheader("➕ Agregar Proceso")

                nuevo_id = st.text_input(
                    "ID Proceso"
                )

                lista_pilares = sorted(
                    df_procesos["PILAR"]
                    .dropna()
                    .astype(str)
                    .unique()
                    .tolist()
                )

                nuevo_pilar = st.selectbox(
                    "Pilar",
                    [""] + lista_pilares
                )

                nuevo_proceso = st.text_input(
                    "Proceso"
                )

                if st.button("➕ Agregar Proceso"):

                    if (
                        nuevo_id != ""
                        and nuevo_pilar != ""
                        and nuevo_proceso != ""
                    ):

                        nuevo_df = pd.DataFrame({

                            "ID": [nuevo_id],
                            "PILAR": [nuevo_pilar],
                            "PROCESO": [nuevo_proceso]

                        })

                        df_admin = pd.concat(
                            [df_admin, nuevo_df],
                            ignore_index=True
                        )

                        guardar_sql(
                            df_admin,
                            hoja_excel
                        )

                        st.success(
                            "✅ Proceso agregado"
                        )

                        st.rerun()

            # =========================================================
            # PILARES
            # =========================================================

            elif hoja_excel == "PILARES":

                st.subheader("➕ Agregar Pilar")

                nuevo_id = st.text_input(
                    "ID Pilar"
                )

                nuevo_pilar = st.text_input(
                    "Nombre Pilar"
                )

                if st.button("➕ Agregar Pilar"):

                    if (
                        nuevo_id != ""
                        and nuevo_pilar != ""
                    ):

                        nuevo_df = pd.DataFrame({

                            "ID": [nuevo_id],
                            "PILAR": [nuevo_pilar]

                        })

                        df_admin = pd.concat(
                            [df_admin, nuevo_df],
                            ignore_index=True
                        )

                        guardar_sql(
                            df_admin,
                            hoja_excel
                        )

                        st.success(
                            "✅ Pilar agregado"
                        )

                        st.rerun()

            # =========================================================
            # AUDITADOS
            # =========================================================

            elif hoja_excel == "AUDITADOS":

                st.subheader("➕ Agregar Auditado")

                nuevo_auditado = st.text_input(
                    "Nombre Auditado"
                )

                empresa_auditado = st.selectbox(
                    "Empresa",
                    lista_empresas
                )

                if st.button("➕ Agregar Auditado"):

                    if (
                        nuevo_auditado != ""
                        and empresa_auditado != ""
                    ):

                        nuevo_df = pd.DataFrame({

                            "Auditados": [nuevo_auditado],
                            "Empresa": [empresa_auditado]

                        })

                        df_admin = pd.concat(
                            [df_admin, nuevo_df],
                            ignore_index=True
                        )

                        guardar_sql(
                            df_admin,
                            hoja_excel
                        )

                        st.success(
                            "✅ Auditado agregado"
                        )

                        st.rerun()            

            # =========================================================
            # LOCALIDADES
            # =========================================================

            elif hoja_excel == "LOCALIDADES":

                st.subheader("➕ Agregar Localidad")

                nueva_localidad = st.text_input(
                    "Nombre Localidad"
                )

                empresa_localidad = st.selectbox(
                    "Empresa",
                    lista_empresas
                )

                if st.button("➕ Agregar Localidad"):

                    if (
                        nueva_localidad != ""
                        and empresa_localidad != ""
                    ):

                        nuevo_df = pd.DataFrame({

                            "Localidades": [nueva_localidad],
                            "Empresa": [empresa_localidad]

                        })

                        df_admin = pd.concat(
                            [df_admin, nuevo_df],
                            ignore_index=True
                        )

                        guardar_sql(
                            df_admin,
                            hoja_excel
                        )

                        st.success(
                            "✅ Localidad agregada"
                        )

                        st.rerun()

            # =========================================================
            # PREGUNTAS
            # =========================================================

            elif hoja_excel == "PREGUNTAS":

                st.subheader("➕ Agregar Pregunta")

                nueva_id = st.text_input(
                    "ID Pregunta"
                )

                nueva_seccion = st.selectbox(
                    "Sección",
                    [
                        "",
                        "Proceso",
                        "Preguntas Generales"
                    ]
                )

                nuevo_proceso = st.selectbox(
                    "Proceso",
                    [""] + df_procesos["PROCESO"]
                    .dropna()
                    .astype(str)
                    .tolist()
                )

                nueva_pregunta = st.text_area(
                    "Pregunta"
                )

                nuevo_tipo = st.selectbox(
                    "Tipo",
                    [
                        "",
                        "RADIO",
                        "SELECT",
                        "TEXTO",
                        "NUMERO",
                        "FECHA",
                        "FOTO"
                    ]
                )

                nuevas_opciones = st.text_input(
                    "Opciones (separadas por |)"
                )

                nueva_visible_si = st.text_input(
                    "Visible Si"
                )

                nueva_activa = st.selectbox(
                    "Activa",
                    ["Si", "No"]
                )

                if st.button("➕ Agregar Pregunta"):

                    if (
                        nueva_id != ""
                        and nueva_pregunta != ""
                    ):

                        proceso_id = ""

                        if nuevo_proceso != "":

                            proceso_id = df_procesos[
                                df_procesos["PROCESO"]
                                == nuevo_proceso
                            ]["ID"].values[0]

                        nuevo_df = pd.DataFrame({

                            "ID": [nueva_id],
                            "SECCION": [nueva_seccion],
                            "PROCESO_ID": [proceso_id],
                            "PREGUNTA": [nueva_pregunta],
                            "TIPO": [nuevo_tipo],
                            "OPCIONES": [nuevas_opciones],
                            "VISIBLE_SI": [nueva_visible_si],
                            "ACTIVA": [nueva_activa]

                        })

                        df_admin = pd.concat(
                            [df_admin, nuevo_df],
                            ignore_index=True
                        )

                        guardar_sql(
                            df_admin,
                            hoja_excel
                        )

                        st.success(
                            "✅ Pregunta agregada"
                        )

                        st.rerun()

            # =========================================================
            # RESTO
            # =========================================================

            else:

                st.subheader("➕ Agregar Valor")

                nuevo_valor = st.text_input(
                    "Nuevo valor"
                )

                if st.button("➕ Agregar"):

                    if nuevo_valor != "":

                        nuevo_df = pd.DataFrame({

                            df_admin.columns[0]:
                            [nuevo_valor]

                        })

                        df_admin = pd.concat(
                            [df_admin, nuevo_df],
                            ignore_index=True
                        )

                        guardar_sql(
                            df_admin,
                            hoja_excel
                        )

                        st.success(
                            "✅ Valor agregado"
                        )

                        st.rerun()

            st.divider()

            # =========================================================
            # ELIMINAR
            # =========================================================

            lista_eliminar = [""] + (
                df_admin.iloc[:, 0]
                .astype(str)
                .tolist()
            )

            eliminar_valor = st.selectbox(
                "Eliminar valor",
                lista_eliminar,
                index=0
            )

            if st.button("🗑️ Eliminar"):

                if eliminar_valor != "":

                    df_admin = df_admin[
                        df_admin.iloc[:, 0]
                        .astype(str)
                        != eliminar_valor
                    ]

                    guardar_sql(
                        df_admin,
                        hoja_excel
                    )

                    st.success(
                        "✅ Valor eliminado"
                    )

                    st.rerun()

# =========================================================
# CALENDARIO
# =========================================================

if seleccion == "Calendario":

    st.title("📅 Calendario OWD")

    # ------------------------------------------------
    # LEER GOOGLE SHEETS
    # ------------------------------------------------

    url_sheet = (
        "https://docs.google.com/spreadsheets/d/"
        "15gt8H1fcmZSFAhQBCcOvlTopMXTIW6lFMYgXJi0BS6k"
        "/export?format=csv&gid=0"
    )

    df_cal = pd.read_csv(url_sheet)

    st.write(df_cal.head())
    st.write(df_cal.columns.tolist())

    # ------------------------------------------------
    # NORMALIZAR CAMPOS
    # ------------------------------------------------

    df_cal["Fecha Programacion"] = pd.to_datetime(
        df_cal["Fecha Programacion"],
        errors="coerce",
        dayfirst=True
    )

    df_cal["PILAR"] = (
        df_cal["Area Operario"]
        .astype(str)
        .str.strip()
    )

    df_cal["PROCESO"] = (
        df_cal["OWD a realizar"]
        .astype(str)
        .str.strip()
    )

    df_cal["AUDITOR"] = (
        df_cal["Auditor 1"]
        .astype(str)
        .str.strip()
    )

    # ------------------------------------------------
    # FILTROS
    # ------------------------------------------------

    col1, col2, col3 = st.columns(3)

    lista_meses = sorted(
        df_cal["Fecha Programacion"]
        .dropna()
        .dt.strftime("%Y-%m")
        .unique()
    )

    mes = col1.selectbox(
        "Mes",
        lista_meses,
        index=len(lista_meses)-1
    )

    lista_auditores = sorted(
        df_cal["AUDITOR"]
        .dropna()
        .unique()
        .tolist()
    )

    auditor_filtro = col2.selectbox(
        "Auditor",
        ["Todos"] + lista_auditores
    )

    lista_operarios = sorted(
        df_cal["Operario"]
        .dropna()
        .astype(str)
        .unique()
        .tolist()
    )

    operario_filtro = col3.selectbox(
        "Operario",
        ["Todos"] + lista_operarios
    )

    # ------------------------------------------------
    # FILTRAR
    # ------------------------------------------------

    df_filtrado = df_cal.copy()

    df_filtrado = df_filtrado[
        df_filtrado["Fecha Programacion"]
        .dt.strftime("%Y-%m")
        == mes
    ]

    if auditor_filtro != "Todos":

        df_filtrado = df_filtrado[
            df_filtrado["AUDITOR"]
            == auditor_filtro
        ]

    if operario_filtro != "Todos":

        df_filtrado = df_filtrado[
            df_filtrado["Operario"]
            == operario_filtro
        ]

    # ------------------------------------------------
    # COLORES POR PILAR
    # ------------------------------------------------

    colores = {

        "Seguridad":
            "#ef4444",

        "Flota":
            "#3b82f6",

        "Gestión":
            "#f59e0b",

        "Planeamiento":
            "#6b7280",

        "Almacén":
            "#10b981",

        "Entrega":
            "#8b5cf6"
    }

    # ------------------------------------------------
    # RESUMEN
    # ------------------------------------------------

    st.info(
        f"OWD planificadas: {len(df_filtrado)}"
    )

    st.divider()

    # ------------------------------------------------
    # EVENTOS
    # ------------------------------------------------

    if df_filtrado.empty:

        st.warning(
            "No existen OWD para los filtros seleccionados."
        )

    else:

        df_filtrado = df_filtrado.sort_values(
            "Fecha Programacion"
        )

        for _, row in df_filtrado.iterrows():

            fecha = row["Fecha Programacion"]

            pilar = str(
                row["PILAR"]
            )

            proceso = str(
                row["PROCESO"]
            )

            auditor = str(
                row["AUDITOR"]
            )

            operario = str(
                row["Operario"]
            )

            estado = str(
                row["Estado"]
            )

            color = colores.get(
                pilar,
                "#6b7280"
            )

            st.markdown(
                f"""
                <div style="
                    border-left:8px solid {color};
                    background:#111827;
                    padding:12px;
                    margin-bottom:10px;
                    border-radius:10px;
                    color:white;
                ">

                <b>📅 {fecha.strftime('%d/%m/%Y')}</b><br>

                🏭 <b>{pilar}</b><br>

                ⚙️ {proceso}<br>

                👤 Auditor: {auditor}<br>

                👷 Operario: {operario}<br>

                📌 Estado: {estado}

                </div>
                """,
                unsafe_allow_html=True
            )