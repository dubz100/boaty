"""Shared PDF building blocks for Boaty engineering documents.

Used by the ADD (and later the ICD and subsystem specifications) so every
document shares one look: DejaVu fonts, A4, running footer with document
ID and issue, bookmarked headings and an automatic table of contents.
"""
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (Image, KeepTogether, NextPageTemplate,
                                PageBreak, Paragraph, Spacer, Table,
                                TableStyle)
from reportlab.platypus.doctemplate import BaseDocTemplate, PageTemplate
from reportlab.platypus.frames import Frame
from reportlab.platypus.tableofcontents import TableOfContents

__all__ = ["mm", "colors", "Spacer", "PageBreak", "KeepTogether",
           "NextPageTemplate", "Paragraph", "P", "H1", "H2", "bullets", "fig",
           "table", "callout", "cover", "control_and_contents", "Doc", "S",
           "INK", "INK2", "RULE", "TINT", "BLUE", "BLUE_T", "ORANGE",
           "ORANGE_T", "GREEN_T"]

FONT_DIR = Path("/usr/share/fonts/truetype/dejavu")
pdfmetrics.registerFont(TTFont("DV", FONT_DIR / "DejaVuSans.ttf"))
pdfmetrics.registerFont(TTFont("DVB", FONT_DIR / "DejaVuSans-Bold.ttf"))
pdfmetrics.registerFontFamily("DV", normal="DV", bold="DVB", italic="DV",
                              boldItalic="DVB")

INK = colors.HexColor("#0b0b0b")
INK2 = colors.HexColor("#52514e")
RULE = colors.HexColor("#d9d8d0")
TINT = colors.HexColor("#f4f3ee")
BLUE = colors.HexColor("#2a78d6")
BLUE_T = colors.HexColor("#e8f1fb")
ORANGE = colors.HexColor("#eb6834")
ORANGE_T = colors.HexColor("#fdf0ea")
GREEN_T = colors.HexColor("#e3f5ec")

S = {}
S["body"] = ParagraphStyle("body", fontName="DV", fontSize=9.2, leading=13,
                           textColor=INK, spaceAfter=5)
S["small"] = ParagraphStyle("small", parent=S["body"], fontSize=7.8,
                            leading=10.4, textColor=INK2)
S["cell"] = ParagraphStyle("cell", parent=S["body"], fontSize=7.8,
                           leading=10.2, spaceAfter=0)
S["cellb"] = ParagraphStyle("cellb", parent=S["cell"], fontName="DVB")
S["cellc"] = ParagraphStyle("cellc", parent=S["cell"], alignment=1)
S["note"] = ParagraphStyle("note", parent=S["cell"], textColor=INK2,
                           fontSize=7.2, leading=9.4)
S["h1"] = ParagraphStyle("h1", fontName="DVB", fontSize=14.5, leading=18,
                         textColor=INK, spaceBefore=2, spaceAfter=8)
S["h2"] = ParagraphStyle("h2", fontName="DVB", fontSize=10.8, leading=14,
                         textColor=INK, spaceBefore=9, spaceAfter=4)
S["caption"] = ParagraphStyle("cap", parent=S["small"], spaceBefore=3,
                              spaceAfter=10)
S["bullet"] = ParagraphStyle("bullet", parent=S["body"], leftIndent=11,
                             bulletIndent=2, spaceAfter=2.5)
S["title"] = ParagraphStyle("title", fontName="DVB", fontSize=28, leading=33)
S["sub"] = ParagraphStyle("sub", fontName="DV", fontSize=12.5, leading=17,
                          textColor=INK2)
S["toc1"] = ParagraphStyle("toc1", fontName="DVB", fontSize=9.4, leading=15)
S["toc2"] = ParagraphStyle("toc2", fontName="DV", fontSize=8.6, leading=12.5,
                           leftIndent=14)


def P(t, st="body"):
    return Paragraph(t, S[st])


def H1(t):
    p = Paragraph(t, S["h1"])
    p._toc = (0, t)
    return p


def H2(t):
    p = Paragraph(t, S["h2"])
    p._toc = (1, t)
    return p


def bullets(items):
    return [Paragraph(t, S["bullet"], bulletText="•") for t in items]


def fig(path, width_mm, caption=None):
    iw, ih = ImageReader(str(path)).getSize()
    img = Image(str(path), width=width_mm * mm, height=width_mm * mm * ih / iw)
    parts = [img]
    if caption:
        parts.append(P(caption, "caption"))
    return KeepTogether(parts)


