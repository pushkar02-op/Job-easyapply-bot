import json

def load_config(path="config.json"):
    with open(path) as f:
        return json.load(f)

def get_resume_context(config):
    context = config.get("resume_context", "")
    if isinstance(context, dict):
        return json.dumps(context, indent=2)
    return context
