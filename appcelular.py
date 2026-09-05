import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import plotly.express as px
from datetime import datetime, date, timedelta
from zoneinfo import ZoneInfo
import json
import os
import re
import base64
from fpdf import FPDF
import io

# ==========================================
# 0. CONFIGURACIÓN DE FECHA / HORA LOCAL (COLOMBIA)
# ==========================================
DIAS_ES = {
    "Monday": "Lunes", "Tuesday": "Martes", "Wednesday": "Miércoles",
    "Thursday": "Jueves", "Friday": "Viernes", "Saturday": "Sábado", "Sunday": "Domingo"
}
MESES_ES = {
    "January": "enero", "February": "febrero", "March": "marzo", "April": "abril",
    "May": "mayo", "June": "junio", "July": "julio", "August": "agosto",
    "September": "septiembre", "October": "octubre", "November": "noviembre", "December": "diciembre"
}

def obtener_fecha_hora_colombia():
    """Obtiene la fecha y hora exacta actual en el huso horario de Colombia (America/Bogota)."""
    ahora = datetime.now(ZoneInfo("America/Bogota"))
    
    dia_sem = DIAS_ES.get(ahora.strftime("%A"), "")
    dia_num = ahora.day
    mes = MESES_ES.get(ahora.strftime("%B"), "")
    anio = ahora.year
    
    hora_12 = ahora.strftime("%I").lstrip("0")
    if not hora_12:
        hora_12 = "12"
    minutos = ahora.strftime("%M")
    ampm_str = "p. m." if ahora.hour >= 12 else "a. m."
    
    return f"{dia_sem} {dia_num} de {mes} de {anio}, {hora_12}:{minutos} {ampm_str}"

# ==========================================
# 1. CONFIGURACIÓN DE PÁGINA Y SOPORTE MÓVIL
# ==========================================
st.set_page_config(
    page_title="Bytepulse - Quantumsoft",
    page_icon="📈",
    layout="centered"
)

st.markdown("""
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
        <meta name="mobile-web-app-capable" content="yes">
        <meta name="theme-color" content="#0b0f19">
        <style>
            .stApp {
                background-color: #0b0f19;
                color: #ffffff;
            }
            .element-container, .stMetric {
                width: 100% !important;
            }
        </style>
    </head>
""", unsafe_allow_html=True)

DB_FILE = "usuarios_data.json"
LOGO_FILE = "bytepulse-logo.png"

def obtener_logo_base64():
    """Convierte la imagen local del logo a formato data URI en Base64 para Plotly."""
    if os.path.exists(LOGO_FILE):
        try:
            with open(LOGO_FILE, "rb") as f:
                encoded = base64.b64encode(f.read()).decode("utf-8")
                return f"data:image/png;base64,{encoded}"
        except Exception:
            pass
    return None

def cargar_datos():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "admin": {
            "password": "123",
            "telefono": "3000000000",
            "transacciones": [],
            "metas": []
        }
    }

def guardar_datos():
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(st.session_state.db_usuarios, f, indent=4, ensure_ascii=False)

def validar_telefono_colombia(telefono):
    patron = r"^3\d{9}$"
    return bool(re.match(patron, telefono))

if 'db_usuarios' not in st.session_state:
    st.session_state.db_usuarios = cargar_datos()

if 'usuario_actual' not in st.session_state:
    st.session_state.usuario_actual = None

if 'mostrar_registro' not in st.session_state:
    st.session_state.mostrar_registro = False

def formato_cop(valor):
    if valor < 0:
        return f"-${abs(valor):,.0f}".replace(",", ".")
    return f"${valor:,.0f}".replace(",", ".")

def parsear_monto(texto_monto):
    if not texto_monto:
        return 0.0
    limpio = re.sub(r"[^\d]", "", str(texto_monto))
    return float(limpio) if limpio else 0.0

def recalcular_metas(usuario_data):
    """Actualiza el progreso real de cada meta sumando los movimientos asociados."""
    for meta in usuario_data.get("metas", []):
        nombre_meta = meta["Meta"]
        total_acumulado = 0.0
        for t in usuario_data.get("transacciones", []):
            if t.get("Meta_Asociada") == nombre_meta:
                monto = t.get("Monto", 0.0)
                tipo = t.get("Tipo")
                categoria = t.get("Categoría")
                
                if tipo == "Ahorro / Inversión" or categoria == "Ahorro Meta":
                    total_acumulado += monto
                elif categoria == "Uso Fondo Meta":
                    total_acumulado -= monto
        meta["Actual"] = max(0.0, total_acumulado)

