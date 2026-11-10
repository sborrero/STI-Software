import os
import shutil
import subprocess
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

APP_TITLE = "Digital Video Lab - Módulo 5: Comparativa de códecs"

class CodecLab:
    def __init__(self, root):
        self.root = root
        self.root.title(APP_TITLE)
        self.root.geometry("900x650")
        self.root.minsize(780, 560)
        self.video_path = tk.StringVar()
        # Carpeta samples situada junto al programa; se crea si todavía no existe.
        self.samples_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "samples")
        os.makedirs(self.samples_dir, exist_ok=True)
        self.output_dir = tk.StringVar(value=self.samples_dir)
        self.bitrate = tk.StringVar(value="2M")
        self.status = tk.StringVar(value="Selecciona un vídeo para comenzar.")
        self.results = []

        main = ttk.Frame(root, padding=14)
        main.pack(fill="both", expand=True)

        ttk.Label(main, text="Comparativa práctica de códecs", font=("Segoe UI", 17, "bold")).pack(anchor="w")
        ttk.Label(
            main,
            text="Usaremos el mismo vídeo y el mismo bitrate objetivo para comparar el tamaño de los archivos.",
            wraplength=850
        ).pack(anchor="w", pady=(4, 12))

        filebox = ttk.LabelFrame(main, text="1. Vídeo de origen", padding=10)
        filebox.pack(fill="x", pady=5)
        row = ttk.Frame(filebox)
        row.pack(fill="x")
        ttk.Entry(row, textvariable=self.video_path).pack(side="left", fill="x", expand=True)
        ttk.Button(row, text="Elegir vídeo…", command=self.choose_video).pack(side="left", padx=(8, 0))

        outbox = ttk.LabelFrame(main, text="2. Parámetros de compresión", padding=10)
        outbox.pack(fill="x", pady=5)
        row = ttk.Frame(outbox)
        row.pack(fill="x", pady=3)
        ttk.Label(row, text="Carpeta de resultados:").pack(side="left")
        ttk.Entry(row, textvariable=self.output_dir).pack(side="left", fill="x", expand=True, padx=8)
        ttk.Button(row, text="Elegir carpeta…", command=self.choose_folder).pack(side="left")
        row2 = ttk.Frame(outbox)
        row2.pack(fill="x", pady=(8, 2))
        ttk.Label(row2, text="Bitrate de vídeo objetivo:").pack(side="left")
        ttk.Combobox(
            row2, textvariable=self.bitrate, state="readonly", width=10,
            values=("1M", "2M", "3M", "4M", "5M", "8M")
        ).pack(side="left", padx=8)
        ttk.Label(row2, text="M = Mbit/s. Se aplicará el mismo valor a los tres códecs.").pack(side="left")

        actions = ttk.Frame(main)
        actions.pack(fill="x", pady=10)
        self.run_button = ttk.Button(actions, text="Comprimir con los tres códecs", command=self.start)
        self.run_button.pack(side="left")
        ttk.Button(actions, text="Limpiar resultados", command=self.clear).pack(side="left", padx=8)

        progress_row = ttk.Frame(main)
        progress_row.pack(fill="x", pady=(0, 6))
        self.progress = ttk.Progressbar(progress_row, mode="determinate", maximum=100)
        self.progress.pack(side="left", fill="x", expand=True)
        self.progress_label = ttk.Label(progress_row, text="0 %", width=8, anchor="e")
        self.progress_label.pack(side="left", padx=(8, 0))

        resultbox = ttk.LabelFrame(main, text="3. Resultados", padding=10)
        resultbox.pack(fill="both", expand=True, pady=5)
        self.tree = ttk.Treeview(resultbox, columns=("codec", "size", "rate", "file"), show="headings", height=7)
        self.tree.heading("codec", text="Códec")
        self.tree.heading("size", text="Tamaño")
        self.tree.heading("rate", text="Bitrate medio")
        self.tree.heading("file", text="Archivo generado")
        self.tree.column("codec", width=130)
        self.tree.column("size", width=110, anchor="center")
        self.tree.column("rate", width=130, anchor="center")
        self.tree.column("file", width=420)
        self.tree.pack(fill="both", expand=True)

        self.summary = tk.Text(resultbox, height=4, wrap="word", state="disabled")
        self.summary.pack(fill="x", pady=(8, 0))

        ttk.Label(main, textvariable=self.status, foreground="#245b8f", wraplength=850).pack(anchor="w", pady=(8, 0))
        ttk.Label(
            main,
            text="Nota: esta práctica compara el tamaño real de los archivos. La calidad visual puede variar; "
                 "igual bitrate no significa exactamente igual calidad.",
            wraplength=850
        ).pack(anchor="w", pady=(5, 0))

        if not shutil.which("ffmpeg"):
            self.status.set("FFmpeg no está instalado o no está en PATH. La aplicación necesita FFmpeg para comprimir vídeos.")

    def choose_video(self):
        initial_dir = self.samples_dir if os.path.isdir(self.samples_dir) else os.path.dirname(os.path.abspath(__file__))
        name = filedialog.askopenfilename(
            title="Seleccionar vídeo",
            initialdir=initial_dir,
            filetypes=[
                ("Vídeos habituales", "*.mp4 *.avi *.mkv *.mov *.mpeg *.mpg *.ts *.m4v *.webm"),
                ("Todos los archivos", "*.*")
            ]
        )
        if name:
            self.video_path.set(name)
            if not self.output_dir.get():
                self.output_dir.set(self.samples_dir)

    def choose_folder(self):
        folder = filedialog.askdirectory(
            title="Carpeta donde guardar los vídeos comprimidos",
            initialdir=self.samples_dir if os.path.isdir(self.samples_dir) else os.path.dirname(os.path.abspath(__file__))
        )
        if folder:
            self.output_dir.set(folder)

    def clear(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.results.clear()
        self.progress["value"] = 0
        self.progress_label.configure(text="0 %")
        self.set_summary("")

    def set_summary(self, text):
        self.summary.configure(state="normal")
        self.summary.delete("1.0", "end")
        self.summary.insert("1.0", text)
        self.summary.configure(state="disabled")

    def start(self):
        if not self.video_path.get() or not os.path.isfile(self.video_path.get()):
            messagebox.showwarning("Falta el vídeo", "Selecciona primero un archivo de vídeo.")
            return
        if not shutil.which("ffmpeg"):
            messagebox.showerror(
                "FFmpeg no encontrado",
                "No encuentro FFmpeg. Instálalo y añade su carpeta bin al PATH de Windows. "
                "Después cierra y vuelve a abrir esta aplicación."
            )
            return
        folder = self.output_dir.get().strip()
        if not folder:
            messagebox.showwarning("Falta la carpeta", "Selecciona una carpeta para guardar los resultados.")
            return
        os.makedirs(folder, exist_ok=True)
        self.run_button.configure(state="disabled")
        self.progress["value"] = 0
        self.progress_label.configure(text="0 %")
        self.status.set("Preparando la compresión…")
        threading.Thread(target=self.encode_all, daemon=True).start()

    def encode_all(self):
        source = self.video_path.get()
        folder = self.output_dir.get()
        rate = self.bitrate.get()
        source_duration = self.get_duration(source)
        if not source_duration:
            self.root.after(0, lambda: self.status.set("No se pudo leer la duración del vídeo de origen."))
            self.root.after(0, self.finish)
            return

        jobs = [
            ("MPEG-2", "mpeg2video", "mpeg", os.path.join(folder, "video_mpeg2.mpg")),
            ("H.264 / AVC", "libx264", "mp4", os.path.join(folder, "video_h264.mp4")),
            ("H.265 / HEVC", "libx265", "mp4", os.path.join(folder, "video_h265.mp4")),
        ]
        new_results = []
        for job_index, (label, encoder, mux, destination) in enumerate(jobs):
            self.root.after(0, lambda n=label: self.status.set(
                "Comprimiendo " + n + ". La barra muestra el avance de este vídeo…"
            ))
            cmd = [
                "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
                "-i", source, "-an", "-c:v", encoder, "-b:v", rate,
                "-pix_fmt", "yuv420p", "-threads", "2"
            ]
            if encoder in ("libx264", "libx265"):
                cmd += ["-preset", "ultrafast"]
            else:
                cmd += ["-f", mux]
            cmd += ["-progress", "pipe:1", "-nostats", destination]

            try:
                process = subprocess.Popen(
                    cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                    text=True, encoding="utf-8", errors="replace", bufsize=1
                )
                while True:
                    line = process.stdout.readline()
                    if not line:
                        if process.poll() is not None:
                            break
                        continue
                    line = line.strip()
                    if line.startswith(("out_time_us=", "out_time_ms=")):
                        try:
                            # FFmpeg reports these timestamps in microseconds.
                            seconds = int(line.split("=", 1)[1]) / 1_000_000
                            pct = min(100, max(0, seconds / source_duration * 100))
                            overall = (job_index * 100 + pct) / 3
                            self.root.after(0, lambda v=overall, c=pct, n=label:
                                            self.update_progress(v, c, n))
                        except ValueError:
                            pass
                    elif line == "progress=end":
                        self.root.after(0, lambda v=(job_index + 1) * 100 / 3: self.update_progress(v))

                stderr_text = process.stderr.read()
                return_code = process.wait()
                if return_code != 0:
                    details = stderr_text.strip().splitlines()
                    raise RuntimeError(details[-1] if details else "Error de FFmpeg")
                size = os.path.getsize(destination)
                duration = self.get_duration(destination)
                avg_rate = (size * 8 / duration / 1_000_000) if duration else 0
                result = (label, size, avg_rate, destination)
                new_results.append(result)
                self.root.after(0, lambda r=result: self.add_result(r))
            except Exception as exc:
                self.root.after(0, lambda n=label, e=str(exc): self.status.set(f"Error en {n}: {e}"))

        self.results = new_results
        self.root.after(0, self.finish)

    def update_progress(self, value, current=0, codec=""):
        self.progress["value"] = value
        self.progress_label.configure(text=f"{value:.0f} %")
        self.status.set(
            f"Comprimiendo {codec}: {current:.0f} % del vídeo "
            f"(progreso total de la comparativa: {value:.0f} %)."
        )

    def get_duration(self, filename):
        if not shutil.which("ffprobe"):
            return None
        cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration",
               "-of", "default=noprint_wrappers=1:nokey=1", filename]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
            return float(result.stdout.strip()) if result.returncode == 0 else None
        except Exception:
            return None

    def add_result(self, result):
        label, size, avg_rate, filename = result
        self.tree.insert("", "end", values=(
            label, f"{size / 1024 / 1024:.2f} MB",
            f"{avg_rate:.2f} Mbit/s" if avg_rate else "No disponible",
            os.path.basename(filename)
        ))

    def finish(self):
        self.run_button.configure(state="normal")
        if not self.results:
            self.status.set("No se ha podido generar ningún vídeo. Comprueba que FFmpeg dispone de los codificadores necesarios.")
            return
        smallest = min(self.results, key=lambda x: x[1])
        largest = max(self.results, key=lambda x: x[1])
        if largest[1] > 0:
            saving = (1 - smallest[1] / largest[1]) * 100
            text = (
                f"El archivo más pequeño es {smallest[0]} ({smallest[1] / 1024 / 1024:.2f} MB). "
                f"El más grande es {largest[0]} ({largest[1] / 1024 / 1024:.2f} MB). "
                f"La diferencia entre ambos tamaños es del {saving:.1f} % respecto al mayor."
            )
        else:
            text = "Resultados generados."
        self.set_summary(text)
        self.progress["value"] = 100
        self.progress_label.configure(text="100 %")
        self.status.set("Comparativa terminada. Los vídeos están guardados en la carpeta seleccionada.")

if __name__ == "__main__":
    root = tk.Tk()
    app = CodecLab(root)
    root.mainloop()
