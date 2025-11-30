"""
Creative Agent:
Generates creative suggestions for low-CTR ads.
If config.use_llm is True, the agent prepares LLM prompts (does not call API by default).
"""

import random
from collections import Counter
from typing import Dict, Any, List

class CreativeAgent:
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.templates = [
            ("Feel the comfort all day", "Discover soft support that moves with you — no marks, all comfort.", "Shop Now"),
            ("Perfect fit, no compromise", "Find your size-forward fit with breathable fabric and gentle support.", "Find Your Fit"),
            ("Limited time: 20% off", "Grab the comfort bras you love — limited stock.", "Shop the Sale"),
            ("Say goodbye to discomfort", "Seamless design that stays invisible under clothes.", "Buy Now"),
            ("New: Breathable fabric", "Experience breathable material made for long days.", "Explore")
        ]
        random.seed(self.config.get("seed", 42))

    def generate(self, data_summary: Dict[str, Any]) -> List[Dict[str, Any]]:
        low = data_summary.get("low_ctr_ads", [])[:12]
        corpus = []
        for r in low:
            msg = r.get("creative_message") or ""
            corpus += [w.strip(".,!?\"'()").lower() for w in msg.split() if len(w) > 3]
        top_words = [w for w, _ in Counter(corpus).most_common(8)]

        out = []
        for i, r in enumerate(low):
            campaign = r.get("campaign_name") or "Unknown"
            original = r.get("creative_message") or ""
            impressions = int(r.get("impressions") or 0)
            ctr = float(r.get("ctr") or 0.0)
            # Build 3 suggestions using templates and dataset keywords
            suggestions = []
            for t in self.templates[:3]:
                suggestions.append({
                    "headline": t[0],
                    "message": t[1] + ((" Using themes: " + ", ".join(top_words[:3])) if top_words else ""),
                    "cta": t[2],
                    "reason_generated": "Template + dataset top words"
                })
            out.append({
                "campaign": campaign,
                "original_message": original,
                "impressions": impressions,
                "ctr": round(ctr, 4),
                "suggestions": suggestions
            })
        return out
