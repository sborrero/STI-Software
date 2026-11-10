import numpy as np
import matplotlib.pyplot as plt
from matplotlib.widgets import Button, RadioButtons, Slider, CheckButtons
from scipy.signal import butter, sosfiltfilt

# ============================================================
# SEQUENTIAL ADC / DAC EDUCATIONAL SIMULATOR
#
# Autor: Santiago Borrero Ortiz
# Copyright (c) 2026 Santiago Borrero Ortiz
#
# Código fuente: MIT License (ver archivo LICENSE).
# Documentación y materiales didácticos: CC BY 4.0
# (ver archivo LICENSE-DOCUMENTACION).
#
# Requisitos: pip install numpy matplotlib scipy
# Ejecución:  python simulador_adc_dac_v18.py
# ============================================================

DURACION = 0.004       # 4 ms de señal representada
FS_GRAFICA = 200000    # Resolution interna para dibujar señales suaves

frecuencia = 2000.0
fs = 8000.0
bits = 8
modo = "ADC"
etapa = 0
indice_completo = 0
forzar_aliasing = True
numero_muestras_visibles = 1
muestreo_automatico = False

ETAPAS_ADC = [
    "1. Analog signal",
    "2. Anti-aliasing filter",
    "3. Sampling",
    "4. Quantization",
    "5. Binary encoding",
]

ETAPAS_DAC = [
    "1. Digital signal",
    "2. Decoding",
    "3. D/A conversion",
    "4. ZOH hold",
    "5. Reconstruction filter",
]


# ------------------------- Procesamiento -------------------------

def cuantificar(x, nbits):
    """Cuantificador uniforme de -1 a +1."""
    numero_niveles = 2 ** nbits
    codigos = np.rint(
        (np.clip(x, -1, 1) + 1) * (numero_niveles - 1) / 2
    ).astype(int)
    niveles = 2 * codigos / (numero_niveles - 1) - 1
    return codigos, niveles


def obtener_datos():
    t = np.arange(0, DURACION, 1 / FS_GRAFICA)
    original = np.sin(2 * np.pi * frecuencia * t)

    # FILTRO ANTIALIASING:
    # Corte al 85 % de Nyquist para dejar una banda de transición.
    # A 44,1 kHz deja pasar 7 kHz prácticamente sin atenuación.
    # A 8 kHz atenúa 7 kHz, porque supera Nyquist (4 kHz).
    nyquist = fs / 2
    corte_anti = 0.85 * nyquist
    sos_anti = butter(
        6, corte_anti,
        btype="lowpass",
        fs=FS_GRAFICA,
        output="sos"
    )
    filtrada = sosfiltfilt(sos_anti, original)

    # La casilla permite saltarse el filtro para demostrar el aliasing.
    entrada_muestreador = original if forzar_aliasing else filtrada

    # MUESTREO
    ts = np.arange(0, DURACION, 1 / fs)
    muestras = np.interp(ts, t, entrada_muestreador)

    # CUANTIFICACIÓN
    codigos, niveles = cuantificar(muestras, bits)

    # RETENCIÓN DE ORDEN CERO (ZOH)
    indices = np.minimum((t * fs).astype(int), len(niveles) - 1)
    zoh = niveles[indices]

    # INTERPOLACIÓN LINEAL
    lineal = np.interp(t, ts, niveles)

    # FILTRO RECONSTRUCTOR
    corte_dac = min(0.40 * fs, 0.45 * FS_GRAFICA)
    sos_dac = butter(
        6, corte_dac,
        btype="lowpass",
        fs=FS_GRAFICA,
        output="sos"
    )
    reconstruida = sosfiltfilt(sos_dac, zoh)

    # Frecuencia aparente de una senoide muestreada sin filtro antialiasing.
    alias = abs(((frecuencia + fs / 2) % fs) - fs / 2)

    return {
        "t": t,
        "original": original,
        "filtrada": filtrada,
        "entrada": entrada_muestreador,
        "ts": ts,
        "muestras": muestras,
        "codigos": codigos,
        "niveles": niveles,
        "zoh": zoh,
        "lineal": lineal,
        "reconstruida": reconstruida,
        "corte_anti": corte_anti,
        "alias": alias,
    }


# ------------------------- Interfaz -------------------------

plt.close("all")
fig = plt.figure(figsize=(14, 8.5))
try:
    fig.canvas.manager.set_window_title("ADC / DAC Simulator")
except Exception:
    pass

ax_esquema = fig.add_axes([0.04, 0.82, 0.92, 0.11])

# En el paso de muestreo se muestran dos gráficas:
# izquierda = señal y muestras; derecha = solo las samples.
ax_plot = fig.add_axes([0.10, 0.31, 0.82, 0.43])
ax_solo_muestras = fig.add_axes([0.68, 0.31, 0.25, 0.43])
ax_solo_muestras.set_visible(False)
ax_error_completo = fig.add_axes([0.08, 0.225, 0.84, 0.11])
ax_error_completo.set_visible(False)

