from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def rank_round_drafts(project_root: Path, round_id: str) -> dict[str, Any]:
    candidates_path = project_root / "outputs" / "beat_battle_agent" / round_id / "ranked" / "draft_candidates.json"
    if not candidates_path.exists():
        return {"round_id": round_id, "ranked_count": 0, "blocker": "missing_draft_candidates"}
    rows = json.loads(candidates_path.read_text(encoding="utf-8"))
    rows = rows if isinstance(rows, list) else []
    ranked = sorted(rows, key=lambda row: float(row.get("ranker_input_score", 0.0)), reverse=True)
    ranked_path = project_root / "outputs" / "beat_battle_agent" / round_id / "ranked" / "ranked_drafts.json"
    ranked_path.parent.mkdir(parents=True, exist_ok=True)
    ranked_path.write_text(json.dumps(ranked, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    selected = ranked[0] if ranked else {}
    selected_path = project_root / "outputs" / "beat_battle_agent" / round_id / "selected_submission" / "selected_submission.json"
    selected_path.parent.mkdir(parents=True, exist_ok=True)
    selected_path.write_text(json.dumps(selected, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    report = {
        "round_id": round_id,
        "ranked_count": len(ranked),
        "selected_submission_path": selected_path.as_posix(),
        "ranked_drafts_path": ranked_path.as_posix(),
        "blocker": "" if ranked else "no_rankable_drafts",
    }
    report_root = project_root / "reports" / "beat_battle_agent"
    report_root.mkdir(parents=True, exist_ok=True)
    (report_root / f"{round_id}_draft_ranker.json").write_text(json.dumps(report, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    (report_root / f"{round_id}_draft_ranker.md").write_text(
        "\n".join(
            [
                "# Battle Draft Ranker",
                "",
                f"- round_id: `{round_id}`",
                f"- ranked_count: `{len(ranked)}`",
                f"- selected_submission_path: `{selected_path.as_posix()}`",
                f"- blocker: `{report['blocker'] or 'none'}`",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return report
