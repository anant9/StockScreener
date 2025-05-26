import re

def parse_prompt(prompt: str) -> dict: prompt = prompt.lower() result = { "change_pct": None, "interval_minutes": None }

# Parse % change
pct_match = re.search(r"(\d+(\.\d+)?)\s*%", prompt)
if pct_match:
    result["change_pct"] = float(pct_match.group(1))

# Parse time interval
time_match = re.search(r"(\d{1,3})\s*(minutes|minute|min|m)", prompt)
if time_match:
    result["interval_minutes"] = int(time_match.group(1))

return result