ax_info = fig.add_axes([0.07, 0.19, 0.86, 0.075])
ax_info.axis("off")

ax_modo = fig.add_axes([0.04, 0.72, 0.20, 0.105])
radio_modo = RadioButtons(ax_modo, ("ADC", "DAC", "Complete"))
ax_modo.set_title("Workflow", fontsize=9)

ax_fs = fig.add_axes([0.25, 0.13, 0.28, 0.025])
slider_fs = Slider(
    ax_fs, "Fs (Hz)", 4000, 48000,
    valinit=8000, valstep=1000
)

ax_f = fig.add_axes([0.25, 0.08, 0.28, 0.025])
slider_f = Slider(
    ax_f, "Frequency (Hz)", 500, 20000,
    valinit=2000, valstep=500
)

ax_bits = fig.add_axes([0.65, 0.10, 0.14, 0.11])
radio_bits = RadioButtons(ax_bits, ("4 bits", "8 bits", "12 bits"), active=1)
ax_bits.set_title("Resolution")

ax_alias = fig.add_axes([0.82, 0.10, 0.16, 0.11])
check_alias = CheckButtons(ax_alias, ["Bypass filter\n(aliasing demo)"], [True])

ax_prev = fig.add_axes([0.34, 0.015, 0.13, 0.045])
ax_next = fig.add_axes([0.51, 0.015, 0.13, 0.045])
btn_prev = Button(ax_prev, "Previous")
btn_next = Button(ax_next, "Next")

ax_muestra = fig.add_axes([0.68, 0.015, 0.13, 0.045])
ax_reiniciar_muestras = fig.add_axes([0.83, 0.015, 0.13, 0.045])
btn_muestra = Button(ax_muestra, "Sample +")
btn_reiniciar_muestras = Button(ax_reiniciar_muestras, "Reset")

ax_auto = fig.add_axes([0.68, 0.075, 0.28, 0.045])
btn_auto = Button(ax_auto, "Start automatic")

titulo_general = fig.text(
    0.5, 0.965, "", ha="center",
    fontsize=16, fontweight="bold"
)
paso_texto = fig.text(0.5, 0.935, "", ha="center", fontsize=11)


def dibujar_esquema():
    ax_esquema.clear()
    ax_esquema.axis("off")
    if modo == "Complete":
        nombres = [
            "Signal", "Sampling", "Quantization", "Encoding",
            "Channel", "Decoding", "DAC / filter"
        ]
        xs = np.linspace(0.045, 0.955, len(nombres))
        activo = indice_completo
    else:
        nombres = ETAPAS_ADC if modo == "ADC" else ETAPAS_DAC
        xs = np.linspace(0.10, 0.90, len(nombres))
        activo = etapa

    for i, (x, nombre) in enumerate(zip(xs, nombres)):
        color = "#bce5ca" if i == activo else "#e9edf2"
        ax_esquema.text(
            x, 0.52, nombre.replace(" / ", "\\n/ "),
            ha="center", va="center", fontsize=7.5 if modo == "Complete" else 9,
            bbox=dict(
                boxstyle="round,pad=0.42",
                fc=color,
                ec="#238b57" if i == activo else "#89939e",
                lw=2 if i == activo else 1
            ),
            transform=ax_esquema.transAxes
        )
        if i < len(xs) - 1:
            ax_esquema.annotate(
                "",
                xy=(xs[i + 1] - 0.055, 0.52),
                xytext=(x + 0.055, 0.52),
                xycoords=ax_esquema.transAxes,
                arrowprops=dict(arrowstyle="->", lw=1.3)
            )


def preparar_eje(ax, titulo, ylabel):
    ax.set_title(titulo, fontsize=11)
    ax.set_xlabel("Time (ms)")
    ax.set_ylabel(ylabel)
    ax.grid(True, alpha=0.3)
    ax.set_xlim(0, DURACION * 1000)



