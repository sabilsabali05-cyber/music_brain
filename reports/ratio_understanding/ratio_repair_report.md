# Ratio Repair Report

- baseline_v1_score: `0.120831`
- baseline_v2_score: `0.547743`
- repaired_score: `0.547743`
- final_controls_within_tolerance: `3`

## Attempt History
- attempt 1: score=`0.547743` controls_within_tolerance=`3` failures=`['5:3', '5:4']`
- attempt 2: score=`0.547743` controls_within_tolerance=`3` failures=`['5:3', '5:4']`
- attempt 3: score=`0.547743` controls_within_tolerance=`3` failures=`['5:3', '5:4']`

## Guardrails
- Repair loop does not fake success by editing report files.
- Best compliance + warning profile is selected within max 3 attempts.

