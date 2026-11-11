import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Calculadora RT60 · STI", page_icon="🔊", layout="wide")
BASE = Path(__file__).resolve().parent
FREQS = ["125", "250", "500", "1000", "2000", "4000"]
BANDS = ["125 Hz", "250 Hz", "500 Hz", "1 kHz", "2 kHz", "4 kHz"]

@st.cache_data
def load_database():
    with open(BASE / "database.json", "r", encoding="utf-8") as f:
        db = json.load(f)
    return pd.DataFrame(db["materials"]), pd.DataFrame(db["rooms"])

materials, rooms = load_database()
material_names = materials["selector"].tolist()
material_lookup = materials.set_index("selector")
def pick(prefix, fallback=None):
    return next((n for n in material_names if n.lower().startswith(prefix.lower())), fallback or material_names[0])

wall_default = pick("Hormigón normal")
floor_default = pick("Hormigón normal")
ceiling_default = pick("Techo")
glass_default = pick("Vidrio de ventana normal")
door_default = pick("Madera ordinaria")
occupant_default = pick("Pupitre y silla de madera con alumno")

st.title("🔊 Calculadora de tiempo de reverberación RT60")
st.caption("STI · Cálculo por bandas de octava · Base de datos de materiales del Excel")

t1, t2, t3, t4, t5, t6 = st.tabs(["1 · Recinto", "2 · Paredes y huecos", "3 · Suelo, techo y otros", "4 · Personas y elementos", "5 · Resultados", "6 · Base de datos"])

with t1:
    room_types = rooms["tipo"].tolist()
    default_type = "Aula de enseñanza secundaria o FP"
    room_type = st.selectbox("Tipo de recinto", room_types, index=room_types.index(default_type) if default_type in room_types else 0)
    room_info = rooms.loc[rooms["tipo"] == room_type].iloc[0]
    st.info(f"**Objetivo acústico:** {room_info['objetivo']}  \n**RT60 orientativo:** {room_info['tr']}")
    c1, c2, c3 = st.columns(3)
    length = c1.number_input("Longitud del recinto (m)", min_value=0.5, value=10.0, step=0.5)
    width = c2.number_input("Anchura del recinto (m)", min_value=0.5, value=8.0, step=0.5)
    height = c3.number_input("Altura (m)", min_value=0.5, value=3.0, step=0.1)
    volume = length * width * height
    st.metric("Volumen", f"{volume:.2f} m³")
    if st.button("Generar geometría inicial", type="primary"):
        st.session_state["walls"] = pd.DataFrame([
            {"Pared": "Pared larga 1", "Largo (m)": length, "Alto (m)": height, "Material": wall_default},
            {"Pared": "Pared larga 2", "Largo (m)": length, "Alto (m)": height, "Material": wall_default},
            {"Pared": "Pared corta 1", "Largo (m)": width, "Alto (m)": height, "Material": wall_default},
            {"Pared": "Pared corta 2", "Largo (m)": width, "Alto (m)": height, "Material": wall_default},
        ])
        st.session_state["openings"] = pd.DataFrame([
            {"Tipo": "Ventana", "Pared": "Pared larga 1", "Cantidad": 0, "Ancho (m)": 1.2, "Alto (m)": 1.2, "Material": glass_default},
            {"Tipo": "Puerta", "Pared": "Pared larga 1", "Cantidad": 0, "Ancho (m)": 0.9, "Alto (m)": 2.1, "Material": door_default},
        ])
        st.session_state["other_surfaces"] = pd.DataFrame([
            {"Elemento": "Techo", "Cantidad": 1, "Largo (m)": length, "Ancho (m)": width, "Material": ceiling_default},
            {"Elemento": "Suelo", "Cantidad": 1, "Largo (m)": length, "Ancho (m)": width, "Material": floor_default},
        ])
        st.success("Geometría inicial creada. Puedes modificarla en las pestañas siguientes.")

