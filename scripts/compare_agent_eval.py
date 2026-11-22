"""Compare frozen agent benchmark reports and reject regressions."""
import json, sys
from pathlib import Path

baseline = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
candidate = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
regressions = [key for key, value in baseline.get("checks", {}).items()
               if value and not candidate.get("checks", {}).get(key, False)]
improved = [key for key, value in candidate.get("checks", {}).items()
            if value and not baseline.get("checks", {}).get(key, False)]
improved_metrics = [key for key, value in candidate.get("metrics", {}).items()
                    if value and not baseline.get("metrics", {}).get(key, False)]
passed = (candidate.get("score", 0) > baseline.get("score", 0)
          and not regressions and candidate.get("passed", False))
report = {"baseline_score": baseline.get("score", 0),
          "candidate_score": candidate.get("score", 0),
          "gain": round(candidate.get("score", 0) - baseline.get("score", 0), 4),
          "improved_capabilities": improved, "improved_metrics": improved_metrics, "regressions": regressions,
          "promotion": "eligible_for_pr" if passed else "rejected"}
print(json.dumps(report, ensure_ascii=False, indent=2))
raise SystemExit(0 if passed else 1)
