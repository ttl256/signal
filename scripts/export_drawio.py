#!/usr/bin/env python3
"""Export every draw.io page as a light/dark SVG pair (10px border by default)."""

import argparse
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import unicodedata
from xml.dom import minidom
import xml.etree.ElementTree as ET


def slug(text):
    """Keep Unicode letters while removing path separators and URL punctuation."""
    text = unicodedata.normalize("NFKC", text).lower()
    return re.sub(r"[^\w-]+", "-", text).strip("-_")


def page_names(source):
    root = ET.parse(source).getroot()
    if root.tag == "mxGraphModel":
        return ["page-1"]
    if root.tag != "mxfile":
        raise ValueError("Expected a .drawio XML file with an mxfile or mxGraphModel root")
    pages = root.findall("diagram")
    if not pages:
        raise ValueError("The diagram contains no pages")
    # Page names remain readable XML even when each page's contents are compressed.
    return [page.get("name") or f"page-{i}" for i, page in enumerate(pages, 1)]


def output_stems(source, names):
    prefix = slug(source.stem) or "diagram"
    used = set()
    stems = []
    for index, name in enumerate(names, 1):
        base = f"{prefix}-{slug(name) or f'page-{index}'}"
        stem = base
        suffix = 2
        while stem.casefold() in used:
            stem = f"{base}-{suffix}"
            suffix += 1
        used.add(stem.casefold())
        stems.append(stem)
    return stems


def find_drawio(explicit):
    if explicit:
        candidates = [str(Path(explicit).expanduser())]
    else:
        candidates = [
            "drawio",
            "draw.io",
            "/Applications/draw.io.app/Contents/MacOS/draw.io",
            str(Path.home() / "Applications/draw.io.app/Contents/MacOS/draw.io"),
        ]
    for candidate in candidates:
        found = shutil.which(candidate)
        if found:
            return str(Path(found).resolve())
    raise ValueError("draw.io Desktop executable not found; provide its path with --drawio")


def export_command(binary, source, output, index, theme, border):
    return [
        binary,
        "--export", "--format", "svg",
        "--page-index", str(index),
        "--border", str(border),
        "--theme", theme,
        "--embed-svg-fonts", "true",
        "--embed-svg-images",
        "--output", str(output),
        str(source),
    ]


def add_opaque_background(output, theme):
    """Back transparent page areas with a solid color, including in SVG viewers."""
    color = "#ffffff" if theme == "light" else "#121212"
    # The CLI preserves transparency when the source page has no background.
    # A painted rectangle works even in viewers that ignore the SVG root's CSS.
    with minidom.parse(str(output)) as document:
        root = document.documentElement
        style = re.sub(
            r"(?:^|;)\s*background(?:-color)?\s*:[^;]*",
            "", root.getAttribute("style"), flags=re.IGNORECASE,
        ).strip(" ;")
        root.setAttribute("style", f"{style}; background: {color}; background-color: {color};")
        tag = f"{root.prefix}:rect" if root.prefix else "rect"
        backdrop = document.createElementNS(root.namespaceURI, tag)
        for name, value in {"x": "0", "y": "0", "width": "100%", "height": "100%", "fill": color}.items():
            backdrop.setAttribute(name, value)
        root.insertBefore(backdrop, root.firstChild)
        output.write_bytes(document.toxml(encoding="utf-8"))


def export_pages(binary, source, destination, names, stems, border):
    destination.mkdir(parents=True, exist_ok=True)
    # Complete and validate every export before replacing any destination SVGs.
    with tempfile.TemporaryDirectory(prefix=".drawio-export-", dir=destination) as tmp:
        staged = []
        for index, (name, stem) in enumerate(zip(names, stems), 1):
            for theme in ("light", "dark"):
                output = Path(tmp) / f"{stem}-{theme}.svg"
                print(f"Page {index}/{len(names)} ({name}), {theme}: {output.name}", flush=True)
                command = export_command(binary, source, output, index, theme, border)
                result = subprocess.run(
                    command, capture_output=True, text=True, errors="replace", timeout=120,
                )
                if result.returncode:
                    detail = (result.stderr or result.stdout).strip()
                    raise ValueError(f"draw.io failed for page {index} ({theme}): {detail}")
                if not output.is_file():
                    raise ValueError(f"draw.io produced no SVG for page {index} ({theme})")
                if ET.parse(output).getroot().tag != "{http://www.w3.org/2000/svg}svg":
                    raise ValueError(f"draw.io produced an invalid SVG: {output.name}")
                add_opaque_background(output, theme)
                staged.append(output)
        for output in staged:
            os.replace(output, destination / output.name)
    print(f"Exported {len(stems) * 2} SVGs to {destination}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="Source .drawio diagram")
    parser.add_argument("destination", type=Path, help="Directory for exported SVGs")
    parser.add_argument("--border", type=int, default=10, help="Border in pixels (default: 10)")
    parser.add_argument("--drawio", help="Path to the draw.io Desktop executable")
    parser.add_argument("--dry-run", action="store_true", help="Print commands without exporting")
    args = parser.parse_args()
    if args.border < 0:
        parser.error("--border must be nonnegative")
    source = args.source.expanduser().resolve()
    destination = args.destination.expanduser().resolve()
    try:
        if not source.is_file():
            raise ValueError(f"Source file not found: {source}")
        if destination.exists() and not destination.is_dir():
            raise ValueError(f"Destination is not a directory: {destination}")
        names = page_names(source)
        stems = output_stems(source, names)
        binary = find_drawio(args.drawio)
        if args.dry_run:
            for index, stem in enumerate(stems, 1):
                for theme in ("light", "dark"):
                    output = destination / f"{stem}-{theme}.svg"
                    print(shlex.join(export_command(binary, source, output, index, theme, args.border)))
        else:
            export_pages(binary, source, destination, names, stems, args.border)
    except (OSError, ValueError, ET.ParseError, subprocess.TimeoutExpired) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
