import math
import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

st.set_page_config(page_title="Diseño de megafonía NTE-IAM", page_icon="🔊", layout="wide")

# Datos transcritos de las tablas de cálculo de la NTE-IAM/1977 (BOE, 20-08-1977).
# Tabla 1: separación máxima L y superficie S por altavoz.
TABLA_1 = {
    2.5: {1: (5.50, 30.00), 2: (3.60, 12.00), 3: (2.50, 6.00)},
    3.0: {1: (9.00, 81.00), 2: (5.00, 25.00), 3: (3.50, 12.00)},
    3.5: {1: (12.00, 144.00), 2: (7.00, 49.00), 3: (5.00, 25.00)},
    4.0: {1: (15.00, 225.00), 2: (9.00, 81.00), 3: (6.00, 42.00)},
}
VOLUMENES = [40, 80, 160, 280, 400, 800, 1600, 2800, 4000, 8000]
RUIDOS = [50, 65, 80]
TABLA_2 = {
    50: [0.002, 0.004, 0.007, 0.012, 0.018, 0.035, 0.065, 0.12, 0.16, 0.30],
    65: [0.06, 0.12, 0.22, 0.39, 0.63, 1.00, 2.00, 3.50, 4.80, 9.00],
    80: [2.00, 3.80, 7.20, 12.50, 18.00, 32.00, 60.00, 100.00, 140.00, 270.00],
}


def interp(x, x0, x1, y0, y1):
    if x1 == x0:
        return y0
    return y0 + (x - x0) * (y1 - y0) / (x1 - x0)


def interp_1d(x, xs, ys):
    if x < xs[0] or x > xs[-1]:
        raise ValueError(f"Valor fuera del rango permitido ({xs[0]}–{xs[-1]}).")
    for i in range(len(xs) - 1):
        if xs[i] <= x <= xs[i + 1]:
            return interp(x, xs[i], xs[i + 1], ys[i], ys[i + 1])
    return ys[-1]


def superficie_por_altavoz(altura, nivel):
    alturas = sorted(TABLA_1)
    if altura < alturas[0] or altura > alturas[-1]:
        raise ValueError("La NTE-IAM contempla alturas entre 2,5 y 4 m.")
    if altura in TABLA_1:
        return TABLA_1[altura][nivel][1], TABLA_1[altura][nivel][0]
    for i in range(len(alturas) - 1):
        h0, h1 = alturas[i], alturas[i + 1]
        if h0 <= altura <= h1:
            s0, l0 = TABLA_1[h0][nivel][1], TABLA_1[h0][nivel][0]
            s1, l1 = TABLA_1[h1][nivel][1], TABLA_1[h1][nivel][0]
            return interp(altura, h0, h1, s0, s1), interp(altura, h0, h1, l0, l1)


def potencia_norma(volumen, ruido):
    if not (VOLUMENES[0] <= volumen <= VOLUMENES[-1]):
        raise ValueError(f"El volumen debe estar entre {VOLUMENES[0]} y {VOLUMENES[-1]} m³ para usar la tabla.")
    if not (RUIDOS[0] <= ruido <= RUIDOS[-1]):
        raise ValueError("El ruido debe estar entre 50 y 80 dB para usar la tabla.")
    p_por_ruido = {
        r: interp_1d(volumen, VOLUMENES, TABLA_2[r]) for r in RUIDOS
    }
    return interp_1d(ruido, RUIDOS, [p_por_ruido[r] for r in RUIDOS])


def distribuir(largo, ancho, n):
    """Distribuye altavoces en filas equilibradas y centradas.

    El número procede del criterio de superficie de la NTE-IAM.
    Esta función propone solo una geometría de implantación orientativa.
    """
    if n <= 0:
        return [], 0, 0, []

    # Elegir una retícula con celdas de aspecto próximo al cuadrado
    # y el menor número posible de huecos.
    mejor = None
    for filas in range(1, n + 1):
        cols = math.ceil(n / filas)
        aspecto = (largo / cols) / (ancho / filas)
        huecos = filas * cols - n
        coste = abs(math.log(aspecto)) + 0.12 * huecos
        if mejor is None or coste < mejor[0]:
            mejor = (coste, filas, cols)

    _, filas, cols = mejor
    base, resto = divmod(n, filas)
    puntos = []
    recuento_filas = []

    for f in range(filas):
        cantidad = base + (1 if f < resto else 0)
        recuento_filas.append(cantidad)
        y = (f + 0.5) * ancho / filas
        for c in range(cantidad):
            x = (c + 0.5) * largo / cantidad
            puntos.append((x, y))

    return puntos, filas, cols, recuento_filas



