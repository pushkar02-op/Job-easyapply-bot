# gemini_tester.py

import os
import json
from dotenv import load_dotenv
from gemini_helper import configure_api, create_model, answer_question
from gemini_prompter import generate_gemini_prompt

# 1. Load config & resume context
with open("config.json") as f:
    config = json.load(f)
resume_context = config  # using your structured config as context

# 2. Init Gemini
load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY")
configure_api(API_KEY)
model = create_model(
    "gemini-1.5-flash",
    "You are a helpful assistant that fills out LinkedIn Easy Apply fields."
)

# 3. Define some test fields (text / dropdown / radio)
test_fields = [
    {
        "label": "What's your current CTC?  The input must satisfy: Enter a decimal number larger than 0.0",
        "type": "text",
        "options": None
    }
]

# 4. Run through each, build prompt, get and print answer
for field in test_fields:
    prompt = generate_gemini_prompt(
        field_label=field["label"],
        input_type=field["type"],
        resume_context=resume_context,
        options=field.get("options")
    )
    print("\n" + "="*80)
    print("PROMPT:")
    print(prompt)
    print("\nRESPONSE:")
    answer = answer_question(model, context="", question=prompt)
    print(answer)
print("\nDone testing.")
