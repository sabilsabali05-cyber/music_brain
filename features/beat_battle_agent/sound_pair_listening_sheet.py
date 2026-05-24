from __future__ import annotations

import json
from html import escape
from pathlib import Path

from .sound_pair_record_schema import BattleSoundPairRecord


def write_listening_sheet(records: list[BattleSoundPairRecord], html_path: Path, md_path: Path, review_notes_path: Path) -> None:
    html_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    review_notes_path.parent.mkdir(parents=True, exist_ok=True)

    lines = [
        "# Beat Battle Sound Pair Listening Sheet",
        "",
    ]
    html_rows: list[str] = []
    review_rows: list[dict[str, object]] = []
    for idx, record in enumerate(records, start=1):
        lines.extend(
            [
                f"## Pair {idx}: `{record.synplant_variation_id}`",
                f"- round_id: `{record.round_id}`",
                f"- provided_sound_id: `{record.provided_sound_id}`",
                f"- provided_sound_path: `{record.provided_local_copy_path or 'missing'}`",
                f"- synplant_variation_path: `{record.synplant_variation_path}`",
                f"- generation_status: `{record.synplant_generation_status}`",
                f"- blocker: `{record.synplant_blocker or 'none'}`",
                "- questions:",
            ]
        )
        for question in record.listening_questions:
            lines.append(f"  - {question}")
        lines.append("")

        html_rows.append(
            "<tr>"
            f"<td>{escape(record.synplant_variation_id)}</td>"
            f"<td>{escape(record.provided_sound_id)}</td>"
            f"<td>{escape(record.provided_local_copy_path or 'missing')}</td>"
            f"<td>{escape(record.synplant_variation_path)}</td>"
            f"<td>{escape(record.synplant_generation_status)}</td>"
            f"<td>{escape(record.synplant_blocker or 'none')}</td>"
            "</tr>"
        )
        review_rows.append(
            {
                "sound_pair_id": record.synplant_variation_id,
                "provided_sound_id": record.provided_sound_id,
                "winner": "skip",
                "preserve_character_score": 0,
                "uniqueness_score": 0,
                "mix_ready": False,
                "notes": "",
                "questions": list(record.listening_questions),
            }
        )

    md_path.write_text("\n".join(lines), encoding="utf-8")
    html_path.write_text(
        "\n".join(
            [
                "<html><head><meta charset='utf-8'><title>Beat Battle Sound Pair Listening Sheet</title></head><body>",
                "<h1>Beat Battle Sound Pair Listening Sheet</h1>",
                "<table border='1' cellpadding='6' cellspacing='0'>",
                "<thead><tr><th>sound_pair_id</th><th>provided_sound_id</th><th>provided_sound_path</th><th>synplant_variation_path</th><th>generation_status</th><th>blocker</th></tr></thead>",
                "<tbody>",
                *html_rows,
                "</tbody></table>",
                "<h2>Required Questions</h2>",
                "<ol>",
                *[f"<li>{escape(question)}</li>" for question in (records[0].listening_questions if records else [])],
                "</ol>",
                "</body></html>",
                "",
            ]
        ),
        encoding="utf-8",
    )
    review_notes_path.write_text(
        json.dumps({"reviews": review_rows}, indent=2, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )
