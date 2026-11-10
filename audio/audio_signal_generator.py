"""
Audio Signal Generator
Generador independiente de señales de audio para prácticas de FFT.
Requisitos: numpy, sounddevice
Instalación: python -m pip install numpy sounddevice
Ejecución: python audio_signal_generator.py
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
import numpy as np

try:
    import sounddevice as sd
except ImportError:
    sd = None

try:
    from scipy.io.wavfile import write as wav_write
except ImportError:
    wav_write = None


class AudioSignalGenerator:
    def __init__(self, root):
        self.root = root
        self.root.title("Audio Signal Generator | v1.0")
        self.root.geometry("760x610")
        self.root.minsize(680, 560)

        self.fs = tk.IntVar(value=44100)
        self.duration = tk.DoubleVar(value=5.0)
        self.waveform = tk.StringVar(value="Senoidal")
        self.frequency = tk.DoubleVar(value=1000.0)
        self.amplitude = tk.DoubleVar(value=0.25)
        self.frequency2_enabled = tk.BooleanVar(value=False)
        self.frequency2 = tk.DoubleVar(value=2000.0)
        self.amplitude2 = tk.DoubleVar(value=0.25)
        self.status = tk.StringVar(value="Preparado.")
        self.playing = False
        self.stop_event = threading.Event()
        self.stream = None
        self.phase = 0.0
        self.phase2 = 0.0
        self.build()

    def build(self):
        main = ttk.Frame(self.root, padding=14)
        main.pack(fill=tk.BOTH, expand=True)

        ttk.Label(main, text="Generador de señales de audio",
                  font=("Segoe UI", 16, "bold")).pack(anchor="w")
        ttk.Label(main, text="Genera tonos de prueba para comprobar el analizador FFT."
                  ).pack(anchor="w", pady=(2, 12))

        params = ttk.LabelFrame(main, text="Señal principal", padding=10)
        params.pack(fill=tk.X, pady=5)

        row = ttk.Frame(params)
        row.pack(fill=tk.X, pady=4)
        ttk.Label(row, text="Forma de onda:", width=17).pack(side=tk.LEFT)
        ttk.Combobox(row, textvariable=self.waveform, state="readonly",
                     values=["Senoidal", "Cuadrada", "Triangular", "Diente de sierra"],
                     width=20).pack(side=tk.LEFT)
        ttk.Label(row, text="Frecuencia (Hz):").pack(side=tk.LEFT, padx=(18, 5))
        ttk.Entry(row, textvariable=self.frequency, width=12).pack(side=tk.LEFT)

        row = ttk.Frame(params)
        row.pack(fill=tk.X, pady=4)
        ttk.Label(row, text="Amplitud:", width=17).pack(side=tk.LEFT)
        ttk.Scale(row, from_=0.01, to=0.90, variable=self.amplitude,
                  orient=tk.HORIZONTAL, length=250).pack(side=tk.LEFT)
        self.amp_label = ttk.Label(row, width=10)
        self.amp_label.pack(side=tk.LEFT, padx=8)
        self.amplitude.trace_add("write", lambda *_: self.amp_label.config(
            text=f"{self.amplitude.get():.2f}"))
        self.amp_label.config(text=f"{self.amplitude.get():.2f}")

        second = ttk.LabelFrame(main, text="Segunda frecuencia (opcional)", padding=10)
        second.pack(fill=tk.X, pady=5)
        ttk.Checkbutton(second, text="Añadir una segunda frecuencia",
                        variable=self.frequency2_enabled).pack(anchor="w")
        row = ttk.Frame(second)
        row.pack(fill=tk.X, pady=5)
        ttk.Label(row, text="Frecuencia 2 (Hz):", width=17).pack(side=tk.LEFT)
        ttk.Entry(row, textvariable=self.frequency2, width=12).pack(side=tk.LEFT)
        ttk.Label(row, text="Amplitud 2:").pack(side=tk.LEFT, padx=(18, 5))
        ttk.Scale(row, from_=0.01, to=0.90, variable=self.amplitude2,
                  orient=tk.HORIZONTAL, length=190).pack(side=tk.LEFT)
        self.amp2_label = ttk.Label(row, width=7, text="0.25")
        self.amp2_label.pack(side=tk.LEFT, padx=6)
        self.amplitude2.trace_add("write", lambda *_: self.amp2_label.config(
            text=f"{self.amplitude2.get():.2f}"))

        output = ttk.LabelFrame(main, text="Salida", padding=10)
        output.pack(fill=tk.X, pady=5)
        row = ttk.Frame(output)
        row.pack(fill=tk.X, pady=4)
        ttk.Label(row, text="Frecuencia de muestreo:", width=22).pack(side=tk.LEFT)
        ttk.Combobox(row, textvariable=self.fs, state="readonly",
                     values=[22050, 44100, 48000], width=12).pack(side=tk.LEFT)
        ttk.Label(row, text="Duración (s):").pack(side=tk.LEFT, padx=(20, 5))
        ttk.Entry(row, textvariable=self.duration, width=8).pack(side=tk.LEFT)

        buttons = ttk.Frame(main)
        buttons.pack(fill=tk.X, pady=14)
        self.play_button = ttk.Button(buttons, text="▶ Reproducir señal",
                                      command=self.start)
        self.play_button.pack(side=tk.LEFT)
        self.stop_button = ttk.Button(buttons, text="■ Detener",
                                      command=self.stop, state=tk.DISABLED)
        self.stop_button.pack(side=tk.LEFT, padx=8)
        ttk.Button(buttons, text="Guardar WAV…", command=self.save_wav).pack(side=tk.LEFT, padx=8)

        note = ("Consejo: empieza con una senoide de 1.000 Hz y amplitud 0,25. "
                "En el analizador deberías ver un pico alrededor de 1 kHz.")
        ttk.Label(main, text=note, wraplength=700).pack(anchor="w", pady=(2, 10))
        ttk.Label(main, textvariable=self.status, relief=tk.SUNKEN,
                  anchor="w", padding=7).pack(fill=tk.X, side=tk.BOTTOM)

    def validate(self):
        try:
            f1 = float(self.frequency.get())
            a1 = float(self.amplitude.get())
            dur = float(self.duration.get())
            fs = int(self.fs.get())
            if not (1 <= f1 < fs / 2):
                raise ValueError("La frecuencia principal debe estar entre 1 Hz y Nyquist.")
            if not (0 < a1 <= 0.9):
                raise ValueError("La amplitud debe estar entre 0 y 0,90.")
            if not (0.1 <= dur <= 300):
                raise ValueError("La duración debe estar entre 0,1 y 300 segundos.")
            if self.frequency2_enabled.get():
                f2 = float(self.frequency2.get())
                a2 = float(self.amplitude2.get())
                if not (1 <= f2 < fs / 2):
                    raise ValueError("La segunda frecuencia debe estar por debajo de Nyquist.")
                if not (0 < a2 <= 0.9):
                    raise ValueError("La amplitud 2 debe estar entre 0 y 0,90.")
            return f1, a1, dur, fs
        except (ValueError, tk.TclError) as exc:
            messagebox.showerror("Parámetros no válidos", str(exc))
            return None

    def make_signal(self):
        valid = self.validate()
        if valid is None:
            return None
        f1, a1, dur, fs = valid
        n = int(round(dur * fs))
        t = np.arange(n, dtype=np.float64) / fs

        def oscillator(freq, amp):
            phase = (freq * t) % 1.0
            kind = self.waveform.get()
            if kind == "Senoidal":
                return amp * np.sin(2 * np.pi * phase)
            if kind == "Cuadrada":
                return amp * np.where(np.sin(2 * np.pi * phase) >= 0, 1.0, -1.0)
            if kind == "Triangular":
                return amp * (2 * np.abs(2 * phase - 1) - 1)
            return amp * (2 * phase - 1)

        signal = oscillator(f1, a1)
        description = f"{self.waveform.get().lower()} de {f1:g} Hz"
        if self.frequency2_enabled.get():
            f2 = float(self.frequency2.get())
            a2 = float(self.amplitude2.get())
            signal += oscillator(f2, a2)
            description += f" + {f2:g} Hz"
        # Evita saturación digital si se suman dos señales.
        peak = float(np.max(np.abs(signal))) if len(signal) else 0.0
        if peak > 0.98:
            signal = signal * (0.98 / peak)
            description += " (nivel ajustado para evitar saturación)"
        return fs, signal.astype(np.float32), description

    def start(self):
        if sd is None:
            messagebox.showerror("Falta sounddevice",
                "Instala las dependencias con:\npython -m pip install numpy sounddevice")
            return
        if self.playing:
            return
        made = self.make_signal()
        if made is None:
            return
        fs, signal, description = made
        self.playing = True
        self.play_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        self.status.set(f"Reproduciendo: {description} · {fs:,} Hz")
        self.stop_event.clear()

        def worker():
            try:
                sd.play(signal, fs, blocking=True)
            except Exception as exc:
                self.root.after(0, lambda: messagebox.showerror("Error de reproducción", str(exc)))
            finally:
                self.root.after(0, self.finished)
        threading.Thread(target=worker, daemon=True).start()

    def stop(self):
        self.stop_event.set()
        if sd is not None:
            try:
                sd.stop()
            except Exception:
                pass
        self.finished()

    def finished(self):
        self.playing = False
        self.play_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        self.status.set("Preparado.")

    def save_wav(self):
        if wav_write is None:
            messagebox.showerror("Falta SciPy",
                "Para guardar WAV instala también scipy:\npython -m pip install scipy")
            return
        made = self.make_signal()
        if made is None:
            return
        fs, signal, description = made
        path = filedialog.asksaveasfilename(
            title="Guardar señal WAV",
            defaultextension=".wav",
            filetypes=[("Audio WAV", "*.wav")],
            initialfile="tono_prueba.wav")
        if not path:
            return
        pcm = np.clip(signal, -1, 1)
        pcm16 = (pcm * 32767).astype(np.int16)
        try:
            wav_write(path, fs, pcm16)
            self.status.set(f"WAV guardado: {path}")
            messagebox.showinfo("WAV guardado",
                f"Se ha guardado la señal:\n{path}\n\n{description}")
        except Exception as exc:
            messagebox.showerror("Error al guardar", str(exc))


if __name__ == "__main__":
    root = tk.Tk()
    app = AudioSignalGenerator(root)
    root.mainloop()
