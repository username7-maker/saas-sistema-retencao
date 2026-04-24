from __future__ import annotations

import argparse
import html
import re
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import ListFlowable, ListItem, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


ROOT = Path(__file__).resolve().parents[1]
DOCS_DIR = ROOT / "docs" / "training"


def build_styles():
    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name="TitleAiGym",
            parent=styles["Title"],
            fontName="Helvetica-Bold",
            fontSize=20,
            leading=24,
            spaceAfter=12,
            textColor=colors.HexColor("#111827"),
            alignment=TA_CENTER,
        )
    )
    styles.add(
        ParagraphStyle(
            name="H1AiGym",
            parent=styles["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=16,
            leading=20,
            spaceBefore=10,
            spaceAfter=8,
            textColor=colors.HexColor("#111827"),
        )
    )
    styles.add(
        ParagraphStyle(
            name="H2AiGym",
            parent=styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=13,
            leading=17,
            spaceBefore=10,
            spaceAfter=6,
            textColor=colors.HexColor("#1f2937"),
        )
    )
    styles.add(
        ParagraphStyle(
            name="H3AiGym",
            parent=styles["Heading3"],
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=14,
            spaceBefore=8,
            spaceAfter=4,
            textColor=colors.HexColor("#374151"),
        )
    )
    styles.add(
        ParagraphStyle(
            name="BodyAiGym",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=10,
            leading=13,
            spaceAfter=4,
            textColor=colors.HexColor("#111827"),
        )
    )
    styles.add(
        ParagraphStyle(
            name="SmallAiGym",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=8.5,
            leading=10.5,
            spaceAfter=2,
            textColor=colors.HexColor("#4b5563"),
        )
    )
    return styles


def inline_markup(text: str) -> str:
    escaped = html.escape(text.strip())
    escaped = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", escaped)
    escaped = re.sub(r"`(.+?)`", r"<font name='Courier'>\1</font>", escaped)
    escaped = re.sub(r"\[(.+?)\]\((.+?)\)", r"<u>\1</u> (\2)", escaped)
    return escaped


def is_numbered(line: str) -> bool:
    return bool(re.match(r"^\d+\.\s+", line))


def parse_table_row(line: str) -> list[str]:
    cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
    return cells


def table_column_widths(num_cols: int) -> list[float]:
    usable_width = A4[0] - (16 * mm * 2)
    if num_cols == 0:
        return []
    if num_cols == 6:
        return [30 * mm, 25 * mm, 22 * mm, 20 * mm, 42 * mm, 42 * mm]
    return [usable_width / num_cols] * num_cols


def render_markdown_to_story(markdown_text: str):
    styles = build_styles()
    story = []
    lines = markdown_text.splitlines()
    i = 0
    first_title_seen = False

    while i < len(lines):
        line = lines[i].rstrip()
        stripped = line.strip()

        if not stripped:
            i += 1
            continue

        if stripped.startswith("# "):
            style_name = "TitleAiGym" if not first_title_seen else "H1AiGym"
            first_title_seen = True
            story.append(Paragraph(inline_markup(stripped[2:]), styles[style_name]))
            story.append(Spacer(1, 2))
            i += 1
            continue

        if stripped.startswith("## "):
            story.append(Paragraph(inline_markup(stripped[3:]), styles["H1AiGym"]))
            i += 1
            continue

        if stripped.startswith("### "):
            story.append(Paragraph(inline_markup(stripped[4:]), styles["H2AiGym"]))
            i += 1
            continue

        if stripped.startswith("**") and stripped.endswith("**") and len(stripped) > 4:
            story.append(Paragraph(inline_markup(stripped), styles["H3AiGym"]))
            i += 1
            continue

        if stripped.startswith("|"):
            table_lines = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                current = lines[i].strip()
                if not re.match(r"^\|\s*-", current):
                    table_lines.append(current)
                i += 1
            if table_lines:
                rows = [parse_table_row(row) for row in table_lines]
                cell_styles = build_styles()
                table_data = []
                for row_index, row in enumerate(rows):
                    style = cell_styles["SmallAiGym"] if row_index else cell_styles["H3AiGym"]
                    table_data.append([Paragraph(inline_markup(cell), style) for cell in row])
                table = Table(table_data, colWidths=table_column_widths(len(rows[0])), repeatRows=1)
                table.setStyle(
                    TableStyle(
                        [
                            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e5e7eb")),
                            ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#111827")),
                            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#d1d5db")),
                            ("BACKGROUND", (0, 1), (-1, -1), colors.white),
                            ("VALIGN", (0, 0), (-1, -1), "TOP"),
                            ("LEFTPADDING", (0, 0), (-1, -1), 5),
                            ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                            ("TOPPADDING", (0, 0), (-1, -1), 4),
                            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                        ]
                    )
                )
                story.append(table)
                story.append(Spacer(1, 6))
            continue

        if stripped.startswith("- "):
            items = []
            while i < len(lines) and lines[i].strip().startswith("- "):
                item_text = lines[i].strip()[2:].strip()
                items.append(ListItem(Paragraph(inline_markup(item_text), styles["BodyAiGym"])))
                i += 1
            story.append(ListFlowable(items, bulletType="bullet", start="circle", leftIndent=14))
            story.append(Spacer(1, 4))
            continue

        if is_numbered(stripped):
            items = []
            while i < len(lines) and is_numbered(lines[i].strip()):
                item_text = re.sub(r"^\d+\.\s+", "", lines[i].strip())
                items.append(ListItem(Paragraph(inline_markup(item_text), styles["BodyAiGym"])))
                i += 1
            story.append(ListFlowable(items, bulletType="1", leftIndent=14))
            story.append(Spacer(1, 4))
            continue

        paragraph_lines = [stripped]
        i += 1
        while i < len(lines):
            next_line = lines[i].strip()
            if not next_line:
                break
            if next_line.startswith(("# ", "## ", "### ", "- ", "|")) or is_numbered(next_line):
                break
            if next_line.startswith("**") and next_line.endswith("**"):
                break
            paragraph_lines.append(next_line)
            i += 1
        story.append(Paragraph(inline_markup(" ".join(paragraph_lines)), styles["BodyAiGym"]))

    return story


def export_pdf(markdown_path: Path, pdf_path: Path) -> None:
    story = render_markdown_to_story(markdown_path.read_text(encoding="utf-8"))
    document = SimpleDocTemplate(
        str(pdf_path),
        pagesize=A4,
        leftMargin=16 * mm,
        rightMargin=16 * mm,
        topMargin=16 * mm,
        bottomMargin=16 * mm,
        title=markdown_path.stem,
        author="Codex",
    )
    document.build(story)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input",
        default=str(DOCS_DIR / "ai-gym-os-guia-operacional.md"),
    )
    parser.add_argument(
        "--output",
        default=str(DOCS_DIR / "ai-gym-os-guia-operacional.pdf"),
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)
    export_pdf(input_path, output_path)
    print(output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