with t2:
    st.subheader("Paredes: largo, alto y material")
    if "walls" not in st.session_state:
        st.session_state["walls"] = pd.DataFrame([
            {"Pared": "Pared larga 1", "Largo (m)": 10.0, "Alto (m)": 3.0, "Material": wall_default},
            {"Pared": "Pared larga 2", "Largo (m)": 10.0, "Alto (m)": 3.0, "Material": wall_default},
            {"Pared": "Pared corta 1", "Largo (m)": 8.0, "Alto (m)": 3.0, "Material": wall_default},
            {"Pared": "Pared corta 2", "Largo (m)": 8.0, "Alto (m)": 3.0, "Material": wall_default},
        ])
    walls = st.data_editor(
        st.session_state["walls"], key="walls_v04", num_rows="dynamic",
        width="stretch", hide_index=True,
        column_config={
            "Pared": st.column_config.TextColumn("Identificación", required=True),
            "Largo (m)": st.column_config.NumberColumn("Largo (m)", min_value=0.0, step=0.1, required=True),
            "Alto (m)": st.column_config.NumberColumn("Alto (m)", min_value=0.0, step=0.1, required=True),
            "Material": st.column_config.SelectboxColumn("Material de pared", options=material_names, required=True),
        })
    st.session_state["walls"] = walls
    wall_names = walls["Pared"].fillna("").tolist()
    st.divider()
    st.subheader("Ventanas, puertas y otros huecos")
    st.write("Introduce ancho y alto, no la superficie. La aplicación calcula el área y la descuenta de la pared indicada. El hueco se añade después con su propio material.")
    if "openings" not in st.session_state:
        st.session_state["openings"] = pd.DataFrame([
            {"Tipo": "Ventana", "Pared": wall_names[0] if wall_names else "", "Cantidad": 0, "Ancho (m)": 1.2, "Alto (m)": 1.2, "Material": glass_default},
            {"Tipo": "Puerta", "Pared": wall_names[0] if wall_names else "", "Cantidad": 0, "Ancho (m)": 0.9, "Alto (m)": 2.1, "Material": door_default},
        ])
    openings = st.data_editor(
        st.session_state["openings"], key="openings_v04", num_rows="dynamic",
        width="stretch", hide_index=True,
        column_config={
            "Tipo": st.column_config.SelectboxColumn("Tipo", options=["Ventana", "Puerta", "Hueco / otro"], required=True),
            "Pared": st.column_config.SelectboxColumn("Pared donde está", options=wall_names, required=True),
            "Cantidad": st.column_config.NumberColumn("Cantidad", min_value=0.0, step=1.0, required=True),
            "Ancho (m)": st.column_config.NumberColumn("Ancho (m)", min_value=0.0, step=0.1, required=True),
            "Alto (m)": st.column_config.NumberColumn("Alto (m)", min_value=0.0, step=0.1, required=True),
            "Material": st.column_config.SelectboxColumn("Material propio", options=material_names, required=True),
        })
    st.session_state["openings"] = openings
    # Live preview of gross, opening and net areas by wall.
    preview = []
    for _, w in walls.iterrows():
        gross = max(0, float(w["Largo (m)"] or 0) * float(w["Alto (m)"] or 0))
        deducted = 0.0
        for _, op in openings.iterrows():
            if op.get("Pared") == w.get("Pared"):
                deducted += max(0, float(op["Cantidad"] or 0) * float(op["Ancho (m)"] or 0) * float(op["Alto (m)"] or 0))
        preview.append({"Pared": w["Pared"], "Área bruta (m²)": gross, "Huecos (m²)": deducted, "Pared neta (m²)": gross-deducted})
    st.markdown("**Comprobación de superficies netas**")
    st.dataframe(pd.DataFrame(preview), width="stretch", hide_index=True)
    if any(x["Pared neta (m²)"] < -1e-8 for x in preview):
        st.error("Hay huecos cuya superficie total supera la superficie de alguna pared. Revisa las dimensiones y cantidades.")

    st.markdown("**Esquema cenital del recinto**")
    st.caption("Esquema orientativo: las ventanas y puertas de cada fila se distribuyen automáticamente y de forma uniforme a lo largo de la pared seleccionada. La posición vertical no se representa.")
    if len(walls) >= 4:
        fig, ax = plt.subplots(figsize=(8, 5))
        # The first four walls define the room perimeter: top, bottom, left, right.
        wall_specs = [
            (walls.iloc[0], (0, width), (length, width)),
            (walls.iloc[1], (0, 0), (length, 0)),
            (walls.iloc[2], (0, 0), (0, width)),
            (walls.iloc[3], (length, 0), (length, width)),
        ]
        for wi, (wr, p1, p2) in enumerate(wall_specs):
            ax.plot([p1[0], p2[0]], [p1[1], p2[1]], color="black", linewidth=5, solid_capstyle="butt")
            ax.text((p1[0]+p2[0])/2, (p1[1]+p2[1])/2, str(wr["Pared"]), fontsize=8,
                    ha="center", va="bottom" if wi < 2 else "center",
                    bbox={"facecolor":"white","alpha":0.8,"edgecolor":"none"})
        for _, op in openings.iterrows():
            wall_name = op.get("Pared")
            idxs = [i for i, wname in enumerate(walls["Pared"].tolist()) if wname == wall_name]
            if not idxs:
                continue
            idx = idxs[0]
            n = max(0, int(float(op.get("Cantidad", 0) or 0)))
            opening_width = max(0.0, float(op.get("Ancho (m)", 0) or 0))
            wall_length = float(walls.iloc[idx].get("Largo (m)", 0) or 0)
            # Reparto uniforme: mismo hueco entre extremos y entre aberturas.
            gap = max(0.0, (wall_length - n * opening_width) / (n + 1)) if n else 0.0
            for k in range(n):
                pos = gap + k * (opening_width + gap)
                color = "#2878B5" if op.get("Tipo") == "Ventana" else "#D97706"
                if idx == 0:
                    ax.plot([pos, pos+opening_width], [width, width], color=color, linewidth=7, solid_capstyle="butt")
                    tx, ty = pos+opening_width/2, width+0.18
                elif idx == 1:
                    ax.plot([pos, pos+opening_width], [0, 0], color=color, linewidth=7, solid_capstyle="butt")
                    tx, ty = pos+opening_width/2, -0.25
                elif idx == 2:
                    ax.plot([0, 0], [pos, pos+opening_width], color=color, linewidth=7, solid_capstyle="butt")
                    tx, ty = -0.25, pos+opening_width/2
                else:
                    ax.plot([length, length], [pos, pos+opening_width], color=color, linewidth=7, solid_capstyle="butt")
                    tx, ty = length+0.25, pos+opening_width/2
                ax.text(tx, ty, "V" if op.get("Tipo") == "Ventana" else "P", fontsize=8, ha="center", va="center")
        ax.set_aspect("equal")
        ax.set_xlim(-0.8, length+0.8)
        ax.set_ylim(-0.8, width+0.8)
        ax.set_xlabel("Longitud (m)")
        ax.set_ylabel("Anchura (m)")
        ax.set_title("Planta esquemática · V = ventana · P = puerta")
        ax.grid(True, alpha=.2)
        st.pyplot(fig, width="stretch")
        plt.close(fig)
    else:
        st.info("Para dibujar el perímetro se necesitan las cuatro paredes principales.")

