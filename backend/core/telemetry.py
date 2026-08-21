import datetime
import json
import os
from typing import Optional

def log_model_telemetry(
    task: str,
    provider: str,
    model: str,
    reason: str,
    cost: Optional[float] = None,
    latency: Optional[float] = None,
    quality_score: Optional[float] = None,
    retry_count: int = 0
):
    """
    Logs model routing telemetry to a centralized log file.
    """
    record = {
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "task": task,
        "provider": provider,
        "model": model,
        "reason": reason,
        "estimated_cost": cost,
        "latency": latency,
        "quality_score": quality_score,
        "retry_count": retry_count
    }
    
    # Normally this would go to a structured logging service like Cloud Logging
    # For now, append to a local jsonl file for audit purposes.
    from config import TEMP_DIR
    log_path = os.path.join(TEMP_DIR, "model_telemetry.jsonl")
    
    try:
        with open(log_path, "a") as f:
            f.write(json.dumps(record) + "\n")
        print(f"[Telemetry] Logged model selection: {task} -> {model} ({reason})")
    except Exception as e:
        print(f"[Telemetry] Warning: failed to log telemetry: {e}")
