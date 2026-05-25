# Ratio Control Failure Analysis (v1)

- source_eval: `reports/ratio_understanding/ratio_controlled_generation_eval.json`
- baseline_compliance_score: `0.120831`
- failed_controls: `4/5`

## Failed Controls
- `3:2` requested=`1.5` actual=`1.053639846743295` error=`0.44636015325670503` tolerance=`0.08` root_cause=`phrase`
- `5:3` requested=`1.6666666666666667` actual=`9.72` error=`8.053333333333333` tolerance=`0.08` root_cause=`rhythm quantization`
- `5:4` requested=`1.25` actual=`0.02881844380403458` error=`1.2211815561959654` tolerance=`0.08` root_cause=`interval detection`
- `8:5` requested=`1.6` actual=`1.727735368956743` error=`0.12773536895674284` tolerance=`0.1` root_cause=`density model`

## Diagnosis Summary
- Generator and evaluator used coarse proxies with no explicit phrase/chord/rhythm boundary planning.
- Rhythm and interval controls had the largest structural mismatch between requested and measured quantities.
- Density metric tracked a broad split rather than strongest peak timing, reducing control precision.
- Compliance repair should focus on plan-first generation and plan-aware measurement without hard-coded passes.