def generar_pdf_transacciones(usuario, transacciones):
    pdf = FPDF()
    pdf.add_page()
    
    if os.path.exists(LOGO_FILE):
        try:
            pdf.image(LOGO_FILE, x=12, y=10, w=22)
        except Exception:
            pass

    pdf.set_xy(38, 12)
    pdf.set_font("Arial", "B", 15)
    pdf.cell(140, 8, "Bytepulse - Reporte de Movimientos", 0, 1, "L")
    
    pdf.set_x(38)
    pdf.set_font("Arial", "", 11)
    pdf.cell(140, 6, f"Usuario: {usuario.capitalize()}", 0, 1, "L")
    
    fecha_generacion_str = obtener_fecha_hora_colombia()
    
    pdf.set_x(38)
    pdf.cell(140, 6, f"Fecha de generacion: {fecha_generacion_str}", 0, 1, "L")
    
    pdf.ln(10)
    
    pdf.set_font("Arial", "B", 9)
    pdf.cell(25, 8, "Fecha", 1, 0, "C")
    pdf.cell(25, 8, "Tipo", 1, 0, "C")
    pdf.cell(35, 8, "Categoria", 1, 0, "C")
    pdf.cell(30, 8, "Monto", 1, 0, "C")
    pdf.cell(45, 8, "Descripcion", 1, 0, "C")
    pdf.cell(30, 8, "Meta", 1, 1, "C")
    
    pdf.set_font("Arial", "", 8)
    for t in transacciones:
        pdf.cell(25, 7, str(t.get("Fecha", "")), 1)
        pdf.cell(25, 7, str(t.get("Tipo", "")), 1)
        pdf.cell(35, 7, str(t.get("Categoría", "")), 1)
        pdf.cell(30, 7, f"${t.get('Monto', 0):,.0f}", 1)
        pdf.cell(45, 7, str(t.get("Descripción", "")), 1)
        pdf.cell(30, 7, str(t.get("Meta_Asociada", "Ninguna")), 1)
        pdf.ln()
        
    pdf_output = pdf.output(dest='S')
    if isinstance(pdf_output, str):
        return pdf_output.encode('latin1')
    return bytes(pdf_output)

def generar_pdf_meta(usuario, meta, transacciones_meta):
    pdf = FPDF()
    pdf.add_page()
    
    if os.path.exists(LOGO_FILE):
        try:
            pdf.image(LOGO_FILE, x=12, y=10, w=22)
        except Exception:
            pass

    pdf.set_xy(38, 12)
    pdf.set_font("Arial", "B", 15)
    pdf.cell(140, 8, f"Bytepulse - Meta: {meta['Meta']}", 0, 1, "L")
    
    pdf.set_x(38)
    pdf.set_font("Arial", "", 11)
    pdf.cell(140, 6, f"Usuario: {usuario.capitalize()}", 0, 1, "L")
    
    fecha_generacion_str = obtener_fecha_hora_colombia()
    
    pdf.set_x(38)
    pdf.cell(140, 6, f"Fecha de generacion: {fecha_generacion_str}", 0, 1, "L")
    
    pdf.ln(5)
    pdf.set_font("Arial", "B", 10)
    pdf.cell(190, 6, f"Objetivo: ${meta['Objetivo']:,.0f} | Acumulado Actual: ${meta['Actual']:,.0f}", 0, 1, "L")
    pdf.cell(190, 6, f"Periodo: {meta.get('Fecha_Inicio')} al {meta.get('Fecha_Fin')}", 0, 1, "L")
    
    pdf.ln(6)
    
    pdf.set_font("Arial", "B", 9)
    pdf.cell(25, 8, "Fecha", 1, 0, "C")
    pdf.cell(30, 8, "Tipo", 1, 0, "C")
    pdf.cell(35, 8, "Categoria", 1, 0, "C")
    pdf.cell(30, 8, "Monto", 1, 0, "C")
    pdf.cell(30, 8, "Acumulado", 1, 0, "C")
    pdf.cell(40, 8, "Descripcion", 1, 1, "C")
    
    pdf.set_font("Arial", "", 8)
    acumulado_temporal = 0
    for t in transacciones_meta:
        monto = t.get('Monto', 0)
        tipo = t.get("Tipo")
        categoria = t.get("Categoría")
        if tipo == "Ahorro / Inversión" or categoria == "Ahorro Meta":
            acumulado_temporal += monto
        elif categoria == "Uso Fondo Meta":
            acumulado_temporal -= monto
            
        desc_limpia = "Ahorro diario" if t.get("Categoría") == "Ahorro Meta" and not str(t.get("Descripción", "")).strip() else str(t.get("Descripción", ""))
        if t.get("Categoría") == "Ahorro Meta" and not desc_limpia:
            desc_limpia = "Ahorro diario"
            
        pdf.cell(25, 7, str(t.get("Fecha", "")), 1)
        pdf.cell(30, 7, str(tipo or ""), 1)
        pdf.cell(35, 7, str(categoria or ""), 1)
        pdf.cell(30, 7, f"${monto:,.0f}", 1)
        pdf.cell(30, 7, f"${acumulado_temporal:,.0f}", 1)
        pdf.cell(40, 7, desc_limpia, 1)
        pdf.ln()
        
    pdf_output = pdf.output(dest='S')
    if isinstance(pdf_output, str):
        return pdf_output.encode('latin1')
    return bytes(pdf_output)

