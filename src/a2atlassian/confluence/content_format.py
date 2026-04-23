"""Markdown → Confluence storage-format translator.

Block-oriented translator. Splits input on blank lines into blocks, then
translates each block independently. HTML blocks (starting with ``<``) pass
through unchanged — this is the hook that lets callers mix raw Confluence
storage (e.g. macros) with markdown.

Recursive `<details>` → ``expand`` macro handling lives in this module too,
but is implemented in a later task (Task 11).
"""

from __future__ import annotations

import re

_MENTION_RE = re.compile(r"@user:([A-Za-z0-9:_-]+)")
_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+)$")
_FENCE_OPEN_RE = re.compile(r"^```(\w+)?\s*$")


def markdown_to_storage(text: str) -> str:
    """Translate markdown source to Confluence storage format XHTML."""
    if not text:
        return ""
    blocks = _split_blocks(text)
    return "".join(_translate_block(b) for b in blocks)


def _split_blocks(text: str) -> list[str]:
    """Split on blank lines, preserving fenced code blocks as single blocks."""
    lines = text.splitlines()
    blocks: list[str] = []
    buf: list[str] = []
    in_fence = False
    for line in lines:
        if _FENCE_OPEN_RE.match(line.strip()):
            buf.append(line)
            if in_fence:
                blocks.append("\n".join(buf))
                buf = []
                in_fence = False
            else:
                in_fence = True
            continue
        if in_fence:
            buf.append(line)
            continue
        if line.strip() == "":
            if buf:
                blocks.append("\n".join(buf))
                buf = []
            continue
        buf.append(line)
    if buf:
        blocks.append("\n".join(buf))
    return blocks


def _translate_block(block: str) -> str:
    stripped = block.strip()
    if not stripped:
        return ""

    if stripped.startswith("<"):
        return stripped

    first = stripped.splitlines()[0]
    m = _FENCE_OPEN_RE.match(first)
    if m:
        lang = m.group(1) or ""
        body_lines = stripped.splitlines()[1:]
        if body_lines and _FENCE_OPEN_RE.match(body_lines[-1].strip()):
            body_lines = body_lines[:-1]
        body = "\n".join(body_lines)
        lang_param = f'<ac:parameter ac:name="language">{lang}</ac:parameter>' if lang else ""
        return (
            '<ac:structured-macro ac:name="code">'
            f"{lang_param}"
            f"<ac:plain-text-body><![CDATA[{body}]]></ac:plain-text-body>"
            "</ac:structured-macro>"
        )

    if _looks_like_table(stripped):
        return _translate_table(stripped)

    m = _HEADING_RE.match(stripped)
    if m:
        level = len(m.group(1))
        return f"<h{level}>{_inline(m.group(2))}</h{level}>"

    return f"<p>{_inline(stripped)}</p>"


def _looks_like_table(block: str) -> bool:
    lines = block.splitlines()
    if len(lines) < 2:
        return False
    if "|" not in lines[0]:
        return False
    sep = lines[1].strip()
    cells = [c.strip() for c in sep.strip("|").split("|") if c.strip()]
    return bool(cells) and all(set(c) <= set("-:") for c in cells)


def _split_row(row: str) -> list[str]:
    row = row.strip()
    row = row.removeprefix("|")
    row = row.removesuffix("|")
    return [cell.strip() for cell in row.split("|")]


def _translate_table(block: str) -> str:
    lines = block.splitlines()
    header_cells = _split_row(lines[0])
    data_rows = [_split_row(line) for line in lines[2:] if line.strip()]
    head = "".join(f"<th>{_inline(c)}</th>" for c in header_cells)
    rows = ["<tr>" + "".join(f"<td>{_inline(c)}</td>" for c in r) + "</tr>" for r in data_rows]
    return f"<table><tbody><tr>{head}</tr>{''.join(rows)}</tbody></table>"


def _inline(text: str) -> str:
    """Apply inline transforms: user mentions."""

    def _mention(match: re.Match[str]) -> str:
        account_id = match.group(1)
        return f'<ac:link><ri:user ri:account-id="{account_id}"/></ac:link>'

    return _MENTION_RE.sub(_mention, text)
