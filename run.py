#!/usr/bin/env python3
"""
Orchestrator for the Agentic FB Ads Analyst.

Usage:
    python src/orchestrator/run.py "Analyze ROAS drop" --config config/config.yaml --sample
"""

import os
import sys
import json
import argparse
import random
from datetime import datetime
import yaml

# Ensure src package path so local imports work when running as script
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from agents.planner_agent import PlannerAgent
from agents.data_agent import DataAgent
from agents.insight_agent import InsightAgent
from agents.evaluator_agent import EvaluatorAgent
from agents.creative_agent import CreativeAgent
from utils.logger import log_event
from utils.io_utils import write_json, read_json

def load_config(path):
    with open(path, "r") as fh:
        return yaml.safe_load(fh)

def append_memory(memory_path, validated_insights, threshold=0.5):
    existing = []
    if os.path.exists(memory_path):
        try:
            existing = read_json(memory_path)
        except Exception:
            existing = []
    now = datetime.utcnow().isoformat() + "Z"
    for ins in validated_insights:
        if ins.get("confidence", 0) >= threshold:
            rec = {
                "campaign": ins.get("campaign"),
                "hypothesis": ins.get("hypothesis"),
                "confidence": ins.get("confidence"),
                "last_seen": now
            }
            # dedupe
            found = False
            for r in existing:
                if r.get("campaign") == rec["campaign"] and r.get("hypothesis") == rec["hypothesis"]:
                    # update
                    r["last_seen"] = now
                    r["confidence"] = max(r.get("confidence", 0), rec["confidence"])
                    found = True
                    break
            if not found:
                existing.append(rec)
    write_json(memory_path, existing)

def run_pipeline(config_path="config/config.yaml", query="Analyze ROAS drop", sample=False, seed=None):
    cfg = load_config(config_path)
    if seed is None:
        seed = cfg.get("seed", 42)
    random.seed(seed)

    data_path = cfg.get("sample_data_path") if (sample or cfg.get("use_sample_default")) else cfg.get("data_path")
    reports_path = cfg.get("reports_path", "reports")
    logs_path = cfg.get("logs_path", "logs/run_logs.json")
    memory_path = cfg.get("memory_path", "memory/short_term_memory.json")

    os.makedirs(reports_path, exist_ok=True)
    os.makedirs(os.path.dirname(logs_path), exist_ok=True)
    os.makedirs(os.path.dirname(memory_path), exist_ok=True)

    start = datetime.utcnow().isoformat() + "Z"
    log_event("START_RUN", {"query": query, "data_path": data_path, "time": start, "seed": seed})

    # Planner
    planner = PlannerAgent()
    plan = planner.generate_plan(query)
    log_event("PLAN_CREATED", plan)

    # Data Agent
    data_agent = DataAgent(data_path)
    data_summary = data_agent.load_and_summarize()
    log_event("DATA_SUMMARY", {"overall": data_summary.get("overall", {})})

    # Insight Agent
    insight_agent = InsightAgent(cfg, memory_path=memory_path)
    insights = insight_agent.generate_insights(data_summary, plan)
    log_event("INSIGHTS_GENERATED", {"count": len(insights)})

    # Evaluator
    evaluator = EvaluatorAgent(cfg)
    validated = evaluator.validate(insights, data_summary)
    log_event("INSIGHTS_VALIDATED", {"count": len(validated)})

    # Persist validated insights to reports
    write_json(os.path.join(reports_path, "insights.json"), validated)

    # Append to memory (short-term)
    append_memory(memory_path, validated, threshold=cfg.get("confidence_persist_threshold", 0.5))

    # Creative Agent
    creative_agent = CreativeAgent(cfg)
    creatives = creative_agent.generate(data_summary)
    write_json(os.path.join(reports_path, "creatives.json"), creatives)
    log_event("CREATIVES_GENERATED", {"count": len(creatives)})

    # Build a human-friendly report
    report_md = []
    report_md.append("# Agentic Facebook Performance Analyst — Run Report")
    report_md.append(f"Run time (UTC): {start}\n")
    overall = data_summary.get("overall", {})
    report_md.append("## Data Summary")
    report_md.append(f"- Date range: {overall.get('date_range')}")
    report_md.append(f"- Total spend: ${overall.get('total_spend', 0):.2f}")
    report_md.append(f"- Total impressions: {overall.get('total_impressions', 0):,}")
    report_md.append(f"- Average CTR: {overall.get('average_ctr', 0):.4f}")
    report_md.append(f"- Average ROAS: {overall.get('average_roas', 0):.3f}\n")
    report_md.append("## Insights")
    for ins in validated:
        report_md.append(f"### Campaign: {ins.get('campaign')}")
        report_md.append(f"- Hypothesis: {ins.get('hypothesis')}")
        report_md.append(f"- Confidence: {ins.get('confidence')}")
        report_md.append(f"- Evidence: {ins.get('evidence')}\n")
    report_md.append("## Creative Suggestions (sample)")
    for c in creatives[:6]:
        report_md.append(f"### Campaign: {c.get('campaign')}")
        report_md.append(f"- Original message: {c.get('original_message')}")
        report_md.append("- Suggestions:")
        for s in c.get("suggestions", []):
            report_md.append(f"  - Headline: {s.get('headline')}")
            report_md.append(f"    Message: {s.get('message')}")
            report_md.append(f"    CTA: {s.get('cta')}")
        report_md.append("\n")
    with open(os.path.join(reports_path, "report.md"), "w") as fh:
        fh.write("\n".join(report_md))

    end = datetime.utcnow().isoformat() + "Z"
    log_event("RUN_COMPLETE", {"insights": len(validated), "creatives": len(creatives), "start": start, "end": end})
    print(f"Run complete. Reports in {reports_path}. Logs in {logs_path}. Memory in {memory_path}.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("query", nargs="?", default="Analyze ROAS drop")
    parser.add_argument("--config", default="config/config.yaml")
    parser.add_argument("--sample", action="store_true", help="Use sample data for reproducible, fast runs")
    parser.add_argument("--seed", type=int, default=None, help="Override config seed")
    args = parser.parse_args()
    run_pipeline(config_path=args.config, query=args.query, sample=args.sample, seed=args.seed)