with t3:
    st.subheader("Suelo, techo y otras superficies")
    st.write("También se introducen mediante dimensiones. Puedes añadir elementos como tarimas, paneles, mamparas o revestimientos; cada fila tiene su material.")
    if "other_surfaces" not in st.session_state:
        st.session_state["other_surfaces"] = pd.DataFrame([
            {"Elemento": "Techo", "Cantidad": 1, "Largo (m)": 10.0, "Ancho (m)": 8.0, "Material": ceiling_default},
            {"Elemento": "Suelo", "Cantidad": 1, "Largo (m)": 10.0, "Ancho (m)": 8.0, "Material": floor_default},
        ])
    other = st.data_editor(
        st.session_state["other_surfaces"], key="other_v04", num_rows="dynamic",
        width="stretch", hide_index=True,
        column_config={
            "Elemento": st.column_config.TextColumn("Elemento", required=True),
            "Cantidad": st.column_config.NumberColumn("Cantidad", min_value=0.0, step=1.0, required=True),
            "Largo (m)": st.column_config.NumberColumn("Largo (m)", min_value=0.0, step=0.1, required=True),
            "Ancho (m)": st.column_config.NumberColumn("Ancho (m)", min_value=0.0, step=0.1, required=True),
            "Material": st.column_config.SelectboxColumn("Material", options=material_names, required=True),
        })
    st.session_state["other_surfaces"] = other