def dibujar_completo(d):
    """Presenta progresivamente la cadena completa emisor-canal-receptor."""
    fase = indice_completo
    tms = d["t"] * 1000
    tsms = d["ts"] * 1000
    codigos = d["codigos"]
    niveles = d["niveles"]
    muestras = d["muestras"]
    total = len(codigos)

    ax_error_completo.set_visible(fase == 2)
    ax_info.set_visible(fase != 2)
    ax_plot.set_position([0.07, 0.32, 0.55, 0.43])
    ax_solo_muestras.set_position([0.68, 0.32, 0.28, 0.43])
    ax_solo_muestras.set_visible(True)
    ax_plot.clear()
    ax_solo_muestras.clear()

    # Zona del emisor. En cuantificación se usa una gráfica independiente
    # de códigos digitales, sin senoide ni leyenda de voltaje.
    if fase == 2:
        ax_plot.set_position([0.08, 0.39, 0.84, 0.36])
        ax_solo_muestras.set_visible(False)
        indices = np.arange(1, total + 1)
        ax_plot.clear()
        ax_plot.set_title("3. QUANTIZATION: assigned digital code",
                          fontsize=11)
        numero_niveles = 2**bits
        codigo_maximo = numero_niveles - 1

        # Líneas horizontales para TODOS los niveles posibles de cuantificación.
        # hlines crea una colección eficiente incluso con 4096 niveles (12 bits).
        niveles_horizontales = np.arange(numero_niveles)
        ax_plot.hlines(
            niveles_horizontales,
            xmin=0.5, xmax=total + 0.5,
            colors="#9aa5b1", linewidths=0.35, alpha=0.42,
            zorder=1
        )

        # Una posición por muestra, repartidas uniformemente por todo el ancho.
        posiciones = np.linspace(1, total, total)
        ax_plot.scatter(
            posiciones, codigos.astype(int),
            color="#d62748", edgecolors="white",
            linewidths=0.35, s=38, zorder=3
        )
        ax_plot.set_xlim(0.5, total + 0.5)
        ax_plot.set_ylim(-0.5, codigo_maximo + 0.5)
        ax_plot.set_ylabel(f"Digital code (0–{codigo_maximo})")
        ax_plot.set_xticks(posiciones)
        ax_plot.tick_params(axis="x", labelbottom=False)
        # Etiquetas legibles: todos los códigos solo en 4 bits;
        # en 8/12 bits se rotulan marcas espaciadas, pero se dibujan
        # igualmente las líneas de todos los niveles.
        if bits == 4:
            ax_plot.set_yticks(niveles_horizontales)
        else:
            salto = 16 if bits == 8 else 256
            marcas = np.arange(0, numero_niveles, salto)
            if marcas[-1] != codigo_maximo:
                marcas = np.append(marcas, codigo_maximo)
            ax_plot.set_yticks(marcas)
        ax_plot.grid(axis="x", alpha=0.18, zorder=0)

        error_lsb = (muestras - niveles) * (2**bits - 1) / 2
        ax_error_completo.clear()
        ax_error_completo.set_title("Quantization error", fontsize=8, pad=1)
        ax_error_completo.axhline(0, color="0.35", lw=0.8)
        ax_error_completo.stem(
            indices, error_lsb, linefmt="#f28e2b",
            markerfmt="o", basefmt=" "
        )
        ax_error_completo.set_xlim(0.5, total + 0.5)
        ax_error_completo.set_xticks(indices)
        ax_error_completo.set_xlabel("Sample number", fontsize=8)
        ax_error_completo.set_ylabel("Error (LSB)", fontsize=8)
        ax_error_completo.tick_params(labelsize=8)
        ax_error_completo.grid(True, alpha=0.25)
    elif fase == 3:
        # Encoding: la gráfica representa exactamente los códigos
        # que aparecen en la tabla binaria de la derecha.
        ax_solo_muestras.set_visible(True)
        posiciones = np.arange(1, total + 1)
        numero_niveles = 2**bits
        codigo_maximo = numero_niveles - 1

        ax_plot.clear()
        ax_plot.set_title("4. ENCODING: digital code for each sample",
                          fontsize=11)
        # Líneas guía seleccionadas, no los cientos/miles de niveles.
        if bits == 4:
            paso_guia = 1
        elif bits == 8:
            paso_guia = 16
        else:
            paso_guia = 256
        guias = np.arange(0, numero_niveles, paso_guia)
        if guias[-1] != codigo_maximo:
            guias = np.append(guias, codigo_maximo)
        ax_plot.hlines(
            guias, xmin=0.5, xmax=total + 0.5,
            colors="#9aa5b1", linewidths=0.55, alpha=0.5,
            zorder=1
        )
        ax_plot.plot(
            posiciones, codigos.astype(int),
            color="#d62748", marker="o", markersize=5,
            linewidth=1.2, zorder=3
        )
        ax_plot.set_xlim(0.5, total + 0.5)
        ax_plot.set_ylim(-0.5, codigo_maximo + 0.5)
        ax_plot.set_xticks(posiciones)
        ax_plot.set_xlabel("Sample number")
        ax_plot.set_ylabel(f"Digital code (0–{codigo_maximo})")
        ax_plot.set_yticks(guias)
        ax_plot.grid(axis="x", alpha=0.18)
        ax_plot.text(
            0.02, 0.96,
            "Each point matches the binary word in the table",
            va="top", transform=ax_plot.transAxes, fontsize=9,
            bbox=dict(boxstyle="round", fc="white", ec="0.8")
        )
    else:
        ax_solo_muestras.set_visible(True)
        preparar_eje(ax_plot, "TRANSMITTER: analog-to-digital conversion", "Amplitude")
        ax_plot.plot(tms, d["entrada"], color="#16865b", lw=1.8,
                     label="Analog signal")
        if fase >= 1:
            ax_plot.plot(tsms, muestras, "o", color="C1", ms=5,
                         label="Samples")
            ax_plot.vlines(tsms, 0, muestras, color="C1", alpha=0.35)
        ax_plot.legend(loc="upper right", fontsize=8)

    # Zona de canal y receptor.
    ax_solo_muestras.axis("off")
    if fase == 2:
        ax_solo_muestras.set_visible(False)
    if fase <= 2 or fase == 6:
        ax_solo_muestras.text(
            0.02, 0.96, "CHANNEL AND RECEIVER",
            fontsize=11, fontweight="bold", va="top",
            transform=ax_solo_muestras.transAxes
        )

    if fase <= 2:
        texto = (
            "The transmitter prepares the samples.\n\n"
            f"Samples in this interval: {total}\n"
            f"Resolution: {bits} bits\n"
            f"Available levels: {2**bits}"
        )
        ax_solo_muestras.text(0.03, 0.72, texto, fontsize=10,
                              linespacing=1.6,
                              transform=ax_solo_muestras.transAxes)
    elif fase == 3:
        ax_solo_muestras.text(
            0.02, 0.96, "GENERATED BINARY WORDS",
            fontsize=9.2, fontweight="bold", va="top",
            transform=ax_solo_muestras.transAxes
        )
        for i, c in enumerate(codigos):
            col = i // 10
            fila = i % 10
            x = 0.03 + col * 0.49
            y = 0.82 - fila * 0.075
            ax_solo_muestras.text(
                x, y, f"{i+1:02d}: {format(int(c), f'0{bits}b')}",
                fontsize=7.5, family="monospace",
                transform=ax_solo_muestras.transAxes
            )
    elif fase == 4:
        ax_solo_muestras.text(
            0.02, 0.96, "TRANSMISSION THROUGH THE CHANNEL",
            fontsize=9.5, fontweight="bold", va="top",
            transform=ax_solo_muestras.transAxes
        )
        columnas = 4
        for i, c in enumerate(codigos):
            col = i % columnas
            fila = i // columnas
            x = 0.02 + col * 0.245
            y = 0.80 - fila * 0.105
            ax_solo_muestras.text(
                x, y, format(int(c), f"0{bits}b"),
                fontsize=7.0, family="monospace",
                transform=ax_solo_muestras.transAxes
            )
        ax_solo_muestras.annotate(
            "", xy=(0.84, 0.19), xytext=(0.16, 0.19),
            xycoords="axes fraction",
            arrowprops=dict(arrowstyle="->", lw=2, color="#174a8b")
        )
        ax_solo_muestras.text(
            0.02, 0.23, "TRANSMITTER", fontsize=8, ha="left",
            transform=ax_solo_muestras.transAxes
        )
        ax_solo_muestras.text(
            0.98, 0.23, "RECEIVER", fontsize=8, ha="right",
            transform=ax_solo_muestras.transAxes
        )
        ax_solo_muestras.text(
            0.03, 0.05,
            f"{len(codigos)} palabras · {len(codigos) * bits} bits",
            fontsize=8, transform=ax_solo_muestras.transAxes
        )
    elif fase == 5:
        # Decoding: representar los códigos decimales recuperados.
        # La gráfica y la tabla muestran exactamente los mismos valores.
        ax_plot.clear()
        ax_plot.set_title(
            "6. DECODING: codes recovered by the receiver",
            fontsize=11
        )

        posiciones = np.arange(1, total + 1)
        numero_niveles = 2**bits
        codigo_maximo = numero_niveles - 1

        if bits == 4:
            paso_guia = 1
        elif bits == 8:
            paso_guia = 16
        else:
            paso_guia = 256

        guias = np.arange(0, numero_niveles, paso_guia)
        if guias[-1] != codigo_maximo:
            guias = np.append(guias, codigo_maximo)

        ax_plot.hlines(
            guias, xmin=0.5, xmax=total + 0.5,
            colors="#9aa5b1", linewidths=0.55, alpha=0.5,
            zorder=1
        )
        ax_plot.plot(
            posiciones, codigos.astype(int),
            color="#16865b", marker="o", markersize=5,
            linewidth=1.2, zorder=3
        )
        ax_plot.set_xlim(0.5, total + 0.5)
        ax_plot.set_ylim(-0.5, codigo_maximo + 0.5)
        ax_plot.set_xticks(posiciones)
        ax_plot.set_xlabel("Sample number")
        ax_plot.set_ylabel(f"Recovered code (0–{codigo_maximo})")
        ax_plot.set_yticks(guias)
        ax_plot.grid(axis="x", alpha=0.18)

        ax_solo_muestras.set_visible(True)
        ax_solo_muestras.clear()
        ax_solo_muestras.axis("off")
        ax_solo_muestras.text(
            0.03, 0.91, "RECEIVER DECODING",
            fontsize=10, fontweight="bold",
            transform=ax_solo_muestras.transAxes
        )
        ax_solo_muestras.text(
            0.03, 0.82, "RECEIVED BITS       DECIMAL CODE",
            fontsize=8.5, fontweight="bold",
            family="monospace",
            transform=ax_solo_muestras.transAxes
        )
        for i, c in enumerate(codigos):
            col = i // 10
            fila = i % 10
            x = 0.03 + col * 0.50
            y = 0.72 - fila * 0.067
            ax_solo_muestras.text(
                x, y,
                f"{format(int(c), f'0{bits}b')}  →  {int(c)}",
                fontsize=7.5, family="monospace",
                transform=ax_solo_muestras.transAxes
            )

    else:
        # Pantalla final: destacar la señal reconstruida tras el filtro.
        ax_plot.set_position([0.07, 0.32, 0.60, 0.43])
        ax_solo_muestras.set_position([0.72, 0.32, 0.25, 0.43])
        ax_plot.clear()
        preparar_eje(ax_plot, "7. SIGNAL RECONSTRUCTION", "Amplitudee")
        ax_plot.plot(
            tms, d["original"], "--", color="#929292",
            alpha=0.75, lw=1.8, label="Original signal"
        )
        ax_plot.step(
            tms, d["zoh"], where="post", color="#f0a15a",
            alpha=0.42, lw=1.4, label="ZOH output"
        )
        ax_plot.plot(
            tms, d["reconstruida"], color="#168b45",
            lw=3.0, zorder=4, label="Reconstructed signal (filtered)"
        )
        ax_plot.legend(loc="upper right", fontsize=8.5, framealpha=0.92)

        ax_solo_muestras.clear()
        ax_solo_muestras.axis("off")
        ax_solo_muestras.text(
            0.03, 0.91, "RECONSTRUCTION PROCESS",
            fontsize=10, fontweight="bold",
            transform=ax_solo_muestras.transAxes
        )
        ax_solo_muestras.text(
            0.03, 0.72,
            "1. Receives the binary words\\n"
            "2. Decodes the digital values\\n"
            "3. Converts codes into voltage levels\\n"
            "4. Holds each level (ZOH)\\n"
            "5. Filters and smooths the signal",
            fontsize=9.2, linespacing=1.8,
            transform=ax_solo_muestras.transAxes
        )

    titulos = [
        "1. Analog signal de entrada",
        "2. Sampling: captura de valores en instantes determinados",
        "3. Quantization: mapping samples to discrete levels",
        "4. Encoding: each level is represented in binary",
        "5. Transmission: binary words travel through the channel",
        "6. Decoding: the receiver recovers the codes",
        "7. Reconstruction: D/A conversion and filtering"
    ]
    explicaciones = [
        f"The transmitter receives an analog signal of {frecuencia:.0f} Hz, continuous in time. A block of 20 samples will be processed.",
        f"The sampling clock runs at Fs = {fs:.0f} Hz. The sampling period is T = {1e6/fs:.1f} µs. {total} samples are shown.",
        f"The quantizer assigns each sample to the nearest available level. With {bits} bits there are {2**bits} levels.",
        f"Each quantized sample is converted into a {bits} bits. are generated. {total} palabras.",
        f"The {total} words are transmitted through an ideal channel. The data stream contains {total*bits} bits, with no noise or errors.",
        "The receiver groups the bits into fixed-length words and recovers the corresponding numerical codes.",
        "The DAC converts the codes into voltage levels. The ZOH holds each level, and the reconstruction filter smooths the signal."
    ]
    if fase != 2:
        ax_info.set_visible(True)
        ax_info.clear()
        ax_info.axis("off")
        ax_info.text(0.01, 0.60, explicaciones[fase], fontsize=10.2,
                     wrap=True, transform=ax_info.transAxes)
    titulo_general.set_text("TRANSMISSION AND RECEPTION: ADC → CHANNEL → DAC")
    paso_texto.set_text(f"{titulos[fase]}   |   Stage {fase + 1} of 7")
    dibujar_esquema()

