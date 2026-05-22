from __future__ import annotations

import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from features.rhythm_standard_fixtures import STANDARD_RHYTHM_FIXTURES
from features.rhythm_lexicon import classify_rhythm_pattern


def _is_positive(fixture: dict[str, object]) -> bool:
    return fixture.get("expected_family") not in {None, "", "None"}


def evaluate_rhythm_lexicon() -> dict[str, object]:
    results: list[dict[str, object]] = []
    confusion: dict[str, dict[str, int]] = {}
    exact_hits = 0
    in_top3 = 0
    false_positive = 0
    false_negative = 0
    ambiguous_count = 0
    overmatch_count = 0

    for fixture in STANDARD_RHYTHM_FIXTURES:
        if not isinstance(fixture, dict):
            continue
        classification = classify_rhythm_pattern(
            {
                "token_pattern": fixture.get("token_pattern", ""),
                "accent_pattern": fixture.get("accent_pattern", ""),
                "normalized_ratio_pattern": fixture.get("interval_ratios", []),
                "repeat_count": 4,
            }
        )
        expected_family = fixture.get("expected_family")
        predicted_family = classification.get("matched_family")
        top3 = [item.get("matched_family") for item in classification.get("top3_matches", []) if isinstance(item, dict)]
        match_strength = str(classification.get("match_strength", "weak"))
        is_positive = _is_positive(fixture)
        if is_positive and predicted_family == expected_family:
            exact_hits += 1
        if is_positive and expected_family in top3:
            in_top3 += 1
        if is_positive and predicted_family != expected_family and match_strength in {"strong", "moderate"}:
            false_negative += 1
        if not is_positive and match_strength in {"strong", "moderate"}:
            false_positive += 1
        if bool(classification.get("rhythm_family_ambiguous", False)) or match_strength == "ambiguous":
            ambiguous_count += 1
        if "all-onset token pattern" in [str(item) for item in classification.get("mismatch_reasons", [])]:
            overmatch_count += 1

        expected_key = str(expected_family or "negative")
        confusion.setdefault(expected_key, {})
        pred_key = str(predicted_family or "none")
        confusion[expected_key][pred_key] = confusion[expected_key].get(pred_key, 0) + 1

        result_item = {
            "fixture_id": fixture.get("fixture_id"),
            "expected_family": expected_family,
            "predicted_family": predicted_family,
            "match_strength": match_strength,
            "confidence": classification.get("confidence"),
            "top3_matches": top3,
            "ambiguous": classification.get("rhythm_family_ambiguous", False),
            "mismatch_reasons": classification.get("mismatch_reasons", []),
        }
        results.append(result_item)

    total = len(results)
    positives = sum(1 for item in STANDARD_RHYTHM_FIXTURES if isinstance(item, dict) and _is_positive(item))
    negatives = total - positives
    summary = {
        "total_fixtures": total,
        "positive_fixtures": positives,
        "negative_fixtures": negatives,
        "exact_family_hits": exact_hits,
        "expected_family_in_top3": in_top3,
        "false_positive_count": false_positive,
        "false_negative_count": false_negative,
        "ambiguous_count": ambiguous_count,
        "overmatch_count": overmatch_count,
        "confusion": confusion,
        "fixture_results": results,
    }
    return summary


def _write_reports(summary: dict[str, object]) -> tuple[Path, Path]:
    reports_dir = Path("reports") / "rhythm_lexicon"
    reports_dir.mkdir(parents=True, exist_ok=True)
    json_path = reports_dir / "evaluation_report.json"
    md_path = reports_dir / "evaluation_report.md"
    json_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    lines = [
        "# Rhythm Lexicon Evaluation Report",
        "",
        f"- total_fixtures: `{summary.get('total_fixtures')}`",
        f"- positive_fixtures: `{summary.get('positive_fixtures')}`",
        f"- negative_fixtures: `{summary.get('negative_fixtures')}`",
        f"- exact_family_hits: `{summary.get('exact_family_hits')}`",
        f"- expected_family_in_top3: `{summary.get('expected_family_in_top3')}`",
        f"- false_positive_count: `{summary.get('false_positive_count')}`",
        f"- false_negative_count: `{summary.get('false_negative_count')}`",
        f"- ambiguous_count: `{summary.get('ambiguous_count')}`",
        f"- overmatch_count: `{summary.get('overmatch_count')}`",
        "",
        "## Confusion Summary",
    ]
    confusion = summary.get("confusion", {})
    if isinstance(confusion, dict):
        for expected, row in confusion.items():
            lines.append(f"- expected `{expected}` -> `{json.dumps(row, ensure_ascii=True)}`")
    lines.extend(["", "## Fixture Results"])
    for item in summary.get("fixture_results", []):
        if not isinstance(item, dict):
            continue
        lines.append(
            f"- `{item.get('fixture_id')}` expected=`{item.get('expected_family')}` "
            f"predicted=`{item.get('predicted_family')}` strength=`{item.get('match_strength')}` "
            f"confidence=`{item.get('confidence')}`"
        )
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return json_path, md_path


def main() -> int:
    summary = evaluate_rhythm_lexicon()
    json_path, md_path = _write_reports(summary)
    print(f"RHYTHM_LEXICON_EVAL_JSON={json_path.as_posix()}")
    print(f"RHYTHM_LEXICON_EVAL_MD={md_path.as_posix()}")
    print(f"TOTAL_FIXTURES={summary.get('total_fixtures')}")
    print(f"EXACT_FAMILY_HITS={summary.get('exact_family_hits')}")
    print(f"EXPECTED_FAMILY_IN_TOP3={summary.get('expected_family_in_top3')}")
    print(f"FALSE_POSITIVE_COUNT={summary.get('false_positive_count')}")
    print(f"FALSE_NEGATIVE_COUNT={summary.get('false_negative_count')}")
    print(f"AMBIGUOUS_COUNT={summary.get('ambiguous_count')}")
    print(f"OVERMATCH_COUNT={summary.get('overmatch_count')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
