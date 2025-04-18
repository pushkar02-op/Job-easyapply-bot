import json
import os
from datetime import datetime

class JobTracker:
    def __init__(self, path="applied_jobs.json"):
        self.path = path
        self.jobs = self._load_applied_jobs()

    def _load_applied_jobs(self):
        if not os.path.exists(self.path):
            return []
        with open(self.path, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return []

    def has_applied(self, job_id):
        return any(job.get("job_id") == job_id for job in self.jobs)

    def mark_as_applied(self, job_id, job_title, company):
        self.jobs.append({
            "job_id": job_id,
            "job_title": job_title,
            "company": company,
            "applied_at": datetime.utcnow().isoformat()
        })
        self._save()

    def _save(self):
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self.jobs, f, indent=2, ensure_ascii=False)