def dimensionamiento_angulo(largo, ancho, altura_techo, altura_oido, angulo_completo):
    """Predimensionado geométrico idealizado a partir del ángulo nominal."""
    altura_util = altura_techo - altura_oido
    if altura_util <= 0:
        raise ValueError("La altura del techo debe ser mayor que la altura de los oídos.")
    radio = altura_util * math.tan(math.radians(angulo_completo / 2))
    diametro = 2 * radio
    columnas = max(1, math.ceil(largo / diametro))
    filas = max(1, math.ceil(ancho / diametro))
    return {
        "altura_util": altura_util,
        "radio": radio,
        "diametro": diametro,
        "filas": filas,
        "columnas": columnas,
        "numero": filas * columnas,
    }


def distribuir_cobertura(largo, ancho, filas, columnas):
    """Centros de celdas geométricas de cobertura."""
    return [
        ((c + 0.5) * largo / columnas, (f + 0.5) * ancho / filas)
        for f in range(filas)
        for c in range(columnas)
    ]


def curva_polar_teorica(angulo_completo):
    """
    Curva teórica ilustrativa: 0 dB en eje, -6 dB en el semiancho
    nominal y caída progresiva fuera de él. No representa un fabricante.
    """
    semiancho = angulo_completo / 2
    angulos = np.array([0, semiancho * 0.5, semiancho,
                        min(90, semiancho + 15), 90], dtype=float)
    caidas = np.array([0, -1.5, -6, -10, -15], dtype=float)
    return angulos, caidas


def parsear_curva_polar(texto):
    """Lee pares ángulo,atenuación_dB; admite coma o punto decimal."""
    pares = []
    for linea in texto.strip().splitlines():
        linea = linea.strip()
        if not linea or linea.startswith("#"):
            continue
        partes = linea.replace(";", ",").split(",")
        if len(partes) != 2:
            raise ValueError(
                "Cada línea debe contener dos valores: ángulo, atenuación_dB."
            )
        try:
            ang, caida = [float(x.strip().replace(",", ".")) for x in partes]
        except ValueError as exc:
            raise ValueError("No se pudo interpretar una línea de la curva polar.") from exc
        if not 0 <= ang <= 90 or caida > 0 or caida < -60:
            raise ValueError(
                "Usa ángulos entre 0 y 90° y atenuaciones entre 0 y -60 dB."
            )
        pares.append((ang, caida))

    if len(pares) < 2:
        raise ValueError("Introduce al menos dos puntos de la curva polar.")
    pares.sort(key=lambda x: x[0])
    angulos = np.array([p[0] for p in pares], dtype=float)
    caidas = np.array([p[1] for p in pares], dtype=float)
    if len(np.unique(angulos)) != len(angulos):
        raise ValueError("No repitas ángulos en la curva polar.")
    if angulos[0] != 0:
        angulos = np.insert(angulos, 0, 0.0)
        caidas = np.insert(caidas, 0, 0.0)
    return angulos, caidas


def calcular_mapa_spl(largo, ancho, altura_techo, altura_oido,
                      puntos, sensibilidad, potencia, angulo_completo,
                      resolucion=0.25, polar_angulos=None, polar_caidas=None):
    """
    Mapa SPL de campo directo con suma energética de fuentes.
    La directividad se interpola desde una curva polar en un único plano.
    """
    xs = np.arange(0.25, max(0.26, largo), resolucion)
    ys = np.arange(0.25, max(0.26, ancho), resolucion)
    if len(xs) == 0:
        xs = np.array([largo / 2])
    if len(ys) == 0:
        ys = np.array([ancho / 2])

    xx, yy = np.meshgrid(xs, ys)
    altura_util = altura_techo - altura_oido
    if altura_util <= 0:
        raise ValueError("La altura del techo debe superar la altura de escucha.")

    if polar_angulos is None or polar_caidas is None:
        polar_angulos, polar_caidas = curva_polar_teorica(angulo_completo)

    suma_energia = np.zeros_like(xx, dtype=float)
    for sx, sy in puntos:
        horizontal = np.sqrt((xx - sx) ** 2 + (yy - sy) ** 2)
        distancia = np.sqrt(horizontal ** 2 + altura_util ** 2)
        distancia = np.maximum(distancia, 0.1)
        angulo_fuera_eje = np.degrees(np.arctan2(horizontal, altura_util))
        atenuacion = np.interp(
            angulo_fuera_eje, polar_angulos, polar_caidas,
            left=polar_caidas[0], right=polar_caidas[-1]
        )
        nivel = (
            sensibilidad + 10 * np.log10(potencia)
            - 20 * np.log10(distancia) + atenuacion
        )
        suma_energia += 10 ** (nivel / 10)

    spl = 10 * np.log10(np.maximum(suma_energia, 1e-12))
    return xx, yy, spl


def porcentaje_area_bajo_objetivo(mapa, objetivo):
    """Porcentaje de puntos del plano de escucha por debajo del SPL objetivo."""
    return float(np.mean(mapa < objetivo) * 100)


