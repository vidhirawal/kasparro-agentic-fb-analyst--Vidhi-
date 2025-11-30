from src.agents.evaluator_agent import EvaluatorAgent

def test_evaluator_low_ctr_boosts_confidence():
    cfg = {"roas_drop_pct": 0.15, "ctr_drop_pct": 0.10, "min_impressions_for_confidence": 1000}
    evalr = EvaluatorAgent(cfg)
    insights = [
        {
            "campaign": "Test Campaign",
            "hypothesis": "creative underperformance",
            "evidence": {"sample_impressions": 2000, "sample_ctr": 0.015},
            "confidence": 0.5
        }
    ]
    validated = evalr.validate(insights, {})
    assert validated[0]["confidence"] >= 0.8
