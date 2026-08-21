import sys
sys.path.append(r"d:\AI-Content-Hub-main\AI-Content-Hub-main\backend")

from core.repositories.blueprint_repo import BlueprintRepository

repo = BlueprintRepository()
user_id = "a0VJGEgKVmQydW8pBy27B9Zkn0i1"
project_id = "test_video_cloner"
blueprint_id = "bp_72a68d3a15e7_001"

print(f"Trying to get {blueprint_id}")
bp = repo.get(user_id, project_id, blueprint_id)
print(f"Result: {bp}")