def escalar_potencia_mapa(largo, ancho, altura_techo, altura_oido,
                          puntos, sensibilidad, potencia_por_altavoz,
                          angulo_completo, polar_angulos, polar_caidas):
    """Calcula el mapa SPL con la curva polar seleccionada."""
    return calcular_mapa_spl(
        largo, ancho, altura_techo, altura_oido, puntos,
        sensibilidad, potencia_por_altavoz, angulo_completo,
        polar_angulos=polar_angulos, polar_caidas=polar_caidas
    )

def dibujar_mapa_spl(xx, yy, spl, puntos, largo, ancho,
                     vmin=None, vmax=None, titulo="Mapa SPL estimado",
                     objetivo=None, limite_superior=None):
    """Mapa de SPL con escala común para permitir comparaciones visuales."""
    fig, ax = plt.subplots(figsize=(8, 5.2))
    if vmin is None:
        vmin = float(np.floor(np.nanmin(spl) / 5) * 5)
    if vmax is None:
        vmax = float(np.ceil(np.nanmax(spl) / 5) * 5)
    if vmax <= vmin:
        vmax = vmin + 5

    niveles = np.linspace(vmin, vmax, 18)
    m = ax.contourf(
        xx, yy, spl, levels=niveles, cmap="RdYlGn",
        vmin=vmin, vmax=vmax, extend="both"
    )
    fig.colorbar(m, ax=ax, label="Nivel estimado (dB SPL)")
    if objetivo is not None and np.nanmin(spl) <= objetivo <= np.nanmax(spl):
        ax.contour(xx, yy, spl, levels=[objetivo], colors="black",
                   linewidths=1.2, linestyles="--")
    if limite_superior is not None and np.nanmin(spl) <= limite_superior <= np.nanmax(spl):
        ax.contour(xx, yy, spl, levels=[limite_superior], colors="white",
                   linewidths=1.2, linestyles=":")
    ax.add_patch(Rectangle((0, 0), largo, ancho, fill=False,
                           linewidth=2, edgecolor="#263238"))
    if puntos:
        px, py = zip(*puntos)
        ax.scatter(px, py, marker="^", s=75, c="black",
                   edgecolors="white", linewidths=0.8, label="Altavoces")
        ax.legend(loc="upper right", fontsize=8)
    ax.set_xlim(0, largo)
    ax.set_ylim(0, ancho)
    ax.set_aspect("equal", adjustable="box")
    ax.set_xlabel("Longitud (m)")
    ax.set_ylabel("Anchura (m)")
    ax.set_title(titulo, fontsize=11)
    fig.tight_layout()
    return fig


def dibujar_plano(recinto, mostrar_celdas=True, mostrar_cotas=True):
    """
    Plano esquemático a escala.
    Las celdas representan una distribución geométrica orientativa,
    no una huella acústica certificada de cada altavoz.
    """
    largo = recinto["Largo (m)"]
    ancho = recinto["Ancho (m)"]
    n = recinto["Altavoces"]
    puntos, filas, cols, recuento_filas = distribuir(largo, ancho, n)

    fig, ax = plt.subplots(figsize=(11, 6.5))
    ax.add_patch(Rectangle((0, 0), largo, ancho, fill=False,
                           linewidth=2.2, edgecolor="#263238"))

    dy = ancho / filas

    # Cada banda contiene el mismo número, o casi el mismo, de altavoces.
    if mostrar_celdas:
        for f, cantidad in enumerate(recuento_filas):
            dx_fila = largo / cantidad
            for c in range(cantidad):
                ax.add_patch(Rectangle(
                    (c * dx_fila, f * dy), dx_fila, dy,
                    facecolor="#90caf9", alpha=0.13,
                    edgecolor="#78909c", linewidth=0.8,
                    linestyle="--"
                ))

    # Altavoces numerados con símbolo reconocible.
    for i, (x, y) in enumerate(puntos, 1):
        ax.scatter(x, y, s=310, marker="o", color="#1565c0",
                   edgecolors="white", linewidths=1.5, zorder=5)
        ax.text(x, y, str(i), ha="center", va="center",
                fontsize=8, color="white", weight="bold", zorder=6)

    # Cotas generales y dimensiones de las celdas.
    if mostrar_cotas:
        ax.annotate("", xy=(0, -0.55), xytext=(largo, -0.55),
                    arrowprops=dict(arrowstyle="<->", color="#37474f"))
        ax.text(largo / 2, -0.82, f"{largo:.2f} m",
                ha="center", va="top", fontsize=9)
        ax.annotate("", xy=(-0.55, 0), xytext=(-0.55, ancho),
                    arrowprops=dict(arrowstyle="<->", color="#37474f"))
        ax.text(-0.82, ancho / 2, f"{ancho:.2f} m",
                ha="right", va="center", rotation=90, fontsize=9)

    ax.set_xlim(-1.15, largo + 0.35)
    ax.set_ylim(-1.15, ancho + 0.35)
    ax.set_aspect("equal", adjustable="box")
    ax.set_xlabel("Longitud (m)")
    ax.set_ylabel("Anchura (m)")
    ax.set_title(
        f"Planta del recinto · {n} altavoces · distribución {filas} × {cols}",
        pad=14, weight="bold"
    )
    ax.grid(True, alpha=0.15)
    fig.tight_layout()
    return fig, puntos, filas, cols, recuento_filas, largo / max(recuento_filas), dy