# ==========================================
# 2. AUTENTICACIÓN Y REGISTRO
# ==========================================
if st.session_state.usuario_actual is None:
    col_logo1, col_logo2, col_logo3 = st.columns([1, 2, 1])
    with col_logo2:
        if os.path.exists(LOGO_FILE):
            st.image(LOGO_FILE, width=100)
        else:
            st.markdown("<div style='text-align: center; font-size: 40px;'>🦝⚡</div>", unsafe_allow_html=True)
            
    st.markdown("<h2 style='text-align: center;'>Bytepulse 📈</h2>", unsafe_allow_html=True)
    st.markdown(f"<p style='text-align: center; font-size: 12px; color: gray;'>Gestión Financiera | 🕒 {obtener_fecha_hora_colombia()}</p>", unsafe_allow_html=True)
    st.divider()

    if not st.session_state.mostrar_registro:
        st.subheader("🔑 Iniciar Sesión")
        with st.form("form_login"):
            user_login = st.text_input("Usuario").strip().lower()
            pass_login = st.text_input("Contraseña", type="password")
            btn_login = st.form_submit_button("Entrar", use_container_width=True)

            if btn_login:
                db = st.session_state.db_usuarios
                if user_login in db and db[user_login]["password"] == pass_login:
                    st.session_state.usuario_actual = user_login
                    recalcular_metas(db[user_login])
                    st.success(f"¡Bienvenido {user_login}!")
                    st.rerun()
                else:
                    st.error("Usuario o contraseña incorrectos.")

        st.write("")
        if st.button("📝 ¿No tienes cuenta? Regístrate aquí", use_container_width=True):
            st.session_state.mostrar_registro = True
            st.rerun()
    else:
        st.subheader("📝 Crear Nueva Cuenta")
        with st.form("form_registro"):
            user_reg = st.text_input("Nuevo Usuario").strip().lower()
            pass_reg = st.text_input("Nueva Contraseña", type="password")
            tel_reg = st.text_input("Celular (+57 Colombia)", placeholder="Ej: 3101234567").strip()
            btn_reg = st.form_submit_button("Registrarse", use_container_width=True)

            if btn_reg:
                if not user_reg or not pass_reg or not tel_reg:
                    st.warning("Completa todos los campos.")
                elif user_reg in st.session_state.db_usuarios:
                    st.error("El usuario ya existe.")
                elif not validar_telefono_colombia(tel_reg):
                    st.error("Celular inválido (10 dígitos empezando por 3).")
                else:
                    st.session_state.db_usuarios[user_reg] = {
                        "password": pass_reg,
                        "telefono": tel_reg,
                        "transacciones": [],
                        "metas": []
                    }
                    guardar_datos()
                    st.success("Cuenta creada con éxito.")
                    st.session_state.mostrar_registro = False
                    st.rerun()

        if st.button("⬅️ Volver al Login", use_container_width=True):
            st.session_state.mostrar_registro = False
            st.rerun()
    st.stop()

# ==========================================
# 3. PANEL PRINCIPAL Y MENÚ LATERAL
# ==========================================
user = st.session_state.usuario_actual
datos_user = st.session_state.db_usuarios[user]
es_admin = (user == "admin")

recalcular_metas(datos_user)

with st.sidebar:
    if os.path.exists(LOGO_FILE):
        col_l1, col_l2, col_l3 = st.columns([1, 2, 1])
        with col_l2:
            st.image(LOGO_FILE, width=80)
            
    st.markdown(f"### 👤 {user.capitalize()}")
    st.caption(f"🕒 {obtener_fecha_hora_colombia()}")
    st.divider()
    
    opciones_disponibles = ["📊 Dashboard", "📝 Movimientos", "🎯 Ahorro", "📈 Metas", "⚙️ Ajustes"]
    if es_admin:
        opciones_disponibles.append("👑 Admin")
        
    menu_seleccionado = st.radio("Navegación", opciones_disponibles)
    
    st.divider()
    if st.button("🔒 Cerrar Sesión", use_container_width=True):
        st.session_state.usuario_actual = None
        st.rerun()

df = pd.DataFrame(datos_user["transacciones"])