def dibujar():
    global frecuencia, fs, bits, forzar_aliasing

    frecuencia = slider_f.val
    fs = slider_fs.val
    bits = int(radio_bits.value_selected.split()[0])
    forzar_aliasing = check_alias.get_status()[0]

    d = obtener_datos()
    if modo == "Complete":
        # El recorrido completo transmite un bloque didáctico de 20 samples.
        # ADC y DAC conservan todos sus datos y su duración originales.
        n_bloque = min(20, len(d["ts"]))
        fin_bloque = d["ts"][n_bloque - 1] + 1 / fs
        mascara_t = d["t"] < fin_bloque
        d = dict(d)
        for clave in ("t", "original", "filtrada", "entrada",
                      "zoh", "lineal", "reconstruida"):
            d[clave] = d[clave][mascara_t]
        for clave in ("ts", "muestras", "codigos", "niveles"):
            d[clave] = d[clave][:n_bloque]

    tms = d["t"] * 1000
    tsms = d["ts"] * 1000

    ax_plot.clear()
    ax_solo_muestras.clear()
    if modo != "Complete":
        ax_error_completo.set_visible(False)
        ax_info.set_visible(True)
    if modo == "Complete":
        dibujar_completo(d)
        fig.canvas.draw_idle()
        return

    mostrar_panel_lateral = (modo == "ADC" and etapa in (2, 3))
    if mostrar_panel_lateral:
        ax_plot.set_position([0.08, 0.31, 0.55, 0.43])
        ax_solo_muestras.set_position([0.69, 0.31, 0.25, 0.43])
        ax_solo_muestras.set_visible(True)
    else:
        ax_plot.set_position([0.10, 0.31, 0.82, 0.43])
        ax_solo_muestras.set_visible(False)

    if modo == "ADC":

        if etapa == 0:
            preparar_eje(ax_plot, "Analog input signal", "Amplitude")
            ax_plot.plot(tms, d["original"], color="#16865b", lw=2)
            titulo = "Input: continuous analog signal"
            explicacion = (
                f"The input signal is a sine wave of {frecuencia:.0f} Hz. "
                "At this point, it is still continuous in time."
            )

        elif etapa == 1:
            preparar_eje(ax_plot, "Before and after filtering", "Amplitude")
            ax_plot.plot(
                tms, d["original"], "--", alpha=0.55,
                label="Before filtering"
            )
            ax_plot.plot(
                tms, d["filtrada"], lw=2,
                label="After anti-aliasing filter"
            )
            ax_plot.legend()
            titulo = "Anti-aliasing filter: limits frequencies"
            explicacion = (
                f"Nyquist = Fs/2 = {fs/2:.0f} Hz. El filtro tiene un corte "
                f"aproximado de {d['corte_anti']:.0f} Hz. "
                "With a sufficiently high Fs, 7 kHz should pass with almost no attenuation; "
                "if Fs is too low, the filter attenuates that frequency."
            )

        elif etapa == 2:
            # Cada pulsación captura una muestra adicional.
            total_muestras = len(d["ts"])
            visibles = min(numero_muestras_visibles, total_muestras)
            ts_visibles = tsms[:visibles]
            muestras_visibles = d["muestras"][:visibles]

            preparar_eje(ax_plot, "Input signal and sampled points", "Amplitude")
            ax_plot.plot(tms, d["entrada"], alpha=0.55, lw=1.5,
                         label="Signal de entrada")
            ax_plot.plot(ts_visibles, muestras_visibles, "o",
                         color="C1", ms=6, linestyle="none",
                         label="Captured samples")
            ax_plot.vlines(ts_visibles, 0, muestras_visibles,
                           color="C1", alpha=0.45, linewidth=1)

            instante_actual = ts_visibles[-1]
            ax_plot.axvline(instante_actual, color="crimson",
                            linestyle="--", alpha=0.75,
                            label="Sampling instant")
            ax_plot.legend(loc="upper right", fontsize=8)

            preparar_eje(ax_solo_muestras, "Samples only", "Amplitude")
            ax_solo_muestras.axhline(0, color="gray", lw=0.8)
            ax_solo_muestras.stem(ts_visibles, muestras_visibles,
                                  linefmt="C1-", markerfmt="C1o",
                                  basefmt=" ")
            ax_solo_muestras.axvline(instante_actual, color="crimson",
                                     linestyle="--", alpha=0.75)
            ax_solo_muestras.set_xlim(0, DURACION * 1000)

            titulo = "Sampling: the clock captures samples one by one"
            explicacion = (
                f"Fs = {fs:.0f} samples/s; T = {1e6/fs:.1f} µs. "
                f"{visibles} of {total_muestras} samples have been captured. "
                "Usa «Sample +» para avanzar pulso a pulso o "
                "«Start automatic» para ver cómo el reloj captura "
                "the samples continuously."
            )

        elif etapa == 3:
            numero_niveles = 2 ** bits
            codigos_antes = (
                (d["muestras"] + 1) * (numero_niveles - 1) / 2
            )
            error_lsb = codigos_antes - d["codigos"]

            preparar_eje(
                ax_plot,
                f"Quantization: {numero_niveles} levels ({bits} bits)",
                "Quantization code"
            )
            ax_plot.plot(
                tsms, codigos_antes, "o",
                ms=7, markerfacecolor="none", markeredgewidth=1.4,
                label="Before quantization", zorder=3
            )
            ax_plot.step(
                tsms, d["codigos"], where="mid",
                color="C1", linewidth=1.4,
                label="Quantized code", zorder=2
            )
            ax_plot.plot(tsms, d["codigos"], "s", color="C1", ms=4, zorder=4)

            for x, y0, y1 in zip(tsms, codigos_antes, d["codigos"]):
                ax_plot.plot([x, x], [y0, y1], color="crimson",
                             alpha=0.8, linewidth=1.0, zorder=5)

            ax_plot.set_ylim(-0.5, numero_niveles - 0.5)
            if bits == 4:
                ticks = np.arange(0, numero_niveles, 1)
            elif bits == 8:
                ticks = np.arange(0, numero_niveles, 32)
            else:
                ticks = np.arange(0, numero_niveles, 512)
            ax_plot.set_yticks(ticks)
            ax_plot.legend(loc="upper right", fontsize=8)

            # Ampliación del error de cuantificación en unidades LSB.
            preparar_eje(ax_solo_muestras, "Error detail", "Error (LSB)")
            ax_solo_muestras.axhspan(-0.5, 0.5, color="green", alpha=0.08,
                                     label="Margen ±0,5 LSB")
            ax_solo_muestras.axhline(0, color="black", linewidth=0.8)
            ax_solo_muestras.stem(tsms, error_lsb, linefmt="C3-",
                                  markerfmt="C3o", basefmt=" ")
            ax_solo_muestras.set_ylim(-0.6, 0.6)
            ax_solo_muestras.set_yticks([-0.5, 0, 0.5])
            ax_solo_muestras.legend(loc="upper right", fontsize=7)

            titulo = f"Quantization: {numero_niveles} available levels"
            explicacion = (
                f"The main panel shows codes from 0 to {numero_niveles - 1}. "
                "The quantization error is enlarged on the right in LSB. "
                "With 8 bits, input and output almost overlap because the error "
                "is very small."
            )

        else:
            ax_plot.axis("off")
            ax_plot.text(
                0.02, 0.90,
                "Sample       Nivel       Código binario",
                fontsize=12, fontweight="bold",
                transform=ax_plot.transAxes
            )
            for i, c in enumerate(d["codigos"][:12]):
                ax_plot.text(
                    0.05, 0.79 - i * 0.065,
                    f"{i:>3}          {c:>5}       {format(int(c), f'0{bits}b')}",
                    fontsize=11, family="monospace",
                    transform=ax_plot.transAxes
                )
            titulo = "Encoding: each level is converted into bits"
            explicacion = (
                f"Each quantized sample is represented by a "
                f"binaria de {bits} bits."
            )

    else:  # DAC

        if etapa == 0:
            ax_plot.axis("off")
            cadena = "   ".join(
                format(int(c), f"0{bits}b") for c in d["codigos"][:12]
            )
            ax_plot.text(
                0.02, 0.75, "Palabras binarias recibidas:",
                fontsize=12, fontweight="bold",
                transform=ax_plot.transAxes
            )
            ax_plot.text(
                0.02, 0.52, cadena,
                fontsize=11, family="monospace",
                transform=ax_plot.transAxes
            )
            titulo = "Digital input"
            explicacion = (
                "El DAC recibe palabras binarias que representan "
                "los valores de las samples."
            )

        elif etapa == 1:
            preparar_eje(ax_plot, "Decoded numerical values", "Code")
            ax_plot.step(tsms, d["codigos"], where="mid")
            titulo = "Decoding: from bits to numerical values"
            explicacion = (
                f"Each {bits}-bit word represents a number between "
                f"0 y {2**bits - 1}."
            )

        elif etapa == 2:
            preparar_eje(ax_plot, "DAC output voltage levels", "Normalized voltage")
            ax_plot.stem(
                tsms, d["niveles"],
                linefmt="C2-", markerfmt="C2o", basefmt=" "
            )
            titulo = "D/A conversion: each code is converted into a voltage"
            explicacion = (
                "Each number is converted into a proportional voltage level. "
                "The signal has not been smoothed yet."
            )

        elif etapa == 3:
            preparar_eje(ax_plot, "ZOH output staircase", "Normalized voltage")
            ax_plot.step(
                tms, d["zoh"], where="post",
                label="Salida escalonada ZOH"
            )
            ax_plot.plot(
                tsms, d["niveles"], "o", ms=3,
                label="Sample values"
            )
            ax_plot.legend()
            titulo = "ZOH: each level is held until the next sample"
            explicacion = (
                "The hold circuit keeps each value constant for one sampling "
                "period. This produces a staircase waveform."
            )

        else:
            preparar_eje(ax_plot, "Signal before and after filtering", "Amplitude")
            ax_plot.plot(
                tms, d["zoh"], "--", alpha=0.55,
                label="Signal escalonada"
            )
            ax_plot.plot(
                tms, d["reconstruida"], lw=2,
                label="After reconstruction filter"
            )
            ax_plot.legend()
            titulo = "Reconstruction filter: smooths the signal"
            explicacion = (
                "The low-pass filter attenuates the high-frequency components "
                "of the staircase and produces a smoother signal."
            )

    ax_info.clear()
    ax_info.axis("off")
    ax_info.text(
        0.01, 0.75, explicacion,
        fontsize=10.5, wrap=True,
        transform=ax_info.transAxes
    )

    if modo == "ADC" and etapa == 2 and forzar_aliasing:
        ax_info.text(
            0.01, 0.10,
            f"Demonstration: the filter has been bypassed. A signal of "
            f"{frecuencia:.0f} Hz muestreada a {fs:.0f} Hz aparenta "
            f"{d['alias']:.0f} Hz.",
            color="crimson", fontsize=10, fontweight="bold",
            transform=ax_info.transAxes
        )

    titulo_general.set_text(
        "ANALOG-TO-DIGITAL CONVERSION (ADC)"
        if modo == "ADC"
        else "DIGITAL-TO-ANALOG CONVERSION (DAC)"
    )
    nombres = ETAPAS_ADC if modo == "ADC" else ETAPAS_DAC
    paso_texto.set_text(f"{nombres[etapa]}   |   Etapa {etapa + 1} de 5")

    dibujar_esquema()
    fig.canvas.draw_idle()


