import os
from google.cloud import firestore

# Let the library find ADC on Windows automatically
db = firestore.Client(project="shortcutai-backend")
user_id = "a0VJGEgKVmQydW8pBy27B9Zkn0i1"
project_id = "test_video_cloner"

docs = db.collection("users").document(user_id).collection("projects").document(project_id).collection("blueprints").stream()
print(f"Docs:")
for doc in docs:
    d = doc.to_dict()
    print(f"Doc ID: {doc.id}, bp_id: {d.get('blueprint_id')}, status: {d.get('status')}")