with t4:
    st.subheader("Personas, asientos y elementos discretos")
    st.write("Selecciona cada elemento de la base de datos. La absorción por unidad se multiplica por la cantidad.")
    if "discrete" not in st.session_state:
        st.session_state["discrete"] = pd.DataFrame([
            {"Elemento": "Alumnos con pupitre y silla", "Cantidad": 0, "Material / elemento": occupant_default},
            {"Elemento": "Espectadores", "Cantidad": 0, "Material / elemento": pick("Espectador")},
            {"Elemento": "Butacas tapizadas", "Cantidad": 0, "Material / elemento": pick("Butaca tapizada")},
        ])
    discrete = st.data_editor(
        st.session_state["discrete"], key="discrete_v04", num_rows="dynamic",
        width="stretch", hide_index=True,
        column_config={
            "Elemento": st.column_config.TextColumn("Elemento", required=True),
            "Cantidad": st.column_config.NumberColumn("Cantidad", min_value=0.0, step=1.0, required=True),
            "Material / elemento": st.column_config.SelectboxColumn("Elemento de la base de datos", options=material_names, required=True),
        })
    st.session_state["discrete"] = discrete


with t6:
    st.subheader("Gestión de la base de datos")
    st.write("Puedes modificar materiales existentes o añadir nuevas filas. Para cada material introduce el coeficiente de absorción por banda de octava. Los cambios se guardan en `database.json`.")
    db_path = BASE / "database.json"
    current_db = json.loads(db_path.read_text(encoding="utf-8"))

    st.markdown("**Materiales y elementos**")
    st.caption("Los coeficientes se expresan como absorción por m² para superficies o como absorción equivalente por unidad para elementos discretos.")
    material_df = pd.DataFrame(current_db["materials"])
    editable_cols = ["Material"] + FREQS
    material_edit = st.data_editor(
        material_df[editable_cols],
        key="database_material_editor_v08",
        num_rows="dynamic",
        width="stretch",
        hide_index=True,
        column_config={
            "Material": st.column_config.TextColumn("Material / elemento", required=True),
            **{f: st.column_config.NumberColumn(f"{f} Hz", min_value=0.0, step=0.01, format="%.4f") for f in FREQS},
        },
    )

    st.markdown("**Tipos de recinto y objetivos acústicos**")
    room_df = pd.DataFrame(current_db["rooms"])
    room_edit = st.data_editor(
        room_df[["tipo", "tr", "objetivo"]],
        key="database_room_editor_v08",
        num_rows="dynamic",
        width="stretch",
        hide_index=True,
        column_config={
            "tipo": st.column_config.TextColumn("Tipo de recinto", required=True),
            "tr": st.column_config.TextColumn("Intervalo RT60", required=True),
            "objetivo": st.column_config.TextColumn("Objetivo acústico", required=True),
        }
    )

    if st.button("Guardar cambios en la base de datos", type="primary", key="save_database_v08"):
        clean_materials = []
        for _, row in material_edit.iterrows():
            name = str(row.get("Material", "")).strip()
            if not name or name.lower() == "nan":
                continue
            item = {"Material": name}
            for f in FREQS:
                val = pd.to_numeric(row.get(f), errors="coerce")
                item[f] = None if pd.isna(val) else float(val)
            item["selector"] = name
            clean_materials.append(item)

        clean_rooms = []
        for _, row in room_edit.iterrows():
            name = str(row.get("tipo", "")).strip()
            if not name or name.lower() == "nan":
                continue
            clean_rooms.append({
                "tipo": name,
                "tr": str(row.get("tr", "")).strip(),
                "objetivo": str(row.get("objetivo", "")).strip()
            })

        if not clean_materials:
            st.error("La base de datos debe contener al menos un material.")
        elif not clean_rooms:
            st.error("La base de datos debe contener al menos un tipo de recinto.")
        else:
            db_path.write_text(json.dumps({"materials": clean_materials, "rooms": clean_rooms}, ensure_ascii=False, indent=2), encoding="utf-8")
            st.cache_data.clear()
            st.success("Base de datos guardada. La aplicación se actualizará con los nuevos datos.")
            st.rerun()