def cambiar_modo(valor):
    global modo, etapa, numero_muestras_visibles, indice_completo
    if muestreo_automatico:
        detener_automatico()
    modo = valor
    etapa = 0
    indice_completo = 0
    numero_muestras_visibles = 1
    dibujar()


def anterior(evento):
    global etapa, numero_muestras_visibles, indice_completo
    if muestreo_automatico:
        detener_automatico()
    if modo == "Complete":
        indice_completo = max(0, indice_completo - 1)
        dibujar()
        return
    etapa = max(0, etapa - 1)
    if modo == "ADC" and etapa == 2:
        numero_muestras_visibles = 1
    dibujar()


def siguiente(evento):
    global etapa, numero_muestras_visibles, indice_completo
    if muestreo_automatico:
        detener_automatico()
    if modo == "Complete":
        indice_completo = min(6, indice_completo + 1)
        dibujar()
        return
    etapa = min(4, etapa + 1)
    if modo == "ADC" and etapa == 2:
        numero_muestras_visibles = 1
    dibujar()


def avanzar_muestra(evento):
    global numero_muestras_visibles, indice_completo
    if muestreo_automatico:
        detener_automatico()
    if modo == "Complete":
        indice_completo = min(6, indice_completo + 1)
        dibujar()
        return
    d = obtener_datos()
    numero_muestras_visibles = min(numero_muestras_visibles + 1, len(d["ts"]))
    dibujar()


