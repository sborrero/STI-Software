from pathlib import Path
import io
import os
import re
import shutil
import subprocess
import tempfile
import tkinter as tk
from tkinter import filedialog
import cv2
import numpy as np
import streamlit as st
from PIL import Image, ImageDraw

VERSION = "0.7"
st.set_page_config(page_title="Video Compression Lab STI", page_icon="🎞️", layout="wide")
st.title("Video Compression Lab STI")
st.caption(f"Versión {VERSION} · De la simulación didáctica a la codificación H.264 real")
st.info("Las pestañas anteriores son simulaciones didácticas. La pestaña final utiliza FFmpeg y el codificador H.264 real (libx264), si está instalado.")

def choose_video_file():
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    name = filedialog.askopenfilename(
        title="Seleccionar vídeo",
        filetypes=[("Vídeos", "*.mp4 *.mov *.mkv *.avi *.webm *.mpeg *.mpg *.ts *.m4v"),
                   ("Todos los archivos", "*.*")]
    )
    root.destroy()
    return name

def block_matching(frame_a, frame_b, block_size=16, radius=8, max_width=960):
    h0, w0 = frame_a.shape[:2]
    scale = min(1.0, max_width / float(w0))
    if scale < 1:
        size = (int(round(w0 * scale)), int(round(h0 * scale)))
        a = cv2.resize(frame_a, size, interpolation=cv2.INTER_AREA)
        b = cv2.resize(frame_b, size, interpolation=cv2.INTER_AREA)
    else:
        a, b = frame_a.copy(), frame_b.copy()

    ga = cv2.cvtColor(a, cv2.COLOR_RGB2GRAY)
    gb = cv2.cvtColor(b, cv2.COLOR_RGB2GRAY)
    h, w = ga.shape
    bs, rad = int(block_size), int(radius)
    padded = cv2.copyMakeBorder(ga, rad, rad, rad, rad, cv2.BORDER_REPLICATE)
    predicted = np.zeros_like(b)
    vectors = []
    residual_values = []

    for y in range(0, h - bs + 1, bs):
        for x in range(0, w - bs + 1, bs):
            template = gb[y:y+bs, x:x+bs]
            search = padded[y:y+bs+2*rad, x:x+bs+2*rad]
            _, _, min_loc, _ = cv2.minMaxLoc(
                cv2.matchTemplate(search, template, cv2.TM_SQDIFF_NORMED)
            )
            px = max(0, min(w-bs, x-rad+min_loc[0]))
            py = max(0, min(h-bs, y-rad+min_loc[1]))
            matched = a[py:py+bs, px:px+bs]
            current = b[y:y+bs, x:x+bs]
            predicted[y:y+bs, x:x+bs] = matched
            err = cv2.absdiff(cv2.cvtColor(current, cv2.COLOR_RGB2GRAY),
                              cv2.cvtColor(matched, cv2.COLOR_RGB2GRAY))
            residual_values.append(float(np.mean(err)))
            vectors.append((x, y, x-px, y-py))

    arrows = b.copy()
    for x, y, dx, dy in vectors:
        if dx or dy:
            start = (x-dx+bs//2, y-dy+bs//2)
            end = (x+bs//2, y+bs//2)
            cv2.arrowedLine(arrows, start, end, (255, 40, 40), 1, tipLength=0.25)

    residual = cv2.absdiff(b, predicted)
    mean_motion = float(np.mean([np.hypot(v[2], v[3]) for v in vectors])) if vectors else 0.0
    return {
        "arrows": arrows, "predicted": predicted, "residual": residual,
        "blocks": len(vectors), "mean_motion": mean_motion,
        "mean_residual": float(np.mean(cv2.cvtColor(residual, cv2.COLOR_RGB2GRAY))),
        "nonzero": sum(1 for v in vectors if v[2] or v[3]),
        "size": (w, h), "scale": scale
    }



def build_p_frame(reference, current, block_size=16, radius=12, quant_step=1, max_width=960):
    """
    Demostración didáctica de una imagen P:
    1) predice cada bloque de B buscando una zona en A;
    2) calcula residual con signo B - predicción;
    3) cuantifica el residual de forma simplificada;
    4) reconstruye predicción + residual cuantificado.
    """
    h0, w0 = reference.shape[:2]
    scale = min(1.0, max_width / float(w0))
    if scale < 1.0:
        size = (int(round(w0 * scale)), int(round(h0 * scale)))
        a = cv2.resize(reference, size, interpolation=cv2.INTER_AREA)
        b = cv2.resize(current, size, interpolation=cv2.INTER_AREA)
    else:
        a, b = reference.copy(), current.copy()

    ga = cv2.cvtColor(a, cv2.COLOR_RGB2GRAY)
    gb = cv2.cvtColor(b, cv2.COLOR_RGB2GRAY)
    h, w = ga.shape
    bs, rad = int(block_size), int(radius)

    prediction = np.zeros_like(b)
    vector_view = b.copy()
    vectors = []
    residual_blocks = []

    for y in range(0, h, bs):
        for x in range(0, w, bs):
            bh = min(bs, h-y)
            bw = min(bs, w-x)
            template = gb[y:y+bh, x:x+bw]

            # Search window in reference A, clipped at image borders.
            sx0, sy0 = max(0, x-rad), max(0, y-rad)
            sx1, sy1 = min(w, x+bw+rad), min(h, y+bh+rad)
            search = ga[sy0:sy1, sx0:sx1]

            if search.shape[0] < bh or search.shape[1] < bw:
                px, py, score = x, y, 1.0
            else:
                match = cv2.matchTemplate(search, template, cv2.TM_SQDIFF_NORMED)
                score, _, loc, _ = cv2.minMaxLoc(match)
                px, py = sx0 + loc[0], sy0 + loc[1]

            prediction[y:y+bh, x:x+bw] = a[py:py+bh, px:px+bw]
            dx, dy = x-px, y-py
            vectors.append((x, y, dx, dy, float(score)))
            if dx or dy:
                cv2.arrowedLine(vector_view,
                                (int(px+bw//2), int(py+bh//2)),
                                (int(x+bw//2), int(y+bh//2)),
                                (255, 40, 40), 1, tipLength=0.25)

    # Signed residual: preserve sign so prediction + residual reconstructs B.
    residual = b.astype(np.int16) - prediction.astype(np.int16)
    step = max(1, int(quant_step))
    quantized = np.clip(np.round(residual / step) * step, -255, 255).astype(np.int16)
    reconstructed = np.clip(prediction.astype(np.int16) + quantized, 0, 255).astype(np.uint8)
    error = cv2.absdiff(b, reconstructed)
    residual_vis = np.clip(np.abs(residual).astype(np.uint16) * 3, 0, 255).astype(np.uint8)

    mse = float(np.mean((b.astype(np.float32)-reconstructed.astype(np.float32))**2))
    psnr = float("inf") if mse == 0 else 10.0 * np.log10((255.0**2)/mse)
    motion_mean = float(np.mean([np.hypot(v[2], v[3]) for v in vectors])) if vectors else 0.0

    return {
        "reference": a, "current": b, "prediction": prediction,
        "vectors": vector_view, "residual": residual_vis,
        "quantized_residual": quantized, "reconstructed": reconstructed,
        "error": error, "motion_mean": motion_mean,
        "residual_mean": float(np.mean(np.abs(residual))),
        "psnr": psnr, "mse": mse, "blocks": len(vectors),
        "size": (w, h), "scale": scale, "quant_step": step
    }


def track_one_block(frames, start_x, start_y, block_size=16, radius=12, delay_ms=350):
    """Seguimiento secuencial de un bloque entre fotogramas consecutivos."""
    original_w = frames[0].shape[1]
    scale = min(1.0, 960 / float(original_w))
    work_w = int(round(frames[0].shape[1] * scale))
    work_h = int(round(frames[0].shape[0] * scale))
    resized = [
        cv2.resize(f, (work_w, work_h), interpolation=cv2.INTER_AREA) if scale < 1 else f.copy()
        for f in frames
    ]
    gray = [cv2.cvtColor(f, cv2.COLOR_RGB2GRAY) for f in resized]
    bs, rad = int(block_size), int(radius)
    x = max(0, min(int(start_x), work_w - bs))
    y = max(0, min(int(start_y), work_h - bs))
    positions, scores, animation = [], [], []

    for i, frame in enumerate(resized):
        positions.append((x, y))
        canvas = frame.copy()
        cv2.rectangle(canvas, (x, y), (x + bs - 1, y + bs - 1), (255, 35, 35), 2)
        cv2.drawMarker(canvas, (x + bs//2, y + bs//2), (255, 230, 30),
                       cv2.MARKER_CROSS, 10, 1)
        label = f"Frame {i+1}/{len(resized)}  block ({x},{y})"
        cv2.putText(canvas, label, (12, 25), cv2.FONT_HERSHEY_SIMPLEX, .6,
                    (0, 0, 0), 3, cv2.LINE_AA)
        cv2.putText(canvas, label, (12, 25), cv2.FONT_HERSHEY_SIMPLEX, .6,
                    (255, 255, 255), 1, cv2.LINE_AA)
        animation.append(Image.fromarray(canvas))

        if i == len(resized) - 1:
            break

        template = gray[i][y:y+bs, x:x+bs]
        x0, y0 = max(0, x-rad), max(0, y-rad)
        x1, y1 = min(work_w, x+bs+rad), min(work_h, y+bs+rad)
        search = gray[i+1][y0:y1, x0:x1]
        if template.shape != (bs, bs) or search.shape[0] < bs or search.shape[1] < bs:
            scores.append(1.0)
            continue
        result = cv2.matchTemplate(search, template, cv2.TM_SQDIFF_NORMED)
        score, _, loc, _ = cv2.minMaxLoc(result)
        x = max(0, min(work_w-bs, x0+loc[0]))
        y = max(0, min(work_h-bs, y0+loc[1]))
        scores.append(float(score))

    buf = io.BytesIO()
    animation[0].save(buf, format="GIF", save_all=True, append_images=animation[1:],
                      duration=int(delay_ms), loop=0, optimize=True)
    steps = [float(np.hypot(positions[i][0]-positions[i-1][0],
                            positions[i][1]-positions[i-1][1]))
             for i in range(1, len(positions))]
    return {
        "gif": buf.getvalue(), "positions": positions, "scores": scores,
        "mean_step": float(np.mean(steps)) if steps else 0.0,
        "distance": float(sum(steps)), "size": (work_w, work_h)
    }


def run_ffmpeg_comparison(source, start_seconds, duration_seconds, crf_values):
    """Encode the same source segment with real libx264 at several CRF values."""
    ffmpeg = shutil.which("ffmpeg")
    ffprobe = shutil.which("ffprobe")
    if not ffmpeg or not ffprobe:
        raise RuntimeError("No se encuentran ffmpeg y/o ffprobe en PATH. Instala FFmpeg y reinicia PowerShell/Streamlit.")

    results = []
    temp_root = tempfile.mkdtemp(prefix="video_compression_sti_")
    for crf in crf_values:
        target = os.path.join(temp_root, f"h264_crf_{crf}.mp4")
        cmd = [ffmpeg, "-y", "-hide_banner", "-loglevel", "error",
               "-i", source, "-ss", str(start_seconds), "-t", str(duration_seconds),
               "-an", "-c:v", "libx264", "-preset", "medium", "-crf", str(crf),
               "-pix_fmt", "yuv420p", "-movflags", "+faststart", target]
        enc = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        if enc.returncode != 0 or not os.path.exists(target):
            raise RuntimeError(f"Falló la codificación CRF {crf}: {(enc.stderr or enc.stdout)[-1800:]}")

        probe_cmd = [ffprobe, "-v", "error", "-select_streams", "v:0",
                     "-show_entries", "stream=width,height,r_frame_rate,duration:format=duration,size,bit_rate",
                     "-of", "json", target]
        probe = subprocess.run(probe_cmd, capture_output=True, text=True, timeout=60)
        import json
        metadata = json.loads(probe.stdout or "{}")
        fmt = metadata.get("format", {})
        actual_duration = float(fmt.get("duration", duration_seconds) or duration_seconds)
        size_bytes = os.path.getsize(target)

        # Compare decoded H.264 output against the corresponding source segment.
        psnr_cmd = [ffmpeg, "-hide_banner", "-i", target, "-i", source,
                    "-filter_complex",
                    f"[1:v]trim=start={start_seconds}:duration={duration_seconds},setpts=PTS-STARTPTS[ref];"
                    f"[0:v]setpts=PTS-STARTPTS[dist];[ref][dist]psnr",
                    "-an", "-f", "null", "-"]
        psnr_run = subprocess.run(psnr_cmd, capture_output=True, text=True, timeout=600)
        log = (psnr_run.stderr or "") + (psnr_run.stdout or "")
        matches = re.findall(r"平均|average:([0-9.]+)", log)
        psnr = float(matches[-1]) if matches else None
        with open(target, "rb") as f:
            video_bytes = f.read()
        results.append({
            "crf": crf, "size_bytes": size_bytes,
            "size_mb": size_bytes / (1024*1024),
            "bitrate_kbps": (size_bytes*8/actual_duration/1000) if actual_duration else 0,
            "duration": actual_duration, "psnr": psnr,
            "data": video_bytes, "filename": f"h264_crf_{crf}.mp4",
            "psnr_log": log[-1200:]
        })
    return results


with st.sidebar:
    st.header("1. Vídeo")
    if st.button("📂 Buscar vídeo en el ordenador", type="primary", use_container_width=True):
        try:
            chosen = choose_video_file()
            if chosen:
                st.session_state.video_path = chosen
                st.session_state.frames = None
                st.session_state.motion = None
        except Exception as exc:
            st.error(f"No se pudo abrir el selector: {exc}")
    video_path = st.session_state.get("video_path", "")
    if video_path:
        st.success("Vídeo seleccionado")
        st.caption(video_path)
    else:
        st.caption("Selecciona un archivo de vídeo.")
    st.divider()
    st.header("2. Extracción")
    start = st.number_input("Comenzar en (segundos)", min_value=0.0, value=0.0, step=1.0)
    count = st.number_input("Número de fotogramas", min_value=2, max_value=500, value=100)
    stride = st.number_input("Separación", min_value=1, max_value=100, value=1)
    extract = st.button("Leer fotogramas", use_container_width=True, disabled=not bool(video_path))

if "frames" not in st.session_state:
    st.session_state.frames = None
    st.session_state.info = None
    st.session_state.motion = None

if extract:
    p = Path(video_path)
    cap = cv2.VideoCapture(str(p))
    if not p.is_file() or not cap.isOpened():
        st.error("No se puede abrir el archivo seleccionado.")
    else:
        fps = cap.get(cv2.CAP_PROP_FPS)
        total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        first = int(round(start*fps)) if fps > 0 else 0
        cap.set(cv2.CAP_PROP_POS_FRAMES, first)
        frames, indices = [], []
        pos = first
        for _ in range(int(count)):
            ok, bgr = cap.read()
            if not ok:
                break
            frames.append(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB))
            indices.append(pos)
            pos += int(stride)
            if int(stride) > 1:
                cap.set(cv2.CAP_PROP_POS_FRAMES, pos)
        cap.release()
        if frames:
            st.session_state.frames = frames
            st.session_state.info = {"fps": fps, "total": total, "width": w, "height": h, "indices": indices}
            st.session_state.source = str(p)
            st.session_state.motion = None
            st.success(f"Leídos {len(frames)} fotogramas.")
        else:
            st.error("No se han extraído fotogramas.")

frames, info = st.session_state.frames, st.session_state.info
if frames is None:
    st.subheader("Cómo empezar")
    st.markdown("1. Pulsa **Buscar vídeo en el ordenador**.\\n2. Selecciona el vídeo.\\n3. Deja 100 fotogramas y separación 1.\\n4. Pulsa **Leer fotogramas**.")
    st.code("python -m pip install streamlit opencv-python numpy pillow")
    st.code("python -m streamlit run video_compression_lab_v0_7_1.py")
    st.stop()

fps = info["fps"]
m1, m2, m3, m4 = st.columns(4)
m1.metric("Resolución", f'{info["width"]} × {info["height"]}')
m2.metric("FPS", f"{fps:.3f}" if fps else "—")
m3.metric("Fotogramas leídos", len(frames))
m4.metric("Duración analizada", f"{len(frames)/fps:.2f} s" if fps else "—")
st.caption(st.session_state.source)

t1, t2, t3, t4, t5, t6, t7, t8 = st.tabs(["Fotogramas", "Comparación temporal", "Estructura espacial", "Movimiento por bloques", "Seguimiento de bloque", "Construir imagen P", "Estructura GOP", "Compresión H.264 real"])

with t1:
    i = st.slider("Selecciona un fotograma", 0, len(frames)-1, 0, key="show_frame")
    origin = info["indices"][i]
    st.image(frames[i], caption=f"Fotograma {i+1} · índice original {origin}", use_container_width=True)
    st.markdown("**Vista de contacto**")
    ids = list(range(0, len(frames), max(1, len(frames)//10)))[:10]
    cols = st.columns(5)
    for n, j in enumerate(ids):
        im = Image.fromarray(frames[j])
        im.thumbnail((220, 130))
        cols[n % 5].image(im, caption=f"Fotograma {j+1}", use_container_width=True)

with t2:
    st.subheader("Redundancia temporal: comparación píxel a píxel")
    ca, cb = st.columns(2)
    aidx = ca.slider("Fotograma A", 0, len(frames)-1, 0, key="cmp_a")
    bidx = cb.slider("Fotograma B", 0, len(frames)-1, min(1, len(frames)-1), key="cmp_b")
    fa, fb = frames[aidx], frames[bidx]
    ca.image(fa, caption=f"A · {aidx+1}", use_container_width=True)
    cb.image(fb, caption=f"B · {bidx+1}", use_container_width=True)
    if fa.shape == fb.shape:
        diff = cv2.absdiff(fa, fb)
        gray = cv2.cvtColor(diff, cv2.COLOR_RGB2GRAY)
        threshold = st.slider("Umbral de diferencia", 0, 100, 15)
        changed = gray > threshold
        x, y = st.columns(2)
        x.metric("Píxeles que cambian", f"{np.mean(changed)*100:.2f}%")
        y.metric("Diferencia media (0–255)", f"{np.mean(diff):.2f}")
        gain = st.slider("Amplificación", 1, 8, 4)
        x, y = st.columns(2)
        x.image(np.clip(diff.astype(np.uint16)*gain, 0, 255).astype(np.uint8), caption="Diferencia amplificada", use_container_width=True)
        overlay = fb.copy()
        overlay[changed] = [255, 35, 35]
        y.image(overlay, caption="Píxeles diferentes en rojo", use_container_width=True)

with t3:
    st.subheader("Redundancia espacial")
    si = st.slider("Fotograma", 0, len(frames)-1, 0, key="spatial_frame")
    bs = st.select_slider("Tamaño de bloque", options=[4, 8, 16, 32], value=16)
    image = Image.fromarray(frames[si]).copy()
    draw = ImageDraw.Draw(image)
    ww, hh = image.size
    for x in range(0, ww, int(bs)):
        draw.line((x, 0, x, hh), fill=(255, 65, 65), width=1)
    for y in range(0, hh, int(bs)):
        draw.line((0, y, ww, y), fill=(255, 65, 65), width=1)
    st.image(image, caption=f"Rejilla {bs} × {bs} píxeles", use_container_width=True)
    st.caption("La rejilla permite observar regiones. La compresión aprovecha correlaciones entre píxeles; cada bloque no se guarda como un único color.")

with t4:
    st.subheader("Estimación de movimiento mediante búsqueda de bloques")
    st.write("Para cada bloque de B se busca una zona parecida en A dentro de un radio limitado. La flecha representa el desplazamiento estimado.")
    ca, cb = st.columns(2)
    ma = ca.slider("Fotograma de referencia A", 0, len(frames)-1, 0, key="mv_a")
    mb = cb.slider("Fotograma actual B", 0, len(frames)-1, min(1, len(frames)-1), key="mv_b")
    ca, cb = st.columns(2)
    mbs = ca.select_slider("Tamaño de bloque", options=[8, 16, 32], value=16, key="mv_bs")
    rad = cb.select_slider("Radio de búsqueda (píxeles)", options=[4, 8, 12, 16, 24], value=8, key="mv_rad")
    st.caption("El cálculo se realiza sobre una copia reducida a un máximo de 960 píxeles de ancho para mejorar el rendimiento.")
    if st.button("Calcular movimiento por bloques", type="primary"):
        if ma == mb:
            st.warning("Selecciona dos fotogramas distintos.")
        else:
            with st.spinner("Buscando bloques similares..."):
                st.session_state.motion = {
                    "data": block_matching(frames[ma], frames[mb], mbs, rad),
                    "a": ma, "b": mb, "bs": mbs, "rad": rad
                }
    saved = st.session_state.motion
    if saved:
        r = saved["data"]
        q1, q2, q3 = st.columns(3)
        q1.metric("Bloques analizados", r["blocks"])
        q2.metric("Movimiento medio", f'{r["mean_motion"]:.2f} px')
        q3.metric("Error residual medio", f'{r["mean_residual"]:.2f} / 255')
        st.caption(f'{r["nonzero"]} bloques con vector no nulo · resolución de trabajo {r["size"][0]}×{r["size"][1]}')
        st.markdown("**1. Fotograma B con vectores de movimiento**")
        st.image(r["arrows"], use_container_width=True)
        st.markdown("**2. Predicción construida con bloques de A**")
        st.image(r["predicted"], use_container_width=True)
        gain = st.slider("Amplificación del error residual", 1, 6, 3)
        residual = np.clip(r["residual"].astype(np.uint16)*gain, 0, 255).astype(np.uint8)
        st.markdown("**3. Error residual: diferencia entre B y la predicción**")
        st.image(residual, use_container_width=True)
        st.info("El vector describe el desplazamiento estimado. El residual contiene lo que el movimiento por sí solo no consigue explicar.")
    else:
        st.warning("Selecciona A y B y pulsa «Calcular movimiento por bloques».")


with t5:
    st.subheader("Seguir un bloque lentamente por todos los fotogramas")
    st.write(
        "Selecciona una zona del primer fotograma. El programa la busca en el siguiente "
        "y repite el proceso hasta recorrer toda la secuencia."
    )
    work_w = min(960, frames[0].shape[1])
    scale_ui = work_w / float(frames[0].shape[1])
    work_h = int(round(frames[0].shape[0] * scale_ui))
    bs_track = st.select_slider("Tamaño del bloque", options=[8, 16, 32, 48], value=16,
                                key="track_bs")
    c1, c2 = st.columns(2)
    x_track = c1.slider("Posición inicial X", 0, max(0, work_w-int(bs_track)),
                        max(0, (work_w-int(bs_track))//2), key="track_x")
    y_track = c2.slider("Posición inicial Y", 0, max(0, work_h-int(bs_track)),
                        max(0, (work_h-int(bs_track))//2), key="track_y")
    c3, c4 = st.columns(2)
    radius_track = c3.select_slider("Radio de búsqueda", options=[4, 8, 12, 16, 24, 32],
                                    value=12, key="track_radius")
    delay_track = c4.select_slider("Velocidad", options=[150, 250, 350, 500, 750],
                                   value=350, format_func=lambda n: f"{n} ms/fotograma",
                                   key="track_delay")
    st.caption(f"Coordenadas sobre la imagen de trabajo de {work_w} × {work_h} píxeles.")
    if st.button("Seguir bloque por toda la secuencia", type="primary"):
        with st.spinner("Calculando el seguimiento y preparando la animación..."):
            st.session_state["block_track"] = track_one_block(
                frames, x_track, y_track, bs_track, radius_track, delay_track
            )
    result = st.session_state.get("block_track")
    if result:
        st.markdown("**Animación del bloque seguido**")
        st.image(result["gif"], caption="El rectángulo rojo marca la posición estimada del bloque en cada fotograma.")
        a, b, c = st.columns(3)
        a.metric("Fotogramas recorridos", len(result["positions"]))
        b.metric("Desplazamiento medio por paso", f'{result["mean_step"]:.2f} px')
        c.metric("Distancia acumulada", f'{result["distance"]:.1f} px')
        with st.expander("Consultar coordenadas del bloque"):
            st.dataframe(
                [{"Fotograma": i+1, "X": p[0], "Y": p[1]}
                 for i, p in enumerate(result["positions"])],
                use_container_width=True, hide_index=True
            )
        st.info(
            "El seguimiento es secuencial: cada posición encontrada se usa como referencia "
            "para el fotograma siguiente. Puede perder el bloque si queda oculto, cambia mucho "
            "de aspecto o sale del radio de búsqueda. Es seguimiento visual por bloques, no "
            "reconocimiento del personaje."
        )
    else:
        st.warning("Selecciona el bloque inicial y pulsa «Seguir bloque por toda la secuencia».")



with t6:
    st.subheader("Construcción didáctica de una imagen P")
    st.write(
        "Vamos a crear una predicción del fotograma B usando el fotograma A como referencia. "
        "Después calcularemos el residual y lo sumaremos a la predicción para reconstruir B."
    )
    st.warning(
        "Modelo simplificado: búsqueda de bloques + residual de píxeles. "
        "Un codificador MPEG real aplica además transformadas, cuantificación por coeficientes, "
        "predicción más sofisticada y codificación entrópica."
    )
    ca, cb = st.columns(2)
    p_a = ca.slider("Imagen de referencia A", 0, len(frames)-1, 0, key="pframe_a")
    p_b = cb.slider("Imagen que queremos codificar B", 0, len(frames)-1,
                    min(10, len(frames)-1), key="pframe_b")
    c1, c2, c3 = st.columns(3)
    p_block = c1.select_slider("Bloque", options=[8, 16, 32], value=16, key="p_block")
    p_radius = c2.select_slider("Radio de búsqueda", options=[4, 8, 12, 16, 24],
                                value=12, key="p_radius")
    qstep = c3.select_slider("Cuantificación didáctica del residual",
                             options=[1, 2, 4, 8, 16, 32], value=1, key="p_qstep")
    st.caption(
        "Con cuantificación 1 se conserva el residual de píxeles prácticamente sin pérdida. "
        "Al aumentar el paso, se reduce la precisión y aparece más error."
    )
    if st.button("Construir imagen P", type="primary"):
        if p_a == p_b:
            st.warning("Elige dos fotogramas diferentes.")
        else:
            with st.spinner("Estimando movimiento, calculando residual y reconstruyendo..."):
                st.session_state["p_frame_result"] = build_p_frame(
                    frames[p_a], frames[p_b], p_block, p_radius, qstep
                )
                st.session_state["p_frame_settings"] = {
                    "a": p_a, "b": p_b, "block": p_block,
                    "radius": p_radius, "qstep": qstep
                }

    p_result = st.session_state.get("p_frame_result")
    if p_result:
        r = p_result
        settings = st.session_state["p_frame_settings"]
        st.markdown(
            f'**Resultado: A={settings["a"]} → B={settings["b"]} · '
            f'bloques {settings["block"]} · radio {settings["radius"]} · '
            f'paso residual {settings["qstep"]}**'
        )
        m1, m2, m3 = st.columns(3)
        m1.metric("Movimiento medio", f'{r["motion_mean"]:.2f} px')
        m2.metric("Residual absoluto medio", f'{r["residual_mean"]:.2f} / 255')
        m3.metric("PSNR reconstrucción", "∞" if np.isinf(r["psnr"]) else f'{r["psnr"]:.2f} dB')

        st.markdown("**Etapa 1. Fotograma original B**")
        st.image(r["current"], use_container_width=True)
        st.markdown("**Etapa 2. Predicción a partir de A y vectores estimados**")
        st.image(r["vectors"], use_container_width=True)
        st.image(r["prediction"], caption="Predicción construida con bloques del fotograma A", use_container_width=True)
        st.markdown("**Etapa 3. Residual (diferencia con signo, visualizada en intensidad)**")
        st.image(r["residual"], caption="Residual absoluto amplificado para poder verlo", use_container_width=True)
        st.markdown("**Etapa 4. Imagen P reconstruida = predicción + residual cuantificado**")
        st.image(r["reconstructed"], use_container_width=True)
        st.markdown("**Etapa 5. Error que queda tras la reconstrucción**")
        st.image(r["error"], caption="Con paso residual 1 debería ser prácticamente negro.", use_container_width=True)
        st.info(
            "La imagen P no consiste solo en vectores: necesita también el residual. "
            "El vector explica el desplazamiento estimado; el residual corrige diferencias "
            "de iluminación, textura, deformación, oclusiones y errores de búsqueda."
        )
    else:
        st.warning("Selecciona dos fotogramas y pulsa «Construir imagen P».")


with t7:
    st.subheader("Organización de imágenes I, P y B en un GOP")
    st.write(
        "Un GOP (Group of Pictures) agrupa imágenes que se relacionan entre sí para "
        "reducir redundancia temporal. Vamos a distinguir el orden en que se muestran "
        "las imágenes del orden necesario para decodificarlas."
    )
    pattern_name = st.selectbox(
        "Estructura que queremos estudiar",
        ["I – B – B – P – B – B – P", "I – P – P – P"],
        key="gop_pattern"
    )
    if pattern_name.startswith("I – B"):
        display_types = ["I", "B", "B", "P", "B", "B", "P"]
        coding_types = ["I", "P", "B", "B", "P", "B", "B"]
        references = {
            0: "No necesita otra imagen de referencia.",
            1: "B1: utiliza como referencias I0 y P3.",
            2: "B2: utiliza como referencias I0 y P3.",
            3: "P3: utiliza la referencia anterior I0.",
            4: "B4: utiliza como referencias P3 y P6.",
            5: "B5: utiliza como referencias P3 y P6.",
            6: "P6: utiliza la referencia anterior P3."
        }
        coding_explanation = (
            "Para decodificar las B1 y B2, primero debe estar disponible P3, "
            "aunque P3 se muestra después de ellas. Por eso P3 se transmite antes "
            "que esas B. Lo mismo ocurre con P6 y las dos B que lo preceden."
        )
    else:
        display_types = ["I", "P", "P", "P"]
        coding_types = display_types.copy()
        references = {
            0: "No necesita otra imagen de referencia.",
            1: "P1: predicción basada en I0.",
            2: "P2: predicción basada en P1.",
            3: "P3: predicción basada en P2."
        }
        coding_explanation = (
            "En esta secuencia sencilla, el orden de transmisión coincide con el "
            "orden de visualización: cada imagen P puede reconstruirse usando una "
            "referencia anterior ya decodificada."
        )

    st.markdown("#### 1. Orden de visualización")
    cols = st.columns(len(display_types))
    for idx, (col, kind) in enumerate(zip(cols, display_types)):
        color = {"I": "#d8ead5", "P": "#dce8f8", "B": "#f8e8c9"}[kind]
        col.markdown(
            f'<div style="text-align:center;background:{color};padding:14px 4px;'
            f'border-radius:8px;border:1px solid #999">'
            f'<div style="font-size:24px;font-weight:700">{kind}</div>'
            f'<div style="font-size:12px">Imagen {idx}</div></div>',
            unsafe_allow_html=True
        )
    st.caption("I: intra · P: predictiva · B: bidireccional")

    st.markdown("#### 2. Orden de transmisión / decodificación (esquema simplificado)")
    coding_labels = [f"{kind}{display_types.index(kind) if display_types.count(kind)==1 else ''}" for kind in coding_types]
    # Identify each displayed picture unambiguously, including repeated types.
    remaining = {kind: [i for i, value in enumerate(display_types) if value == kind]
                 for kind in set(display_types)}
    coding_indices = []
    for kind in coding_types:
        candidates = remaining[kind]
        idx = candidates.pop(0)
        coding_indices.append(idx)
    coding_cols = st.columns(len(coding_types))
    for order, (col, kind, display_idx) in enumerate(zip(coding_cols, coding_types, coding_indices), start=1):
        col.markdown(
            f'<div style="text-align:center;padding:10px 3px;border:1px solid #999;'
            f'border-radius:8px"><div style="font-size:11px">Orden {order}</div>'
            f'<div style="font-size:21px;font-weight:700">{kind}{display_idx}</div>'
            f'<div style="font-size:10px">Visual {display_idx}</div></div>',
            unsafe_allow_html=True
        )
    st.info(coding_explanation)

    st.markdown("#### 3. ¿De qué imágenes depende cada una?")
    selected_display = st.selectbox(
        "Selecciona una imagen en el orden de visualización",
        options=list(range(len(display_types))),
        format_func=lambda i: f"Imagen {i} · tipo {display_types[i]}",
        key="gop_selected"
    )
    st.write(references[selected_display])
    if display_types[selected_display] == "B":
        st.caption("Una B puede combinar predicción hacia delante y hacia atrás. No todas las configuraciones reales usan exactamente este patrón.")
    elif display_types[selected_display] == "P":
        st.caption("Una P puede utilizar una imagen I o P anterior como referencia; puede codificar también un residual para corregir la predicción.")
    else:
        st.caption("Una I se puede reconstruir sin utilizar otras imágenes del GOP como referencia.")

    st.markdown("#### 4. Resumen de dependencias")
    if pattern_name.startswith("I – B"):
        st.markdown(
            "- **I0** es la referencia inicial.\n"
            "- **P3** se predice desde I0.\n"
            "- **B1 y B2** pueden usar I0 y P3.\n"
            "- **P6** se predice desde P3.\n"
            "- **B4 y B5** pueden usar P3 y P6."
        )
    else:
        st.markdown(
            "- **I0** es la referencia inicial.\n"
            "- **P1** se predice desde I0.\n"
            "- **P2** se predice desde P1.\n"
            "- **P3** se predice desde P2."
        )
    st.warning(
        "Este apartado representa relaciones conceptuales de un GOP. No analiza ni "
        "modifica la estructura GOP real del archivo seleccionado y no implementa "
        "un codificador/decodificador MPEG. En estándares y perfiles reales, la "
        "estructura, las referencias y el orden pueden variar."
    )


with t8:
    st.subheader("Compresión real con H.264 (libx264)")
    st.write(
        "En esta última práctica FFmpeg codifica un fragmento real del vídeo en H.264. "
        "Repetiremos la codificación con distintos valores CRF y compararemos tamaño, "
        "bitrate y calidad de reconstrucción. A diferencia de la pestaña de imagen P, "
        "aquí sí se genera un archivo comprimido real."
    )
    ffmpeg_path = shutil.which("ffmpeg")
    ffprobe_path = shutil.which("ffprobe")
    if ffmpeg_path and ffprobe_path:
        st.success(f"FFmpeg y FFprobe detectados: {ffmpeg_path}")
    else:
        st.error("No se detectan FFmpeg y FFprobe en PATH. Instala FFmpeg, añade su carpeta bin al PATH y reinicia Streamlit.")
        st.markdown("Puedes descargar FFmpeg desde [ffmpeg.org](https://ffmpeg.org/download.html). En Windows, comprueba en PowerShell con `ffmpeg -version` y `ffprobe -version`.")

    c1, c2 = st.columns(2)
    enc_start = c1.number_input("Inicio del fragmento (segundos)", min_value=0.0, value=0.0, step=1.0, key="enc_start")
    enc_duration = c2.number_input("Duración a codificar (segundos)", min_value=2.0, max_value=30.0, value=8.0, step=1.0, key="enc_duration")
    st.caption("Para que la comparación sea rápida, empieza con un fragmento de 8 segundos. Se codifica vídeo sin audio, con el mismo preset medium.")
    crf_values = st.multiselect("Valores CRF que vamos a comparar", [18, 23, 28], default=[18, 23, 28], key="crf_values")
    st.caption("CRF bajo = más calidad y archivos mayores. CRF alto = más compresión y, normalmente, menor calidad. CRF 23 es un punto de partida habitual, no una garantía de calidad fija.")
    if st.button("Codificar y comparar con H.264", type="primary", disabled=not (ffmpeg_path and ffprobe_path), key="run_real_h264"):
        if not crf_values:
            st.warning("Selecciona al menos un valor CRF.")
        elif enc_start + enc_duration > (info["total"] / fps if fps else 1e9):
            st.warning("El fragmento solicitado supera la duración del vídeo.")
        else:
            try:
                with st.spinner("FFmpeg está codificando los fragmentos. Puede tardar unos minutos..."):
                    st.session_state.h264_results = run_ffmpeg_comparison(
                        st.session_state.source, float(enc_start), float(enc_duration), sorted(crf_values)
                    )
                    st.session_state.h264_settings = {"start": enc_start, "duration": enc_duration, "crf": sorted(crf_values)}
                st.success("Codificación terminada.")
            except Exception as exc:
                st.error(f"No se pudo completar la comparación: {exc}")

    results = st.session_state.get("h264_results")
    if results:
        st.markdown("#### Resultados de la codificación")
        import pandas as pd
        table = []
        for r in results:
            table.append({
                "CRF": r["crf"], "Tamaño (MB)": round(r["size_mb"], 3),
                "Bitrate (kb/s)": round(r["bitrate_kbps"]),
                "PSNR (dB)": (round(r["psnr"], 2) if r["psnr"] is not None else "No disponible")
            })
        st.dataframe(pd.DataFrame(table), hide_index=True, use_container_width=True)
        st.markdown("#### Archivos generados")
        cols = st.columns(len(results))
        for col, r in zip(cols, results):
            col.metric(f"CRF {r['crf']}", f"{r['size_mb']:.3f} MB")
            col.download_button("Descargar MP4", data=r["data"], file_name=r["filename"], mime="video/mp4", key=f"download_crf_{r['crf']}")
        st.markdown("#### Cómo interpretar")
        st.markdown(
            "- **CRF menor:** conserva más información, por lo general aumenta el tamaño y el PSNR.\n"
            "- **CRF mayor:** descarta más información, normalmente reduce el tamaño y el PSNR.\n"
            "- **Bitrate:** cantidad media de bits por segundo del archivo generado.\n"
            "- **PSNR:** compara los fotogramas decodificados con el fragmento original; cuanto mayor, menor error pixel a pixel."
        )
        st.warning("El PSNR puede no aparecer si FFmpeg no consigue emparejar los fotogramas de referencia y salida. Los tamaños y bitrates siguen siendo mediciones reales de los MP4 generados. El audio se ha excluido para comparar únicamente la compresión de vídeo.")
    else:
        st.info("Selecciona los valores CRF y pulsa «Codificar y comparar con H.264» para generar los MP4.")


st.divider()
st.caption("Video Compression Lab STI · v0.7 · Incluye comparación de codificación H.264 real con FFmpeg/libx264.")
