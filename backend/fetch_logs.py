import json
import subprocess
from datetime import datetime, timedelta

time_limit = (datetime.utcnow() - timedelta(minutes=25)).isoformat() + 'Z'
cmd = ['gcloud.cmd', 'logging', 'read', f'resource.type=cloud_run_revision AND resource.labels.service_name=ai-video-backend AND timestamp>="{time_limit}"', '--project=shortcutai-backend', '--limit=50', '--format=json']
p = subprocess.run(cmd, capture_output=True, text=True)
try:
    logs = json.loads(p.stdout)
    for log in logs:
        if 'textPayload' in log:
            print(log['textPayload'])
        elif 'jsonPayload' in log:
            print(log['jsonPayload'])
except Exception as e:
    print('Failed to parse:', e)