if "recintos" not in st.session_state:
    st.session_state.recintos = []

st.title("🔊 Diseño de instalaciones de megafonía")
st.caption("Herramienta didáctica basada en NTE-IAM/1977 · Cálculo preliminar por recintos")

with st.sidebar:
    st.header("Nuevo recinto")
    nombre = st.text_input("Nombre", "Aula 1", key="nombre_recinto")
    c1, c2 = st.columns(2)
    largo = c1.number_input("Largo (m)", min_value=1.0, max_value=100.0, value=10.0, step=0.5)
    ancho = c2.number_input("Ancho (m)", min_value=1.0, max_value=100.0, value=8.0, step=0.5)
    altura = st.selectbox("Altura (m)", [2.5, 3.0, 3.5, 4.0], index=1)
    nivel_txt = st.selectbox("Nivel de calidad", ["I · Básico", "II · Medio", "III · Alto"], index=1)
    nivel = {"I · Básico": 1, "II · Medio": 2, "III · Alto": 3}[nivel_txt]
    ruido = st.select_slider("Ruido ambiente (dB)", options=[50, 65, 80], value=65)
    tension = st.selectbox("Tensión de línea", [50, 70, 100], index=2)
    agregar = st.button("➕ Calcular y añadir recinto", type="primary", width="stretch")
    if agregar:
        superficie = largo * ancho
        volumen = superficie * altura
        s_alt, separacion = superficie_por_altavoz(altura, nivel)
        n = math.ceil(superficie / s_alt)
        p_total = potencia_norma(volumen, ruido)
        p_alt = p_total / n
        z_alt = tension ** 2 / p_alt if p_alt > 0 else float("inf")
        st.session_state.recintos.append({
            "Recinto": nombre, "Largo (m)": largo, "Ancho (m)": ancho,
            "Altura (m)": altura, "Nivel": nivel_txt, "Ruido (dB)": ruido,
            "Superficie (m²)": superficie, "Volumen (m³)": volumen,
            "Superficie/altavoz (m²)": s_alt, "Separación L (m)": separacion,
            "Altavoces": n, "Potencia total (W)": p_total,
            "Potencia/altavoz (W)": p_alt, "Tensión (V)": tension,
            "Z equivalente por altavoz (Ω)": z_alt,
        })