def reiniciar_muestras(evento):
    global numero_muestras_visibles, indice_completo
    if muestreo_automatico:
        detener_automatico()
    numero_muestras_visibles = 1
    indice_completo = 0
    dibujar()


# Temporizador gráfico: la animación se ralentiza deliberadamente para
# que el alumnado pueda distinguir los pulsos y las samples.
temporizador = fig.canvas.new_timer(interval=350)


def pulso_automatico():
    global numero_muestras_visibles, muestreo_automatico, indice_completo

    if not muestreo_automatico:
        detener_automatico()
        return

    if modo == "Complete":
        if indice_completo >= 6:
            detener_automatico()
            return
        indice_completo += 1
        dibujar()
        if indice_completo >= 6:
            detener_automatico()
        return

    if modo != "ADC" or etapa != 2:
        detener_automatico()
        return

    d = obtener_datos()
    total = len(d["ts"])

    if numero_muestras_visibles >= total:
        detener_automatico()
        return

    numero_muestras_visibles += 1
    dibujar()

    if numero_muestras_visibles >= total:
        detener_automatico()


def detener_automatico():
    global muestreo_automatico
    muestreo_automatico = False
    temporizador.stop()
    btn_auto.label.set_text("Start automatic")
    fig.canvas.draw_idle()


