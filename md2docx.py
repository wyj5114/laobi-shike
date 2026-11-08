#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Markdown → Word（含图表、课件截图；公式降级为可读 Unicode）。

可作为模块调用：build(md_path, docx_path, base_dir)
"""
import os
import re
import sys

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

CJK = "微软雅黑"

SYMBOLS = [
    (r"\\mathbb\s*R", "ℝ"), (r"\\mathbb\s*N", "ℕ"), (r"\\mathbb\s*Z", "ℤ"),
    (r"\\operatorname\{arccot\}", "arccot"), (r"\\operatorname\{([a-zA-Z]+)\}", r"\1"),
    (r"\\text\{([^{}]*)\}", r"\1"), (r"\\mathrm\{([^{}]*)\}", r"\1"),
    (r"\\qquad", "    "), (r"\\quad", "  "), (r"\\,", " "), (r"\\;", " "), (r"\\!", ""),
    (r"\\left", ""), (r"\\right", ""), (r"\\displaystyle", ""),
    (r"\\Longleftrightarrow", "⇔"), (r"\\Leftrightarrow", "⇔"), (r"\\Longrightarrow", "⇒"),
    (r"\\Rightarrow", "⇒"), (r"\\iff", "⇔"), (r"\\sim", "~"), (r"\\approx", "≈"),
    (r"\\neq", "≠"), (r"\\ne\b", "≠"), (r"\\leqslant", "≤"), (r"\\geqslant", "≥"),
    (r"\\leq", "≤"), (r"\\le\b", "≤"), (r"\\geq", "≥"), (r"\\ge\b", "≥"),
    (r"\\pm", "±"), (r"\\mp", "∓"), (r"\\infty", "∞"), (r"\\to\b", "→"),
    (r"\\rightarrow", "→"), (r"\\in\b", "∈"), (r"\\notin", "∉"), (r"\\subset", "⊂"),
    (r"\\cup", "∪"), (r"\\cap", "∩"), (r"\\forall", "∀"), (r"\\exists", "∃"),
    (r"\\times", "×"), (r"\\cdot", "·"), (r"\\div", "÷"), (r"\\ast", "*"),
    (r"\\alpha", "α"), (r"\\beta", "β"), (r"\\gamma", "γ"), (r"\\delta", "δ"),
    (r"\\Delta", "Δ"), (r"\\theta", "θ"), (r"\\lambda", "λ"), (r"\\mu", "μ"),
    (r"\\pi", "π"), (r"\\varphi", "φ"), (r"\\phi", "φ"), (r"\\omega", "ω"),
    (r"\\Omega", "Ω"), (r"\\varepsilon", "ε"), (r"\\epsilon", "ε"), (r"\\sigma", "σ"),
    (r"\\sum", "Σ"), (r"\\prod", "∏"), (r"\\int", "∫"), (r"\\partial", "∂"),
    (r"\\cdots", "…"), (r"\\ldots", "…"), (r"\\dots", "…"),
    (r"\\sin", "sin"), (r"\\cos", "cos"), (r"\\tan", "tan"), (r"\\cot", "cot"),
    (r"\\sec", "sec"), (r"\\csc", "csc"), (r"\\arcsin", "arcsin"), (r"\\arccos", "arccos"),
    (r"\\arctan", "arctan"), (r"\\arccot", "arccot"), (r"\\ln", "ln"), (r"\\log", "log"),
    (r"\\exp", "exp"), (r"\\lim", "lim"), (r"\\max", "max"), (r"\\min", "min"),
    (r"\\sqrt", "√"), (r"\\%", "%"), (r"\\\{", "{"), (r"\\\}", "}"), (r"\\\\\\\\",
     "；"),
]

SUP = str.maketrans("0123456789+-=()n", "⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻⁼⁽⁾ⁿ")


def _frac(m):
    a, b = m.group(1), m.group(2)
    if re.search(r"[+\-− ]", a):
        a = f"({a})"
    if re.search(r"[+\-− ]", b):
        b = f"({b})"
    return f"{a}/{b}"


def latex_to_text(src):
    s = src
    for _ in range(6):
        new = re.sub(r"\\frac\{([^{}]*)\}\{([^{}]*)\}", _frac, s)
        new = re.sub(r"\\frac\s*(\d)\s*(\d)", lambda m: f"{m.group(1)}/{m.group(2)}", new)
        if new == s:
            break
        s = new
    s = re.sub(r"\\sqrt\{([^{}]*)\}", lambda m: "√(" + m.group(1) + ")", s)
    s = re.sub(r"\\sqrt\s*(\w)", lambda m: "√" + m.group(1), s)
    for pat, rep in SYMBOLS:
        s = re.sub(pat, rep, s)
    s = re.sub(r"\^\{([^{}]*)\}", lambda m: m.group(1).translate(SUP)
               if re.fullmatch(r"[0-9+\-=()n]+", m.group(1)) else "^(" + m.group(1) + ")", s)
    s = re.sub(r"_\{([^{}]*)\}", lambda m: "_(" + m.group(1) + ")", s)
    s = re.sub(r"\^(\w)", lambda m: m.group(1).translate(SUP)
               if m.group(1).isdigit() else "^" + m.group(1), s)
    s = s.replace("{", "").replace("}", "")
    return re.sub(r"[ \t]{2,}", " ", s).strip()


def conv_inline(text):
    text = re.sub(r"\$\$(.+?)\$\$", lambda m: latex_to_text(m.group(1)), text, flags=re.S)
    text = re.sub(r"\$(.+?)\$", lambda m: latex_to_text(m.group(1)), text, flags=re.S)
    return text


def add_runs(par, text, italic=False):
    for part in re.split(r"(\*\*[^*]+\*\*|`[^`]+`)", text):
        if not part:
            continue
        if part.startswith("**") and part.endswith("**"):
            r = par.add_run(part[2:-2])
            r.bold = True
        elif part.startswith("`") and part.endswith("`"):
            r = par.add_run(part[1:-1])
            r.font.name = "Consolas"
            r.font.color.rgb = RGBColor(0xB0, 0x30, 0x60)
        else:
            r = par.add_run(part)
        r.italic = italic
        r.font.name = CJK
        try:
            r._element.rPr.rFonts.set(qn("w:eastAsia"), CJK)
        except Exception:
            pass


def _styles(doc):
    st = doc.styles["Normal"]
    st.font.name = CJK
    st.font.size = Pt(10.5)
    st.element.rPr.rFonts.set(qn("w:eastAsia"), CJK)
    st.paragraph_format.space_after = Pt(4)
    st.paragraph_format.line_spacing = 1.25
    for name, size in (("Heading 1", 18), ("Heading 2", 15), ("Heading 3", 12.5)):
        try:
            h = doc.styles[name]
            h.font.name = CJK
            h.font.size = Pt(size)
            h.font.color.rgb = RGBColor(0x1A, 0x1A, 0x1A)
            h.element.rPr.rFonts.set(qn("w:eastAsia"), CJK)
        except Exception:
            pass


def build(md_path, docx_path, base_dir=None, with_images=True):
    base_dir = base_dir or os.path.dirname(os.path.abspath(md_path))
    md = open(md_path, encoding="utf-8").read()
    doc = Document()
    _styles(doc)
    sec = doc.sections[0]
    sec.left_margin = sec.right_margin = Cm(2.2)
    sec.top_margin = sec.bottom_margin = Cm(2.0)
    usable = Cm(21.0 - 4.4)

    lines = md.splitlines()
    i, img_count = 0, 0
    while i < len(lines):
        s = lines[i].strip()

        if not s or s == "---":
            i += 1
            continue

        if s.startswith("|") and i + 1 < len(lines) and re.match(r"^\|[\s:|-]+\|$", lines[i + 1].strip()):
            rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
                if not re.match(r"^[\s:|-]+$", "".join(cells)):
                    rows.append(cells)
                i += 1
            if rows:
                ncol = max(len(r) for r in rows)
                tbl = doc.add_table(rows=0, cols=ncol)
                tbl.style = "Table Grid"
                for ri, row in enumerate(rows):
                    cells = tbl.add_row().cells
                    for ci in range(ncol):
                        p = cells[ci].paragraphs[0]
                        p.paragraph_format.space_after = Pt(1)
                        add_runs(p, conv_inline(row[ci]) if ci < len(row) else "")
                        if ri == 0:
                            for r in p.runs:
                                r.bold = True
                doc.add_paragraph()
            continue

        m = re.match(r"!\[([^\]]*)\]\(([^)]+)\)", s)
        if m:
            if with_images:
                path = os.path.join(base_dir, m.group(2).replace("/", os.sep))
                if os.path.exists(path):
                    p = doc.add_paragraph()
                    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                    p.paragraph_format.space_before = Pt(6)
                    p.add_run().add_picture(path, width=int(usable * 0.92))
                    img_count += 1
                else:
                    print("  缺图:", path)
            i += 1
            continue

        if s.startswith("*") and s.endswith("*") and not s.startswith("**"):
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.paragraph_format.space_after = Pt(10)
            add_runs(p, conv_inline(s.strip("*")), italic=True)
            i += 1
            continue

        m = re.match(r"^(#{1,4})\s+(.*)$", s)
        if m:
            lvl = len(m.group(1))
            h = doc.add_heading("", level=0 if lvl == 1 else min(lvl - 1, 3))
            h.paragraph_format.space_before = Pt(14 if lvl <= 2 else 10)
            h.paragraph_format.space_after = Pt(6)
            add_runs(h, conv_inline(m.group(2).strip()))
            i += 1
            continue

        if s.startswith(">"):
            p = doc.add_paragraph()
            p.paragraph_format.left_indent = Cm(0.6)
            p.paragraph_format.space_after = Pt(2)
            add_runs(p, conv_inline(s.lstrip("> ").strip()), italic=True)
            for r in p.runs:
                r.font.size = Pt(9.5)
                r.font.color.rgb = RGBColor(0x55, 0x55, 0x55)
            i += 1
            continue

        m = re.match(r"^[-*]\s+(.*)$", s)
        if m:
            add_runs(doc.add_paragraph(style="List Bullet"), conv_inline(m.group(1)))
            i += 1
            continue
        m = re.match(r"^(\d+)[.)]\s+(.*)$", s)
        if m:
            add_runs(doc.add_paragraph(style="List Number"), conv_inline(m.group(2)))
            i += 1
            continue

        add_runs(doc.add_paragraph(), conv_inline(s))
        i += 1

    doc.save(docx_path)
    print(f"  docx: {len(doc.paragraphs)} 段, {len(doc.tables)} 表, {img_count} 图")
    return docx_path


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("用法: md2docx.py <input.md> <output.docx>")
        sys.exit(1)
    build(sys.argv[1], sys.argv[2], os.path.dirname(os.path.abspath(sys.argv[1])))
