"""
Data Agent:
Loads CSV, cleans columns, computes compact summary for downstream agents.
"""

import pandas as pd
import numpy as np

class DataAgent:
    def __init__(self, path):
        self.path = path

    def load_df(self):
        try:
            df = pd.read_csv(self.path, parse_dates=["date"])
        except Exception:
            df = pd.read_csv(self.path, low_memory=False)
            if "date" in df.columns:
                df["date"] = pd.to_datetime(df["date"], errors="coerce")
        return df

    def load_and_summarize(self):
        df = self.load_df()
        # ensure expected columns
        expected = ['campaign_name','adset_name','date','spend','impressions','clicks','ctr','purchases','revenue','roas','creative_type','creative_message','audience_type','platform','country']
        for c in expected:
            if c not in df.columns:
                df[c] = np.nan
        # numeric coercion
        for n in ['spend','impressions','clicks','ctr','purchases','revenue','roas']:
            if n in df.columns:
                df[n] = pd.to_numeric(df[n], errors='coerce').fillna(0)

        overall = {
            "date_range": [str(df['date'].min().date()) if 'date' in df.columns else None,
                           str(df['date'].max().date()) if 'date' in df.columns else None],
            "total_spend": float(df['spend'].sum()),
            "total_impressions": int(df['impressions'].sum()),
            "total_clicks": int(df['clicks'].sum()),
            "average_ctr": float(df['ctr'].replace([np.inf, -np.inf], np.nan).dropna().mean() or 0),
            "total_revenue": float(df['revenue'].sum()),
            "average_roas": float(df['roas'].replace([np.inf, -np.inf], np.nan).dropna().mean() or 0),
            "n_rows": int(len(df))
        }

        by_campaign = (df.groupby("campaign_name")
                       .agg(spend=("spend","sum"),
                            impressions=("impressions","sum"),
                            clicks=("clicks","sum"),
                            ctr=("ctr","mean"),
                            purchases=("purchases","sum"),
                            revenue=("revenue","sum"),
                            roas=("roas","mean"))
                       .reset_index().fillna(0).to_dict(orient="records"))

        # low CTR identify
        if 'ctr' in df.columns and not df['ctr'].isnull().all():
            try:
                q = float(df['ctr'].quantile(0.25))
            except Exception:
                q = df['ctr'].mean()
        else:
            q = 0.0

        low_ctr_ads = (df[df['ctr'] <= q]
                       .loc[:, ['campaign_name','adset_name','creative_message','creative_type','impressions','clicks','ctr','spend','roas','audience_type']]
                       .fillna("").to_dict(orient="records"))

        return {"overall": overall, "by_campaign": by_campaign, "low_ctr_ads": low_ctr_ads, "raw_head": df.head(5).to_dict(orient="records")}
