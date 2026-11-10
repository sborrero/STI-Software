"""
DIGITAL VIDEO LAB - MÓDULO 2: MUESTREO Y RESOLUCIÓN
Herramienta didáctica para visualizar el muestreo espacial de una imagen.

Dependencia:
    python -m pip install pillow
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path

try:
    from PIL import Image, ImageTk, ImageDraw
except ImportError:
    Image = ImageTk = ImageDraw = None


class SamplingResolutionLab:
    def __init__(self, root):
        self.root = root
        self.image = None
        self.preview_refs = {}
        root.title("Digital Video Lab - Muestreo y resolución")
        root.geometry("1120x820")
        root.minsize(940, 700)

        main = ttk.Frame(root, padding=10)
        main.pack(fill="both", expand=True)

        top = ttk.Frame(main)
        top.pack(fill="x", pady=(0, 8))
        ttk.Button(top, text="Cargar imagen", command=self.load_image).pack(side="left")
        self.filename = ttk.Label(top, text="Ninguna imagen cargada")
        self.filename.pack(side="left", padx=10)

        controls = ttk.LabelFrame(main, text="Muestreo espacial: elegir número de píxeles", padding=10)
        controls.pack(fill="x", pady=5)

        row1 = ttk.Frame(controls)
        row1.pack(fill="x")
        ttk.Label(row1, text="Resolución horizontal:").pack(side="left")
        self.width_var = tk.IntVar(value=160)
        ttk.Spinbox(row1, from_=8, to=7680, increment=8,
                    textvariable=self.width_var, width=9).pack(side="left", padx=6)
        ttk.Label(row1, text="Resolución vertical:").pack(side="left", padx=(18, 3))
        self.height_var = tk.IntVar(value=90)
        ttk.Spinbox(row1, from_=8, to=4320, increment=8,
                    textvariable=self.height_var, width=9).pack(side="left", padx=6)
        ttk.Button(row1, text="Aplicar muestreo", command=self.apply_sampling).pack(side="left", padx=12)
        ttk.Button(row1, text="Comparar SD / HD / Full HD / UHD",
                   command=self.compare_standards).pack(side="left", padx=8)

        row2 = ttk.Frame(controls)
        row2.pack(fill="x", pady=(8, 0))
        ttk.Label(row2, text="Visualización:").pack(side="left")
        self.view_mode = tk.StringVar(value="Píxeles visibles")
        ttk.Combobox(
            row2, textvariable=self.view_mode, state="readonly", width=20,
            values=["Píxeles visibles", "Imagen suavizada"]
        ).pack(side="left", padx=6)
        ttk.Button(row2, text="Mostrar cuadrícula", command=self.toggle_grid).pack(side="left", padx=8)
        self.grid_on = False

        panels = ttk.Frame(main)
        panels.pack(fill="both", expand=True, pady=8)

        self.original_label = self.make_panel(panels, "Imagen original")
        self.sampled_label = self.make_panel(panels, "Imagen muestreada")
        self.zoom_label = self.make_panel(panels, "Ampliación de la imagen muestreada")

        self.original_label.master.pack(side="left", fill="both", expand=True, padx=4)
        self.sampled_label.master.pack(side="left", fill="both", expand=True, padx=4)
        self.zoom_label.master.pack(side="left", fill="both", expand=True, padx=4)

        self.info = ttk.Label(main, text="Carga una imagen para comenzar.",
                              font=("Segoe UI", 10, "bold"))
        self.info.pack(anchor="w", pady=5)

        ttk.Label(
            main,
            text=(
                "Muestrear una imagen significa tomar muestras de ella en una cuadrícula. "
                "Cada muestra se convierte en un píxel. Cuantos más píxeles se utilizan, "
                "mayor es la resolución espacial y más detalles pueden representarse. "
                "La resolución no debe confundirse con la profundidad de color."
            ),
            wraplength=1060, foreground="#555"
        ).pack(anchor="w", pady=5)

    def make_panel(self, parent, title):
        frame = ttk.LabelFrame(parent, text=title, padding=5, width=350, height=390)
        frame.pack_propagate(False)
        label = ttk.Label(frame, text="Carga una imagen", anchor="center")
        label.pack(fill="both", expand=True)
        return label

    def load_image(self):
        if Image is None:
            messagebox.showerror(
                "Falta Pillow",
                "Instala Pillow desde PowerShell:\n\npython -m pip install pillow"
            )
            return
        filename = filedialog.askopenfilename(
            title="Seleccionar imagen",
            filetypes=[
                ("Imágenes", "*.jpg *.jpeg *.png *.bmp *.gif"),
                ("Todos los archivos", "*.*")
            ]
        )
        if not filename:
            return
        try:
            self.image = Image.open(filename).convert("RGB")
            self.filename.configure(text=Path(filename).name)
            self.width_var.set(self.image.width)
            self.height_var.set(self.image.height)
            self.apply_sampling()
        except Exception as exc:
            messagebox.showerror("No se pudo abrir la imagen", str(exc))

    def display(self, key, label, image, size=(330, 340)):
        preview = image.copy()
        preview.thumbnail(size, Image.Resampling.NEAREST)
        photo = ImageTk.PhotoImage(preview)
        self.preview_refs[key] = photo
        label.configure(image=photo, text="")

    def compare_standards(self):
        """Comparativa de resolución, relación de aspecto y tamaño sin comprimir."""
        if self.image is None:
            messagebox.showinfo("Falta imagen", "Carga primero una imagen.")
            return

        win = tk.Toplevel(self.root)
        win.title("Comparativa de resoluciones de televisión")
        win.geometry("1160x900")
        win.minsize(1000, 760)
        win.transient(self.root)

        ttk.Label(
            win, text="Comparativa de resolución espacial",
            font=("Segoe UI", 14, "bold")
        ).pack(pady=(10, 2))

        controls = ttk.Frame(win)
        controls.pack(fill="x", padx=12, pady=5)

        ttk.Label(controls, text="Experimento:").pack(side="left")
        experiment = tk.StringVar(value="Usar resolución original")
        selector = ttk.Combobox(
            controls, textvariable=experiment, state="readonly", width=30,
            values=[
                "Usar resolución original",
                "Simular una fuente SD (720 × 576)"
            ]
        )
        selector.pack(side="left", padx=5)

        ttk.Label(controls, text="Presentación SD:").pack(side="left", padx=(14, 3))
        sd_aspect = tk.StringVar(value="4:3")
        aspect_selector = ttk.Combobox(
            controls, textvariable=sd_aspect, state="readonly", width=7,
            values=["4:3", "16:9"]
        )
        aspect_selector.pack(side="left", padx=4)

        ttk.Label(
            win,
            text="Tamaño teórico de imagen sin comprimir, suponiendo RGB de 8 bits por componente (24 bits/píxel).",
            foreground="#555"
        ).pack(pady=(0, 3))

        source_label = ttk.Label(win, text="", foreground="#555")
        source_label.pack(pady=(0, 5))

        standards = [
            ("SD (PAL)", 720, 576),
            ("HD", 1280, 720),
            ("Full HD", 1920, 1080),
            ("UHD (4K)", 3840, 2160),
        ]

        cards = ttk.Frame(win, padding=6)
        cards.pack(fill="both", expand=True)
        for col in range(4):
            cards.columnconfigure(col, weight=1)

        card_widgets = []
        for col, (name, w, h) in enumerate(standards):
            card = ttk.LabelFrame(cards, text=name, padding=6)
            card.grid(row=0, column=col, sticky="nsew", padx=4, pady=4)

            whole_label = ttk.Label(card)
            whole_label.pack(pady=(3, 4))
            resolution_label = ttk.Label(card, font=("Segoe UI", 10, "bold"))
            resolution_label.pack()
            pixels_label = ttk.Label(card)
            pixels_label.pack()
            aspect_label = ttk.Label(card, foreground="#555")
            aspect_label.pack()
            size_label = ttk.Label(card, font=("Segoe UI", 9, "bold"))
            size_label.pack(pady=(3, 1))
            crop_label = ttk.Label(card)
            crop_label.pack(pady=(7, 2))
            ttk.Label(card, text="Ampliación del 10 % central",
                      foreground="#555").pack(pady=(0, 5))
            card_widgets.append(
                (whole_label, resolution_label, pixels_label, aspect_label, size_label, crop_label)
            )

        warning = ttk.Label(
            win, text="", wraplength=1090, justify="left",
            foreground="#9a4b00"
        )
        warning.pack(anchor="w", padx=14, pady=7)

        def render(*_):
            if experiment.get().startswith("Simular"):
                source = self.image.resize((720, 576), Image.Resampling.LANCZOS)
                source_w, source_h = source.size
                note = (
                    "Fuente simulada: 720 × 576. Las salidas HD, Full HD y UHD "
                    "se amplían a partir de esta misma fuente SD."
                )
            else:
                source = self.image
                source_w, source_h = source.size
                note = f"Fuente original: {source_w} × {source_h}."

            source_label.configure(
                text=f"{note}  ({source_w*source_h:,} píxeles)"
            )

            for (name, w, h), widgets in zip(standards, card_widgets):
                whole_label, resolution_label, pixels_label, aspect_label, size_label, crop_label = widgets
                sampled = source.resize((w, h), Image.Resampling.BOX)

                # Display aspect ratio: PAL raster can be presented as 4:3 or 16:9.
                display_ratio = (4 / 3) if (name == "SD (PAL)" and sd_aspect.get() == "4:3") else (16 / 9)
                display_h = int(w / display_ratio)
                display_image = sampled.resize((w, display_h), Image.Resampling.BILINEAR)
                display_image.thumbnail((235, 145), Image.Resampling.LANCZOS)
                whole_photo = ImageTk.PhotoImage(display_image)
                whole_label.configure(image=whole_photo)
                whole_label.image = whole_photo

                pixel_count = w * h
                raw_bytes = pixel_count * 3  # RGB 24-bit
                if raw_bytes >= 1_000_000_000:
                    data_text = f"{raw_bytes / 1_000_000_000:.3f} GB"
                else:
                    data_text = f"{raw_bytes / 1_000_000:.2f} MB"

                resolution_label.configure(text=f"{w:,} × {h:,}".replace(",", "."))
                pixels_label.configure(text=f"{pixel_count:,} píxeles".replace(",", "."))
                aspect_label.configure(
                    text=f"Presentación: {display_ratio:.2f}:1".replace(".", ",")
                )
                size_label.configure(text=f"RGB 24 bits: {data_text}")

                # Same central 10% raster crop, enlarged using nearest-neighbour.
                crop_w, crop_h = max(1, w // 10), max(1, h // 10)
                left, top = (w - crop_w) // 2, (h - crop_h) // 2
                crop = sampled.crop((left, top, left + crop_w, top + crop_h))
                zoom = crop.resize((235, 145), Image.Resampling.NEAREST)
                crop_photo = ImageTk.PhotoImage(zoom)
                crop_label.configure(image=crop_photo)
                crop_label.image = crop_photo

            if experiment.get().startswith("Simular"):
                warning.configure(
                    text=(
                        "OBSERVA: aunque HD, Full HD y UHD tienen más píxeles de salida, "
                        "todos parten de la misma fuente SD. La interpolación no recupera "
                        "detalle perdido. El tamaño indicado es de imagen RGB sin comprimir; "
                        "un vídeo comprimido ocupa mucho menos y depende del códec y bitrate."
                    )
                )
            else:
                warning.configure(
                    text=(
                        "La relación de aspecto describe la forma de presentación, no el número "
                        "de píxeles. SD PAL almacena 720 × 576 muestras y puede mostrarse en 4:3 "
                        "o 16:9 mediante píxeles no cuadrados. Los tamaños indicados son datos "
                        "de imagen sin comprimir, no tamaños de archivo de vídeo."
                    )
                )

        selector.bind("<<ComboboxSelected>>", render)
        aspect_selector.bind("<<ComboboxSelected>>", render)
        render()
        ttk.Button(win, text="Cerrar", command=win.destroy).pack(pady=(0, 10))

    def toggle_grid(self):
        self.grid_on = not self.grid_on
        if self.image is not None:
            self.apply_sampling()

    def apply_sampling(self):
        if self.image is None:
            messagebox.showinfo("Falta imagen", "Carga primero una imagen.")
            return
        try:
            w, h = int(self.width_var.get()), int(self.height_var.get())
            if not (1 <= w <= 7680 and 1 <= h <= 4320):
                raise ValueError("Introduce una resolución válida.")
            # First reduce to the selected number of spatial samples.
            small = self.image.resize((w, h), Image.Resampling.BOX)

            if self.view_mode.get() == "Imagen suavizada":
                shown = small.resize(self.image.size, Image.Resampling.BILINEAR)
            else:
                shown = small.resize(self.image.size, Image.Resampling.NEAREST)

            if self.grid_on:
                shown = shown.copy()
                draw = ImageDraw.Draw(shown)
                # Draw a visible grid only when it remains readable.
                step_x = max(1, self.image.width // min(w, 40))
                step_y = max(1, self.image.height // min(h, 30))
                for x in range(0, self.image.width, step_x):
                    draw.line((x, 0, x, self.image.height), fill=(90, 90, 90), width=1)
                for y in range(0, self.image.height, step_y):
                    draw.line((0, y, self.image.width, y), fill=(90, 90, 90), width=1)

            zoom = small.resize((min(600, w * 5), min(500, h * 5)), Image.Resampling.NEAREST)
            self.display("original", self.original_label, self.image)
            self.display("sampled", self.sampled_label, shown)
            self.display("zoom", self.zoom_label, zoom)

            ow, oh = self.image.size
            original_pixels = ow * oh
            new_pixels = w * h
            ratio = new_pixels / original_pixels * 100
            self.info.configure(
                text=(
                    f"Original: {ow} × {oh} = {original_pixels:,} píxeles     "
                    f"Muestreo: {w} × {h} = {new_pixels:,} píxeles     "
                    f"Muestras respecto al original: {ratio:.2f}%"
                )
            )
        except Exception as exc:
            messagebox.showerror("Parámetros no válidos", str(exc))


def main():
    root = tk.Tk()
    SamplingResolutionLab(root)
    root.mainloop()


if __name__ == "__main__":
    main()
