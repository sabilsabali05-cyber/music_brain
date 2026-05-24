from __future__ import annotations

from dataclasses import dataclass, field

from .just_intonation import ratio_to_cents


@dataclass(frozen=True)
class ParsedScala:
    valid: bool
    note_count: int = 0
    intervals_cents: list[float] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


def parse_scl_text(text: str) -> ParsedScala:
    try:
        raw = [line.strip() for line in text.splitlines()]
        lines = [line for line in raw if line and not line.startswith("!")]
        if len(lines) < 2:
            return ParsedScala(valid=False, errors=["Scala file missing required lines"])
        note_count = int(lines[1])
        values = lines[2 : 2 + note_count]
        if len(values) != note_count:
            return ParsedScala(valid=False, errors=["Scala interval count mismatch"])
        cents = [round(float(value), 6) if "." in value else round(ratio_to_cents(value), 6) for value in values]
        return ParsedScala(valid=True, note_count=note_count, intervals_cents=cents)
    except Exception as exc:  # noqa: BLE001
        return ParsedScala(valid=False, errors=[str(exc)])
