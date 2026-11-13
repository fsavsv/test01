#!/usr/bin/env python3
"""
Validate docx content completeness — detect empty documents and headings with missing body content.

Usage:
    python validate_content.py document.docx

Exit codes:
    0  All checks passed
    1  Validation errors found (empty doc, empty sections, etc.)

Checks:
    1. Empty document — no text content at all
    2. Empty heading sections — a heading followed immediately by another heading (same or higher level) with no body paragraphs between them
    3. Hardcoded heading numbers — heading text starts with a number pattern like "1.", "2.1", "3.1.2", "一、", "（一）", "第一章"
"""

import re
import sys
import zipfile
from xml.etree import ElementTree as ET

WML_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


def _text(elem):
    """Extract concatenated text from all w:t descendants."""
    parts = []
    for t in elem.iter(f"{{{WML_NS}}}t"):
        if t.text:
            parts.append(t.text)
    return "".join(parts).strip()


DWP_NS = "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"
DWP14_NS = "http://schemas.microsoft.com/office/word/2010/wordprocessingDrawing"


def _heading_level(p_elem):
    """Return heading level (1-9) from pStyle, or 0 if not a heading."""
    ppr = p_elem.find(f"{{{WML_NS}}}pPr")
    if ppr is None:
        return 0
    pstyle = ppr.find(f"{{{WML_NS}}}pStyle")
    if pstyle is None:
        return 0
    val = pstyle.get(f"{{{WML_NS}}}val", "")
    m = re.match(r"[Hh]eading\s*(\d)", val)
    return int(m.group(1)) if m else 0


def _has_content(p_elem):
    """Check if a paragraph has meaningful content (text, images, or embedded objects)."""
    # Text content
    if _text(p_elem):
        return True
    # Images: <w:drawing> containing wp:inline or wp:anchor
    for drawing in p_elem.iter(f"{{{WML_NS}}}drawing"):
        for ns in (DWP_NS, DWP14_NS):
            if drawing.find(f"{{{ns}}}inline") is not None or drawing.find(f"{{{ns}}}anchor") is not None:
                return True
    # Embedded objects: <w:object>
    if p_elem.find(f".//{{{WML_NS}}}object") is not None:
        return True
    return False


_HARDCODED_NUM_RE = re.compile(
    r"^\d+(\.\d+)*[\.\s\uff0e\u3001]"            # Arabic: "1.", "2.1 ", "3.1.2."
    r"|^[一二三四五六七八九十百]+[、\.\uff0e\u3001]"  # Chinese: "一、", "二."
    r"|^[\uff08\(][一二三四五六七八九十百\d]+[\uff09\)]"  # Parenthesized: "（一）", "(1)"
    r"|^第[一二三四五六七八九十百\d]+[章节部篇]"      # Ordinal: "第一章", "第2节"
)


def validate(docx_path):
    errors = []

    with zipfile.ZipFile(docx_path, "r") as zf:
        if "word/document.xml" not in zf.namelist():
            errors.append("FATAL: word/document.xml not found in archive")
            return errors

        tree = ET.parse(zf.open("word/document.xml"))
        root = tree.getroot()

    body = root.find(f"{{{WML_NS}}}body")
    if body is None:
        errors.append("FATAL: <w:body> not found")
        return errors

    # Iterate all direct children of body (w:p, w:tbl, w:sdt, etc.)
    children = list(body)
    paragraphs = [c for c in children if c.tag == f"{{{WML_NS}}}p"]

    # --- Check 1: empty document ---
    has_any_text = any(_text(p) for p in paragraphs)
    has_any_table = any(c.tag == f"{{{WML_NS}}}tbl" for c in children)
    if not has_any_text and not has_any_table:
        errors.append("EMPTY_DOC: Document contains no text content at all")
        return errors

    # --- Check 2 & 3: per-heading analysis ---
    # Build index over body children: (child_index, heading_level, text) for headings
    heading_entries = []
    for i, child in enumerate(children):
        if child.tag == f"{{{WML_NS}}}p":
            lvl = _heading_level(child)
            if lvl > 0:
                heading_entries.append((i, lvl, _text(child)))

    for pos, (idx, lvl, htxt) in enumerate(heading_entries):
        # Check 3: hardcoded number prefix
        if _HARDCODED_NUM_RE.match(htxt):
            errors.append(
                f"HARDCODED_NUM: Heading {lvl} \"{htxt}\" has hardcoded number prefix — use numbering config instead"
            )

        # Check 2: empty section
        next_idx = heading_entries[pos + 1][0] if pos + 1 < len(heading_entries) else len(children)

        # Count content elements between this heading and next boundary
        content_count = 0
        for j in range(idx + 1, next_idx):
            child = children[j]
            # Tables count as content
            if child.tag == f"{{{WML_NS}}}tbl":
                content_count += 1
                continue
            # Paragraphs: check for text, images, or objects
            if child.tag == f"{{{WML_NS}}}p":
                if _heading_level(child) > 0:
                    break
                if _has_content(child):
                    content_count += 1

        if content_count == 0 and htxt:
            # Skip parent headings (immediately followed by a sub-heading)
            has_sub = False
            if pos + 1 < len(heading_entries):
                next_lvl = heading_entries[pos + 1][1]
                next_i = heading_entries[pos + 1][0]
                if next_lvl > lvl and next_i == idx + 1:
                    has_sub = True
            if not has_sub:
                errors.append(
                    f"EMPTY_SECTION: Heading {lvl} \"{htxt}\" has no body content before next heading"
                )

    return errors


def main():
    if len(sys.argv) < 2:
        print(f"Usage: python {sys.argv[0]} <document.docx>", file=sys.stderr)
        sys.exit(2)

    path = sys.argv[1]
    errors = validate(path)

    if not errors:
        print(f"PASSED: {path} — all content checks OK")
        sys.exit(0)
    else:
        print(f"FAILED: {path} — {len(errors)} issue(s) found:\n")
        for e in errors:
            print(f"  {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
