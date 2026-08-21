import vertexai
from google.cloud import aiplatform

vertexai.init(project="shortcutai-backend", location="us-central1")
models = aiplatform.Model.list()
for m in models:
    if "veo" in m.display_name.lower() or "veo" in m.name.lower():
        print(m.name, m.display_name)
