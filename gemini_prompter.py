def generate_gemini_prompt(field_label: str, input_type: str, resume_context: dict, options: list = None, validation_hint: str = "") -> str:
    """
    Builds a Gemini prompt for a field using dynamically parsed resume context.
    """

    def format_value(key, value):
        if isinstance(value, list):
            return f"{key.capitalize()}: {', '.join(str(v) for v in value)}"
        elif isinstance(value, dict):
            inner = "; ".join(f"{k.capitalize()}: {v}" for k, v in value.items())
            return f"{key.capitalize()} - {inner}"
        elif isinstance(value, str):
            return f"{key.capitalize()}: {value}"
        else:
            return f"{key.capitalize()}: {value}"

    # Build summary lines recursively for structured resume context
    def build_summary(context):
        summary = []
        for key, value in context.items():
            if isinstance(value, list) and all(isinstance(i, dict) for i in value):
                # list of dicts (like experience)
                for idx, entry in enumerate(value, 1):
                    line = f"{key.capitalize()} #{idx}: " + "; ".join(
                        f"{k.capitalize()}: {v}" for k, v in entry.items()
                    )
                    summary.append(line)
            else:
                summary.append(format_value(key, value))
        return summary

    resume_summary = "\n".join(build_summary(resume_context))

    prompt = f"""
You are helping a candidate complete a LinkedIn Easy Apply form.

Candidate Details:
{resume_summary}

Field to Fill:
- Label: {field_label}
- Input Type: {input_type}
"""
    if validation_hint:
        prompt += f"- Validation Requirement: {validation_hint}\n"

    if options:
        prompt += f"- Options: {', '.join(options)}\n"
        prompt += "Select the most appropriate option based on the resume."

    prompt += "\nRespond only with the value to enter. Do not include explanation or punctuation."
    return prompt.strip()
