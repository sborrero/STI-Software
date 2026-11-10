"""
BARRIDO DE TELEVISION - v3.2
Un solo simulador con selección de barrido progresivo o entrelazado.

- Total de líneas configurable entre 10 y 625.
- Zona visible diferenciada de los intervalos de borrado vertical.
- Progresivo/campo 1 en verde y campo 2 en amarillo.
- Retorno horizontal rojo y diagonal, desde el final de una línea al inicio de la siguiente.
- Retorno vertical rojo animado al terminar el cuadro/campo.
- Velocidad regulable durante la animación.

Modelo didáctico: el entrelazado distribuye las líneas en dos campos alternos.
La representación no pretende reproducir todos los detalles temporales de PAL.
"""

import tkinter as tk
from tkinter import ttk


class TVScanSimulator:
    def __init__(self, root):
        self.root = root
        self.root.title("Laboratorio de barrido de televisión")
        self.root.geometry("1040x800")
        self.root.minsize(880, 700)

        self.total_lines = tk.IntVar(value=10)
        self.visible_lines = tk.IntVar(value=576)
        self.mode = tk.StringVar(value="Progresivo")
        self.speed = tk.IntVar(value=65)
        self.keep_image = tk.BooleanVar(value=True)

        self.canvas_w, self.canvas_h = 820, 475
        self.mx, self.my = 70, 48
        self.sw, self.sh = self.canvas_w - 2*self.mx, self.canvas_h - 2*self.my

        self.running = False
        self.after_id = None
        self.phase = "draw"
        self.field = 1
        self.line_in_field = 0
        self.x_percent = 0.0
        self.return_progress = 0.0
        # Guarda el color de cada línea terminada: índice -> color.
        self.completed = {}

        self.build_ui()
        self.recalculate_visible()
        self.draw_base()
        self.update_view()

    def build_ui(self):
        main = ttk.Frame(self.root, padding=12)
        main.pack(fill="both", expand=True)

        ttk.Label(main, text="LABORATORIO DE BARRIDO DE TELEVISIÓN",
                  font=("Segoe UI", 17, "bold")).pack(anchor="w")
        ttk.Label(
            main,
            text="Selecciona el tipo de barrido y el número de líneas. "
                 "El marco interior representa la zona de imagen visible.",
            wraplength=970
        ).pack(anchor="w", pady=(3, 8))

        settings = ttk.LabelFrame(main, text="Configuración", padding=8)
        settings.pack(fill="x", pady=(0, 8))

        row1 = ttk.Frame(settings)
        row1.pack(fill="x", pady=3)
        ttk.Label(row1, text="Tipo de barrido:").pack(side="left")
        mode_box = ttk.Combobox(
            row1, textvariable=self.mode, values=["Progresivo", "Entrelazado"],
            state="readonly", width=16
        )
        mode_box.pack(side="left", padx=(6, 20))
        mode_box.bind("<<ComboboxSelected>>", self.configuration_changed)

        ttk.Label(row1, text="Líneas totales:").pack(side="left")
        self.total_spin = ttk.Spinbox(
            row1, from_=10, to=625, increment=1, width=7,
            textvariable=self.total_lines, command=self.configuration_changed
        )
        self.total_spin.pack(side="left", padx=6)
        self.total_spin.bind("<Return>", self.configuration_changed)
        self.total_spin.bind("<FocusOut>", self.configuration_changed)


        row2 = ttk.Frame(settings)
        row2.pack(fill="x", pady=(7, 2))
        ttk.Label(row2, text="Velocidad:").pack(side="left")
        ttk.Scale(row2, from_=1, to=100, orient="horizontal",
                  variable=self.speed).pack(side="left", fill="x", expand=True, padx=10)
        self.speed_label = ttk.Label(row2, width=18)
        self.speed_label.pack(side="right")

        self.canvas = tk.Canvas(
            main, width=self.canvas_w, height=self.canvas_h,
            bg="#101820", highlightthickness=1, highlightbackground="#52616b"
        )
        self.canvas.pack(fill="both", expand=True)

        buttons = ttk.Frame(main)
        buttons.pack(fill="x", pady=8)
        self.play_button = ttk.Button(buttons, text="▶ Iniciar", command=self.toggle)
        self.play_button.pack(side="left", padx=(0, 6))
        ttk.Button(buttons, text="⏭ Paso", command=self.step).pack(side="left", padx=6)
        ttk.Button(buttons, text="↺ Reiniciar", command=self.reset).pack(side="left", padx=6)
        ttk.Checkbutton(
            buttons, text="Conservar imagen ya barrida",
            variable=self.keep_image, command=self.redraw_completed
        ).pack(side="left", padx=14)

        self.status = ttk.Label(main, font=("Segoe UI", 10, "bold"))
        self.status.pack(anchor="w", pady=(3, 5))

        legend = ttk.Frame(main)
        legend.pack(anchor="w", pady=(0, 5))
        self.legend_item(legend, "#42e695", "Campo 1 / progresivo")
        self.legend_item(legend, "#ffd166", "Campo 2")
        self.legend_item(legend, "#ff625c", "Retorno")
        self.legend_item(legend, "#425466", "Zona no visible / borrado")

        self.explanation = ttk.Label(
            main, text="", foreground="#555", wraplength=970, justify="left"
        )
        self.explanation.pack(anchor="w", pady=(3, 0))

    @staticmethod
    def legend_item(parent, color, label):
        f = ttk.Frame(parent)
        f.pack(side="left", padx=(0, 18))
        sw = tk.Canvas(f, width=24, height=12, highlightthickness=0)
        sw.pack(side="left", padx=(0, 5))
        sw.create_line(1, 6, 23, 6, fill=color, width=3)
        ttk.Label(f, text=label).pack(side="left")

    def clamp_settings(self):
        try:
            total = max(10, min(625, int(self.total_lines.get())))
        except (ValueError, tk.TclError):
            total = 625
        self.total_lines.set(total)

        try:
            visible = int(self.visible_lines.get())
        except (ValueError, tk.TclError):
            visible = round(total * 576 / 625)
        visible = max(1, min(total, visible))
        self.visible_lines.set(visible)

    def recalculate_visible(self):
        self.clamp_settings()
        # Si el usuario modifica el total, la zona visible se ajusta a la
        # proporción PAL 576/625. En la configuración inicial: 576 de 625.
        total = self.total_lines.get()
        self.visible_lines.set(max(1, min(total, round(total * 576 / 625))))

    def configuration_changed(self, _event=None):
        self.pause()
        self.recalculate_visible()
        self.reset()

    def visible_bounds(self):
        total = self.total_lines.get()
        visible = self.visible_lines.get()
        blank = total - visible
        top_blank = blank // 2
        first = top_blank
        last = first + visible - 1
        return first, last

    def actual_line_index(self):
        if self.mode.get() == "Progresivo":
            return self.line_in_field
        # Campo 1: índices 0,2,4...; campo 2: índices 1,3,5...
        return self.line_in_field * 2 + (0 if self.field == 1 else 1)

    def line_y(self, index):
        return self.my + index * self.sh / max(1, self.total_lines.get() - 1)

    def draw_base(self):
        c = self.canvas
        c.delete("all")
        x0, y0, x1, y1 = self.mx, self.my, self.mx+self.sw, self.my+self.sh

        first, last = self.visible_bounds()
        top_y = self.line_y(first)
        bottom_y = self.line_y(last)

        # Bandas exteriores = intervalos de borrado vertical / líneas no visibles.
        c.create_rectangle(x0, y0, x1, top_y, fill="#263541", outline="")
        c.create_rectangle(x0, bottom_y, x1, y1, fill="#263541", outline="")
        c.create_rectangle(x0, y0, x1, y1, outline="#aab7b8", width=2)
        c.create_rectangle(x0, top_y, x1, bottom_y,
                           outline="#e6edf0", width=2, dash=(5, 3))

        c.create_text(x0+5, y0+5, text="BORRADO VERTICAL",
                      fill="#b8c6cc", anchor="nw", font=("Segoe UI", 8))
        c.create_text(x0+5, top_y+5, text="ZONA DE IMAGEN VISIBLE",
                      fill="#e6edf0", anchor="nw", font=("Segoe UI", 8, "bold"))
        c.create_text(x0+5, bottom_y+5, text="BORRADO VERTICAL",
                      fill="#b8c6cc", anchor="nw", font=("Segoe UI", 8))

        self.completed_items = {}
        self.active_line = c.create_line(x0, y0, x0, y0,
                                          fill="#42e695", width=2, state="hidden")
        self.h_return = c.create_line(x0, y0, x0, y0,
                                      fill="#ff625c", width=3, state="hidden")
        self.v_return = c.create_line(x0, y0, x0, y0,
                                      fill="#ff625c", width=4, state="hidden")
        self.beam = c.create_oval(0, 0, 0, 0, fill="#ffe45c",
                                  outline="white", width=1)

    def line_color(self):
        # En progresivo solo hay un tipo de línea. En entrelazado,
        # cada campo conserva un color distinto para que no se confundan.
        if self.mode.get() == "Entrelazado" and self.field == 2:
            return "#ffd166"  # amarillo: segundo campo (líneas pares)
        return "#42e695"      # verde: progresivo o primer campo (impares)

    def redraw_completed(self):
        for item in self.completed_items.values():
            self.canvas.delete(item)
        self.completed_items.clear()
        if self.keep_image.get():
            for idx, color in sorted(self.completed.items()):
                y = self.line_y(idx)
                self.completed_items[idx] = self.canvas.create_line(
                    self.mx, y, self.mx+self.sw, y, fill=color, width=2
                )

    def interval_ms(self):
        return max(1, int(121 - self.speed.get()))

    def current_line_number(self):
        return self.actual_line_index() + 1

    def update_view(self):
        idx = min(self.total_lines.get()-1, self.actual_line_index())
        y = self.line_y(idx)
        x = self.mx + self.x_percent/100*self.sw
        for item in (self.active_line, self.h_return, self.v_return):
            self.canvas.itemconfigure(item, state="hidden")

        beam_x, beam_y = x, y
        if self.phase == "draw":
            self.canvas.coords(self.active_line, self.mx, y, x, y)
            self.canvas.itemconfigure(
                self.active_line, fill=self.line_color(), state="normal"
            )
        elif self.phase == "h_return":
            # El retorno rojo une el final de esta línea con el inicio de la
            # siguiente. Es diagonal y no pasa por encima de la línea recién pintada.
            p = self.return_progress
            current_idx = self.actual_line_index()
            line_step = 2 if self.mode.get() == "Entrelazado" else 1
            next_idx = min(self.total_lines.get() - 1, current_idx + line_step)
            next_y = self.line_y(next_idx)
            x_start = self.mx + self.sw
            y_start = y
            x_end = self.mx
            y_end = next_y
            cur_x = x_start + (x_end-x_start)*p
            cur_y = y_start + (y_end-y_start)*p
            self.canvas.coords(self.h_return, x_start, y_start, cur_x, cur_y)
            self.canvas.itemconfigure(self.h_return, state="normal")
            beam_x, beam_y = cur_x, cur_y
        elif self.phase == "v_return":
            p = self.return_progress
            # Retorno rojo desde la parte inferior hasta el comienzo del cuadro.
            cur_x = self.mx + self.sw*(1-p)
            cur_y = self.my + self.sh*(1-p)
            self.canvas.coords(self.v_return,
                               self.mx+self.sw, self.my+self.sh, cur_x, cur_y)
            self.canvas.itemconfigure(self.v_return, state="normal")
            beam_x, beam_y = cur_x, cur_y

        r = 5
        self.canvas.coords(self.beam, beam_x-r, beam_y-r, beam_x+r, beam_y+r)

        if self.mode.get() == "Progresivo":
            mode_text = "Progresivo"
            field_text = ""
        else:
            mode_text = "Entrelazado"
            field_text = f" | Campo {self.field}"

        phase_text = {
            "draw": "Barrido visible",
            "h_return": "Retorno horizontal (rojo)",
            "v_return": "Retorno vertical (rojo)",
        }[self.phase]
        first, last = self.visible_bounds()
        visible_now = first <= idx <= last
        zone_text = "zona visible" if visible_now else "intervalo de borrado"
        self.status.configure(
            text=f"{mode_text}{field_text} | Línea {idx+1}/{self.total_lines.get()} "
                 f"| {zone_text} | {phase_text}"
        )
        self.explanation.configure(
            text=f"Configuración: {self.total_lines.get()} líneas totales, "
                 f"{self.visible_lines.get()} visibles y "
                 f"{self.total_lines.get()-self.visible_lines.get()} no visibles. "
                 "El marco discontinuo delimita la zona visible; las bandas "
                 "oscuras representan el borrado vertical."
        )

    def advance(self):
        if self.phase == "draw":
            self.x_percent += 5
            if self.x_percent >= 100:
                self.x_percent = 100
                self.phase = "h_return"
                self.return_progress = 0.0

        elif self.phase == "h_return":
            self.return_progress += 0.12
            if self.return_progress >= 1:
                idx = self.actual_line_index()
                self.completed[idx] = self.line_color()
                self.redraw_completed()
                self.x_percent = 0
                self.return_progress = 0

                if self.mode.get() == "Progresivo":
                    if self.line_in_field < self.total_lines.get()-1:
                        self.line_in_field += 1
                        self.phase = "draw"
                    else:
                        self.phase = "v_return"
                else:
                    field_count = ((self.total_lines.get() + 1) // 2 if self.field == 1 else self.total_lines.get() // 2)
                    if self.line_in_field < field_count-1:
                        self.line_in_field += 1
                        self.phase = "draw"
                    else:
                        self.phase = "v_return"
                        self.return_progress = 0

        elif self.phase == "v_return":
            self.return_progress += 0.08
            if self.return_progress >= 1:
                if self.mode.get() == "Entrelazado" and self.field == 1:
                    self.field = 2
                    self.line_in_field = 0
                    self.phase = "draw"
                else:
                    self.field = 1
                    self.line_in_field = 0
                    self.completed.clear()
                    self.redraw_completed()
                    self.phase = "draw"
                self.x_percent = 0
                self.return_progress = 0

        self.update_view()

    def tick(self):
        if not self.running:
            return
        self.advance()
        self.after_id = self.root.after(self.interval_ms(), self.tick)

    def toggle(self):
        if self.running:
            self.pause()
        else:
            self.running = True
            self.play_button.configure(text="Ⅱ Pausar")
            self.tick()

    def pause(self):
        self.running = False
        self.play_button.configure(text="▶ Iniciar")
        if self.after_id is not None:
            self.root.after_cancel(self.after_id)
            self.after_id = None

    def step(self):
        self.pause()
        self.advance()

    def reset(self):
        self.pause()
        self.phase = "draw"
        self.field = 1
        self.line_in_field = 0
        self.x_percent = 0
        self.return_progress = 0
        self.completed.clear()
        self.draw_base()
        self.update_view()



if __name__ == "__main__":
    root = tk.Tk()
    app = TVScanSimulator(root)
    root.mainloop()
