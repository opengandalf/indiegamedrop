#!/usr/bin/env python3
"""Export OpenClaw cron job status to JSON for dashboard consumption."""
import json
import os
import subprocess
import sys

OUTPUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cron_status.json')

# Only IndieGameDrop job IDs
IGD_JOB_IDS = {
    "0249f513-76c1-4e09-b54a-b3d9abf8a516",  # Batch enrich (early morning)
    "518a9a1e-d964-4704-813d-8830d514fd80",  # Batch enrich (morning)
    "5b35c63d-cf96-4062-82d5-78733d429974",  # Batch enrich (mid-morning)
    "1b49f8dd-9ae5-4291-9a8f-b0b527cbc995",  # Batch enrich (afternoon)
    "553aa886-a821-4de7-a2f7-906557305690",  # Batch enrich (evening)
    "78edeb71-cea7-4f8f-a05c-58f54da00652",  # Batch enrich (night)
    "da6b9e46-b95f-4fe0-b42f-548c2bad07c7",  # Discover new games
    "a2ff3c8d-56f4-4d04-a4d2-9fcaee90dce0",  # Daily snapshot + score
    "cefa7590-6f6f-4e7d-a299-9ce7b50904ea",  # Export + deploy site
    "02004776-1b09-4b53-a469-624734dfc7e9",  # Morning article
    "ebc080e2-5d2f-45ed-821a-126b50369ff3",  # Evening article
    "6f965604-09d2-49ee-9702-ac0865f3c33a",  # Evening discover + deploy
    "c7dcb80b-b9a5-49d3-b8fe-bafa83bdef31",  # Weekly Trend Report
}


def export_cron_status():
    """Fetch cron status from openclaw CLI and save filtered JSON."""
    try:
        result = subprocess.run(
            ["openclaw", "cron", "list", "--json"],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode != 0:
            print(f"Error: openclaw cron list failed: {result.stderr}", file=sys.stderr)
            return False

        data = json.loads(result.stdout)
        jobs = [j for j in data.get("jobs", []) if j["id"] in IGD_JOB_IDS]

        with open(OUTPUT, 'w') as f:
            json.dump({"jobs": jobs, "exported_at": __import__('datetime').datetime.utcnow().isoformat()}, f, indent=2)

        print(f"Exported {len(jobs)} IGD jobs to {OUTPUT}")
        return True
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return False


if __name__ == "__main__":
    export_cron_status()
