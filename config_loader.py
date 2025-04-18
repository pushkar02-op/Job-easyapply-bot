import json
import os
import re

def load_config(path="config.json"):
    with open(path) as f:
        raw_config = f.read()
    # Replace ${VAR} with environment variables
    config_str = re.sub(r"\${(.*?)}", lambda m: os.getenv(m.group(1), ""), raw_config)
    return json.loads(config_str)

def get_resume_context(config):
    context = config.get("resume_context", "")
    if isinstance(context, dict):
        return json.dumps(context, indent=2)
    return context