# ==========================================
# 4. VISTA: DASHBOARD
# ==========================================
if menu_seleccionado == "📊 Dashboard":
    st.title("📊 Dashboard")
    st.caption(f"📅 {obtener_fecha_hora_colombia()}")
    
    if not df.empty:
        ingresos_totales = float(df[df['Tipo'] == 'Ingreso']['Monto'].sum())
        gastos_ordinarios = float(df[(df['Tipo'] == 'Gasto') & (df['Categoría'] != 'Uso Fondo Meta')]['Monto'].sum())
        deudas_totales = float(df[df['Tipo'] == 'Deuda']['Monto'].sum())
        ahorros_totales = float(df[df['Tipo'] == 'Ahorro / Inversión']['Monto'].sum())
        gastos_de_ahorros = float(df[df['Categoría'] == 'Uso Fondo Meta']['Monto'].sum())
        
        fondo_ahorro_neto = max(0.0, ahorros_totales - gastos_de_ahorros)
        gastos_totales_visibles = gastos_ordinarios + gastos_de_ahorros
    else:
        ingresos_totales, gastos_ordinarios, deudas_totales, ahorros_totales, gastos_de_ahorros, fondo_ahorro_neto, gastos_totales_visibles = 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0

    egresos_corrientes = gastos_ordinarios + deudas_totales
    balance = ingresos_totales - egresos_corrientes - fondo_ahorro_neto
    
    if ingresos_totales > 0:
        porcentaje_gastado = (egresos_corrientes / ingresos_totales) * 100
        if porcentaje_gastado >= 100:
            st.error(f"🚨 **¡Límite Superado!** ({porcentaje_gastado:.1f}% gastado).")
        elif porcentaje_gastado >= 80:
            st.warning(f"⚠️ **Aviso:** Has consumido el {porcentaje_gastado:.1f}% de tus ingresos.")
        else:
            st.success(f"✅ **Saludable:** {porcentaje_gastado:.1f}% utilizado.")

    mc1, mc2 = st.columns(2)
    with mc1:
        st.metric("Balance Libre", formato_cop(balance))
        st.metric("Gastos Totales", formato_cop(gastos_totales_visibles))
    with mc2:
        st.metric("Ingresos", formato_cop(ingresos_totales))
        st.metric("Fondo Ahorro", formato_cop(fondo_ahorro_neto))
    
    st.divider()

    st.subheader("💡 Presupuesto y Proyección")
    presupuesto_disponible = ingresos_totales - egresos_corrientes
    gasto_diario_sugerido = presupuesto_disponible / 30.0
    gasto_semanal_sugerido = presupuesto_disponible / 4.33
    
    pc1, pc2 = st.columns(2)
    with pc1:
        st.metric("Máx. Diario", formato_cop(gasto_diario_sugerido))
        st.metric("Máx. Semanal", formato_cop(gasto_semanal_sugerido))
    with pc2:
        st.metric("Disp. Mensual", formato_cop(presupuesto_disponible))

    st.divider()
    
    if not df.empty:
        st.subheader("Gráficos de Distribución")
        df_activos = df[df['Monto'] > 0]
        if not df_activos.empty:
            logo_uri = obtener_logo_base64()

            def agregar_logo_a_grafico(fig):
                if logo_uri:
                    fig.add_layout_image(
                        source=logo_uri,
                        xref="paper", yref="paper",
                        x=0.02, y=0.98,
                        sizex=0.18, sizey=0.18,
                        xanchor="left", yanchor="top",
                        opacity=0.85,
                        layer="above"
                    )
                fig.update_layout(margin=dict(l=10, r=10, t=30, b=10), height=280)
                return fig

            st.markdown("##### Por Tipo de Movimiento")
            fig_pie = px.pie(df_activos, values='Monto', names='Tipo', hole=0.4)
            fig_pie = agregar_logo_a_grafico(fig_pie)
            st.plotly_chart(fig_pie, use_container_width=True)
            
            st.markdown("##### Por Categoría")
            df_cat = df_activos.groupby('Categoría', as_index=False)['Monto'].sum()
            fig_bar = px.bar(
                df_cat, 
                x='Categoría', 
                y='Monto', 
                color='Categoría', 
                text_auto='.2s'
            )
            fig_bar.update_layout(
                xaxis_title="",
                yaxis_title="Monto",
                showlegend=False
            )
            fig_bar = agregar_logo_a_grafico(fig_bar)
            st.plotly_chart(fig_bar, use_container_width=True)

# ==========================================
# 5. VISTA: MOVIMIENTOS
# ==========================================
elif menu_seleccionado == "📝 Movimientos":
    st.title("📝 Movimientos")
    
    categorias_disponibles = ["Uso Fondo Meta", "Nómina", "Alquiler", "Alimentación", "Servicios", "Transporte", "Tarjeta Crédito", "Inversión", "Otros"]

    with st.form("form_movimiento", clear_on_submit=True):
        tipo = st.selectbox("Tipo", ["Gasto", "Ahorro / Inversión", "Ingreso", "Deuda"])
        monto_input_raw = st.text_input("Monto (COP $)", value="50.000")
        fecha = st.date_input("Fecha", datetime.now(ZoneInfo("America/Bogota")).date())
        categoria = st.selectbox("Categoría", categorias_disponibles)
        descripcion = st.text_input("Descripción")
        
        guardar = st.form_submit_button("Guardar Transacción", use_container_width=True)

    if guardar:
        monto = parsear_monto(monto_input_raw)
        if monto <= 0:
            st.warning("Monto no válido.")
        else:
            datos_user["transacciones"].append({
                "Fecha": str(fecha), 
                "Tipo": tipo, 
                "Categoría": categoria,
                "Monto": monto, 
                "Descripción": descripcion, 
                "Meta_Asociada": "Ninguna"
            })
            recalcular_metas(datos_user)
            guardar_datos()
            st.success("¡Guardado con éxito!")
            st.rerun()

    st.divider()
    st.subheader("Historial (Excluyendo Ahorros de Metas)")
    
    transacciones_corrientes_con_indices = [
        (i, t) for i, t in enumerate(datos_user["transacciones"])
        if t.get("Categoría") != "Ahorro Meta"
    ]
    
    if not transacciones_corrientes_con_indices:
        st.info("No hay registros corrientes en el historial.")
    else:
        indices_globales, transacciones_corrientes = zip(*transacciones_corrientes_con_indices)
        transacciones_corrientes = list(transacciones_corrientes)
        indices_globales = list(indices_globales)
        
        df_mov = pd.DataFrame(transacciones_corrientes)
        st.dataframe(
            df_mov[['Fecha', 'Tipo', 'Categoría', 'Monto', 'Descripción']],
            use_container_width=True,
            hide_index=True
        )
        
        pdf_bytes = generar_pdf_transacciones(user, transacciones_corrientes)
        st.download_button(
            label="📥 Descargar Reporte en PDF",
            data=pdf_bytes,
            file_name=f"reporte_{user}.pdf",
            mime="application/pdf",
            use_container_width=True
        )
        
        st.write("")
        st.subheader("🗑️ Gestión de Eliminación")
        
        def formato_opcion(i_pos):
            t = transacciones_corrientes[i_pos]
            return f"#{i_pos+1} - {t['Fecha']} | {t['Tipo']} | {formato_cop(t['Monto'])} | {t['Categoría']}"
            
        transaccion_a_borrar_idx = st.selectbox("Seleccionar registro específico", range(len(transacciones_corrientes)), format_func=formato_opcion)
        
        if st.button("❌ Eliminar transacción seleccionada", use_container_width=True):
            indice_real = indices_globales[transaccion_a_borrar_idx]
            datos_user["transacciones"].pop(indice_real)
            recalcular_metas(datos_user)
            guardar_datos()
            st.success("Transacción eliminada correctamente.")
            st.rerun()

        st.write("")
        if "confirmar_borrar_todo" not in st.session_state:
            st.session_state.confirmar_borrar_todo = False

        if not st.session_state.confirmar_borrar_todo:
            if st.button("⚠️ Borrar TODO el historial corriente", use_container_width=True, type="secondary"):
                st.session_state.confirmar_borrar_todo = True
                st.rerun()
        else:
            st.error("¿Estás completamente seguro de borrar tus movimientos corrientes?")
            col_b1, col_b2 = st.columns(2)
            with col_b1:
                if st.button("Sí, borrar todo", use_container_width=True, type="primary"):
                    datos_user["transacciones"] = [t for t in datos_user["transacciones"] if t.get("Categoría") == "Ahorro Meta"]
                    recalcular_metas(datos_user)
                    guardar_datos()
                    st.session_state.confirmar_borrar_todo = False
                    st.success("Historial corriente borrado.")
                    st.rerun()
            with col_b2:
                if st.button("Cancelar", use_container_width=True):
                    st.session_state.confirmar_borrar_todo = False
                    st.rerun()