if st.session_state.recintos:
    resumen = pd.DataFrame(st.session_state.recintos)
    total_alt = int(resumen["Altavoces"].sum())
    total_w = float(resumen["Potencia total (W)"].sum())
    k1, k2, k3 = st.columns(3)
    k1.metric("Recintos", len(resumen))
    k2.metric("Altavoces calculados", total_alt)
    k3.metric("Potencia total según tabla", f"{total_w:.2f} W")

    tab1, tab2, tab3, tab4 = st.tabs([
        "📋 Resultados", "📐 Plano", "⚡ Línea y amplificación", "🔉 SPL y cobertura"
    ])
    with tab1:
        st.subheader("Resumen de recintos")
        st.dataframe(resumen[["Recinto", "Superficie (m²)", "Volumen (m³)", "Nivel", "Ruido (dB)", "Altavoces", "Potencia total (W)"]], width="stretch", hide_index=True)
        st.subheader("Detalle de cálculo")
        elegido = st.selectbox("Selecciona un recinto", resumen["Recinto"].tolist())
        r = next(x for x in st.session_state.recintos if x["Recinto"] == elegido)
        a, b, c = st.columns(3)
        a.metric("Superficie por altavoz", f"{r['Superficie/altavoz (m²)']:.2f} m²")
        b.metric("Separación máxima L", f"{r['Separación L (m)']:.2f} m")
        c.metric("Potencia por altavoz", f"{r['Potencia/altavoz (W)']:.3f} W")
        st.latex(r"n=\left\lceil\frac{S_L}{S}\right\rceil")
        st.write(f"{r['Superficie (m²)']:.2f} / {r['Superficie/altavoz (m²)']:.2f} = {r['Altavoces']} altavoces (redondeo al entero superior).")
        st.write(f"Potencia total estimada por tabla: **{r['Potencia total (W)']:.3f} W**. Potencia media por altavoz: **{r['Potencia/altavoz (W)']:.3f} W**.")
        with st.expander("📘 Interpretación didáctica del cálculo"):
            st.markdown(
                f"""
                **Paso 1. Superficie del recinto**

                \\[S_L = largo \\times ancho = {r['Largo (m)']:.2f} \\times {r['Ancho (m)']:.2f}
                = {r['Superficie (m²)']:.2f}\\;m^2\\]

                **Paso 2. Selección de la superficie asignada a cada altavoz**

                Para una altura de **{r['Altura (m)']} m** y nivel **{r['Nivel']}**,
                la tabla 1 da **{r['Superficie/altavoz (m²)']:.2f} m²** por altavoz.

                **Paso 3. Número de altavoces**

                \\[n = \\left\\lceil \\frac{{{r['Superficie (m²)']:.2f}}}
                {{{r['Superficie/altavoz (m²)']:.2f}}} \\right\\rceil
                = {r['Altavoces']}\\]

                **Paso 4. Potencia**

                La tabla 2 estima **{r['Potencia total (W)']:.3f} W** para
                un volumen de **{r['Volumen (m³)']:.2f} m³** y un ruido de
                **{r['Ruido (dB)']} dB**. La división entre altavoces es un
                reparto medio de esa potencia, no una selección automática
                de la toma comercial del transformador.
                """
            )
    with tab2:
        st.subheader("Plano de distribución de altavoces")
        elegido_plano = st.selectbox(
            "Recinto a representar", resumen["Recinto"].tolist(),
            key="plano_recinto"
        )
        r_plano = next(x for x in st.session_state.recintos
                       if x["Recinto"] == elegido_plano)

        op1, op2 = st.columns(2)
        mostrar_celdas = op1.checkbox("Mostrar retícula de reparto", value=True)
        mostrar_cotas = op2.checkbox("Mostrar cotas del recinto", value=True)

        fig, puntos, filas, cols, recuento_filas, dx, dy = dibujar_plano(
            r_plano, mostrar_celdas, mostrar_cotas
        )
        st.pyplot(fig, width="stretch")

        m1, m2, m3 = st.columns(3)
        m1.metric("Filas", filas)
        m2.metric("Altavoces por fila", " – ".join(map(str, recuento_filas)))
        m3.metric("Altavoces dibujados", len(puntos))

        st.markdown("#### ¿Cómo se ha colocado cada altavoz?")
        st.markdown(
            f"""
            1. Se calcula la superficie del recinto:  
               **{r_plano['Largo (m)']:.2f} × {r_plano['Ancho (m)']:.2f} = "
               f"{r_plano['Superficie (m²)']:.2f} m²**.
            2. La tabla 1 proporciona **{r_plano['Superficie/altavoz (m²)']:.2f} m²**
               por altavoz para la altura y el nivel seleccionados.
            3. El número necesario resulta de dividir la superficie total entre
               la superficie asignada a cada altavoz y redondear al entero superior:
               **{r_plano['Altavoces']} altavoces**.
            4. Para dibujarlos, el programa busca una retícula aproximadamente
               equilibrada y sitúa cada altavoz en el centro de su celda.
            """
        )
        st.markdown(
            f"Las filas contienen **{" – ".join(map(str, recuento_filas))} altavoces**, centrados en cada banda. "
            "La retícula es una propuesta geométrica de reparto, no una "
            "representación del área real de cobertura acústica."
        )
        st.info(
            "Importante: la NTE-IAM establece criterios de superficie y separación "
            "máxima. Este plano es didáctico y orientativo; hay que adaptar la "
            "posición a puertas, luminarias, vigas, mobiliario, zonas de escucha "
            "y características reales de los altavoces."
        )
    with tab3:
        st.subheader("Estimación de línea de 100/70/50 V")
        st.dataframe(resumen[["Recinto", "Tensión (V)", "Altavoces", "Potencia total (W)", "Potencia/altavoz (W)", "Z equivalente por altavoz (Ω)"]], width="stretch", hide_index=True)
        st.metric("Potencia total conectada (suma de recintos)", f"{total_w:.2f} W")
        reserva = st.slider("Reserva de diseño del amplificador (no es un coeficiente NTE)", 0, 50, 20, 5)
        st.metric("Potencia orientativa de amplificador", f"{total_w * (1 + reserva / 100):.2f} W")
        st.warning("La impedancia mostrada es un cálculo equivalente V²/P para la potencia media asignada a cada altavoz; no selecciona automáticamente el transformador comercial ni sustituye la comprobación de tomas, carga total, pérdidas y secciones de cable.")

    with tab4:
        st.subheader("Dimensionamiento geométrico y estimación SPL")
        elegido_spl = st.selectbox(
            "Recinto para el análisis acústico", resumen["Recinto"].tolist(),
            key="spl_recinto"
        )
        r_spl = next(x for x in st.session_state.recintos if x["Recinto"] == elegido_spl)

        st.markdown("#### Características del altavoz de techo")
        c1, c2, c3, c4 = st.columns(4)
        sensibilidad = c1.number_input(
            "Sensibilidad (dB SPL, 1 W/1 m)", min_value=70.0, max_value=110.0,
            value=90.0, step=1.0, key="spl_sensibilidad"
        )
        angulo = c2.selectbox(
            "Ángulo completo nominal", [90, 100, 110, 120, 130, 140, 150],
            index=3, key="spl_angulo"
        )
        potencia_altavoz = c3.selectbox(
            "Toma del transformador", [1.5, 3.0, 6.0, 10.0, 15.0, 20.0],
            index=2, key="spl_potencia"
        )
        altura_oido = c4.selectbox(
            "Altura de los oídos (m)", [1.2, 1.4, 1.6],
            index=0, key="spl_altura_oido"
        )

        st.markdown("#### Directividad del altavoz")
        modelo_directividad = st.radio(
            "Origen de la curva polar",
            ["Curva teórica didáctica", "Curva de fabricante"],
            horizontal=True, key="spl_modelo_directividad"
        )
        texto_polar = """# Ángulo (grados), atenuación respecto al eje (dB)
0, 0
15, -1
30, -2
45, -3
60, -6
75, -10
90, -15"""
        if modelo_directividad == "Curva teórica didáctica":
            polar_angulos, polar_caidas = curva_polar_teorica(angulo)
            st.caption(
                "Se usa una curva teórica suave: no corresponde a ningún modelo "
                "comercial. El ángulo nominal se interpreta como el punto de -6 dB."
            )
        else:
            texto_polar_usuario = st.text_area(
                "Curva polar del fabricante (ángulo, atenuación dB)",
                value=texto_polar, height=155, key="spl_curva_fabricante",
                help="Introduce pares separados por coma o punto y coma. "
                     "Ejemplo: 0,0 / 30,-2 / 60,-6 / 90,-15. "
                     "Usa datos del fabricante para la frecuencia o banda elegida."
            )
            try:
                polar_angulos, polar_caidas = parsear_curva_polar(texto_polar_usuario)
                st.success(f"Curva polar cargada: {len(polar_angulos)} puntos.")
            except ValueError as exc:
                st.error(str(exc))
                st.stop()

        st.markdown("#### Objetivo acústico y criterio de comparación")
        obj_col1, obj_col2 = st.columns(2)
        tipo_objetivo = obj_col1.radio(
            "Referencia de SPL",
            ["Referencia didáctica 65–70 dB", "Objetivo personalizado"],
            key="spl_tipo_objetivo"
        )
        if tipo_objetivo == "Referencia didáctica 65–70 dB":
            spl_objetivo = 65.0
            spl_superior = 70.0
            obj_col2.info("Banda orientativa: 65–70 dB SPL")
        else:
            spl_objetivo = obj_col2.number_input(
                "SPL mínimo deseado (dB)", min_value=40.0, max_value=100.0,
                value=65.0, step=1.0, key="spl_objetivo_personalizado"
            )
            spl_superior = None

        modo_potencia = st.radio(
            "Comparación de potencia",
            ["Misma toma por altavoz", "Igual potencia total en ambos métodos"],
            horizontal=True, key="spl_modo_potencia"
        )

        largo_s = r_spl["Largo (m)"]
        ancho_s = r_spl["Ancho (m)"]
        altura_s = r_spl["Altura (m)"]
        superficie_s = r_spl["Superficie (m²)"]

        try:
            geom = dimensionamiento_angulo(
                largo_s, ancho_s, altura_s, altura_oido, angulo
            )
        except ValueError as exc:
            st.error(str(exc))
        else:
            n_nte = int(r_spl["Altavoces"])
            n_ang = geom["numero"]
            puntos_nte, filas_nte, cols_nte, _ = distribuir(largo_s, ancho_s, n_nte)
            puntos_ang = distribuir_cobertura(
                largo_s, ancho_s, geom["filas"], geom["columnas"]
            )

            st.markdown("#### Comparación de dimensionamiento")
            ca, cb, cc = st.columns(3)
            ca.metric("NTE-IAM · altavoces", n_nte)
            cb.metric("Geometría angular · altavoces", n_ang,
                      delta=f"{n_ang - n_nte:+d} frente a NTE-IAM")
            cc.metric("Diámetro geométrico", f"{geom['diametro']:.2f} m")

            st.write(
                f"Altura entre el altavoz y el plano de escucha: "
                f"**{geom['altura_util']:.2f} m**. El ángulo de {angulo}° "
                f"produce un diámetro geométrico idealizado de "
                f"**{geom['diametro']:.2f} m** en el plano de los oídos."
            )
            st.latex(
                r"D=2(H-h_o)\tan\left(\frac{\theta}{2}\right)"
            )
            st.write(
                f"Se requieren {geom['columnas']} columnas × {geom['filas']} filas "
                f"en este predimensionado geométrico: **{n_ang} altavoces**."
            )

            # Comparar ambos escenarios: misma toma por altavoz o mismo presupuesto total.
            potencia_nte_altavoz = potencia_altavoz
            potencia_ang_altavoz = potencia_altavoz
            if modo_potencia == "Igual potencia total en ambos métodos":
                presupuesto_total = n_nte * potencia_altavoz
                potencia_ang_altavoz = presupuesto_total / n_ang

            xx_nte, yy_nte, mapa_nte = escalar_potencia_mapa(
                largo_s, ancho_s, altura_s, altura_oido, puntos_nte,
                sensibilidad, potencia_nte_altavoz, angulo,
                polar_angulos, polar_caidas
            )
            xx_ang, yy_ang, mapa_ang = escalar_potencia_mapa(
                largo_s, ancho_s, altura_s, altura_oido, puntos_ang,
                sensibilidad, potencia_ang_altavoz, angulo,
                polar_angulos, polar_caidas
            )

            # Misma escala cromática en ambos mapas: evita comparaciones engañosas.
            escala_min = float(np.floor(min(mapa_nte.min(), mapa_ang.min()) / 5) * 5)
            escala_max = float(np.ceil(max(mapa_nte.max(), mapa_ang.max()) / 5) * 5)
            if escala_max <= escala_min:
                escala_max = escala_min + 5

            st.markdown("#### Comparación visual de cobertura SPL")
            st.caption(
                "Ambos mapas utilizan la misma escala de colores y los mismos "
                "parámetros acústicos. Así, un mismo color representa el mismo SPL."
            )
            mapa_col1, mapa_col2 = st.columns(2)
            with mapa_col1:
                st.markdown(f"**NTE-IAM · {len(puntos_nte)} altavoces**")
                st.pyplot(
                    dibujar_mapa_spl(
                        xx_nte, yy_nte, mapa_nte, puntos_nte,
                        largo_s, ancho_s, escala_min, escala_max,
                        "Distribución según NTE-IAM",
                        objetivo=spl_objetivo, limite_superior=spl_superior
                    ),
                    width="stretch"
                )
            with mapa_col2:
                st.markdown(f"**Ángulo de cobertura · {len(puntos_ang)} altavoces**")
                st.pyplot(
                    dibujar_mapa_spl(
                        xx_ang, yy_ang, mapa_ang, puntos_ang,
                        largo_s, ancho_s, escala_min, escala_max,
                        "Distribución geométrica por ángulo",
                        objetivo=spl_objetivo, limite_superior=spl_superior
                    ),
                    width="stretch"
                )

            def resumen_spl(mapa, puntos, potencia_individual):
                centro_i = np.unravel_index(
                    np.argmin((xx_nte - largo_s / 2) ** 2 +
                              (yy_nte - ancho_s / 2) ** 2),
                    xx_nte.shape
                )
                return {
                    "mínimo": float(np.min(mapa)),
                    "máximo": float(np.max(mapa)),
                    "medio": float(10 * np.log10(np.mean(10 ** (mapa / 10)))),
                    "centro": float(mapa[centro_i]),
                    "rango": float(np.max(mapa) - np.min(mapa)),
                    "potencia": len(puntos) * potencia_individual,
                    "potencia_individual": potencia_individual,
                    "area_baja_objetivo": porcentaje_area_bajo_objetivo(mapa, spl_objetivo),
                }

            stats_nte = resumen_spl(mapa_nte, puntos_nte, potencia_nte_altavoz)
            stats_ang = resumen_spl(mapa_ang, puntos_ang, potencia_ang_altavoz)

            st.markdown("#### Comparación numérica")
            tabla_comp = pd.DataFrame([
                {
                    "Indicador": "Número de altavoces",
                    "NTE-IAM": n_nte,
                    "Método angular": n_ang,
                },
                {
                    "Indicador": "SPL mínimo (dB)",
                    "NTE-IAM": round(stats_nte["mínimo"], 1),
                    "Método angular": round(stats_ang["mínimo"], 1),
                },
                {
                    "Indicador": "SPL máximo (dB)",
                    "NTE-IAM": round(stats_nte["máximo"], 1),
                    "Método angular": round(stats_ang["máximo"], 1),
                },
                {
                    "Indicador": "SPL medio energético (dB)",
                    "NTE-IAM": round(stats_nte["medio"], 1),
                    "Método angular": round(stats_ang["medio"], 1),
                },
                {
                    "Indicador": "SPL en el centro (dB)",
                    "NTE-IAM": round(stats_nte["centro"], 1),
                    "Método angular": round(stats_ang["centro"], 1),
                },
                {
                    "Indicador": "Variación máximo–mínimo (dB)",
                    "NTE-IAM": round(stats_nte["rango"], 1),
                    "Método angular": round(stats_ang["rango"], 1),
                },
                {
                    "Indicador": "Potencia por altavoz (W)",
                    "NTE-IAM": round(stats_nte["potencia_individual"], 2),
                    "Método angular": round(stats_ang["potencia_individual"], 2),
                },
                {
                    "Indicador": "Potencia conectada (W)",
                    "NTE-IAM": round(stats_nte["potencia"], 1),
                    "Método angular": round(stats_ang["potencia"], 1),
                },
                {
                    "Indicador": f"Área por debajo de {spl_objetivo:.0f} dB (%)",
                    "NTE-IAM": round(stats_nte["area_baja_objetivo"], 1),
                    "Método angular": round(stats_ang["area_baja_objetivo"], 1),
                },
            ])
            st.dataframe(tabla_comp, width="stretch", hide_index=True)

            st.markdown("#### Interpretación")
            st.write(
                f"Potencia por altavoz: **{stats_nte['potencia_individual']:.2f} W** "
                f"en NTE-IAM y **{stats_ang['potencia_individual']:.2f} W** "
                f"en el método angular. Potencia total: **{stats_nte['potencia']:.1f} W** "
                f"y **{stats_ang['potencia']:.1f} W**, respectivamente."
            )
            if spl_superior is not None:
                st.caption(
                    f"Referencia didáctica seleccionada: banda de {spl_objetivo:.0f}–"
                    f"{spl_superior:.0f} dB SPL. La tabla indica el porcentaje de "
                    f"superficie por debajo del límite inferior. La línea discontinua "
                    f"marca {spl_objetivo:.0f} dB y la punteada {spl_superior:.0f} dB."
                )
            else:
                st.caption(
                    f"Objetivo personalizado: {spl_objetivo:.1f} dB SPL. "
                    "La tabla indica qué porcentaje de puntos queda por debajo "
                    "de ese objetivo; la línea discontinua lo señala en el mapa."
                )
            st.info(
                "Los mapas son estimaciones didácticas de campo directo. La suma "
                "energética no incorpora reverberación, absorción, obstáculos, "
                "fase ni la respuesta polar real del altavoz. El ángulo nominal "
                "no es un límite físico abrupto: la penalización fuera del ángulo "
                "se representa mediante la curva polar seleccionada. La curva teórica "
                "es solo didáctica; la curva de fabricante debe corresponder a la "
                "frecuencia/banda y al plano de medición adecuados. El modelo aún no "
                "incluye reverberación, respuesta en frecuencia ni fase, y no sustituye "
                "mediciones o simulación acústica."
            )

            with st.expander("📘 Interpretación didáctica"):
                st.markdown(
                    f"""
                    - **NTE-IAM:** {n_nte} altavoces, calculados mediante la tabla
                      de superficie por altavoz según altura y nivel de calidad.
                    - **Método angular:** {n_ang} altavoces, calculados a partir de
                      la proyección geométrica del ángulo nominal sobre el plano de escucha.
                    - **Directividad:** {modelo_directividad}; la atenuación fuera del eje
                      se interpola desde una curva polar, no mediante un salto fijo de 6 dB.
                    - **Comparación SPL:** ambos mapas usan idéntica escala cromática.
                    - **Objetivo:** se puede usar la referencia didáctica 65–70 dB
                      o introducir un SPL mínimo personalizado.
                    - **Potencia:** comparación con la misma toma por altavoz o con
                      igual presupuesto total entre los dos métodos.
                    """
                )

    csv = resumen.to_csv(index=False).encode("utf-8-sig")
    st.download_button("⬇️ Descargar resultados CSV", csv, "calculo_megafonia_nte_iam.csv", "text/csv")
    if st.button("🗑️ Borrar todos los recintos"):
        st.session_state.recintos = []
        st.rerun()
