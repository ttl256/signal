---
date: '2026-11-08T17:59:46+03:00'
draft: true
title: 'Cheatsheet'
---

## Running the local server

```bash
hugo server --buildDrafts --disableFastRender
```

## Create a new post

```bash
hugo new content posts/$title/index.md
```

## Footnotes

Lorem ipsum[^1]

[^1]: dolor sit amet

## Details (cut)

{{< details summary="See the details" >}}
This is a **bold** word.

```
And even a code block
```
{{< /details >}}

## Figure

{{< figure
  src="example-topology.svg"
  align="center"
  caption="Lorem ipsum dolor sit amet, consectetur adipiscing elit."
>}}