# ==========================================
# 6. VISTA: AHORRO (GESTIÓN GENERAL)
# ==========================================
elif menu_seleccionado == "🎯 Ahorro":
    st.title("🎯 Ahorro y Creación de Metas")
    
    with st.form("form_nueva_meta", clear_on_submit=True):
        nombre_meta = st.text_input("Nombre de la Meta", value="Viaje")
        monto_meta_raw = st.text_input("Monto Objetivo (COP $)", value="1.000.000")
        
        fecha_inicio = st.date_input("Fecha Inicio", datetime.now(ZoneInfo("America/Bogota")).date())
        fecha_fin = st.date_input("Fecha Límite", datetime.now(ZoneInfo("America/Bogota")).date())
            
        crear_meta_btn = st.form_submit_button("Crear Meta", use_container_width=True)

    if crear_meta_btn:
        monto_meta = parsear_monto(monto_meta_raw)
        if not nombre_meta.strip():
            st.warning("Asigna un nombre.")
        elif monto_meta <= 0:
            st.warning("Objetivo mayor a 0.")
        elif fecha_fin < fecha_inicio:
            st.error("Fechas incorrectas.")
        else:
            datos_user["metas"].append({
                "Meta": nombre_meta,
                "Objetivo": monto_meta,
                "Actual": 0.0,
                "Fecha_Inicio": str(fecha_inicio),
                "Fecha_Fin": str(fecha_fin),
                "ahorros_diarios_marcados": {}
            })
            recalcular_metas(datos_user)
            guardar_datos()
            st.success("¡Meta creada!")
            st.rerun()

    st.divider()
    st.subheader("Listado de Metas Activas")
    
    if not datos_user.get("metas"):
        st.info("Sin metas registradas.")
    else:
        recalcular_metas(datos_user)
        for idx, meta in enumerate(datos_user["metas"]):
            with st.container(border=True):
                st.markdown(f"### 🎯 {meta['Meta']}")
                st.caption(f"📅 Desde {meta.get('Fecha_Inicio')} hasta {meta.get('Fecha_Fin')}")
                
                progreso = min(meta['Actual'] / meta['Objetivo'], 1.0) if meta['Objetivo'] > 0 else 0.0
                st.progress(progreso)
                st.write(f"**Ahorrado:** {formato_cop(meta['Actual'])} / **Obj:** {formato_cop(meta['Objetivo'])} ({progreso*100:.1f}%)")
                
                if st.button("Eliminar Meta", key=f"meta_del_ahorro_{idx}", use_container_width=True):
                    datos_user["transacciones"] = [t for t in datos_user["transacciones"] if t.get("Meta_Asociada") != meta['Meta']]
                    datos_user["metas"].pop(idx)
                    guardar_datos()
                    st.success("Meta eliminada.")
                    st.rerun()

