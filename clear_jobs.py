import json
with open('/opt/whovoted/data/processing_jobs.json', 'w') as f:
    json.dump({}, f)
print("Cleared stuck jobs")