def table(rows, widths, header=True, style_extra=(), font="cell"):
    data = []
    for i, r in enumerate(rows):
        data.append([Paragraph(c, S["cellb" if header and i == 0 else font])
                     if isinstance(c, str) else c for c in r])
    t = Table(data, colWidths=[w * mm for w in widths],
              repeatRows=1 if header else 0)
    st = [("VALIGN", (0, 0), (-1, -1), "TOP"),
          ("TOPPADDING", (0, 0), (-1, -1), 3),
          ("BOTTOMPADDING", (0, 0), (-1, -1), 3.2),
          ("LEFTPADDING", (0, 0), (-1, -1), 3.5),
          ("RIGHTPADDING", (0, 0), (-1, -1), 3.5),
          ("LINEBELOW", (0, 0), (-1, -1), 0.4, RULE)]
    if header:
        st += [("BACKGROUND", (0, 0), (-1, 0), TINT),
               ("LINEBELOW", (0, 0), (-1, 0), 0.8, INK2)]
    t.setStyle(TableStyle(st + list(style_extra)))
    return t


def callout(text, color=BLUE, bg=BLUE_T):
    t = Table([[Paragraph(text, S["body"])]], colWidths=[170 * mm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), bg),
        ("LINEBEFORE", (0, 0), (0, -1), 3, color),
        ("LEFTPADDING", (0, 0), (-1, -1), 9),
        ("RIGHTPADDING", (0, 0), (-1, -1), 9),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2)]))
    return t


def cover(title, subtitle, meta_rows):
    return [Spacer(1, 45 * mm), P("PROJECT BOATY", "small"),
            Spacer(1, 3 * mm), P(title, "title"), Spacer(1, 6 * mm),
            P(subtitle, "sub"), Spacer(1, 14 * mm),
            table(meta_rows, [32, 100], header=False),
            NextPageTemplate("body"), PageBreak()]


def control_and_contents(history_rows, guidance):
    toc = TableOfContents()
    toc.levelStyles = [S["toc1"], S["toc2"]]
    return [P("Document control", "h1"),
            table([["Issue", "Date", "Change", "By"]] + history_rows,
                  [16, 32, 90, 32]),
            Spacer(1, 4 * mm),
            table([["Role", "Name", "Signature / date"],
                   ["Author", "Claude, for Project Boaty", ""],
                   ["Reviewer / approver", "Project owner", ""]],
                  [45, 70, 55]),
            Spacer(1, 4 * mm), P(guidance, "small"), Spacer(1, 6 * mm),
            P("Contents", "h1"), toc, PageBreak()]


class Doc(BaseDocTemplate):
    def __init__(self, path, doc_id, doc_title, issue):
        super().__init__(str(path), pagesize=A4, leftMargin=20 * mm,
                         rightMargin=20 * mm, topMargin=18 * mm,
                         bottomMargin=22 * mm,
                         title=f"Boaty - {doc_title}", author="Project Boaty",
                         subject=doc_id)
        self.footer = f"{doc_id}  ·  {doc_title}  ·  {issue}"
        frame = Frame(self.leftMargin, self.bottomMargin, self.width,
                      self.height, id="f")
        self.addPageTemplates([
            PageTemplate("cover", [frame], onPage=self._cover),
            PageTemplate("body", [frame], onPage=self._furniture)])

    @staticmethod
    def _cover(c, d):
        c.saveState()
        c.setFillColor(BLUE)
        c.rect(0, 0, 8 * mm, A4[1], stroke=0, fill=1)
        c.restoreState()

    def _furniture(self, c, d):
        c.saveState()
        c.setFont("DV", 7.3)
        c.setFillColor(INK2)
        c.drawString(20 * mm, 12 * mm, self.footer)
        c.drawRightString(190 * mm, 12 * mm, f"page {d.page}")
        c.setStrokeColor(RULE)
        c.setLineWidth(0.5)
        c.line(20 * mm, 15 * mm, 190 * mm, 15 * mm)
        c.restoreState()

    def afterFlowable(self, f):
        if hasattr(f, "_toc"):
            level, text = f._toc
            key = f"h{id(f)}"
            self.canv.bookmarkPage(key)
            self.canv.addOutlineEntry(text, key, level=level,
                                      closed=level > 0)
            self.notify("TOCEntry", (level, text, self.page, key))