else:
    st.info("Introduce los datos de un recinto en el panel izquierdo y pulsa **Calcular y añadir recinto**.")
    st.markdown("**Ámbito de la NTE-IAM:** megafonía de uso general con amplificación centralizada y distribución en alta impedancia, en locales de altura no superior a 4 m y superficies no reflectantes.")

with st.expander("Norma y límites de esta versión"):
    st.markdown("""
    - La tabla 1 relaciona altura y nivel de calidad con la superficie cubierta por altavoz y la separación máxima.
    - La tabla 2 estima la potencia eléctrica total en función del volumen y del ruido ambiente.
    - Para alturas intermedias se interpola linealmente entre las filas tabuladas. Para volumen y ruido se realiza interpolación lineal entre valores de la tabla.
    - Esta versión no calcula todavía secciones de conductores, canalizaciones, pérdidas de línea, distribución de circuitos según todas las tablas ni simultaneidad de programas.
    - El módulo SPL y el método angular son estimaciones didácticas complementarias, no fórmulas de cumplimiento de la NTE-IAM.
    - El modelo SPL usa campo directo simplificado; no sustituye simulación acústica ni mediciones in situ.
    - Es una herramienta de aprendizaje y predimensionado, no un proyecto de ejecución ni una declaración de cumplimiento normativo actual.
    """)
    st.markdown("Fuente oficial: [NTE-IAM/1977 · BOE, 13 de agosto de 1977](https://www.boe.es/boe/dias/1977/08/13/pdfs/A18145-18149.pdf) y [conclusión · BOE, 20 de agosto de 1977](https://www.boe.es/boe/dias/1977/08/20/pdfs/R18145-18647.pdf).")
