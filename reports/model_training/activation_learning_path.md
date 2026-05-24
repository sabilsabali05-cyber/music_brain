# Activation Learning Path

- status: `planned`
- model_training_has_occurred: `False`
- policy_scope: `feedback_and_preference_learning_only`

## Policy

- User feedback is allowed for ranker/preference training when authorization is valid.
- Generated MIDI is trainable only after explicit human review.
- Separated stems are weak evidence and not ground truth training targets.
- Transcription witness outputs are witness_not_truth, never direct truth labels.
- Splice and production-only material is excluded from training.
- Copyrighted or unknown authorization data is excluded from training.
- Fine-tuning requires a validated corpus and human review approval.
