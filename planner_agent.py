"""
Planner Agent:
Decomposes user query into a structured list of tasks.
"""

from typing import Dict, Any

class PlannerAgent:
    def __init__(self):
        pass

    def generate_plan(self, query: str) -> Dict[str, Any]:
        """
        Returns a small plan JSON describing tasks.
        """
        plan = {
            "original_query": query,
            "tasks": [
                {"id": "t1", "action": "load_and_summarize_data", "priority": 1},
                {"id": "t2", "action": "generate_insights", "priority": 2},
                {"id": "t3", "action": "validate_insights", "priority": 3},
                {"id": "t4", "action": "generate_creatives", "priority": 4},
                {"id": "t5", "action": "persist_and_report", "priority": 5}
            ]
        }
        return plan
