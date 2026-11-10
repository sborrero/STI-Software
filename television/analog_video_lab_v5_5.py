"""
ANALOG VIDEO LAB - v4.0
Dos pestañas:
1) Barrido: progresivo/entrelazado, líneas configurables y retornos.
2) Formación de imagen: cargar una imagen y reconstruirla línea a línea.\n3) Luminancia y crominancia: separar una imagen en Y, U y V.

Dependencias:
    pip install pillow

Formatos de imagen: JPG, JPEG, PNG, BMP, GIF.
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path

try:
    from PIL import Image, ImageTk, ImageDraw
except ImportError:
    Image = ImageTk = ImageDraw = None


BG = "#101820"
GREEN = "#42e695"
YELLOW = "#ffd166"
RED = "#ff625c"


class BarridoTab:
    """Pestaña de demostración del barrido de líneas."""

    def __init__(self, parent):
        self.parent = parent
        self.total = tk.IntVar(value=10)
        self.mode = tk.StringVar(value="Progresivo")
        self.speed = tk.IntVar(value=65)
        self.running = False
        self.after_id = None
        self.phase = "draw"
        self.field = 1
        self.line_in_field = 0
        self.x = 0.0
        self.return_progress = 0.0
        self.completed = {}

        self.width, self.height = 780, 430
        self.mx, self.my = 55, 38
        self.sw, self.sh = self.width - 2*self.mx, self.height - 2*self.my

        self.build()
        self.draw_base()
        self.update_view()

    def build(self):
        main = ttk.Frame(self.parent, padding=10)
        main.pack(fill="both", expand=True)

        settings = ttk.LabelFrame(main, text="Configuración del barrido", padding=8)
        settings.pack(fill="x")
        r = ttk.Frame(settings)
        r.pack(fill="x")
        ttk.Label(r, text="Modo:").pack(side="left")
        mode = ttk.Combobox(r, textvariable=self.mode,
                            values=["Progresivo", "Entrelazado"],
                            state="readonly", width=15)
        mode.pack(side="left", padx=6)
        mode.bind("<<ComboboxSelected>>", self.config_changed)
        ttk.Label(r, text="Líneas:").pack(side="left", padx=(18, 0))
        spin = ttk.Spinbox(r, from_=10, to=625, textvariable=self.total,
                           width=7, command=self.config_changed)
        spin.pack(side="left", padx=6)
        spin.bind("<Return>", self.config_changed)
        spin.bind("<FocusOut>", self.config_changed)

        r2 = ttk.Frame(settings)
        r2.pack(fill="x", pady=(7, 0))
        ttk.Label(r2, text="Velocidad:").pack(side="left")
        ttk.Scale(r2, from_=1, to=100, variable=self.speed,
                  orient="horizontal").pack(side="left", fill="x", expand=True, padx=8)

        self.canvas = tk.Canvas(main, width=self.width, height=self.height,
                                bg=BG, highlightthickness=1,
                                highlightbackground="#52616b")
        self.canvas.pack(fill="both", expand=True, pady=8)

        controls = ttk.Frame(main)
        controls.pack(fill="x")
        self.play = ttk.Button(controls, text="▶ Iniciar", command=self.toggle)
        self.play.pack(side="left", padx=(0, 6))
        ttk.Button(controls, text="⏭ Paso", command=self.step).pack(side="left", padx=6)
        ttk.Button(controls, text="↺ Reiniciar", command=self.reset).pack(side="left", padx=6)
        self.status = ttk.Label(main, font=("Segoe UI", 10, "bold"))
        self.status.pack(anchor="w", pady=(7, 2))
        ttk.Label(
            main,
            text="Verde: progresivo / primer campo. Amarillo: segundo campo. "
                 "Rojo: retorno horizontal y vertical. El marco discontinuo delimita "
                 "la zona visible; las bandas oscuras representan borrado vertical.",
            wraplength=900, foreground="#555"
        ).pack(anchor="w")

    def total_value(self):
        try:
            n = int(self.total.get())
        except (ValueError, tk.TclError):
            n = 10
        n = max(10, min(625, n))
        self.total.set(n)
        return n

    def config_changed(self, _event=None):
        self.pause()
        self.reset()

    def idx(self):
        return self.line_in_field if self.mode.get() == "Progresivo" else (
            self.line_in_field * 2 + (0 if self.field == 1 else 1)
        )

    def y(self, index):
        return self.my + index * self.sh / max(1, self.total_value() - 1)

    def draw_base(self):
        c = self.canvas
        c.delete("all")
        n = self.total_value()
        visible = max(1, round(n * 576 / 625))
        blank = n - visible
        first = blank // 2
        last = min(n - 1, first + visible - 1)
        top, bottom = self.y(first), self.y(last)
        x0, x1, y0, y1 = self.mx, self.mx+self.sw, self.my, self.my+self.sh
        c.create_rectangle(x0, y0, x1, top, fill="#263541", outline="")
        c.create_rectangle(x0, bottom, x1, y1, fill="#263541", outline="")
        c.create_rectangle(x0, y0, x1, y1, outline="#aab7b8", width=2)
        c.create_rectangle(x0, top, x1, bottom, outline="#e6edf0",
                           width=2, dash=(5, 3))
        c.create_text(x0+5, y0+4, text="BORRADO VERTICAL",
                      fill="#b8c6cc", anchor="nw", font=("Segoe UI", 8))
        c.create_text(x0+5, top+4, text="ZONA VISIBLE",
                      fill="#e6edf0", anchor="nw", font=("Segoe UI", 8, "bold"))
        c.create_text(x0+5, bottom+4, text="BORRADO VERTICAL",
                      fill="#b8c6cc", anchor="nw", font=("Segoe UI", 8))
        self.completed_items = {}
        self.active = c.create_line(x0, y0, x0, y0, fill=GREEN, width=2, state="hidden")
        self.hret = c.create_line(x0, y0, x0, y0, fill=RED, width=3, state="hidden")
        self.vret = c.create_line(x0, y0, x0, y0, fill=RED, width=4, state="hidden")
        self.dot = c.create_oval(0, 0, 0, 0, fill="#ffe45c", outline="white")

    def line_color(self):
        return YELLOW if self.mode.get() == "Entrelazado" and self.field == 2 else GREEN

    def redraw_completed(self):
        for item in self.completed_items.values():
            self.canvas.delete(item)
        self.completed_items.clear()
        for index, color in self.completed.items():
            self.completed_items[index] = self.canvas.create_line(
                self.mx, self.y(index), self.mx+self.sw, self.y(index),
                fill=color, width=2
            )

    def update_view(self):
        n = self.total_value()
        index = min(n-1, self.idx())
        y = self.y(index)
        x = self.mx + self.x/100*self.sw
        for item in (self.active, self.hret, self.vret):
            self.canvas.itemconfigure(item, state="hidden")
        bx, by = x, y
        if self.phase == "draw":
            self.canvas.coords(self.active, self.mx, y, x, y)
            self.canvas.itemconfigure(self.active, fill=self.line_color(), state="normal")
        elif self.phase == "h_return":
            p = self.return_progress
            step = 1 if self.mode.get() == "Progresivo" else 2
            next_y = self.y(min(n-1, index+step))
            bx = self.mx + self.sw*(1-p)
            by = y + (next_y-y)*p
            self.canvas.coords(self.hret, self.mx+self.sw, y, bx, by)
            self.canvas.itemconfigure(self.hret, state="normal")
        elif self.phase == "v_return":
            p = self.return_progress
            bx = self.mx + self.sw*(1-p)
            by = self.my + self.sh*(1-p)
            self.canvas.coords(self.vret, self.mx+self.sw, self.my+self.sh, bx, by)
            self.canvas.itemconfigure(self.vret, state="normal")
        self.canvas.coords(self.dot, bx-5, by-5, bx+5, by+5)
        field = f" | Campo {self.field}" if self.mode.get() == "Entrelazado" else ""
        phase = {"draw": "Barrido visible", "h_return": "Retorno horizontal",
                 "v_return": "Retorno vertical"}[self.phase]
        self.status.configure(
            text=f"{self.mode.get()}{field} | Línea {index+1}/{n} | {phase}"
        )

    def advance(self):
        n = self.total_value()
        if self.phase == "draw":
            self.x += 5
            if self.x >= 100:
                self.x = 100
                self.phase = "h_return"
                self.return_progress = 0
        elif self.phase == "h_return":
            self.return_progress += 0.12
            if self.return_progress >= 1:
                self.completed[self.idx()] = self.line_color()
                self.redraw_completed()
                self.x = 0
                self.return_progress = 0
                if self.mode.get() == "Progresivo":
                    if self.line_in_field < n-1:
                        self.line_in_field += 1
                    else:
                        self.phase = "v_return"
                else:
                    count = (n+1)//2 if self.field == 1 else n//2
                    if self.line_in_field < count-1:
                        self.line_in_field += 1
                    else:
                        self.phase = "v_return"
        else:
            self.return_progress += 0.08
            if self.return_progress >= 1:
                if self.mode.get() == "Entrelazado" and self.field == 1:
                    self.field = 2
                    self.line_in_field = 0
                else:
                    self.field = 1
                    self.line_in_field = 0
                    self.completed.clear()
                    self.redraw_completed()
                self.phase = "draw"
                self.x = 0
                self.return_progress = 0
        self.update_view()

    def tick(self):
        if self.running:
            self.advance()
            self.after_id = self.parent.after(max(1, 121-int(self.speed.get())), self.tick)

    def toggle(self):
        if self.running:
            self.pause()
        else:
            self.running = True
            self.play.configure(text="Ⅱ Pausar")
            self.tick()

    def pause(self):
        self.running = False
        self.play.configure(text="▶ Iniciar")
        if self.after_id:
            self.parent.after_cancel(self.after_id)
            self.after_id = None

    def step(self):
        self.pause()
        self.advance()

    def reset(self):
        self.pause()
        self.phase, self.field, self.line_in_field = "draw", 1, 0
        self.x, self.return_progress = 0, 0
        self.completed.clear()
        self.draw_base()
        self.update_view()


class ImageFormationTab:
    """Carga una imagen y la reconstruye progresivamente o por campos."""

    def __init__(self, parent):
        self.parent = parent
        self.mode = tk.StringVar(value="Progresivo")
        self.speed = tk.IntVar(value=65)
        self.keep_original_size = False
        self.source = None
        self.source_name = ""
        self.running = False
        self.after_id = None
        self.field = 1
        self.line_index = 0
        self.total_lines = 240
        self.display_w = 480
        self.display_h = 300
        self.reconstructed = None
        self.photo_original = None
        self.photo_result = None

        self.build()
        self.set_placeholder()

    def build(self):
        main = ttk.Frame(self.parent, padding=10)
        main.pack(fill="both", expand=True)

        top = ttk.Frame(main)
        top.pack(fill="x")
        ttk.Button(top, text="📂 Cargar imagen", command=self.load_image).pack(side="left")
        ttk.Label(top, text="Modo:").pack(side="left", padx=(18, 4))
        mode = ttk.Combobox(top, textvariable=self.mode,
                            values=["Progresivo", "Entrelazado"],
                            state="readonly", width=15)
        mode.pack(side="left")
        mode.bind("<<ComboboxSelected>>", self.change_mode)

        speedrow = ttk.Frame(main)
        speedrow.pack(fill="x", pady=8)
        ttk.Label(speedrow, text="Velocidad:").pack(side="left")
        ttk.Scale(speedrow, from_=1, to=100, variable=self.speed,
                  orient="horizontal").pack(side="left", fill="x", expand=True, padx=8)

        panels = ttk.Frame(main)
        panels.pack(fill="both", expand=True, pady=5)
        left = ttk.LabelFrame(panels, text="Imagen original", padding=6)
        left.pack(side="left", fill="both", expand=True, padx=(0, 6))
        right = ttk.LabelFrame(panels, text="Imagen reconstruida", padding=6)
        right.pack(side="left", fill="both", expand=True, padx=(6, 0))
        self.original_label = ttk.Label(left, anchor="center")
        self.original_label.pack(fill="both", expand=True)
        self.result_label = ttk.Label(right, anchor="center")
        self.result_label.pack(fill="both", expand=True)

        buttons = ttk.Frame(main)
        buttons.pack(fill="x", pady=8)
        self.play = ttk.Button(buttons, text="▶ Iniciar", command=self.toggle)
        self.play.pack(side="left", padx=(0, 6))
        ttk.Button(buttons, text="⏭ Siguiente línea", command=self.step).pack(side="left", padx=6)
        ttk.Button(buttons, text="↺ Reiniciar", command=self.reset).pack(side="left", padx=6)

        self.status = ttk.Label(main, font=("Segoe UI", 10, "bold"))
        self.status.pack(anchor="w", pady=(4, 2))
        ttk.Label(
            main,
            text="En progresivo se reconstruye de arriba abajo. En entrelazado, "
                 "primero aparecen las líneas impares y después las pares. "
                 "La velocidad puede cambiarse durante la animación.",
            wraplength=900, foreground="#555"
        ).pack(anchor="w")

    def set_placeholder(self):
        if Image is None:
            self.status.configure(
                text="Para cargar imágenes instala Pillow:  python -m pip install pillow"
            )
            self.original_label.configure(text="Pillow no está instalado")
            self.result_label.configure(text="Pillow no está instalado")
            return
        self.status.configure(text="Carga una imagen JPG, PNG, BMP o GIF para comenzar.")
        self.original_label.configure(text="Imagen original")
        self.result_label.configure(text="Aquí aparecerá la reconstrucción")

    def load_image(self):
        if Image is None:
            messagebox.showerror(
                "Falta Pillow",
                "Para cargar JPG, PNG o BMP instala Pillow:\n\npython -m pip install pillow"
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
            image = Image.open(filename).convert("RGB")
            image.thumbnail((self.display_w, self.display_h), Image.Resampling.LANCZOS)
            self.source = image.copy()
            self.source_name = filename
            self.display_w, self.display_h = image.size
            self.reset()
            self.photo_original = ImageTk.PhotoImage(self.source)
            self.original_label.configure(image=self.photo_original, text="")
            self.status.configure(text=f"Imagen cargada: {filename.split('/')[-1]}")
        except Exception as exc:
            messagebox.showerror("No se pudo abrir la imagen", str(exc))

    def change_mode(self, _event=None):
        self.reset()

    def reset(self):
        self.pause()
        if self.source is None:
            self.set_placeholder()
            return
        self.field, self.line_index = 1, 0
        self.total_lines = self.display_h
        self.reconstructed = Image.new("RGB", self.source.size, (0, 0, 0))
        self.refresh_result()
        self.status.configure(
            text=f"Preparado: {self.display_h} líneas de imagen | {self.mode.get()}"
        )

    def refresh_result(self):
        if self.reconstructed is not None:
            self.photo_result = ImageTk.PhotoImage(self.reconstructed)
            self.result_label.configure(image=self.photo_result, text="")

    def advance(self):
        if self.source is None or self.reconstructed is None:
            return
        width, height = self.source.size
        if self.mode.get() == "Progresivo":
            y = self.line_index
            self.reconstructed.paste(self.source.crop((0, y, width, y+1)), (0, y))
            self.line_index += 1
            if self.line_index >= height:
                self.line_index = 0
                self.reconstructed = Image.new("RGB", self.source.size, (0, 0, 0))
        else:
            y = self.line_index * 2 + (0 if self.field == 1 else 1)
            if y < height:
                self.reconstructed.paste(self.source.crop((0, y, width, y+1)), (0, y))
            count = (height+1)//2 if self.field == 1 else height//2
            self.line_index += 1
            if self.line_index >= count:
                if self.field == 1:
                    self.field = 2
                    self.line_index = 0
                else:
                    self.field = 1
                    self.line_index = 0
                    self.reconstructed = Image.new("RGB", self.source.size, (0, 0, 0))
        self.refresh_result()
        if self.mode.get() == "Entrelazado":
            self.status.configure(
                text=f"Entrelazado | Campo {self.field} | "
                     f"Línea {self.line_index+1} | {height} líneas de imagen"
            )
        else:
            self.status.configure(
                text=f"Progresivo | Línea {self.line_index} de {height}"
            )

    def tick(self):
        if self.running:
            self.advance()
            self.after_id = self.parent.after(
                max(1, 121-int(self.speed.get())), self.tick
            )

    def toggle(self):
        if self.source is None:
            messagebox.showinfo("Cargar imagen", "Primero carga una imagen.")
            return
        if self.running:
            self.pause()
        else:
            self.running = True
            self.play.configure(text="Ⅱ Pausar")
            self.tick()

    def pause(self):
        self.running = False
        self.play.configure(text="▶ Iniciar")
        if self.after_id:
            self.parent.after_cancel(self.after_id)
            self.after_id = None

    def step(self):
        self.pause()
        self.advance()



class LuminanciaCrominanciaTab:
    """Separación didáctica de una imagen RGB en Y, U y V."""

    def __init__(self, parent):
        self.parent = parent
        self.source = None
        self.source_name = ""
        self.display_size = (300, 220)
        self.photos = {}
        self.enabled_y = tk.BooleanVar(value=True)
        self.enabled_u = tk.BooleanVar(value=True)
        self.enabled_v = tk.BooleanVar(value=True)
        self.build()
        self.show_empty()

    def build(self):
        main = ttk.Frame(self.parent, padding=10)
        main.pack(fill="both", expand=True)

        top = ttk.Frame(main)
        top.pack(fill="x", pady=(0, 8))
        ttk.Button(top, text="📂 Cargar imagen", command=self.load_image).pack(side="left")
        self.filename_label = ttk.Label(top, text="Ninguna imagen cargada")
        self.filename_label.pack(side="left", padx=10)

        controls = ttk.LabelFrame(main, text="Componentes que llegan al receptor", padding=8)
        controls.pack(fill="x", pady=(0, 8))
        ttk.Checkbutton(controls, text="Y – Luminancia", variable=self.enabled_y,
                        command=self.update_reconstruction).pack(side="left", padx=8)
        ttk.Checkbutton(controls, text="U – Diferencia azul (B−Y)", variable=self.enabled_u,
                        command=self.update_reconstruction).pack(side="left", padx=8)
        ttk.Checkbutton(controls, text="V – Diferencia roja (R−Y)", variable=self.enabled_v,
                        command=self.update_reconstruction).pack(side="left", padx=8)
        ttk.Button(controls, text="Calculadora RGB → YUV", command=self.open_rgb_calculator).pack(
            side="right", padx=8
        )
        ttk.Button(controls, text="Restaurar componentes", command=self.restore_components).pack(
            side="right", padx=8
        )

        grid = ttk.Frame(main)
        grid.pack(fill="both", expand=True)
        panels = [
            ("Imagen original", "original"),
            ("Y – Luminancia", "y"),
            ("U – Crominancia B−Y", "u"),
            ("V – Crominancia R−Y", "v"),
            ("Imagen reconstruida", "result"),
        ]
        for i, (caption, key) in enumerate(panels):
            frame = ttk.LabelFrame(grid, text=caption, padding=5)
            frame.grid(row=i // 3, column=i % 3, sticky="nsew", padx=5, pady=5)
            label = ttk.Label(frame, anchor="center", text="Carga una imagen")
            label.pack(fill="both", expand=True)
            setattr(self, f"{key}_label", label)
        for col in range(3):
            grid.columnconfigure(col, weight=1)
        for row in range(2):
            grid.rowconfigure(row, weight=1)

        self.status = ttk.Label(main, font=("Segoe UI", 10, "bold"))
        self.status.pack(anchor="w", pady=(5, 3))
        explanation = (
            "Y contiene el brillo y permite ver la imagen en blanco y negro. "
            "U y V son señales de diferencia de color: sus valores pueden ser positivos o negativos. "
            "En estas vistas se representan alrededor de un gris neutro. "
            "La calculadora trabaja con tensiones de vídeo: RGB entre 0 y 0,7 V, "
            "Y en voltios y U/V como tensiones de diferencia de color."
        )
        ttk.Label(main, text=explanation, wraplength=980, foreground="#555").pack(anchor="w")

    def show_empty(self):
        self.status.configure(text="Carga una fotografía o imagen de prueba para separar Y, U y V.")

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
            image = Image.open(filename).convert("RGB")
            image.thumbnail(self.display_size, Image.Resampling.LANCZOS)
            self.source = image.copy()
            self.source_name = filename
            self.filename_label.configure(text=Path(filename).name)
            self.calculate_components()
            self.update_reconstruction()
        except Exception as exc:
            messagebox.showerror("No se pudo abrir la imagen", str(exc))

    def calculate_components(self):
        """Conversión RGB a YUV según las ecuaciones habituales de BT.601."""
        width, height = self.source.size
        y_img = Image.new("L", (width, height))
        u_img = Image.new("L", (width, height))
        v_img = Image.new("L", (width, height))
        yp, up, vp = y_img.load(), u_img.load(), v_img.load()
        pixels = self.source.load()

        for yy in range(height):
            for xx in range(width):
                r, g, b = pixels[xx, yy]
                y = 0.299 * r + 0.587 * g + 0.114 * b
                u = 0.492 * (b - y)
                v = 0.877 * (r - y)
                yp[xx, yy] = max(0, min(255, round(y)))
                # Gris neutro = 128; por encima/debajo se representa el signo.
                up[xx, yy] = max(0, min(255, round(128 + u)))
                vp[xx, yy] = max(0, min(255, round(128 + v)))

        self.y_image, self.u_image, self.v_image = y_img, u_img, v_img
        self.y_rgb = Image.merge("RGB", (y_img, y_img, y_img))
        self.u_rgb = Image.merge("RGB", (u_img, u_img, u_img))
        self.v_rgb = Image.merge("RGB", (v_img, v_img, v_img))

    def make_reconstruction(self):
        width, height = self.source.size
        result = Image.new("RGB", (width, height))
        src_y = self.y_image.load()
        src_u = self.u_image.load()
        src_v = self.v_image.load()
        out = result.load()

        use_y = self.enabled_y.get()
        use_u = self.enabled_u.get()
        use_v = self.enabled_v.get()

        for yy in range(height):
            for xx in range(width):
                y = src_y[xx, yy] if use_y else 0
                u = (src_u[xx, yy] - 128) if use_u else 0
                v = (src_v[xx, yy] - 128) if use_v else 0
                # Inversa aproximada de las ecuaciones BT.601.
                r = y + 1.140 * v
                g = y - 0.395 * u - 0.581 * v
                b = y + 2.032 * u
                out[xx, yy] = tuple(
                    max(0, min(255, round(value))) for value in (r, g, b)
                )
        return result

    def set_preview(self, key, image):
        preview = image.copy()
        preview.thumbnail(self.display_size, Image.Resampling.LANCZOS)
        photo = ImageTk.PhotoImage(preview)
        self.photos[key] = photo
        label = getattr(self, f"{key}_label")
        label.configure(image=photo, text="")
        if key == "original":
            label.bind("<Button-1>", self.select_image_pixel)
            label.configure(cursor="crosshair")

    def update_reconstruction(self):
        if self.source is None:
            return
        self.set_preview("original", self.source)
        self.set_preview("y", self.y_rgb)
        self.set_preview("u", self.u_rgb)
        self.set_preview("v", self.v_rgb)
        reconstructed = self.make_reconstruction()
        self.set_preview("result", reconstructed)

        active = []
        if self.enabled_y.get():
            active.append("Y")
        if self.enabled_u.get():
            active.append("U")
        if self.enabled_v.get():
            active.append("V")
        self.status.configure(
            text="Componentes activas: " + (" + ".join(active) if active else "ninguna")
        )

    def restore_components(self):
        self.enabled_y.set(True)
        self.enabled_u.set(True)
        self.enabled_v.set(True)
        self.update_reconstruction()


    def select_image_pixel(self, event):
        """Selecciona un píxel de la imagen original y abre su cálculo RGB/YUV."""
        if self.source is None:
            return
        label = self.original_label
        image_w, image_h = self.source.size
        # La imagen está centrada dentro del Label.
        x0 = max(0, (label.winfo_width() - image_w) // 2)
        y0 = max(0, (label.winfo_height() - image_h) // 2)
        x = event.x - x0
        y = event.y - y0
        if 0 <= x < image_w and 0 <= y < image_h:
            rgb_codes = self.source.getpixel((x, y))
            rgb_volts = tuple(channel * 0.7 / 255.0 for channel in rgb_codes)
            self.open_rgb_calculator(rgb_volts)

    def open_rgb_calculator(self, initial_rgb=(0.7, 0.0, 0.0)):
        """Calcula Y, U y V como tensiones de vídeo y muestra la recuperación RGB."""
        win = tk.Toplevel(self.parent)
        win.title("Luminancia y crominancia: cálculo en voltios")
        win.geometry("790x690")
        win.minsize(740, 640)
        win.transient(self.parent.winfo_toplevel())

        ttk.Label(
            win, text="Conversión de tensiones RGB a luminancia y crominancia",
            font=("Segoe UI", 13, "bold")
        ).pack(pady=(12, 3))
        ttk.Label(
            win,
            text="Escala didáctica de vídeo: negro = 0 V · blanco = 0,7 V",
            foreground="#555"
        ).pack(pady=(0, 8))

        values = {
            "R": tk.DoubleVar(value=float(initial_rgb[0])),
            "G": tk.DoubleVar(value=float(initial_rgb[1])),
            "B": tk.DoubleVar(value=float(initial_rgb[2]))
        }
        contribution_labels = {}
        rgb_swatch = tk.Label(win, width=18, height=2, relief="groove")
        rgb_swatch.pack(pady=3)

        input_frame = ttk.LabelFrame(win, text="1. Tensiones de entrada RGB", padding=8)
        input_frame.pack(fill="x", padx=12, pady=5)
        for channel, title in (("R", "Rojo R"), ("G", "Verde G"), ("B", "Azul B")):
            row = ttk.Frame(input_frame)
            row.pack(fill="x", pady=1)
            ttk.Label(row, text=title, width=12).pack(side="left")
            tk.Scale(
                row, from_=0.0, to=0.7, orient="horizontal", variable=values[channel],
                showvalue=True, resolution=0.01, length=300, digits=3
            ).pack(side="left", padx=5)
            contribution = ttk.Label(row, width=38, font=("Consolas", 9))
            contribution.pack(side="left", padx=5)
            contribution_labels[channel] = contribution

        tx_frame = ttk.LabelFrame(
            win, text="2. Emisor: cálculo de las componentes transmitidas (en voltios)",
            padding=8
        )
        tx_frame.pack(fill="x", padx=12, pady=5)
        tx_text = tk.Text(tx_frame, height=7, wrap="word", font=("Consolas", 10),
                          relief="flat", background="#f2f2f2")
        tx_text.pack(fill="x")
        tx_text.configure(state="disabled")

        rx_frame = ttk.LabelFrame(
            win, text="3. Receptor: recuperación de las tensiones RGB",
            padding=8
        )
        rx_frame.pack(fill="x", padx=12, pady=5)
        rx_text = tk.Text(rx_frame, height=7, wrap="word", font=("Consolas", 10),
                          relief="flat", background="#f2f2f2")
        rx_text.pack(fill="x")
        rx_text.configure(state="disabled")

        result_row = ttk.Frame(win)
        result_row.pack(fill="x", padx=14, pady=6)
        original_box = ttk.LabelFrame(result_row, text="RGB de entrada", padding=5)
        original_box.pack(side="left", expand=True, fill="x", padx=5)
        recovered_box = ttk.LabelFrame(result_row, text="RGB recuperado", padding=5)
        recovered_box.pack(side="left", expand=True, fill="x", padx=5)
        original_swatch = tk.Label(original_box, height=2, relief="sunken")
        original_swatch.pack(fill="x")
        recovered_swatch = tk.Label(recovered_box, height=2, relief="sunken")
        recovered_swatch.pack(fill="x")
        difference_label = ttk.Label(win, font=("Segoe UI", 10, "bold"))
        difference_label.pack(pady=3)

        def set_text(widget, content):
            widget.configure(state="normal")
            widget.delete("1.0", "end")
            widget.insert("1.0", content)
            widget.configure(state="disabled")

        def refresh(*_):
            r, g, b = (values[k].get() for k in ("R", "G", "B"))

            # BT.601: all quantities are now expressed in volts.
            y = 0.299 * r + 0.587 * g + 0.114 * b
            u = 0.492 * (b - y)
            v = 0.877 * (r - y)

            contribution_labels["R"].configure(text=f"0,299 × {r:.2f} V = {0.299*r:.4f} V")
            contribution_labels["G"].configure(text=f"0,587 × {g:.2f} V = {0.587*g:.4f} V")
            contribution_labels["B"].configure(text=f"0,114 × {b:.2f} V = {0.114*b:.4f} V")

            tx = (
                f"Y = 0,299·R + 0,587·G + 0,114·B = {y:.4f} V\\n"
                f"U = 0,492·(B − Y) = 0,492·({b:.3f} − {y:.4f}) = {u:+.4f} V\\n"
                f"V = 0,877·(R − Y) = 0,877·({r:.3f} − {y:.4f}) = {v:+.4f} V\\n"
                "Y es la luminancia. U y V son tensiones de diferencia de color "
                "referidas a cero crominancia."
            )
            set_text(tx_text, tx)

            rr = y + 1.140 * v
            gg = y - 0.395 * u - 0.581 * v
            bb = y + 2.032 * u
            recovered = tuple(max(0.0, min(0.7, q)) for q in (rr, gg, bb))
            rx = (
                "El receptor recupera Y, U y V y aplica la matriz inversa:\\n"
                f"R = Y + 1,140·V = {y:.4f} + 1,140·({v:+.4f}) = {rr:.4f} V\\n"
                f"G = Y − 0,395·U − 0,581·V = {y:.4f} − 0,395·({u:+.4f}) "
                f"− 0,581·({v:+.4f}) = {gg:.4f} V\\n"
                f"B = Y + 2,032·U = {y:.4f} + 2,032·({u:+.4f}) = {bb:.4f} V\\n"
                f"RGB recuperado (limitado a 0–0,7 V): "
                f"R={recovered[0]:.4f} V, G={recovered[1]:.4f} V, B={recovered[2]:.4f} V"
            )
            set_text(rx_text, rx)

            def volts_to_byte(q):
                return max(0, min(255, round(q / 0.7 * 255)))
            rgb_bytes = tuple(volts_to_byte(q) for q in (r, g, b))
            rec_bytes = tuple(volts_to_byte(q) for q in recovered)
            hex_original = "#{:02x}{:02x}{:02x}".format(*rgb_bytes)
            hex_recovered = "#{:02x}{:02x}{:02x}".format(*rec_bytes)
            rgb_swatch.configure(bg=hex_original)
            original_swatch.configure(bg=hex_original)
            recovered_swatch.configure(bg=hex_recovered)
            error = sum(abs(a-c) for a, c in zip((r, g, b), recovered))
            difference_label.configure(
                text=f"Entrada: R={r:.2f} V, G={g:.2f} V, B={b:.2f} V    "
                     f"Error total de redondeo/limitación: {error:.5f} V"
            )

        for var in values.values():
            var.trace_add("write", refresh)

        ttk.Label(
            win,
            text=("Convención: cada componente RGB se expresa entre 0 y 0,7 V, "
                  "tomando el negro como 0 V. Y, U y V salen también en voltios. "
                  "En vídeo compuesto PAL, el sincronismo se sitúa por debajo del nivel "
                  "de borrado; no forma parte de esta matriz de color."),
            wraplength=750, justify="left", foreground="#555"
        ).pack(anchor="w", padx=16, pady=8)

        ttk.Button(win, text="Cerrar", command=win.destroy).pack(pady=(0, 10))
        refresh()


class AnalogVideoLab:
    def __init__(self, root):
        root.title("Analog Video Lab")
        root.geometry("1080x850")
        root.minsize(900, 720)

        notebook = ttk.Notebook(root)
        notebook.pack(fill="both", expand=True, padx=8, pady=8)

        scan_frame = ttk.Frame(notebook)
        image_frame = ttk.Frame(notebook)
        color_frame = ttk.Frame(notebook)
        notebook.add(scan_frame, text="1. Barrido")
        notebook.add(image_frame, text="2. Formación de imagen")
        notebook.add(color_frame, text="3. Luminancia y crominancia")

        self.scan_tab = BarridoTab(scan_frame)
        self.image_tab = ImageFormationTab(image_frame)
        self.color_tab = LuminanciaCrominanciaTab(color_frame)


if __name__ == "__main__":
    root = tk.Tk()
    app = AnalogVideoLab(root)
    root.mainloop()