# ==========================================
# 7. VISTA: METAS (SUGERENCIAS, CHECKLIST, GRÁFICA Y TABLA)
# ==========================================
elif menu_seleccionado == "📈 Metas":
    st.title("📈 Seguimiento de Metas")
    
    if not datos_user.get("metas"):
        st.info("No hay metas creadas. Ve a la sección **Ahorro** para crear una primero.")
    else:
        recalcular_metas(datos_user)
        hoy = datetime.now(ZoneInfo("America/Bogota")).date()
        
        nombres_metas_lista = [m["Meta"] for m in datos_user["metas"]]
        meta_seleccionada_nombre = st.selectbox("Selecciona la meta a gestionar", nombres_metas_lista)
        
        meta = next((m for m in datos_user["metas"] if m["Meta"] == meta_seleccionada_nombre), None)
        
        if meta:
            st.divider()
            st.markdown(f"### 🎯 {meta['Meta']}")
            st.caption(f"📅 Desde {meta.get('Fecha_Inicio')} hasta {meta.get('Fecha_Fin')}")
            
            f_inicio = datetime.strptime(meta.get('Fecha_Inicio', str(hoy)), "%Y-%m-%d").date()
            f_fin = datetime.strptime(meta.get('Fecha_Fin', str(hoy)), "%Y-%m-%d").date()
            
            monto_faltante = max(0.0, meta['Objetivo'] - meta['Actual'])
            dias_restantes = max(1, (f_fin - hoy).days)
            
            sugerencia_diaria = monto_faltante / dias_restantes if dias_restantes > 0 else 0.0
            sugerencia_semanal = sugerencia_diaria * 7
            sugerencia_mensual = sugerencia_diaria * 30
            
            st.markdown("##### 💡 Sugerencia para cumplir tu meta:")
            sc1, sc2, sc3 = st.columns(3)
            with sc1:
                st.metric("Diario", formato_cop(sugerencia_diaria))
            with sc2:
                st.metric("Semanal", formato_cop(sugerencia_semanal))
            with sc3:
                st.metric("Mensual", formato_cop(sugerencia_mensual))

            st.divider()
            
            progreso = min(meta['Actual'] / meta['Objetivo'], 1.0) if meta['Objetivo'] > 0 else 0.0
            st.progress(progreso)
            st.write(f"**Ahorrado:** {formato_cop(meta['Actual'])} / **Obj:** {formato_cop(meta['Objetivo'])} ({progreso*100:.1f}%)")
            
            # --- CHECKLIST DIARIO RÁPIDO CON APORTE PERSONALIZADO ---
            st.markdown("##### ✅ Registro Rápido Diario")
            if "ahorros_diarios_marcados" not in meta:
                meta["ahorros_diarios_marcados"] = {}
            
            fecha_hoy_str = str(hoy)
            ya_hecho_hoy = fecha_hoy_str in meta["ahorros_diarios_marcados"]
            
            col_c1, col_c2 = st.columns([2, 1])
            with col_c1:
                monto_sugerido_hoy = st.text_input("Monto a aportar hoy", value=str(int(sugerencia_diaria)) if sugerencia_diaria > 0 else "5000", key="monto_dia_meta")
            with col_c2:
                st.write("")
                st.write("")
                marcar_hoy = st.checkbox("Marcar como hecho hoy", value=ya_hecho_hoy, key="chk_hoy_meta")

            monto_parseado_chk = parsear_monto(monto_sugerido_hoy)
            
            if marcar_hoy and not ya_hecho_hoy and monto_parseado_chk > 0:
                meta["ahorros_diarios_marcados"][fecha_hoy_str] = monto_parseado_chk
                datos_user["transacciones"].append({
                    "Fecha": fecha_hoy_str,
                    "Tipo": "Ahorro / Inversión",
                    "Categoría": "Ahorro Meta",
                    "Monto": monto_parseado_chk,
                    "Descripción": "Ahorro diario",
                    "Meta_Asociada": meta['Meta']
                })
                recalcular_metas(datos_user)
                guardar_datos()
                st.rerun()
            elif not marcar_hoy and ya_hecho_hoy:
                meta["ahorros_diarios_marcados"].pop(fecha_hoy_str, None)
                datos_user["transacciones"] = [
                    t for t in datos_user["transacciones"] 
                    if not (t.get("Meta_Asociada") == meta['Meta'] and t.get("Fecha") == fecha_hoy_str and t.get("Categoría") == "Ahorro Meta")
                ]
                recalcular_metas(datos_user)
                guardar_datos()
                st.rerun()

            st.divider()

            # --- GRÁFICO LINEAL DE PROGRESO DIARIO / ACUMULADO ---
            st.markdown("##### 📈 Evolución Diaria y Acumulada del Ahorro")
            
            movs_meta_con_indices = [
                (i, t) for i, t in enumerate(datos_user.get("transacciones", []))
                if t.get("Meta_Asociada") == meta['Meta']
            ]
            
            if movs_meta_con_indices:
                _, movs_meta = zip(*movs_meta_con_indices)
                df_grafica = pd.DataFrame(list(movs_meta)).copy()
                
                if not df_grafica.empty:
                    df_grafica['Fecha'] = pd.to_datetime(df_grafica['Fecha'])
                    df_grafica = df_grafica.sort_values('Fecha').reset_index(drop=True)
                    df_grafica['Acumulado'] = df_grafica['Monto'].cumsum()
                    df_grafica['Fecha_Str'] = df_grafica['Fecha'].dt.strftime('%Y-%m-%d')
                    
                    logo_uri = obtener_logo_base64()
                    
                    fig_line = px.line(
                        df_grafica, 
                        x='Fecha_Str', 
                        y='Acumulado', 
                        markers=True,
                        labels={'Fecha_Str': 'Fecha', 'Acumulado': 'Ahorro Acumulado ($)'}
                    )
                    
                    fig_line.add_hline(
                        y=meta['Objetivo'], 
                        line_dash="dash", 
                        line_color="green",
                        annotation_text=f"Objetivo: {formato_cop(meta['Objetivo'])}",
                        annotation_position="top left"
                    )
                    
                    if logo_uri:
                        fig_line.add_layout_image(
                            source=logo_uri,
                            xref="paper", yref="paper",
                            x=0.02, y=0.98,
                            sizex=0.18, sizey=0.18,
                            xanchor="left", yanchor="top",
                            opacity=0.85,
                            layer="above"
                        )
                        
                    fig_line.update_layout(
                        margin=dict(l=10, r=10, t=30, b=10),
                        height=320,
                        xaxis_title="",
                        yaxis_title="Acumulado (COP)"
                    )
                    st.plotly_chart(fig_line, use_container_width=True)
            else:
                st.info("Registra al menos un aporte diario para visualizar la gráfica lineal de evolución.")

            st.divider()

            # --- TABLA AUTOMÁTICA Y ACUMULADA CON ELIMINACIÓN ---
            st.markdown("##### 📋 Tabla de Transacciones y Acumulado")
            
            if movs_meta_con_indices:
                indices_globales, movs_meta = zip(*movs_meta_con_indices)
                movs_meta = list(movs_meta)
                indices_globales = list(indices_globales)
                
                df_meta = pd.DataFrame(movs_meta).copy()
                df_meta['Acumulado'] = df_meta['Monto'].cumsum()
                
                df_meta['Descripción'] = df_meta.apply(
                    lambda row: "Ahorro diario" if row.get('Categoría') == "Ahorro Meta" and not str(row.get('Descripción', '')).strip() or "ahorro" in str(row.get('Descripción', '')).lower() else row.get('Descripción', ''),
                    axis=1
                )
                
                st.dataframe(
                    df_meta[['Fecha', 'Tipo', 'Categoría', 'Monto', 'Acumulado', 'Descripción']],
                    use_container_width=True,
                    hide_index=True
                )
                
                st.write("")
                st.markdown("##### 🗑️ Eliminar Movimiento de esta Meta")
                
                def formato_opcion_meta(idx_pos):
                    t = movs_meta[idx_pos]
                    desc_txt = t.get('Descripción') if t.get('Descripción') else t.get('Categoría')
                    return f"📅 {t['Fecha']} | {t['Tipo']} | {formato_cop(t['Monto'])} | {desc_txt}"
                
                seleccion_borrar_meta = st.selectbox(
                    "Selecciona el movimiento a eliminar", 
                    range(len(movs_meta)), 
                    format_func=formato_opcion_meta,
                    key="select_borrar_meta_trans"
                )
                
                if st.button("❌ Eliminar transacción seleccionada", use_container_width=True, key="btn_eliminar_meta_trans"):
                    indice_real_a_borrar = indices_globales[seleccion_borrar_meta]
                    
                    t_borrada = datos_user["transacciones"][indice_real_a_borrar]
                    if t_borrada.get("Fecha") in meta.get("ahorros_diarios_marcados", {}):
                        meta["ahorros_diarios_marcados"].pop(t_borrada.get("Fecha"), None)
                        
                    datos_user["transacciones"].pop(indice_real_a_borrar)
                    recalcular_metas(datos_user)
                    guardar_datos()
                    st.success("Transacción eliminada correctamente.")
                    st.rerun()

                st.write("")
                pdf_bytes_meta = generar_pdf_meta(user, meta, movs_meta)
                st.download_button(
                    label=f"📥 Descargar PDF ({meta['Meta']})",
                    data=pdf_bytes_meta,
                    file_name=f"meta_{meta['Meta'].lower().replace(' ', '_')}.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )
            else:
                st.info("Aún no hay movimientos registrados para esta meta.")

# ==========================================
# 8. VISTA: AJUSTES (CON FRECUENCIA PERSONALIZADA Y SONIDO NATIVO)
# ==========================================
elif menu_seleccionado == "⚙️ Ajustes":
    st.title("⚙️ Ajustes y Notificaciones")
    st.write(f"Usuario activo: **{user}**")
    st.caption(f"🕒 Hora local: {obtener_fecha_hora_colombia()}")
    
    st.divider()
    st.subheader("🔔 Notificaciones Automáticas Personalizadas")
    st.markdown("""
    Configura cuántas veces al día deseas recibir el recordatorio para registrar tu ahorro e inversión. La aplicación calculará los horarios automáticamente y reproducirá un sonido de alerta en tu dispositivo.
    """)
    
    # Selector de frecuencia diaria
    frecuencia_veces = st.slider("Frecuencia de avisos diarios", min_value=1, max_value=5, value=3)
    
    # Mostrar resumen de cómo se distribuirán
    if frecuencia_veces == 1:
        st.caption("🕒 Se enviará 1 vez al día (a las 12:00 p. m.)")
    elif frecuencia_veces == 2:
        st.caption("🕒 Se enviará 2 veces al día (a las 9:00 a. m. y 6:00 p. m.)")
    elif frecuencia_veces == 3:
        st.caption("🕒 Se enviará 3 veces al día (a las 8:00 a. m., 2:00 p. m. y 8:00 p. m.)")
    elif frecuencia_veces == 4:
        st.caption("🕒 Se enviará 4 veces al día (a las 8:00 a. m., 12:00 p. m., 4:00 p. m. y 8:00 p. m.)")
    elif frecuencia_veces == 5:
        st.caption("🕒 Se enviará 5 veces al día (a las 8:00 a. m., 11:00 a. m., 2:00 p. m., 5:00 p. m. y 8:00 p. m.)")

    # Botones de control de notificaciones con frecuencia y sonido nativo en JS
    col_notif1, col_notif2 = st.columns(2)
    with col_notif1:
        if st.button("Habilitar Alertas Personalizadas", use_container_width=True):
            # Inyectamos el valor seleccionado del slider mediante f-string en JavaScript
            permission_script = f"""
            <script>
            function initCustomNotifications() {{
                if (!("Notification" in window)) {{
                    alert("Este navegador no soporta notificaciones nativas.");
                    return;
                }}
                
                Notification.requestPermission().then(function (permission) {{
                    if (permission === "granted") {{
                        alert("¡Permiso concedido! Se programaron {frecuencia_veces} recordatorios diarios con sonido.");
                        localStorage.setItem("notifications_enabled", "true");
                        
                        // Función para reproducir un sonido sintetizado nativo (Beep de alerta)
                        function playNotificationSound() {{
                            try {{
                                const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
                                const osc = audioCtx.createOscillator();
                                const gain = audioCtx.createGain();
                                osc.type = 'sine';
                                osc.frequency.setValueAtTime(587.33, audioCtx.currentTime); // Nota D5
                                gain.gain.setValueAtTime(0.1, audioCtx.currentTime);
                                osc.connect(gain);
                                gain.connect(audioCtx.destination);
                                osc.start();
                                osc.stop(audioCtx.currentTime + 0.3);
                            }} catch(e) {{
                                console.log("Audio not supported or blocked");
                            }}
                        }}
                        
                        // Definir horarios según la frecuencia elegida ({frecuencia_veces} veces)
                        const frecuencia = {frecuencia_veces};
                        let horariosObjetivo = [];
                        
                        if (frecuencia === 1) horariosObjetivo = [12];
                        else if (frecuencia === 2) horariosObjetivo = [9, 18];
                        else if (frecuencia === 3) horariosObjetivo = [8, 14, 20];
                        else if (frecuencia === 4) horariosObjetivo = [8, 12, 16, 20];
                        else if (frecuencia === 5) horariosObjetivo = [8, 11, 14, 17, 20];
                        
                        // Limpiar intervalo anterior si existía
                        if (window.notificationInterval) {{
                            clearInterval(window.notificationInterval);
                        }}
                        
                        // Verificador en segundo plano cada minuto
                        window.notificationInterval = setInterval(function() {{
                            const now = new Date();
                            const hours = now.getHours();
                            const minutes = now.getMinutes();
                            
                            if (horariosObjetivo.includes(hours) && minutes === 0) {{
                                playNotificationSound();
                                const options = {{
                                    body: "¡Hola! Es hora de registrar tu inversión y ahorro diario en Bytepulse 💰.",
                                    icon: "https://cdn-icons-png.flaticon.com/512/2921/2921222.png",
                                    badge: "https://cdn-icons-png.flaticon.com/512/2921/2921222.png",
                                    tag: "recordatorio-ahorro-" + hours
                                }};
                                new Notification("Recordatorio de Ahorro Diario", options);
                            }}
                        }}, 60000);
                        
                    }} else {{
                        alert("Permiso denegado para mostrar notificaciones.");
                    }}
                }});
            }}
            initCustomNotifications();
            </script>
            """
            components.html(permission_script, height=0)

    with col_notif2:
        if st.button("Probar Notificación con Sonido", use_container_width=True):
            test_notification_script = """
            <script>
            function showNotificationWithSound() {
                if (Notification.permission === "granted") {
                    // Reproducir sonido de prueba
                    try {
                        const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
                        const osc = audioCtx.createOscillator();
                        const gain = audioCtx.createGain();
                        osc.type = 'sine';
                        osc.frequency.setValueAtTime(587.33, audioCtx.currentTime);
                        gain.gain.setValueAtTime(0.1, audioCtx.currentTime);
                        osc.connect(gain);
                        gain.connect(audioCtx.destination);
                        osc.start();
                        osc.stop(audioCtx.currentTime + 0.3);
                    } catch(e) {}

                    const options = {
                        body: "¡Prueba exitosa con sonido! Así sonarán tus alertas en Bytepulse 💰.",
                        icon: "https://cdn-icons-png.flaticon.com/512/2921/2921222.png",
                        badge: "https://cdn-icons-png.flaticon.com/512/2921/2921222.png",
                        tag: "recordatorio-ahorro-test"
                    };
                    new Notification("Recordatorio de Ahorro Diario", options);
                } else {
                    alert("Primero debes hacer clic en 'Habilitar Alertas Personalizadas'.");
                }
            }
            showNotificationWithSound();
            </script>
            """
            components.html(test_notification_script, height=0)
            st.success("¡Disparada con sonido de prueba!")

# ==========================================
# 9. VISTA: ADMIN
# ==========================================
elif menu_seleccionado == "👑 Admin" and es_admin:
    st.title("👑 Admin")
    st.write(f"Usuarios en sistema: {len(st.session_state.db_usuarios)}")
    st.caption(f"🕒 {obtener_fecha_hora_colombia()}")
