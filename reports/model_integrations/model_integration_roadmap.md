# Model Integration Roadmap

Ordered implementation path from privacy gate to rankers-first personalization before generator fine-tuning:

1. Fix privacy gate and redact public leak surfaces.
2. Re-run privacy scanner and direct grep leak gates.
3. Register all model families and default-unavailable integration metadata.
4. Ship local config template with every model disabled by default.
5. Run safe availability checker with no heavyweight imports by default.
6. Generate availability report for configured vs available model state.
7. Apply model policy hooks for authorization, reporting, and training safety.
8. Validate transcription outputs as witness_not_truth in downstream decisions.
9. Treat audio generation backends as reference_only unless explicitly enabled.
10. Use source separation outputs as weak evidence pending human review.
11. Train personalized rankers and preference models from authorized user feedback.
12. Only then evaluate generator fine-tuning with validated training corpus.
