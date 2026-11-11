#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Media Analyzer STI
Analizador didáctico de archivos multimedia para Ubuntu Linux.

Requisitos:
    sudo apt install ffmpeg
    python3 -m pip install rich

Analiza directamente desde disco: no carga el archivo multimedia completo
en memoria. La inspección estructural detallada inicial cubre RIFF/WAVE,
ISO BMFF (MP4/MOV) y páginas Ogg. Para otros contenedores utiliza FFprobe
y la vista hexadecimal.
"""

from __future__ import annotations

import argparse
import json
import shutil
import struct
import subprocess
import sys
from pathlib import Path
from typing import Any

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, IntPrompt
from rich.table import Table
from rich.text import Text

console = Console()
APP_NAME = "MEDIA ANALYZER STI"
VERSION = "1.0"


def human_size(value: int | float | None) -> str:
    if value is None:
        return "No disponible"
    n = float(value)
    for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
        if n < 1024 or unit == "TiB":
            return f"{int(n)} {unit}" if unit == "B" else f"{n:.2f} {unit}"
        n /= 1024
    return f"{n:.2f} TiB"


def run_ffprobe(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    exe = shutil.which("ffprobe")
    if not exe:
        return None, "No se encuentra FFprobe. Instálalo con: sudo apt install ffmpeg"
    cmd = [
        exe, "-v", "error", "-show_format", "-show_streams",
        "-show_chapters", "-of", "json", str(path)
    ]
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=180, check=False
        )
    except subprocess.TimeoutExpired:
        return None, "FFprobe superó el tiempo máximo de análisis (180 s)."
    except OSError as exc:
        return None, f"No se pudo ejecutar FFprobe: {exc}"
    if result.returncode != 0:
        return None, result.stderr.strip() or "FFprobe no pudo analizar el archivo."
    try:
        return json.loads(result.stdout), None
    except json.JSONDecodeError:
        return None, "FFprobe devolvió un JSON no válido."


def print_header() -> None:
    title = Text(APP_NAME, style="bold bright_cyan")
    title.append(f"  v{VERSION}", style="dim")
    console.print(Panel(
        title,
        subtitle="Análisis de audio, vídeo, contenedores y datos binarios",
        border_style="bright_blue",
        box=box.DOUBLE,
        padding=(1, 2),
    ))


def print_kv_table(title: str, values: dict[str, Any]) -> None:
    table = Table(title=title, box=box.ROUNDED, header_style="bold cyan")
    table.add_column("Parámetro", style="bold", min_width=24)
    table.add_column("Valor", overflow="fold")
    for key, value in values.items():
        if value is None or value == "":
            value = "No disponible"
        table.add_row(str(key), str(value))
    console.print(table)


def stream_description(stream: dict[str, Any]) -> dict[str, Any]:
    kind = stream.get("codec_type", "desconocido")
    result: dict[str, Any] = {
        "Índice": stream.get("index"),
        "Tipo de flujo": kind,
        "Códec": stream.get("codec_name"),
        "Nombre del códec": stream.get("codec_long_name"),
        "Idioma": stream.get("tags", {}).get("language"),
        "Título": stream.get("tags", {}).get("title"),
    }
    if kind == "audio":
        result.update({
            "Frecuencia de muestreo": (
                f'{int(stream["sample_rate"]):,} Hz'
                if stream.get("sample_rate") else None
            ),
            "Canales": stream.get("channels"),
            "Distribución": stream.get("channel_layout"),
            "Bits por muestra": (
                stream.get("bits_per_raw_sample")
                or stream.get("bits_per_sample")
            ),
            "Bitrate": (
                f'{int(stream["bit_rate"]):,} bit/s'
                if stream.get("bit_rate") else None
            ),
        })
    elif kind == "video":
        width, height = stream.get("width"), stream.get("height")
        result.update({
            "Resolución": f"{width} × {height}" if width and height else None,
            "Relación de aspecto": stream.get("display_aspect_ratio"),
            "FPS medio": stream.get("avg_frame_rate"),
            "Formato de píxel": stream.get("pix_fmt"),
            "Bitrate": (
                f'{int(stream["bit_rate"]):,} bit/s'
                if stream.get("bit_rate") else None
            ),
        })
    elif kind == "subtitle":
        result["Formato de subtítulos"] = stream.get("codec_name")
    return result


def automatic_analysis(path: Path, data: dict[str, Any] | None = None) -> dict[str, Any] | None:
    if data is None:
        data, error = run_ffprobe(path)
        if error:
            console.print(f"[bold red]Error:[/] {error}")
            return None

    fmt = data.get("format", {})
    duration = fmt.get("duration")
    try:
        duration_text = f"{float(duration):.3f} s" if duration else "No disponible"
    except (TypeError, ValueError):
        duration_text = "No disponible"

    values = {
        "Nombre": path.name,
        "Ruta": str(path),
        "Tamaño": human_size(path.stat().st_size),
        "Contenedor / formato": fmt.get("format_long_name") or fmt.get("format_name"),
        "Identificador": fmt.get("format_name"),
        "Duración": duration_text,
        "Bitrate global": (
            f'{int(fmt["bit_rate"]):,} bit/s' if fmt.get("bit_rate") else None
        ),
        "Número de flujos": len(data.get("streams", [])),
    }
    print_kv_table("ANÁLISIS GENERAL", values)

    streams = data.get("streams", [])
    if streams:
        table = Table(title="FLUJOS MULTIMEDIA", box=box.ROUNDED, header_style="bold cyan")
        table.add_column("N.º", justify="right")
        table.add_column("Tipo")
        table.add_column("Códec")
        table.add_column("Información principal", overflow="fold")
        for stream in streams:
            kind = stream.get("codec_type", "?")
            codec = stream.get("codec_name", "?")
            if kind == "audio":
                extra = f'{stream.get("channels", "?")} canales · {stream.get("sample_rate", "?")} Hz'
            elif kind == "video":
                extra = f'{stream.get("width", "?")}×{stream.get("height", "?")} · {stream.get("avg_frame_rate", "?")} fps'
            else:
                extra = stream.get("codec_long_name", "")
            table.add_row(str(stream.get("index", "")), kind, codec, extra)
        console.print(table)

        for stream in streams:
            console.print(Panel(
                json.dumps(stream_description(stream), ensure_ascii=False, indent=2),
                title=f"Detalle del flujo {stream.get('index', '?')}",
                border_style="cyan",
            ))

    tags = fmt.get("tags", {})
    if tags:
        print_kv_table("METADATOS DEL CONTENEDOR", tags)
    if data.get("chapters"):
        console.print(f"[bold]Capítulos detectados:[/] {len(data['chapters'])}")
    return data


def inspect_wave(path: Path) -> bool:
    size = path.stat().st_size
    rows = []
    fields: dict[str, Any] = {}
    with path.open("rb") as f:
        header = f.read(12)
        if len(header) != 12:
            console.print("[red]Archivo demasiado pequeño para ser RIFF/WAVE.[/]")
            return False
        riff_id, declared_size, wave_id = struct.unpack("<4sI4s", header)
        if riff_id not in (b"RIFF", b"RIFX") or wave_id != b"WAVE":
            console.print("[red]No se reconoce una cabecera RIFF/WAVE.[/]")
            return False
        endian = "<" if riff_id == b"RIFF" else ">"
        fields = {
            "Identificador": riff_id.decode("ascii", "replace"),
            "Tipo": "WAVE",
            "Tamaño declarado RIFF": f"{declared_size} bytes",
            "Tamaño real": f"{size} bytes",
            "Diferencia": f"{size - (declared_size + 8)} bytes",
        }
        offset = 12
        while offset + 8 <= size and len(rows) < 10000:
            f.seek(offset)
            chunk_header = f.read(8)
            if len(chunk_header) != 8:
                break
            chunk_id, chunk_size = struct.unpack(endian + "4sI", chunk_header)
            name = chunk_id.decode("ascii", "replace")
            row = {
                "Chunk": name,
                "Offset cabecera": offset,
                "Tamaño datos": chunk_size,
                "Offset datos": offset + 8,
                "Alineación": "Sí" if chunk_size % 2 == 0 else "Byte de relleno",
            }
            if chunk_id == b"fmt " and chunk_size >= 16:
                f.seek(offset + 8)
                raw = f.read(16)
                if len(raw) == 16:
                    fmt, channels, rate, byte_rate, align, bits = struct.unpack(endian + "HHIIHH", raw)
                    fmt_names = {1: "PCM", 3: "IEEE Float", 6: "A-law", 7: "mu-law"}
                    fields.update({
                        "Formato de audio": fmt_names.get(fmt, f"Formato {fmt}"),
                        "Canales": channels,
                        "Frecuencia de muestreo": f"{rate:,} Hz",
                        "Bits por muestra": bits,
                        "Bitrate": f"{byte_rate * 8:,} bit/s",
                        "Alineación de bloque": f"{align} bytes",
                    })
            rows.append(row)
            next_offset = offset + 8 + chunk_size + (chunk_size & 1)
            if next_offset <= offset:
                break
            offset = next_offset

    print_kv_table("CABECERA RIFF/WAVE", fields)
    table = Table(title="CHUNKS ENCONTRADOS", box=box.ROUNDED, header_style="bold cyan")
    for col in ("Chunk", "Offset cabecera", "Tamaño datos", "Offset datos", "Alineación"):
        table.add_column(col)
    for row in rows:
        table.add_row(*(str(row[c]) for c in ("Chunk", "Offset cabecera", "Tamaño datos", "Offset datos", "Alineación")))
    console.print(table)
    return True


def inspect_mp4(path: Path, limit: int = 1000) -> None:
    size = path.stat().st_size
    rows: list[dict[str, Any]] = []
    containers = {
        "moov", "trak", "mdia", "minf", "stbl", "edts", "dinf",
        "mvex", "moof", "traf", "mfra", "udta", "meta", "ilst",
        "sinf", "schi", "ipro", "iprp", "ipco",
    }

    def walk(start: int, end: int, depth: int) -> None:
        offset = start
        while offset + 8 <= end and len(rows) < limit:
            with path.open("rb") as f:
                f.seek(offset)
                head = f.read(8)
                if len(head) != 8:
                    return
                size32, raw_type = struct.unpack(">I4s", head)
                box_type = raw_type.decode("ascii", "replace")
                header_size = 8
                if size32 == 1:
                    ext = f.read(8)
                    if len(ext) != 8:
                        return
                    box_size = struct.unpack(">Q", ext)[0]
                    header_size = 16
                elif size32 == 0:
                    box_size = end - offset
                else:
                    box_size = size32
            if box_size < header_size or offset + box_size > end:
                rows.append({"Nivel": depth, "Caja": box_type, "Offset": offset, "Tamaño": box_size, "Estado": "Tamaño no válido"})
                return
            rows.append({"Nivel": depth, "Caja": box_type, "Offset": offset, "Tamaño": box_size, "Estado": "Correcto"})
            child_start = offset + header_size + (4 if box_type == "meta" else 0)
            if box_type in containers and child_start < offset + box_size:
                walk(child_start, offset + box_size, depth + 1)
            offset += box_size

    walk(0, size, 0)
    if not rows:
        console.print("[yellow]No se han detectado cajas ISO BMFF.[/]")
        return
    table = Table(title="ESTRUCTURA ISO BMFF (MP4/MOV)", box=box.ROUNDED, header_style="bold cyan")
    for col in ("Nivel", "Caja", "Offset", "Tamaño", "Estado"):
        table.add_column(col)
    for row in rows:
        indent = "  " * min(row["Nivel"], 8)
        table.add_row(str(row["Nivel"]), indent + row["Caja"], f'{row["Offset"]:,}', human_size(row["Tamaño"]), row["Estado"])
    console.print(table)
    console.print("[dim]Inspección estructural de cajas; no equivale a decodificar todos los campos internos.[/]")


def inspect_ogg(path: Path, limit: int = 10000) -> None:
    rows = []
    size = path.stat().st_size
    with path.open("rb") as f:
        offset = 0
        while offset + 27 <= size and len(rows) < limit:
            f.seek(offset)
            header = f.read(27)
            if len(header) != 27:
                break
            if header[:4] != b"OggS":
                # Busca la siguiente captura OggS en bloques pequeños.
                f.seek(offset + 1)
                probe = f.read(min(1024 * 1024, size - offset - 1))
                pos = probe.find(b"OggS")
                if pos < 0:
                    break
                offset += pos + 1
                continue
            version = header[4]
            flags = header[5]
            granule = struct.unpack("<Q", header[6:14])[0]
            serial = struct.unpack("<I", header[14:18])[0]
            sequence = struct.unpack("<I", header[18:22])[0]
            segments = header[26]
            lacing = f.read(segments)
            page_data = sum(lacing)
            page_size = 27 + segments + page_data
            rows.append({
                "Página": len(rows),
                "Offset": offset,
                "Versión": version,
                "Flags": f"0x{flags:02X}",
                "Serial flujo": serial,
                "Secuencia": sequence,
                "Granule position": granule,
                "Segmentos": segments,
                "Tamaño página": page_size,
            })
            if page_size <= 27 or offset + page_size > size:
                break
            offset += page_size
    if not rows:
        console.print("[yellow]No se han encontrado páginas Ogg válidas.[/]")
        return
    table = Table(title="PÁGINAS DEL CONTENEDOR OGG", box=box.ROUNDED, header_style="bold cyan")
    for col in rows[0]:
        table.add_column(col)
    # Mostrar las primeras 100 páginas para no saturar la terminal.
    for row in rows[:100]:
        table.add_row(*(str(v) for v in row.values()))
    console.print(table)
    if len(rows) > 100:
        console.print(f"[dim]Se han detectado {len(rows)} páginas; se muestran las primeras 100.[/]")


def hex_dump(path: Path, offset: int = 0, length: int = 256) -> None:
    size = path.stat().st_size
    if offset < 0 or offset >= size:
        console.print("[red]El offset está fuera del archivo.[/]")
        return
    length = min(max(length, 1), 4096, size - offset)
    with path.open("rb") as f:
        f.seek(offset)
        data = f.read(length)
    table = Table(title=f"VISTA HEXADECIMAL · offset {offset}", box=box.SIMPLE, header_style="bold cyan")
    table.add_column("Offset", style="dim")
    table.add_column("Bytes (hex)")
    table.add_column("ASCII")
    for i in range(0, len(data), 16):
        chunk = data[i:i+16]
        hx = " ".join(f"{b:02X}" for b in chunk)
        ascii_text = "".join(chr(b) if 32 <= b <= 126 else "." for b in chunk)
        table.add_row(f"{offset+i:08X}", hx, ascii_text)
    console.print(table)


def choose_file(initial: str | None = None) -> Path | None:
    candidate = initial
    while True:
        if not candidate:
            console.print(Panel(
                "Pega la ruta del archivo o arrástralo desde el explorador hasta esta terminal.\n"
                "También puedes usar ~ para indicar tu carpeta personal.",
                title="SELECCIÓN DE ARCHIVO",
                border_style="cyan",
            ))
            candidate = Prompt.ask("Archivo")
        candidate = candidate.strip()
        # Quita comillas que suele añadir el terminal al arrastrar archivos con espacios.
        if len(candidate) >= 2 and candidate[0] == candidate[-1] and candidate[0] in ("'", '"'):
            candidate = candidate[1:-1]
        path = Path(candidate).expanduser()
        try:
            path = path.resolve(strict=True)
        except FileNotFoundError:
            console.print(f"[red]No existe:[/] {path}")
            candidate = None
            continue
        if not path.is_file():
            console.print("[red]La ruta no corresponde a un archivo.[/]")
            candidate = None
            continue
        return path


def show_menu() -> str:
    table = Table(title="MENÚ PRINCIPAL", box=box.ROUNDED, header_style="bold cyan")
    table.add_column("Opción", justify="center", style="bold yellow", width=10)
    table.add_column("Operación")
    options = [
        ("1", "Análisis automático (formato, códecs, duración y flujos)"),
        ("2", "Inspección de estructura interna (WAV, MP4/MOV y OGG)"),
        ("3", "Vista hexadecimal"),
        ("4", "Metadatos completos"),
        ("5", "Exportar informe JSON"),
        ("6", "Seleccionar otro archivo"),
        ("0", "Salir"),
    ]
    for key, label in options:
        table.add_row(key, label)
    console.print(table)
    return IntPrompt.ask("Selecciona una opción", choices=["0", "1", "2", "3", "4", "5", "6"]).__str__()


def export_json(path: Path, data: dict[str, Any] | None) -> None:
    if data is None:
        data, error = run_ffprobe(path)
        if error:
            console.print(f"[red]{error}[/]")
            return
    default = path.with_name(path.stem + "_informe.json")
    dest_text = Prompt.ask("Guardar informe como", default=str(default))
    dest = Path(dest_text).expanduser()
    try:
        dest.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        console.print(Panel(f"Informe guardado en:\n[bold green]{dest.resolve()}[/]", border_style="green"))
    except OSError as exc:
        console.print(f"[red]No se pudo guardar el informe: {exc}[/]")


def process_action(action: str, path: Path, data_cache: dict[str, Any] | None) -> dict[str, Any] | None:
    if action == "1":
        return automatic_analysis(path)
    if action == "2":
        ext = path.suffix.lower()
        if ext == ".wav":
            inspect_wave(path)
        elif ext in (".mp4", ".m4v", ".mov"):
            inspect_mp4(path)
        elif ext in (".ogg", ".oga", ".ogv"):
            inspect_ogg(path)
        else:
            console.print("[yellow]La inspección estructural detallada está disponible en esta versión para WAV, MP4/MOV y OGG. Para este formato consulta el análisis automático y la vista hexadecimal.[/]")
        return data_cache
    if action == "3":
        offset = IntPrompt.ask("Offset inicial (decimal)", default=0)
        length = IntPrompt.ask("Número de bytes (1-4096)", default=256)
        hex_dump(path, offset, length)
        return data_cache
    if action == "4":
        data, error = run_ffprobe(path)
        if error:
            console.print(f"[red]{error}[/]")
        else:
            console.print(Panel(
                json.dumps(data.get("format", {}).get("tags", {}), ensure_ascii=False, indent=2),
                title="METADATOS DEL CONTENEDOR",
                border_style="cyan",
            ))
            for stream in data.get("streams", []):
                tags = stream.get("tags", {})
                if tags:
                    console.print(Panel(
                        json.dumps(tags, ensure_ascii=False, indent=2),
                        title=f"Metadatos del flujo {stream.get('index')}",
                        border_style="cyan",
                    ))
            if not data.get("format", {}).get("tags") and not any(s.get("tags") for s in data.get("streams", [])):
                console.print("[yellow]No se han encontrado etiquetas de metadatos.[/]")
            return data
    if action == "5":
        export_json(path, data_cache)
        return data_cache
    return data_cache


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Analizador didáctico de archivos multimedia para Ubuntu (STI)."
    )
    parser.add_argument("archivo", nargs="?", help="Ruta del archivo. Se admiten rutas entre comillas.")
    parser.add_argument(
        "--accion", choices=["analizar", "estructura", "hex", "metadatos", "informe"],
        help="Ejecuta una operación directamente y termina."
    )
    parser.add_argument("--offset", type=int, default=0, help="Offset inicial para --accion hex.")
    parser.add_argument("--bytes", dest="byte_count", type=int, default=256, help="Bytes para --accion hex (máximo 4096).")
    args = parser.parse_args()

    print_header()
    path = choose_file(args.archivo)
    if path is None:
        return 1

    console.print(Panel(
        f"[bold]{path.name}[/]\n[dim]{path}[/]\nTamaño: {human_size(path.stat().st_size)}",
        title="ARCHIVO SELECCIONADO",
        border_style="green",
    ))

    if args.accion:
        mapping = {
            "analizar": "1", "estructura": "2", "hex": "3",
            "metadatos": "4", "informe": "5",
        }
        if args.accion == "hex":
            hex_dump(path, args.offset, args.byte_count)
            return 0
        process_action(mapping[args.accion], path, None)
        return 0

    data_cache = None
    while True:
        action = show_menu()
        if action == "0":
            console.print("[bold green]Fin de Media Analyzer STI.[/]")
            return 0
        if action == "6":
            path = choose_file()
            data_cache = None
            console.print(f"[green]Archivo seleccionado:[/] {path}")
            continue
        data_cache = process_action(action, path, data_cache)
        console.print()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        console.print("\n[yellow]Operación interrumpida por el usuario.[/]")
        raise SystemExit(130)
