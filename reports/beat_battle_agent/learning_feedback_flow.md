# Beat Battle Agent Learning Feedback Flow

- Beat battle round lifecycle outputs and result logs are written to `datasets/beat_battle_agent/result_memory.jsonl`.
- `scripts/analyze_battle_results.py` converts result memory into aggregate metrics and winner-pattern studies.
- `scripts/train_battle_outcome_ranker.py` trains the local battle outcome ranker with truthful mode selection (`heuristic`, `local_train`, `holdout`).
- `scripts/train_composition_taste_ranker.py` ingests beat-battle-agent outcomes into combined taste-learning training rows.
- `scripts/run_music_understanding_loop.py` reports battle-result feedback counts and ranker status so taste/source loops remain closed-loop.
