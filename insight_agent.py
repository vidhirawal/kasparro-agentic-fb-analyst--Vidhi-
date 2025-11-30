"""
Insight Agent:
Generate hypotheses explaining ROAS/CTR patterns by comparing recent vs previous windows.
"""

import pandas as pd
import numpy as np
from datetime import timedelta
import os
from typing import Dict, Any, List

class InsightAgent:
    def __init__(self, config: Dict[str, Any], memory_path: str = None):
        self.config = config or {}
        self.recent_days = self.config.get("recent_window_days", 14)
        self.prev_days = self.config.get("previous_window_days", 30)
        self.roas_drop_pct = self.config.get("roas_drop_pct", 0.15)
        self.ctr_drop_pct = self.config.get("ctr_drop_pct", 0.10)
        self.memory_path = memory_path

    def read_full_df(self, data_path):
        try:
            df = pd.read_csv(data_path, parse_dates=["date"])
        except Exception:
            df = pd.read_csv(data_path, low_memory=False)
            if 'date' in df.columns:
                df['date'] = pd.to_datetime(df['date'], errors='coerce')
        for c in ['spend','impressions','clicks','ctr','purchases','revenue','roas']:
            if c in df.columns:
                df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)
        return df

    def generate_insights(self, data_summary: Dict[str, Any], plan: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Uses data_summary for quick checks, but reads the full CSV if necessary for time windows.
        """
        # Determine path from config
        data_path = self.config.get("data_path") or self.config.get("sample_data_path")
        if os.path.exists(data_path):
            df = self.read_full_df(data_path)
        else:
            # fallback to summary only
            df = None

        insights = []
        # If we have df, compute campaign-level time-window comparisons
        if df is not None and 'date' in df.columns:
            today = df['date'].max()
            recent_cut = today - pd.Timedelta(days=self.recent_days)
            prev_cut = recent_cut - pd.Timedelta(days=self.prev_days)

            for camp, g in df.groupby('campaign_name'):
                g = g.sort_values('date')
                last = g[g['date'] > recent_cut]
                prev = g[(g['date'] <= recent_cut) & (g['date'] > prev_cut)]
                if len(last) < 1 or len(prev) < 1:
                    continue
                roas_last = last['roas'].mean()
                roas_prev = prev['roas'].mean()
                ctr_last = last['ctr'].mean()
                ctr_prev = prev['ctr'].mean()
                spend_last = float(last['spend'].sum())
                spend_prev = float(prev['spend'].sum())
                imps_last = int(last['impressions'].sum())
                imps_prev = int(prev['impressions'].sum())

                roas_change = (roas_last - roas_prev) / (abs(roas_prev) + 1e-9)
                ctr_change = (ctr_last - ctr_prev) / (abs(ctr_prev) + 1e-9)

                evidence = {
                    "roas_prev": float(round(roas_prev, 4)),
                    "roas_last": float(round(roas_last, 4)),
                    "roas_pct_change": float(round(roas_change, 4)),
                    "ctr_prev": float(round(ctr_prev, 4)),
                    "ctr_last": float(round(ctr_last, 4)),
                    "ctr_pct_change": float(round(ctr_change, 4)),
                    "spend_prev": round(spend_prev, 2),
                    "spend_last": round(spend_last, 2),
                    "impressions_prev": imps_prev,
                    "impressions_last": imps_last
                }

                hypothesis = "No clear change"
                confidence = 0.4
                notes = ""

                # Detect meaningful ROAS drop
                if (roas_prev > 0) and (roas_last < roas_prev * (1 - self.roas_drop_pct)):
                    # check ctr drop
                    if (ctr_prev > 0) and (ctr_last < ctr_prev * (1 - self.ctr_drop_pct)):
                        hypothesis = "Creative underperformance leading to ROAS drop (CTR down)"
                        confidence = 0.75
                        notes = "ROAS down > threshold and CTR down > threshold"
                    else:
                        hypothesis = "Audience fatigue or targeting drift (spend up or conversions down)"
                        confidence = 0.6
                        notes = "ROAS down > threshold but CTR stable"
                elif roas_last > roas_prev * (1 + self.roas_drop_pct):
                    hypothesis = "ROAS improved — optimization or positive creative change"
                    confidence = 0.7
                    notes = "ROAS up > threshold"

                insights.append({
                    "campaign": str(camp),
                    "hypothesis": hypothesis,
                    "evidence": evidence,
                    "confidence": round(confidence, 2),
                    "validation_notes": notes
                })
        else:
            # Fallback: produce hypotheses from summary low_ctr_ads
            for row in data_summary.get("low_ctr_ads", [])[:10]:
                camp = row.get("campaign_name") or "Unknown"
                evidence = {
                    "sample_impressions": int(row.get("impressions") or 0),
                    "sample_ctr": float(row.get("ctr") or 0.0)
                }
                insights.append({
                    "campaign": camp,
                    "hypothesis": "Creative underperformance (low CTR sample)",
                    "evidence": evidence,
                    "confidence": 0.55,
                    "validation_notes": "Derived from low-CTR sample in summary"
                })
        # consult memory: nudge confidence for persistent insights
        if self.memory_path and os.path.exists(self.memory_path):
            try:
                import json
                with open(self.memory_path, "r") as fh:
                    mem = json.load(fh)
            except Exception:
                mem = []
            # build lookup of (campaign,hypothesis)
            mem_keys = {(m.get("campaign"), m.get("hypothesis")): m for m in mem}
            for ins in insights:
                key = (ins.get("campaign"), ins.get("hypothesis"))
                if key in mem_keys:
                    # persistent issue -> slightly increase confidence
                    ins["confidence"] = round(min(0.99, ins.get("confidence", 0.4) + 0.05), 2)
                    ins["validation_notes"] = (ins.get("validation_notes", "") or "") + " | persisted across runs in memory"
        return insights
