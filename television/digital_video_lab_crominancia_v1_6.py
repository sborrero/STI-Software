"""
DIGITAL VIDEO LAB - MÓDULO 3: MUESTREO DE CROMINANCIA
Demostración visual de YCbCr y submuestreo 4:4:4, 4:2:2 y 4:2:0.

Dependencia:
    python -m pip install pillow

Nota: conversión YCbCr de rango completo basada en la transformación habitual
de Pillow. Es una demostración didáctica; no implementa un codificador de vídeo.
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path

try:
    from PIL import Image, ImageTk
except ImportError:
    Image = ImageTk = None


class ChromaSamplingLab:
    def __init__(self, root):
        self.root = root
        self.image = None
        self.photos = {}
        root.title("Digital Video Lab - Muestreo de crominancia")
        root.geometry("1180x850")
        root.minsize(980, 720)

        notebook = ttk.Notebook(root)
        notebook.pack(fill="both", expand=True)

        main = ttk.Frame(notebook, padding=10)
        explanation = ttk.Frame(notebook, padding=14)
        calculator = ttk.Frame(notebook, padding=14)
        notebook.add(main, text="Simulador de crominancia")
        notebook.add(explanation, text="¿Qué significa 4:4:4, 4:2:2 y 4:2:0?")
        notebook.add(calculator, text="Calculadora de caudal")

        self.build_explanation_tab(explanation)
        self.build_bitrate_tab(calculator)

        top = ttk.Frame(main)
        top.pack(fill="x", pady=(0, 8))
        ttk.Button(top, text="Cargar imagen", command=self.load_image).pack(side="left")
        self.filename = ttk.Label(top, text="Ninguna imagen cargada")
        self.filename.pack(side="left", padx=10)

        controls = ttk.LabelFrame(main, text="Formato de submuestreo", padding=9)
        controls.pack(fill="x", pady=5)
        row = ttk.Frame(controls)
        row.pack(fill="x")
        ttk.Label(row, text="Seleccionar:").pack(side="left")
        self.mode = tk.StringVar(value="4:2:0")
        ttk.Combobox(
            row, textvariable=self.mode, state="readonly", width=10,
            values=["4:4:4", "4:2:2", "4:2:0"]
        ).pack(side="left", padx=7)
        ttk.Button(row, text="Aplicar", command=self.process).pack(side="left", padx=6)

        self.description = ttk.Label(controls, text="", font=("Segoe UI", 10, "bold"))
        self.description.pack(anchor="w", pady=(7, 2))
        self.sample_info = ttk.Label(controls, text="", wraplength=1080)
        self.sample_info.pack(anchor="w")

        panels = ttk.Frame(main)
        panels.pack(fill="both", expand=True, pady=8)
        self.labels = {}
        panel_specs = [
            ("original", "Imagen original"),
            ("y", "Y – Luminancia"),
            ("cb", "Cb – Crominancia azul"),
            ("cr", "Cr – Crominancia roja"),
            ("reconstructed", "Imagen reconstruida"),
        ]
        for index, (key, title) in enumerate(panel_specs):
            frame = ttk.LabelFrame(panels, text=title, padding=5)
            frame.grid(row=index // 3, column=index % 3, sticky="nsew", padx=4, pady=4)
            label = ttk.Label(frame, text="Carga una imagen", anchor="center")
            label.pack(fill="both", expand=True)
            self.labels[key] = label
        for col in range(3):
            panels.columnconfigure(col, weight=1)
        for row_idx in range(2):
            panels.rowconfigure(row_idx, weight=1)

        pattern = ttk.LabelFrame(main, text="Esquema de muestras de crominancia", padding=8)
        pattern.pack(fill="x", pady=5)
        self.pattern_canvas = tk.Canvas(pattern, height=112, background="white",
                                        highlightthickness=1, highlightbackground="#bbb")
        self.pattern_canvas.pack(fill="x")
        self.draw_pattern()

        ttk.Label(
            main,
            text=(
                "Y se conserva a resolución completa. El submuestreo reduce la cantidad de "
                "muestras de Cb y Cr, aprovechando que el ojo humano suele percibir menos "
                "los detalles finos de color que los detalles de luminancia. La imagen "
                "reconstruida interpola las muestras de crominancia para volver al tamaño "
                "original; por eso puede presentar pequeñas diferencias de color."
            ),
            wraplength=1100, foreground="#555"
        ).pack(anchor="w", pady=6)


    def build_explanation_tab(self, parent):
        """Pestaña explicativa con desplazamiento vertical."""
        # La explicación ocupa más espacio que la ventana: se introduce en
        # un Canvas con barra de desplazamiento vertical.
        container = ttk.Frame(parent)
        container.pack(fill="both", expand=True)

        scroll_canvas = tk.Canvas(container, highlightthickness=0)
        scrollbar = ttk.Scrollbar(
            container, orient="vertical", command=scroll_canvas.yview
        )
        scroll_canvas.configure(yscrollcommand=scrollbar.set)

        scrollbar.pack(side="right", fill="y")
        scroll_canvas.pack(side="left", fill="both", expand=True)

        content = ttk.Frame(scroll_canvas, padding=14)
        window_id = scroll_canvas.create_window(
            (0, 0), window=content, anchor="nw"
        )

        def update_scroll_region(_event=None):
            scroll_canvas.configure(scrollregion=scroll_canvas.bbox("all"))

        def fit_content_width(event):
            scroll_canvas.itemconfigure(window_id, width=event.width)

        content.bind("<Configure>", update_scroll_region)
        scroll_canvas.bind("<Configure>", fit_content_width)

        # Rueda del ratón en Windows y Linux.
        def mousewheel(event):
            if getattr(event, "delta", 0):
                scroll_canvas.yview_scroll(int(-event.delta / 120), "units")
            elif getattr(event, "num", None) == 4:
                scroll_canvas.yview_scroll(-3, "units")
            elif getattr(event, "num", None) == 5:
                scroll_canvas.yview_scroll(3, "units")

        scroll_canvas.bind_all("<MouseWheel>", mousewheel)
        scroll_canvas.bind_all("<Button-4>", mousewheel)
        scroll_canvas.bind_all("<Button-5>", mousewheel)

        """Explicación visual del significado de las relaciones de submuestreo."""
        ttk.Label(
            content, text="Cómo interpretar 4:4:4, 4:2:2 y 4:2:0",
            font=("Segoe UI", 17, "bold")
        ).pack(anchor="w", pady=(0, 8))

        intro = (
            "La notación describe cuántas muestras de crominancia se toman "
            "respecto a las muestras de luminancia en una zona de referencia. "
            "La luminancia (Y) se mantiene a resolución completa; lo que se "
            "reduce es la resolución de Cb y Cr."
        )
        ttk.Label(content, text=intro, wraplength=1080, justify="left").pack(
            anchor="w", pady=(0, 12)
        )

        legend = ttk.LabelFrame(content, text="Qué representa cada componente", padding=10)
        legend.pack(fill="x", pady=5)
        ttk.Label(
            legend,
            text="Y = luminancia (detalle y brillo)     "
                 "Cb = diferencia de color azul     "
                 "Cr = diferencia de color rojo",
            font=("Segoe UI", 10, "bold")
        ).pack(anchor="w")
        ttk.Label(
            legend,
            text="Cada punto Y representa una posición de imagen. Los puntos Cb y Cr "
                 "indican dónde se registra información de color.",
            wraplength=1050
        ).pack(anchor="w", pady=(5, 0))

        entries = [
            (
                "4:4:4 — sin submuestreo de crominancia",
                "Por cada 4 muestras Y en horizontal se toman 4 muestras Cb y 4 muestras Cr. "
                "Cada píxel dispone de su propia información de luminancia y de color.",
                "Muestras Cb: 100 % de las de Y.  Muestras Cr: 100 % de las de Y.",
                "444"
            ),
            (
                "4:2:2 — mitad de resolución de color horizontal",
                "Por cada 4 muestras Y en horizontal se toman 2 muestras Cb y 2 muestras Cr. "
                "Se conserva la resolución vertical de crominancia, pero se reduce a la mitad "
                "en horizontal. Es habitual en producción y edición de vídeo.",
                "Muestras Cb: 50 % de las de Y.  Muestras Cr: 50 % de las de Y.",
                "422"
            ),
            (
                "4:2:0 — mitad de resolución de color horizontal y vertical",
                "Se toman la mitad de muestras de crominancia en horizontal y la mitad en "
                "vertical. En una zona de 2 × 2 píxeles Y (4 muestras Y), hay una muestra Cb "
                "y una muestra Cr. Cada componente de crominancia tiene el 25 % de las "
                "muestras de Y.",
                "Muestras Cb: 25 % de las de Y.  Muestras Cr: 25 % de las de Y.",
                "420"
            ),
        ]

        for title, explanation, ratio, kind in entries:
            box = ttk.LabelFrame(content, text=title, padding=10)
            box.pack(fill="x", pady=6)
            ttk.Label(box, text=explanation, wraplength=1050, justify="left").pack(
                anchor="w"
            )
            ttk.Label(
                box, text=ratio, font=("Segoe UI", 9, "bold")
            ).pack(anchor="w", pady=(5, 0))
            canvas = tk.Canvas(box, height=245, background="white",
                               highlightthickness=1, highlightbackground="#ccc")
            canvas.pack(fill="x", pady=(7, 0))
            self.draw_explanation_pattern(canvas, kind)

        note = ttk.LabelFrame(content, text="Importante: qué NO significa 4:2:0", padding=10)
        note.pack(fill="x", pady=7)
        ttk.Label(
            note,
            text=(
                "No significa que se elimine el 75 % de toda la información de imagen. "
                "La luminancia Y permanece completa. El 25 % se refiere únicamente al "
                "número de muestras de cada componente de crominancia (Cb y Cr), comparado "
                "con el número de muestras Y."
            ),
            wraplength=1050, justify="left"
        ).pack(anchor="w")

    @staticmethod
    def draw_explanation_pattern(canvas, kind):
        """
        Dibuja una matriz de 4 filas x 8 columnas.
        Cada celda representa un píxel: Y siempre está presente.
        Los bloques azules muestran qué píxeles comparten las muestras Cb y Cr.
        """
        canvas.delete("all")
        canvas.create_text(
            14, 12, anchor="nw",
            text="Matriz de 4 filas × 8 columnas: cada recuadro representa un píxel",
            fill="#333", font=("Segoe UI", 10, "bold")
        )

        x0, y0 = 150, 42
        cell_w, cell_h = 66, 43
        grid_w, grid_h = 8 * cell_w, 4 * cell_h

        # Etiquetas de filas
        for r in range(4):
            canvas.create_text(
                125, y0 + r * cell_h + cell_h / 2,
                text=f"Fila {r+1}", anchor="e",
                font=("Segoe UI", 9, "bold"), fill="#444"
            )

        # Dibujar los 32 píxeles y su luminancia
        for r in range(4):
            for c in range(8):
                x = x0 + c * cell_w
                y = y0 + r * cell_h
                canvas.create_rectangle(
                    x, y, x + cell_w, y + cell_h,
                    fill="#f0f0f0", outline="#666", width=1
                )
                canvas.create_text(
                    x + cell_w / 2, y + 12,
                    text="Y", fill="#222",
                    font=("Segoe UI", 10, "bold")
                )

                if kind == "444":
                    chroma_text = "Cb + Cr"
                    canvas.create_text(
                        x + cell_w / 2, y + 29,
                        text=chroma_text, fill="#0875bd",
                        font=("Segoe UI", 8, "bold")
                    )

        if kind == "422":
            # Una muestra Cb y una Cr por cada pareja horizontal.
            # Se dibuja una banda compartida sobre las dos celdas.
            for r in range(4):
                for c in range(0, 8, 2):
                    x = x0 + c * cell_w
                    y = y0 + r * cell_h + 24
                    canvas.create_rectangle(
                        x + 3, y, x + 2 * cell_w - 3, y + 16,
                        fill="#b9ddf5", outline="#0875bd", width=1
                    )
                    canvas.create_text(
                        x + cell_w, y + 8,
                        text="Cb + Cr compartidas",
                        fill="#075b96", font=("Segoe UI", 8, "bold")
                    )

        elif kind == "420":
            # Una muestra Cb y una Cr por cada bloque de 2x2 píxeles.
            for r in range(0, 4, 2):
                for c in range(0, 8, 2):
                    x = x0 + c * cell_w
                    y = y0 + r * cell_h
                    canvas.create_rectangle(
                        x + 3, y + 22, x + 2 * cell_w - 3,
                        y + 2 * cell_h - 3,
                        fill="#b9ddf5", outline="#0875bd", width=2
                    )
                    canvas.create_text(
                        x + cell_w, y + cell_h + 1,
                        text="Cb + Cr compartidas",
                        fill="#075b96", font=("Segoe UI", 8, "bold")
                    )

        # Leyenda y explicación según el formato
        if kind == "444":
            explanation = (
                "En cada píxel hay Y, Cb y Cr propias. "
                "No se comparte información de crominancia."
            )
        elif kind == "422":
            explanation = (
                "Cada píxel tiene su Y. Cada pareja horizontal comparte "
                "una muestra Cb y una muestra Cr."
            )
        else:
            explanation = (
                "Cada píxel tiene su Y. Cada bloque de 2 × 2 píxeles "
                "comparte una muestra Cb y una muestra Cr."
            )

        canvas.create_text(
            x0, y0 + grid_h + 16,
            text=explanation, anchor="nw", width=grid_w + 40,
            fill="#075b96", font=("Segoe UI", 9, "bold")
        )



    def build_bitrate_tab(self, parent):
        """Calculadora de caudal bruto de vídeo sin comprimir."""
        ttk.Label(
            parent, text="Calculadora de caudal binario",
            font=("Segoe UI", 17, "bold")
        ).pack(anchor="w", pady=(0, 6))
        ttk.Label(
            parent,
            text=(
                "Calcula los datos de imagen que habría que transmitir por segundo "
                "según la resolución, la frecuencia de imagen, la profundidad de bits "
                "y el submuestreo de crominancia."
            ),
            wraplength=1080, justify="left"
        ).pack(anchor="w", pady=(0, 12))

        inputs = ttk.LabelFrame(parent, text="Parámetros de vídeo", padding=12)
        inputs.pack(fill="x", pady=5)

        self.calc_width = tk.StringVar(value="1920")
        self.calc_height = tk.StringVar(value="1080")
        self.calc_fps = tk.StringVar(value="25")
        self.calc_bits = tk.StringVar(value="8")

        row1 = ttk.Frame(inputs)
        row1.pack(fill="x", pady=4)
        ttk.Label(row1, text="Resolución:").pack(side="left")
        ttk.Label(row1, text="Ancho (px)").pack(side="left", padx=(12, 3))
        ttk.Entry(row1, textvariable=self.calc_width, width=9).pack(side="left")
        ttk.Label(row1, text="Alto (px)").pack(side="left", padx=(12, 3))
        ttk.Entry(row1, textvariable=self.calc_height, width=9).pack(side="left")
        ttk.Label(row1, text="Imágenes/s:").pack(side="left", padx=(18, 3))
        ttk.Combobox(
            row1, textvariable=self.calc_fps, width=8,
            values=["23.976", "24", "25", "29.97", "30", "50", "59.94", "60"]
        ).pack(side="left")

        row2 = ttk.Frame(inputs)
        row2.pack(fill="x", pady=4)
        ttk.Label(row2, text="Profundidad por componente:").pack(side="left")
        ttk.Combobox(
            row2, textvariable=self.calc_bits, state="readonly", width=8,
            values=["8", "10", "12"]
        ).pack(side="left", padx=7)
        ttk.Label(
            row2, text="bits por muestra (Y, Cb y Cr)"
        ).pack(side="left", padx=5)
        ttk.Label(row2, text="Submuestreo:").pack(side="left", padx=(18, 3))
        self.calc_chroma_mode = tk.StringVar(value="4:2:0")
        ttk.Combobox(
            row2, textvariable=self.calc_chroma_mode, state="readonly", width=8,
            values=["4:4:4", "4:2:2", "4:2:0"]
        ).pack(side="left", padx=5)

        presets = ttk.Frame(inputs)
        presets.pack(fill="x", pady=(8, 2))
        ttk.Label(presets, text="Resoluciones habituales:").pack(side="left")
        for label, w, h in [
            ("SD", 720, 576), ("HD", 1280, 720),
            ("Full HD", 1920, 1080), ("UHD 4K", 3840, 2160)
        ]:
            ttk.Button(
                presets, text=label,
                command=lambda ww=w, hh=h: self.set_calc_resolution(ww, hh)
            ).pack(side="left", padx=3)

        ttk.Button(
            inputs, text="Calcular caudal",
            command=self.calculate_bitrate
        ).pack(anchor="w", pady=(10, 0))

        self.calc_summary = ttk.Label(
            parent, text="Introduce los parámetros y pulsa «Calcular caudal».",
            font=("Segoe UI", 10, "bold"), wraplength=1080
        )
        self.calc_summary.pack(anchor="w", pady=(12, 7))

        results = ttk.LabelFrame(parent, text="Comparación de los tres formatos", padding=8)
        results.pack(fill="both", expand=True, pady=5)

        columns = ("format", "bits_pixel", "samples_frame", "bits_frame",
                   "rate_mbps", "saving")
        self.bitrate_tree = ttk.Treeview(
            results, columns=columns, show="headings", height=4
        )
        headings = {
            "format": "Submuestreo",
            "bits_pixel": "Bits/píxel",
            "samples_frame": "Muestras/imagen",
            "bits_frame": "Mbit/imagen",
            "rate_mbps": "Caudal (Mbit/s)",
            "saving": "Ahorro frente a 4:4:4"
        }
        widths = {
            "format": 105, "bits_pixel": 95, "samples_frame": 160,
            "bits_frame": 125, "rate_mbps": 145, "saving": 165
        }
        for col in columns:
            self.bitrate_tree.heading(col, text=headings[col])
            self.bitrate_tree.column(col, width=widths[col], anchor="center")
        self.bitrate_tree.pack(fill="x", expand=True)

        self.calc_detail = ttk.Label(
            results, text="", justify="left", wraplength=1080
        )
        self.calc_detail.pack(anchor="w", pady=(10, 4))

        systems = ttk.LabelFrame(
            parent, text="¿Cabe este vídeo sin comprimir en cada medio?",
            padding=8
        )
        systems.pack(fill="x", pady=7)
        system_columns = ("system", "capacity", "occupation", "status", "compression")
        self.system_tree = ttk.Treeview(
            systems, columns=system_columns, show="headings", height=3
        )
        system_headings = {
            "system": "Medio de transmisión",
            "capacity": "Capacidad útil",
            "occupation": "Ocupación",
            "status": "¿Cabe?",
            "compression": "Compresión mínima necesaria"
        }
        system_widths = {
            "system": 220, "capacity": 140, "occupation": 120,
            "status": 100, "compression": 210
        }
        for col in system_columns:
            self.system_tree.heading(col, text=system_headings[col])
            self.system_tree.column(col, width=system_widths[col], anchor="center")
        self.system_tree.pack(fill="x", expand=True)

        ttk.Label(
            systems,
            text=(
                "Modelos didácticos fijos: DVB-T, canal de 8 MHz, 64-QAM, modo 8K, "
                "guarda 1/4 y FEC 2/3 (capacidad útil aproximada del múltiplex: "
                "19,9 Mbit/s); DVB-C, canal de 8 MHz, 256-QAM y 6,9 MBd "
                "(aprox. 50,9 Mbit/s tras Reed-Solomon); streaming IP sobre "
                "Ethernet de 100 Mbit/s, reservando el 20 % para variaciones "
                "y otros tráficos (80 Mbit/s disponibles). Se supone que toda "
                "la capacidad indicada se dedica a un único vídeo."
            ),
            wraplength=1080, justify="left"
        ).pack(anchor="w", pady=(8, 2))

        note = ttk.LabelFrame(parent, text="Qué incluye este cálculo", padding=10)
        note.pack(fill="x", pady=5)
        ttk.Label(
            note,
            text=(
                "Es el caudal bruto de las muestras de imagen, sin compresión. "
                "No incluye intervalos de borrado, sincronismos, cabeceras, audio, "
                "metadatos ni otros datos auxiliares. Se supone vídeo YCbCr de tres "
                "componentes y dimensiones pares para los formatos 4:2:2 y 4:2:0."
            ),
            wraplength=1080, justify="left"
        ).pack(anchor="w")

        self.calculate_bitrate()

    def set_calc_resolution(self, width, height):
        self.calc_width.set(str(width))
        self.calc_height.set(str(height))
        self.calculate_bitrate()

    def calculate_bitrate(self):
        try:
            width = int(self.calc_width.get())
            height = int(self.calc_height.get())
            fps = float(self.calc_fps.get().replace(",", "."))
            bits = int(self.calc_bits.get())
            if width <= 0 or height <= 0 or fps <= 0:
                raise ValueError
            if width % 2 or height % 2:
                messagebox.showwarning(
                    "Resolución no válida",
                    "Para comparar 4:2:2 y 4:2:0, utiliza ancho y alto pares."
                )
                return
        except (ValueError, TypeError):
            messagebox.showerror(
                "Parámetros incorrectos",
                "Introduce ancho, alto y frecuencia positivos. "
                "El ancho y el alto deben ser números pares."
            )
            return

        pixels = width * height
        formats = [
            ("4:4:4", 3.0),
            ("4:2:2", 2.0),
            ("4:2:0", 1.5),
        ]
        base_rate = pixels * fps * bits * 3
        rows = []
        details = []

        for name, samples_per_pixel in formats:
            samples = pixels * samples_per_pixel
            bits_frame = samples * bits
            rate = bits_frame * fps
            bits_pixel = samples_per_pixel * bits
            saving = (1 - rate / base_rate) * 100
            rows.append((
                name,
                f"{bits_pixel:g}",
                f"{samples:,.0f}",
                f"{bits_frame / 1_000_000:,.3f}",
                f"{rate / 1_000_000:,.3f}",
                "0 %" if name == "4:4:4" else f"{saving:.1f} %"
            ))

            y_samples = pixels
            if name == "4:4:4":
                cb_samples = cr_samples = pixels
            elif name == "4:2:2":
                cb_samples = cr_samples = pixels / 2
            else:
                cb_samples = cr_samples = pixels / 4

            details.append(
                f"{name}: Y = {y_samples:,.0f}; "
                f"Cb = {cb_samples:,.0f}; Cr = {cr_samples:,.0f} muestras/imagen."
            )

        for item in self.bitrate_tree.get_children():
            self.bitrate_tree.delete(item)
        for row in rows:
            self.bitrate_tree.insert("", "end", values=row)

        self.calc_summary.config(
            text=(
                f"{width} × {height} píxeles · {fps:g} imágenes/s · "
                f"{bits} bits por componente · {pixels:,} píxeles por imagen"
            )
        )
        self.calc_detail.config(
            text=(
                "Desglose de muestras por imagen:\n" + "\n".join(details) +
                "\n\nConversión: caudal (bit/s) = muestras por imagen × "
                "bits por muestra × imágenes por segundo."
            )
        )

        # Comparación del caudal bruto con capacidades de transmisión fijadas.
        chroma_factor = {"4:4:4": 3.0, "4:2:2": 2.0, "4:2:0": 1.5}
        raw_rate_mbps = pixels * fps * bits * chroma_factor[
            self.calc_chroma_mode.get()
        ] / 1_000_000

        # DVB-C: 6,9 MBd × 8 bits/símbolo × (188/204) de carga útil.
        systems = [
            ("TDT DVB-T · 8 MHz", 19.9),
            ("Cable DVB-C · 8 MHz", 6.9 * 8 * 188 / 204),
            ("Streaming IP · Ethernet 100", 80.0),
        ]
        for item in self.system_tree.get_children():
            self.system_tree.delete(item)

        for system_name, capacity in systems:
            occupation = raw_rate_mbps / capacity * 100
            if raw_rate_mbps <= capacity:
                status = "SÍ"
                compression = "No necesaria"
            else:
                status = "NO"
                compression = f"Al menos {raw_rate_mbps / capacity:.1f}:1"
            self.system_tree.insert(
                "", "end",
                values=(
                    system_name, f"{capacity:.2f} Mbit/s",
                    f"{occupation:.1f} %", status, compression
                )
            )

    def load_image(self):
        if Image is None:
            messagebox.showerror(
                "Falta Pillow",
                "Instala Pillow desde PowerShell:\n\npython -m pip install pillow"
            )
            return
        filename = filedialog.askopenfilename(
            title="Seleccionar imagen",
            filetypes=[("Imágenes", "*.jpg *.jpeg *.png *.bmp *.gif"),
                       ("Todos los archivos", "*.*")]
        )
        if not filename:
            return
        try:
            self.image = Image.open(filename).convert("RGB")
            self.filename.configure(
                text=f"{Path(filename).name} ({self.image.width} × {self.image.height})"
            )
            self.process()
        except Exception as exc:
            messagebox.showerror("Error al abrir la imagen", str(exc))

    def show(self, key, image):
        preview = image.copy()
        preview.thumbnail((340, 225), Image.Resampling.LANCZOS)
        photo = ImageTk.PhotoImage(preview)
        self.photos[key] = photo
        self.labels[key].configure(image=photo, text="")

    def draw_pattern(self):
        c = self.pattern_canvas
        c.delete("all")
        mode = self.mode.get()
        c.create_text(12, 12, anchor="nw",
                      text="Cada columna representa una posición horizontal de luminancia (Y). "
                           "Los puntos indican dónde se toman muestras de crominancia.",
                      fill="#333", font=("Segoe UI", 9))
        x0, y0, dx, dy = 55, 55, 46, 25
        for row in range(2):
            c.create_text(18, y0 + row*dy, text=f"Y{row+1}", anchor="w")
            for col in range(8):
                x = x0 + col*dx
                c.create_oval(x-3, y0+row*dy-3, x+3, y0+row*dy+3, fill="#555", outline="")
                c.create_text(x, y0+row*dy+9, text="Y", font=("Segoe UI", 7), fill="#555")

        if mode == "4:4:4":
            positions = [(r, c) for r in range(2) for c in range(8)]
            note = "4:4:4: una muestra Cb y una Cr por cada muestra Y."
        elif mode == "4:2:2":
            positions = [(r, c) for r in range(2) for c in range(0, 8, 2)]
            note = "4:2:2: una muestra Cb y una Cr por cada dos muestras Y, en horizontal."
        else:
            positions = [(r, c) for r in range(0, 2) for c in range(0, 8, 2)]
            note = "4:2:0: una muestra Cb y una Cr por cada bloque de 2 × 2 muestras Y."
        for r, col in positions:
            x, y = x0 + col*dx, y0 + r*dy
            c.create_oval(x-7, y-7, x+7, y+7, outline="#1676d2", width=2)
            c.create_oval(x-4, y-4, x+4, y+4, fill="#1676d2", outline="")
        c.create_text(x0+8*dx+18, 67, anchor="w", text=note,
                      fill="#1676d2", font=("Segoe UI", 10, "bold"))

    def process(self):
        self.draw_pattern()
        if self.image is None:
            return
        try:
            # Pillow's RGB->YCbCr conversion is used for a simple full-range demonstration.
            ycc = self.image.convert("YCbCr")
            y, cb, cr = ycc.split()
            width, height = self.image.size
            mode = self.mode.get()

            if mode == "4:4:4":
                cb_small, cr_small = cb.copy(), cr.copy()
                horizontal_factor, vertical_factor = 1, 1
                description = "4:4:4 – Cb y Cr mantienen la misma resolución que Y."
            elif mode == "4:2:2":
                size = ((width + 1)//2, height)
                cb_small = cb.resize(size, Image.Resampling.BOX)
                cr_small = cr.resize(size, Image.Resampling.BOX)
                horizontal_factor, vertical_factor = 2, 1
                description = "4:2:2 – Cb y Cr tienen la mitad de muestras horizontales."
            else:
                size = ((width + 1)//2, (height + 1)//2)
                cb_small = cb.resize(size, Image.Resampling.BOX)
                cr_small = cr.resize(size, Image.Resampling.BOX)
                horizontal_factor, vertical_factor = 2, 2
                description = "4:2:0 – Cb y Cr tienen la mitad de muestras horizontales y verticales."

            # Upsample chroma back to full resolution for display/reconstruction.
            cb_up = cb_small.resize((width, height), Image.Resampling.BILINEAR)
            cr_up = cr_small.resize((width, height), Image.Resampling.BILINEAR)
            reconstructed = Image.merge("YCbCr", (y, cb_up, cr_up)).convert("RGB")

            self.show("original", self.image)
            self.show("y", y.convert("RGB"))
            # Display chroma centered around neutral gray for visibility.
            self.show("cb", cb.convert("RGB") if False else Image.merge("RGB", (cb, cb, cb)))
            self.show("cr", Image.merge("RGB", (cr, cr, cr)))
            self.show("reconstructed", reconstructed)

            y_count = width * height
            chroma_count = cb_small.width * cb_small.height
            total_samples = y_count + 2 * chroma_count
            self.description.configure(text=description)
            self.sample_info.configure(
                text=(
                    f"Imagen: {width} × {height}.  "
                    f"Y: {y_count:,} muestras.  "
                    f"Cb: {cb_small.width} × {cb_small.height} = {chroma_count:,}.  "
                    f"Cr: {cb_small.width} × {cb_small.height} = {chroma_count:,}.  "
                    f"Total Y+Cb+Cr: {total_samples:,} muestras."
                ).replace(",", ".")
            )
        except Exception as exc:
            messagebox.showerror("Error al procesar YCbCr", str(exc))


def main():
    root = tk.Tk()
    ChromaSamplingLab(root)
    root.mainloop()


if __name__ == "__main__":
    main()
