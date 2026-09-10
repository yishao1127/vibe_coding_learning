"""Safe HTML builders for model result cards."""

from __future__ import annotations

from html import escape
from typing import Iterable


def text(value: str) -> str:
    return escape(value).replace("\n", "<br>")


def bullets(items: Iterable[str], empty_message: str = "暂无补充内容。") -> str:
    values = [f"<li>{text(item)}</li>" for item in items if item.strip()]
    return f"<ul>{''.join(values)}</ul>" if values else f'<p class="muted">{text(empty_message)}</p>'


def section(title: str, body: str) -> str:
    return f'<section><h2>{text(title)}</h2>{body}</section>'


def result_card(title: str, body: str, variant: str = "") -> str:
    """Wrap a controlled result module in a visually distinct card."""
    classes = "result-card" + (f" result-card--{variant}" if variant else "")
    return f'<section class="{classes}"><h2>{text(title)}</h2>{body}</section>'


def result_grid(cards: list[str], columns: int = 2) -> str:
    """Lay controlled cards out in a QTextBrowser-compatible table grid."""
    if columns == 1:
        return "".join(
            f'<table class="result-grid" width="100%"><tr><td class="grid-cell" valign="top">{card}</td></tr></table>'
            for card in cards
        )

    rows = []
    for index in range(0, len(cards), 2):
        left = cards[index]
        right = cards[index + 1] if index + 1 < len(cards) else ""
        rows.append(
            '<tr>'
            f'<td class="grid-cell" width="50%" valign="top">{left}</td>'
            '<td class="grid-gutter" width="18"></td>'
            f'<td class="grid-cell" width="50%" valign="top">{right}</td>'
            '</tr>'
        )
    return f'<table class="result-grid" width="100%" cellspacing="0" cellpadding="0">{"".join(rows)}</table>'


def page_document(body: str) -> str:
    return f"""<!DOCTYPE html>
<html><head><style>
body {{ background: #F7F9FC; color: #26354C; font-family: "Source Han Sans CN", "Microsoft YaHei UI", "Segoe UI"; font-size: 12pt; line-height: 1.42; margin: 0; }}
h1 {{ color: #172B4D; font-size: 16pt; margin: 0 0 4px; }}
h2 {{ color: #34445C; font-size: 10.5pt; font-weight: 700; margin: 0 0 9px; }}
p {{ margin: 5px 0; }} ul {{ margin: 4px 0; padding-left: 21px; }} li {{ margin: 3px 0; }}
.result-card {{ background: #FFFFFF; border: 1px solid #C9D5E5; border-radius: 10px; margin: 0 0 18px; padding: 14px 16px; }}
.result-card--primary {{ background: #F1F6FF; border: 2px solid #A9C7FA; }}
.result-card--compact {{ padding-top: 12px; padding-bottom: 12px; }}
.hero {{ background: #E8F1FF; border-left: 4px solid #155EEF; border-radius: 6px; color: #123B80; font-size: 14pt; font-weight: 600; padding: 12px 14px; }}
.meta {{ color: #66758A; font-size: 10.5pt; }} .muted {{ color: #748196; }}
.alternative {{ background: #F8FAFD; border: 1px solid #E4EAF3; border-radius: 7px; margin: 8px 0 0; padding: 10px 12px; }}
.example {{ background: #F8FAFD; border-radius: 7px; margin: 8px 0 0; padding: 10px 12px; }}
.example .english {{ color: #223B61; font-weight: 600; }} .example .chinese {{ color: #66758A; margin-top: 3px; }}
.issue {{ background: #FFF8ED; border-left: 4px solid #E59B16; border-radius: 8px; margin: 10px 0; padding: 11px 14px; }}
.tag {{ background: #E8F0FE; border-radius: 10px; color: #155EEF; display: inline-block; font-size: 10pt; font-weight: 700; padding: 2px 9px; }}
.correction {{ color: #087443; font-weight: 700; }}
table {{ border-collapse: collapse; width: 100%; }} td {{ border-bottom: 1px solid #E8EDF4; padding: 7px 5px; }} td:first-child {{ color: #66758A; width: 38%; }}
.result-grid {{ border-collapse: collapse; margin: 0 0 12px; }}
.result-grid td.grid-cell {{ border: none; color: #26354C; padding: 0; vertical-align: top; width: 50%; }}
.result-grid td.grid-gutter {{ border: none; padding: 0; width: 18px; }}
.result-grid .result-card {{ margin: 0 0 18px; }}
</style></head><body>{body}</body></html>"""
