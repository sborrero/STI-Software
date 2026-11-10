"""
PCM Audio Comparator - Comparador A/B de digitalización
Autor: Santiago Borrero Ortiz
Versión: 1.3

Dependencias:
    pip install numpy scipy matplotlib sounddevice

Uso:
    python pcm_audio_comparator_v1_1.py

Admite ficheros WAV mono y estéreo; los convierte a mono para el análisis. El audio se procesa con:
    1) Remuestreo con filtro antialias (scipy.signal.resample_poly).
    2) Cuantificación PCM uniforme.
    3) Reconstrucción a la frecuencia original para comparar y escuchar.

Nota didáctica:
La reconstrucción se realiza mediante interpolación/remuestreo FIR. Es una
aproximación educativa al proceso DAC, no un modelo de un convertidor físico.
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path

import numpy as np
from scipy.io import wavfile
from scipy.signal import resample_poly
from math import gcd

import matplotlib
matplotlib.use("TkAgg")
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

try:
    import sounddevice as sd
except ImportError:
    sd = None


class DigitalAudioLab:
    def __init__(self, root):
        self.root = root
        self.root.title("PCM Audio Comparator | v1.3")
        self.root.geometry("1450x950")
        self.root.minsize(1100, 760)

        self.file_path = None
        self.original_fs = None
        self.original = None
        self.sampled = None
        self.quantized = None
        self.reconstructed = None
        self.processed_fs = None

        self.fs_a_var = tk.StringVar(value="44100")
        self.bits_a_var = tk.StringVar(value="16")
        self.fs_b_var = tk.StringVar(value="8000")
        self.bits_b_var = tk.StringVar(value="4")
        self.zoom_start_var = tk.StringVar(value="0.00")
        self.zoom_duration_var = tk.StringVar(value="0.01")
        self.play_duration_var = tk.StringVar(value="2.0")
        self.audio_duration = 0.0
        self.status_var = tk.StringVar(value="Abre un fichero WAV mono o estéreo para comenzar.")
        self.info_var = tk.StringVar(value="No hay ningún fichero cargado.")
        self.metrics_var = tk.StringVar(
            value="Carga un WAV y pulsa «Actualizar comparación» para calcular los resultados."
        )

        self._build_ui()

    def _build_ui(self):
        top = ttk.Frame(self.root, padding=(10, 8))
        top.pack(fill=tk.X)
        ttk.Button(top, text="Abrir archivo WAV...", command=self.open_wav).pack(side=tk.LEFT)
        self.file_label = ttk.Label(top, text="Ningún fichero seleccionado", width=55)
        self.file_label.pack(side=tk.LEFT, padx=10)

        compare = ttk.LabelFrame(self.root, text="Configuración de las dos digitalizaciones", padding=8)
        compare.pack(fill=tk.X, padx=10, pady=(0, 6))

        frame_a = ttk.LabelFrame(compare, text="Proceso A — Referencia", padding=7)
        frame_a.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6))
        ttk.Label(frame_a, text="Frecuencia:").grid(row=0, column=0, sticky="w")
        ttk.Combobox(frame_a, textvariable=self.fs_a_var, state="readonly", width=10,
                     values=("8000", "11025", "16000", "22050", "44100")).grid(row=0, column=1, padx=5)
        ttk.Label(frame_a, text="Bits:").grid(row=0, column=2, sticky="w")
        ttk.Combobox(frame_a, textvariable=self.bits_a_var, state="readonly", width=6,
                     values=("4", "8", "12", "16")).grid(row=0, column=3, padx=5)

        frame_b = ttk.LabelFrame(compare, text="Proceso B — Comparación", padding=7)
        frame_b.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(6, 0))
        ttk.Label(frame_b, text="Frecuencia:").grid(row=0, column=0, sticky="w")
        ttk.Combobox(frame_b, textvariable=self.fs_b_var, state="readonly", width=10,
                     values=("8000", "11025", "16000", "22050", "44100")).grid(row=0, column=1, padx=5)
        ttk.Label(frame_b, text="Bits:").grid(row=0, column=2, sticky="w")
        ttk.Combobox(frame_b, textvariable=self.bits_b_var, state="readonly", width=6,
                     values=("4", "8", "12", "16")).grid(row=0, column=3, padx=5)
        ttk.Button(compare, text="Actualizar comparación", command=self.process_audio).pack(side=tk.LEFT, padx=12)

        study = ttk.LabelFrame(self.root, text="Fragmento de estudio y escucha", padding=7)
        study.pack(fill=tk.X, padx=10, pady=(0, 6))
        ttk.Label(study, text="Inicio (s):").pack(side=tk.LEFT)
        self.zoom_start_spin = ttk.Spinbox(study, from_=0.0, to=9999.0, increment=0.05,
                                           textvariable=self.zoom_start_var, width=9)
        self.zoom_start_spin.pack(side=tk.LEFT, padx=(5, 12))
        ttk.Label(study, text="Intervalo de análisis:").pack(side=tk.LEFT)
        ttk.Combobox(study, textvariable=self.zoom_duration_var, state="readonly", width=8,
                     values=("0.005", "0.010", "0.020", "0.050", "0.100", "0.250", "0.500", "1.000", "2.000", "5.000", "10.000")).pack(side=tk.LEFT, padx=5)
        ttk.Button(study, text="Mostrar intervalo", command=self._draw_plots).pack(side=tk.LEFT, padx=7)
        ttk.Separator(study, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=9)
        ttk.Label(study, text="Escuchar:").pack(side=tk.LEFT)
        ttk.Combobox(study, textvariable=self.play_duration_var, state="readonly", width=5,
                     values=("1.0", "2.0", "3.0", "5.0")).pack(side=tk.LEFT, padx=5)
        ttk.Button(study, text="▶ Original", command=self.play_original).pack(side=tk.LEFT, padx=3)
        ttk.Button(study, text="▶ A", command=self.play_a).pack(side=tk.LEFT, padx=3)
        ttk.Button(study, text="▶ B", command=self.play_b).pack(side=tk.LEFT, padx=3)
        ttk.Button(study, text="■ Detener", command=self.stop_audio).pack(side=tk.LEFT, padx=3)

        info = ttk.LabelFrame(self.root, text="Información del audio", padding=6)
        info.pack(fill=tk.X, padx=10, pady=(0, 5))
        ttk.Label(info, textvariable=self.info_var).pack(anchor="w")

        metrics = ttk.LabelFrame(self.root, text="Resumen numérico A/B", padding=6)
        metrics.pack(fill=tk.X, padx=10, pady=(0, 5))
        ttk.Label(metrics, textvariable=self.metrics_var, justify=tk.LEFT, anchor="w",
                  wraplength=1350, font=("Consolas", 9)).pack(fill=tk.X, anchor="w")

        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=(2, 5))
        self.figures, self.axes, self.canvases = {}, {}, {}

        for key, title, rows in (("overview", "Vista general", 1),
                                 ("a", "Proceso A", 3),
                                 ("b", "Proceso B", 3),
                                 ("compare", "Comparación A/B", 2)):
            tab = ttk.Frame(self.notebook)
            self.notebook.add(tab, text=title)
            fig = Figure(figsize=(12.5, 7.0 if rows > 1 else 5.2), dpi=100)
            axes = [fig.add_subplot(rows, 1, i + 1) for i in range(rows)]
            if rows > 1:
                for axis in axes[1:]:
                    axis.sharex(axes[0])
            fig.subplots_adjust(hspace=0.48, left=0.085, right=0.98, top=0.93, bottom=0.10)
            canvas = FigureCanvasTkAgg(fig, master=tab)
            canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
            self.figures[key], self.axes[key], self.canvases[key] = fig, axes, canvas

        ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN,
                  anchor="w", padding=5).pack(fill=tk.X, side=tk.BOTTOM)
        self._draw_empty()

    def _draw_empty(self):
        for key, axes in self.axes.items():
            for axis in axes:
                axis.clear()
                axis.grid(True, alpha=0.25)
            self.canvases[key].draw_idle()

    def _draw_plots(self):
        if self.original is None or not hasattr(self, "result_a"):
            return
        fs0 = self.original_fs
        total_duration = len(self.original) / fs0
        try:
            zstart = max(0.0, float(self.zoom_start_var.get()))
            zlen = max(0.001, float(self.zoom_duration_var.get()))
        except ValueError:
            self.status_var.set("Revisa el inicio y la duración del intervalo.")
            return
        zstart = min(zstart, max(0.0, total_duration - 1 / fs0))
        zend = min(total_duration, zstart + zlen)
        self.zoom_start_var.set(f"{zstart:.4f}")
        i0 = max(0, int(zstart * fs0))
        i1 = min(len(self.original), max(i0 + 2, int(np.ceil(zend * fs0))))
        tz = np.arange(i0, i1) / fs0
        orig = self.original[i0:i1]

        ax = self.axes["overview"][0]
        ax.clear()
        stride = max(1, len(self.original) // 30000)
        ax.plot(np.arange(0, len(self.original), stride) / fs0,
                self.original[::stride], linewidth=0.75)
        ax.axvspan(zstart, zend, color="orange", alpha=0.28, label="Fragmento de estudio")
        ax.set_title(f"Grabación completa — {total_duration:.2f} s")
        ax.set_xlabel("Tiempo (s)")
        ax.set_ylabel("Amplitud")
        ax.set_xlim(0, total_duration)
        ax.legend(loc="upper right")
        ax.grid(True, alpha=0.25)

        for key, result, label, color in (("a", self.result_a, "Proceso A", "tab:blue"),
                                          ("b", self.result_b, "Proceso B", "tab:red")):
            axes = self.axes[key]
            for axis in axes:
                axis.clear()
                axis.grid(True, alpha=0.25)
            axes[0].plot(tz, orig, color="black", linewidth=1.15)
            axes[0].set_title(f"{label} — señal original de referencia")
            axes[0].set_ylabel("Amplitud")

            rate = result["fs"]
            a = max(0, int(np.ceil(zstart * rate - 1e-10)))
            b = min(len(result["quantized"]), int(np.ceil(zend * rate - 1e-10)))
            tt = np.arange(a, b) / rate
            vv = result["quantized"][a:b]
            axes[1].plot(tz, orig, color="0.65", linewidth=1.0, label="Original")
            if len(tt):
                axes[1].step(tt, vv, where="post", color=color, linewidth=1.35,
                             label="Muestras cuantificadas")
                axes[1].plot(tt, vv, "o", color=color, markersize=5)
            axes[1].set_title(f"Muestreo y cuantificación — {rate:,} Hz · {result['bits']} bits · {result['levels']:,} niveles")
            axes[1].set_ylabel("Amplitud")
            axes[1].legend(loc="upper right")

            rec = result["reconstructed"]
            k0, k1 = min(i0, len(rec)), min(i1, len(rec))
            axes[2].plot(tz, orig, color="0.55", linewidth=1.0, label="Original")
            axes[2].plot(np.arange(k0, k1) / fs0, rec[k0:k1],
                         color=color, linewidth=1.25, label="Reconstruida")
            axes[2].set_title("Reconstrucción DAC — comparación con la señal original")
            axes[2].set_ylabel("Amplitud")
            axes[2].set_xlabel("Tiempo (s)")
            axes[2].legend(loc="upper right")
            for axis in axes:
                axis.set_xlim(zstart, zend)
                axis.grid(True, alpha=0.25)
            self.canvases[key].draw_idle()

        axes = self.axes["compare"]
        for axis in axes:
            axis.clear()
            axis.grid(True, alpha=0.25)
        ra, rb = self.result_a["reconstructed"], self.result_b["reconstructed"]
        ka0, ka1 = min(i0, len(ra)), min(i1, len(ra))
        kb0, kb1 = min(i0, len(rb)), min(i1, len(rb))
        axes[0].plot(tz, orig, color="black", linewidth=1.15, label="Original")
        axes[0].plot(np.arange(ka0, ka1) / fs0, ra[ka0:ka1], linewidth=1.1, label="Proceso A")
        axes[0].plot(np.arange(kb0, kb1) / fs0, rb[kb0:kb1], linewidth=1.1, label="Proceso B")
        axes[0].set_title("Comparación de las señales reconstruidas")
        axes[0].set_ylabel("Amplitud")
        axes[0].legend(loc="upper right")
        axes[1].plot(np.arange(ka0, ka1) / fs0, self.original[ka0:ka1] - ra[ka0:ka1],
                     label="Error A", linewidth=1.1)
        axes[1].plot(np.arange(kb0, kb1) / fs0, self.original[kb0:kb1] - rb[kb0:kb1],
                     label="Error B", linewidth=1.1)
        axes[1].set_title("Error de reconstrucción: original − reconstruida")
        axes[1].set_ylabel("Error")
        axes[1].set_xlabel("Tiempo (s)")
        axes[1].legend(loc="upper right")
        for axis in axes:
            axis.set_xlim(zstart, zend)
            axis.grid(True, alpha=0.25)
        for canvas in self.canvases.values():
            canvas.draw_idle()

    @staticmethod
    def _to_float_audio(data):
        if np.issubdtype(data.dtype, np.integer):
            info = np.iinfo(data.dtype)
            # Normalización simétrica aproximada al intervalo [-1, 1].
            scale = max(abs(info.min), abs(info.max))
            return data.astype(np.float64) / scale
        return np.asarray(data, dtype=np.float64)

    def open_wav(self):
        filename = filedialog.askopenfilename(
            title="Seleccionar fichero WAV mono o estéreo",
            filetypes=[("Audio WAV", "*.wav"), ("Todos los archivos", "*.*")]
        )
        if not filename:
            return

        try:
            fs, data = wavfile.read(filename)
            if len(data) == 0 or fs <= 0:
                raise ValueError("El fichero no contiene audio válido.")

            # Convertir a coma flotante antes de mezclar los canales.
            audio = self._to_float_audio(data)
            audio = np.nan_to_num(audio)

            channel_note = "Mono original"
            if audio.ndim == 2:
                if audio.shape[1] != 2:
                    messagebox.showwarning(
                        "Número de canales no compatible",
                        f"El fichero tiene {audio.shape[1]} canales.\\n"
                        "Esta versión admite WAV mono o estéreo."
                    )
                    return
                # Conversión estéreo a mono: promedio de los canales L y R.
                audio = np.mean(audio, axis=1)
                channel_note = "Estéreo convertido automáticamente a mono (L+R)/2"
            elif audio.ndim != 1:
                messagebox.showwarning(
                    "Formato no compatible",
                    "El fichero debe ser WAV mono o estéreo."
                )
                return

            peak = np.max(np.abs(audio))
            if peak > 1.0:
                audio = audio / peak

            self.file_path = Path(filename)
            self.original_fs = int(fs)
            self.original = audio
            self.file_label.config(text=self.file_path.name)
            duration = len(audio) / self.original_fs
            self.audio_duration = duration
            self.zoom_start_var.set("0.00")
            self.info_var.set(
                f"{channel_note}   |   Frecuencia: {self.original_fs:,} Hz   |   "
                f"Muestras: {len(audio):,}   |   Duración: {duration:.2f} s   |   "
                f"Pico: {np.max(np.abs(audio)):.3f}"
            )
            self.process_audio()
        except Exception as exc:
            messagebox.showerror("Error al abrir WAV", str(exc))

    def _parameters_changed(self, _event=None):
        if self.original is not None:
            self.process_audio()

    def _process_one(self, target_fs, bits):
        common = gcd(self.original_fs, target_fs)
        sampled = resample_poly(self.original, target_fs // common, self.original_fs // common)

        scale = 2 ** (bits - 1)
        codes = np.clip(np.round(np.clip(sampled, -1.0, 1.0) * scale), -scale, scale - 1)
        quantized = codes / scale

        common_back = gcd(target_fs, self.original_fs)
        reconstructed = resample_poly(
            quantized, self.original_fs // common_back, target_fs // common_back
        )
        n = min(len(self.original), len(reconstructed))
        reconstructed = reconstructed[:n]

        q_error = sampled - quantized
        q_rms = float(np.sqrt(np.mean(q_error ** 2)))
        sig_rms = float(np.sqrt(np.mean(sampled ** 2)))
        if q_rms <= 1e-15:
            sqnr = "∞"
        elif sig_rms <= 1e-15:
            sqnr = "N/D"
        else:
            sqnr = f"{20*np.log10(sig_rms/q_rms):.2f} dB"

        total_error = self.original[:n] - reconstructed
        total_rmse = float(np.sqrt(np.mean(total_error ** 2)))
        duration = len(self.original) / self.original_fs
        pcm_rate = target_fs * bits
        pcm_bytes = int(np.ceil(duration * pcm_rate / 8))

        return {
            "fs": target_fs, "bits": bits, "sampled": sampled,
            "quantized": quantized, "reconstructed": reconstructed,
            "samples": len(sampled), "ts_us": 1e6 / target_fs,
            "levels": 2 ** bits, "pcm_rate": pcm_rate, "pcm_bytes": pcm_bytes,
            "q_rms": q_rms, "sqnr": sqnr, "total_rmse": total_rmse
        }

    def process_audio(self):
        if self.original is None:
            self.status_var.set("Primero abre un fichero WAV mono o estéreo.")
            return

        fs_a, bits_a = int(self.fs_a_var.get()), int(self.bits_a_var.get())
        fs_b, bits_b = int(self.fs_b_var.get()), int(self.bits_b_var.get())
        if fs_a > self.original_fs or fs_b > self.original_fs:
            messagebox.showwarning(
                "Frecuencia no válida",
                "Las frecuencias A y B deben ser iguales o inferiores a la frecuencia original del WAV."
            )
            return

        try:
            self.result_a = self._process_one(fs_a, bits_a)
            self.result_b = self._process_one(fs_b, bits_b)
        except Exception as exc:
            messagebox.showerror("Error al comparar", str(exc))
            return

        def row(tag, r):
            kib = r["pcm_bytes"] / 1024
            return (
                f"{tag}: Fs {r['fs']:,} Hz | Ts {r['ts_us']:.2f} µs | "
                f"{r['samples']:,} muestras | {r['bits']} bits | "
                f"{r['levels']:,} niveles | PCM {r['pcm_rate']:,} bit/s | "
                f"{r['pcm_bytes']:,} bytes ({kib:.1f} KiB)\n"
                f"     Error RMS cuantificación: {r['q_rms']:.6f} | "
                f"SQNR: {r['sqnr']} | Error RMS total: {r['total_rmse']:.6f}"
            )
        self.metrics_var.set(row("A", self.result_a) + "\n" + row("B", self.result_b))
        self.status_var.set("Comparación A/B actualizada. Escucha ambos resultados con el mismo fragmento.")
        self._draw_plots()

    def _get_playback_slice(self, data):
        try:
            start = max(0.0, float(self.zoom_start_var.get()))
            duration = max(1.0, float(self.play_duration_var.get()))
        except ValueError:
            start, duration = 0.0, 2.0
        i0 = min(len(data), int(start*self.original_fs))
        i1 = min(len(data), int((start+duration)*self.original_fs))
        if i1 <= i0:
            i1 = min(len(data), i0+self.original_fs)
        return data[i0:i1]

    def play_original(self):
        if self.original is not None:
            self._play(self._get_playback_slice(self.original), self.original_fs)

    def play_a(self):
        if hasattr(self, "result_a"):
            self._play(self._get_playback_slice(self.result_a["reconstructed"]), self.original_fs)

    def play_b(self):
        if hasattr(self, "result_b"):
            self._play(self._get_playback_slice(self.result_b["reconstructed"]), self.original_fs)

    def _play(self, data, fs):
        if sd is None:
            messagebox.showerror(
                "Falta una dependencia",
                "Para reproducir audio instala sounddevice:\n\n"
                "python -m pip install sounddevice"
            )
            return
        try:
            sd.stop()
            sd.play(np.asarray(data, dtype=np.float32), fs)
        except Exception as exc:
            messagebox.showerror("Error de reproducción", str(exc))

    def stop_audio(self):
        if sd is not None:
            sd.stop()


def main():
    root = tk.Tk()
    DigitalAudioLab(root)
    root.mainloop()


if __name__ == "__main__":
    main()