def alternar_automatico(evento):
    global muestreo_automatico, numero_muestras_visibles, etapa, indice_completo

    if muestreo_automatico:
        detener_automatico()
        return

    if modo == "Complete":
        if indice_completo >= 6:
            indice_completo = 0
            dibujar()
    elif modo != "ADC" or etapa != 2:
        # Al iniciar desde otra etapa, llevar al recorrido ADC y al muestreo.
        radio_modo.set_active(0)
        # set_active dispara cambiar_modo; después seleccionamos etapa 2.
        etapa = 2
        numero_muestras_visibles = 1
        dibujar()

    d = obtener_datos()
    if modo != "Complete" and numero_muestras_visibles >= len(d["ts"]):
        numero_muestras_visibles = 1
        dibujar()

    muestreo_automatico = True
    btn_auto.label.set_text("Pause automatic")
    temporizador.start()


temporizador.add_callback(pulso_automatico)

radio_modo.on_clicked(cambiar_modo)
slider_fs.on_changed(lambda valor: dibujar())
slider_f.on_changed(lambda valor: dibujar())
radio_bits.on_clicked(lambda valor: dibujar())
check_alias.on_clicked(lambda valor: dibujar())
btn_prev.on_clicked(anterior)
btn_next.on_clicked(siguiente)
btn_muestra.on_clicked(avanzar_muestra)
btn_reiniciar_muestras.on_clicked(reiniciar_muestras)
btn_auto.on_clicked(alternar_automatico)

dibujar()
plt.show()
