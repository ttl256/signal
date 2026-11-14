# Exporting draw.io diagrams

Run from the repository root:

```sh
python3 scripts/export_drawio.py \
  diagram-sources/bfd-for-evpn-bgp.drawio \
  content/posts/bfd-for-evpn-bgp
```

Requires Python 3.9+ and a recent draw.io Desktop with `--theme` and 1-based
`--page-index` support. The script automatically finds the macOS application or
`drawio` / `draw.io` on `PATH`. Use `--drawio /path/to/executable` to choose another
installation. Desktop export requires a graphical environment; it is not part of
the GitHub Pages build.

Each page produces two SVGs, with **Border Width set to 10**:

```text
bfd-for-evpn-bgp-base-topology-light.svg
bfd-for-evpn-bgp-base-topology-dark.svg
bfd-for-evpn-bgp-failure-light.svg
bfd-for-evpn-bgp-failure-dark.svg
bfd-for-evpn-bgp-extended-light.svg
bfd-for-evpn-bgp-extended-dark.svg
```

Filenames combine the source filename, page name, and appearance. Spaces and
punctuation become hyphens. Duplicate names get numeric suffixes. Matching files
are replaced only after all exports have completed successfully; unrelated files
are left alone. Renaming a page creates new filenames, so update its figure block
and remove obsolete exports when needed.

Exports use the equivalent of these SVG export settings:

- **Embed Images: enabled** (`--embed-svg-images`).
- **Embed Fonts: enabled** (`--embed-svg-fonts true`). This also lets draw.io add
  rasterized text fallbacks for formatted labels. These fallbacks increase file
  size and are retained deliberately.
- **Appearance: Light and Dark**, exported separately.
- **Border Width: 10**, configurable with `--border`.
- **Transparent Background: disabled**. The script adds a solid white (`#ffffff`)
  backdrop to light exports and a solid dark (`#121212`) backdrop to dark exports.
  This covers areas the CLI otherwise leaves transparent, even when the source
  page has no background. Any background already drawn by draw.io remains above
  that backdrop.

The source diagram is not changed, and editable diagram data is not embedded.

Use the exports with the site's figure shortcode:

```go-html-template
{{< figure
  src="bfd-for-evpn-bgp-base-topology-light.svg"
  srcDark="bfd-for-evpn-bgp-base-topology-dark.svg"
  link="bfd-for-evpn-bgp-base-topology-light.svg"
  align="center"
>}}
```

Add `--dry-run` to inspect the draw.io commands without running it or creating
files. The opaque backdrop is added after each export, not by a CLI flag.
Use `--border 20` to override the default border.

## Border behavior in draw.io Desktop 32.6.1

A controlled export of a 200 × 100 rectangle with a 2px stroke gave:

| Requested border | SVG canvas | Left/top margin | Right/bottom margin |
| --- | --- | --- | --- |
| 0 | 203 × 103 | 0 | 1 |
| 10 | 233 × 133 | 10 | 21 |
| 20 | 263 × 163 | 20 | 41 |

Margins are measured from the outside of the rectangle's stroke. The extra
right/bottom space comes from the installed renderer: `export.js` increases the
graph's bounds by the border plus one pixel, then `Graph.getSvg` uses those bounds
and adds the SVG border again. This is independent of font embedding and of the
background added by this script.

The script deliberately continues to pass the requested border to draw.io; it
does not crop or compensate for this version-specific behavior. The extra space
does not clip the diagram. Recheck this small fixture when updating draw.io
before introducing a workaround.
