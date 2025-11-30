"""
Evaluator Agent:
Validate hypotheses quantitatively, adjust confidence, and add notes.
"""

from typing import List, Dict, Any

class EvaluatorAgent:
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.roas_drop_pct = self.config.get("roas_drop_pct", 0.15)
        self.ctr_drop_pct = self.config.get("ctr_drop_pct", 0.10)
        self.min_impressions = self.config.get("min_impressions_for_confidence", 1000)

    def validate(self, insights: List[Dict[str, Any]], data_summary: Dict[str, Any]) -> List[Dict[str, Any]]:
        validated = []
        for ins in insights:
            c = dict(ins)  # shallow copy
            conf = float(c.get("confidence", 0.5))
            evidence = c.get("evidence", {})

            # If evidence contains roas_pct_change and ctr_pct_change, use thresholds to adjust confidence
            roas_pct = evidence.get("roas_pct_change")
            ctr_pct = evidence.get("ctr_pct_change")
            imps = evidence.get("impressions_last") or evidence.get("impressions_prev") or evidence.get("sample_impressions") or 0

            # boost confidence if impactful and impressions high
            if roas_pct is not None and ctr_pct is not None:
                if roas_pct <= -self.roas_drop_pct and ctr_pct <= -self.ctr_drop_pct and imps >= self.min_impressions:
                    conf = max(conf, 0.85)
                    c["validation_notes"] = "Strong numeric support: ROAS and CTR both decreased and impressions are high."
                elif roas_pct <= -self.roas_drop_pct and imps >= self.min_impressions:
                    conf = max(conf, 0.7)
                    c["validation_notes"] = "ROAS decreased meaningfully; investigate creatives and audiences."
                elif roas_pct >= self.roas_drop_pct:
                    conf = max(conf, 0.65)
                    c["validation_notes"] = "ROAS increased — positive signal."
                else:
                    # ambiguous evidence -> lower confidence
                    conf = min(conf, 0.5)
                    c["validation_notes"] = c.get("validation_notes", "") + " Ambiguous numeric signal."
            else:
                # fallback low-ctr sample handling
                sample_ctr = evidence.get("sample_ctr")
                sample_imps = evidence.get("sample_impressions", 0)
                if sample_ctr is not None:
                    if sample_ctr < 0.02 and sample_imps >= self.min_impressions:
                        conf = max(conf, 0.8)
                        c["validation_notes"] = "Low CTR on high impressions sample; creative likely underperforming."
                    elif sample_ctr < 0.03:
                        conf = max(conf, 0.65)
                    else:
                        conf = min(conf, conf)

            c["confidence"] = round(float(conf), 2)
            validated.append(c)
        return validated