with t5:
    st.subheader("Resultados RT60 por bandas de octava")
    walls = st.session_state.get("walls", pd.DataFrame()).copy()
    openings = st.session_state.get("openings", pd.DataFrame()).copy()
    other = st.session_state.get("other_surfaces", pd.DataFrame()).copy()
    discrete = st.session_state.get("discrete", pd.DataFrame()).copy()

    A = {f: 0.0 for f in FREQS}
    A_discrete = {f: 0.0 for f in FREQS}
    surface_terms = []  # (área, coeficientes por banda)
    detail = []
    errors = []
    # Wall net area = gross wall area - openings assigned to that wall.
    for _, w in walls.iterrows():
        wall_name = w.get("Pared", "")
        gross = max(0.0, float(w.get("Largo (m)", 0) or 0) * float(w.get("Alto (m)", 0) or 0))
        holes = 0.0
        for _, op in openings.iterrows():
            if op.get("Pared") == wall_name:
                holes += max(0.0, float(op.get("Cantidad", 0) or 0) * float(op.get("Ancho (m)", 0) or 0) * float(op.get("Alto (m)", 0) or 0))
        net = gross - holes
        if net < -1e-8:
            errors.append(f"{wall_name}: los huecos superan el área de pared.")
            continue
        mat_name = w.get("Material")
        if mat_name not in material_lookup.index:
            continue
        mat = material_lookup.loc[mat_name]
        row = {"Tipo": "Pared", "Elemento": wall_name, "Área neta (m²)": net, "Material": mat_name}
        for f in FREQS:
            alpha = float(mat[f]) if pd.notna(mat[f]) else 0.0
            ae = net * alpha
            A[f] += ae
            row[f"{f} Hz · A"] = ae
        surface_terms.append((net, {f: (float(mat[f]) if pd.notna(mat[f]) else 0.0) for f in FREQS}))
        detail.append(row)
    # Openings added back using their own material coefficients.
    for _, op in openings.iterrows():
        area = max(0.0, float(op.get("Cantidad", 0) or 0) * float(op.get("Ancho (m)", 0) or 0) * float(op.get("Alto (m)", 0) or 0))
        mat_name = op.get("Material")
        if mat_name not in material_lookup.index:
            continue
        mat = material_lookup.loc[mat_name]
        row = {"Tipo": op.get("Tipo", "Hueco"), "Elemento": f"{op.get('Tipo')} en {op.get('Pared')}", "Área (m²)": area, "Material": mat_name}
        for f in FREQS:
            alpha = float(mat[f]) if pd.notna(mat[f]) else 0.0
            ae = area * alpha
            A[f] += ae
            row[f"{f} Hz · A"] = ae
        surface_terms.append((area, {f: (float(mat[f]) if pd.notna(mat[f]) else 0.0) for f in FREQS}))
        detail.append(row)
    # Other horizontal / additional surfaces.
    for _, s in other.iterrows():
        area = max(0.0, float(s.get("Cantidad", 0) or 0) * float(s.get("Largo (m)", 0) or 0) * float(s.get("Ancho (m)", 0) or 0))
        mat_name = s.get("Material")
        if mat_name not in material_lookup.index:
            continue
        mat = material_lookup.loc[mat_name]
        row = {"Tipo": "Otra superficie", "Elemento": s.get("Elemento", ""), "Área (m²)": area, "Material": mat_name}
        for f in FREQS:
            alpha = float(mat[f]) if pd.notna(mat[f]) else 0.0
            ae = area * alpha
            A[f] += ae
            row[f"{f} Hz · A"] = ae
        surface_terms.append((area, {f: (float(mat[f]) if pd.notna(mat[f]) else 0.0) for f in FREQS}))
        detail.append(row)
    # Discrete items use equivalent absorption per unit from the database.
    for _, e in discrete.iterrows():
        qty = max(0.0, float(e.get("Cantidad", 0) or 0))
        mat_name = e.get("Material / elemento")
        if mat_name not in material_lookup.index:
            continue
        mat = material_lookup.loc[mat_name]
        row = {"Tipo": "Elemento discreto", "Elemento": e.get("Elemento", ""), "Cantidad": qty, "Material / elemento": mat_name}
        for f in FREQS:
            val = mat[f]
            ae = qty * (float(val) if pd.notna(val) else 0.0)
            A[f] += ae
            A_discrete[f] += ae
            row[f"{f} Hz · A"] = ae
        detail.append(row)

    if errors:
        for err in errors:
            st.error(err)
    else:
        total_surface = sum(area for area, _ in surface_terms)
        comparison_rows = []
        for f, band in zip(FREQS, BANDS):
            absorption_total = A[f]
            rt_sabine = 0.161 * volume / absorption_total if absorption_total > 0 else np.nan

            # Eyring: el coeficiente medio se calcula SOLO con las superficies.
            # La absorción equivalente de elementos discretos se suma aparte.
            surface_absorption = absorption_total - A_discrete[f]
            alpha_mean = surface_absorption / total_surface if total_surface > 0 else np.nan
            eyring_denominator = np.nan
            if pd.notna(alpha_mean) and 0 <= alpha_mean < 1:
                eyring_denominator = -total_surface * np.log(1 - alpha_mean) + A_discrete[f]
                rt_eyring = 0.161 * volume / eyring_denominator if eyring_denominator > 0 else np.nan
            else:
                rt_eyring = np.nan

            # Millington-Sette: suma logarítmica SOLO para superficies.
            # Los elementos discretos se añaden aparte como absorción equivalente,
            # ya que no tienen una superficie geométrica asignada.
            ms_denominator = 0.0
            ms_valid = total_surface > 0
            for area, coeffs in surface_terms:
                alpha = coeffs[f]
                if alpha < 0 or alpha >= 1:
                    ms_valid = False
                    break
                if area > 0:
                    ms_denominator += -area * np.log(1 - alpha)
            ms_denominator += A_discrete[f]
            rt_millington = (0.161 * volume / ms_denominator
                             if ms_valid and ms_denominator > 0 else np.nan)

            comparison_rows.append({
                "Frecuencia": band,
                "Absorción A (m² sabin)": absorption_total,
                "Sabine (s)": rt_sabine,
                "Eyring (s)": rt_eyring,
                "Millington-Sette (s)": rt_millington,
                "α media superficies": alpha_mean
            })
        result = pd.DataFrame(comparison_rows)
        c1, c2, c3 = st.columns(3)
        c1.metric("Volumen", f"{volume:.1f} m³")
        c2.metric("Absorción a 500 Hz", f"{A['500']:.2f} m² sabin")
        rt500 = result.loc[result["Frecuencia"] == "500 Hz", "Sabine (s)"].iloc[0]
        c3.metric("RT60 a 500 Hz", f"{rt500:.2f} s" if pd.notna(rt500) else "—")
        st.markdown("**Comparación de los tres métodos**")
        st.caption(f"Superficie total considerada: {total_surface:.2f} m². Sabine se mantiene como referencia principal; las otras dos columnas permiten observar el efecto del modelo matemático.")
        st.dataframe(result, width="stretch", hide_index=True)

        # Compare calculated RT60 with the selected room's reference interval.
        import re
        range_text = str(room_info["tr"])
        # Admite coma o punto decimal y distintos guiones como separador.
        normalized_range = range_text.replace("−", "-").replace("–", "-").replace("—", "-")
        nums = re.findall(r"\d+(?:[,.]\d+)?", normalized_range)
        if len(nums) >= 2:
            target_min, target_max = [float(x.replace(",", ".")) for x in nums[:2]]
            if target_min > target_max:
                target_min, target_max = target_max, target_min
            st.markdown("**Adecuación acústica para el tipo de recinto**")
            for _, rr in result.iterrows():
                value = rr["Sabine (s)"]
                if pd.isna(value):
                    st.warning(f"{rr['Frecuencia']}: no se puede evaluar porque la absorción calculada es cero.")
                elif target_min <= value <= target_max:
                    st.success(f"{rr['Frecuencia']}: {value:.2f} s · Dentro del intervalo orientativo ({target_min:.2f}–{target_max:.2f} s).")
                elif value > target_max:
                    st.error(f"{rr['Frecuencia']}: {value:.2f} s · Excesivo; supera el máximo orientativo de {target_max:.2f} s.")
                else:
                    st.warning(f"{rr['Frecuencia']}: {value:.2f} s · Inferior al mínimo orientativo de {target_min:.2f} s.")
            rt_vals = result["Sabine (s)"].dropna()
            if len(rt_vals) and (rt_vals > target_max).any():
                st.markdown("**Posibles mejoras para reducir la reverberación**")
                st.write("- Sustituir o complementar el techo reflectante con un falso techo acústico absorbente.")
                st.write("- Añadir paneles absorbentes en paredes, especialmente en las zonas de primeras reflexiones.")
                st.write("- Incorporar cortinas acústicas en ventanas si el uso y la iluminación lo permiten.")
                st.write("- En aulas, considerar superficies absorbentes y mobiliario tapizado, manteniendo la absorción distribuida.")
                st.write("- Si el exceso se concentra en 125–250 Hz, estudiar trampas de graves o absorbentes de mayor espesor; los paneles finos suelen actuar principalmente en frecuencias medias y altas.")
                st.caption("Las propuestas son orientativas. Para dimensionarlas hay que simular el área y los coeficientes de los materiales concretos, no asumir una mejora fija.")
            elif len(rt_vals) and (rt_vals < target_min).any():
                st.markdown("**Posibles ajustes si la sala queda demasiado seca**")
                st.write("- Reducir la superficie de materiales muy absorbentes o elegir un acabado menos absorbente.")
                st.write("- Recuperar superficies reflectantes en zonas seleccionadas, sin perjudicar la inteligibilidad ni generar ecos molestos.")
        else:
            st.warning(f"No se ha podido interpretar automáticamente el intervalo de referencia: {range_text}")

        fig, ax = plt.subplots(figsize=(8, 4))
        ax.plot(BANDS, result["Sabine (s)"], marker="o", linewidth=2, label="Sabine")
        ax.plot(BANDS, result["Eyring (s)"], marker="s", linewidth=1.5, label="Eyring")
        ax.plot(BANDS, result["Millington-Sette (s)"], marker="^", linewidth=1.5, label="Millington-Sette")
        ax.legend()
        ax.set_xlabel("Frecuencia")
        ax.set_ylabel("RT60 (s)")
        ax.set_title("Tiempo de reverberación por bandas de octava")
        ax.grid(True, alpha=.3)
        st.pyplot(fig, width="stretch")
        plt.close(fig)
        st.markdown("**Desglose de absorción equivalente**")
        st.dataframe(pd.DataFrame(detail), width="stretch", hide_index=True)
        st.download_button("Descargar resultados CSV", result.to_csv(index=False, sep=";").encode("utf-8-sig"), "resultados_RT60.csv", "text/csv")
        st.caption("Sabine: RT60 = 0,161·V/(A_superficies + A_discretos). Eyring: RT60 = 0,161·V/[−S·ln(1−α_media_superficies) + A_discretos]. Millington-Sette: RT60 = 0,161·V/[Σ(−Si·ln(1−αi)) + A_discretos]. En Eyring y Millington-Sette, las personas, butacas y demás elementos discretos se suman como absorción equivalente independiente, no como superficie. Si α_media de superficies no está entre 0 y 1, Eyring no se calcula; si algún αi de superficie es ≥1, Millington-Sette no se calcula. Comparación orientativa bajo hipótesis de campo difuso.")
