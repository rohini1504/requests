from llm_client import call_llm
import json
import re

def run(diff):
    prompt = f"""Review this code diff. Reply ONLY with a JSON object, no other text, no markdown fences.

Format:
{{
  "HIGH":   [{{"issue": "...", "file": "...", "fix": "one-line code fix or pattern"}}],
  "MEDIUM": [{{"issue": "...", "file": "...", "fix": "one-line code fix or pattern"}}],
  "LOW":    [{{"issue": "...", "file": "..."}}]
}}

Rules:
- HIGH: bugs, security vulnerabilities, crashes
- MEDIUM: missing error handling, bad patterns, logic flaws
- LOW: naming, style, readability (no fix needed)
- issue: max 10 words
- fix: a concrete code snippet or replacement pattern, max 1-2 lines
- max 2 items per level
- empty list [] if nothing found

DIFF:
{diff[:4000]}"""

    response = call_llm(
        prompt,
        system_prompt="You are a strict code reviewer. Reply only with the JSON object."
    )

    clean = re.sub(r"```(?:json)?|```", "", response).strip()

    try:
        parsed = json.loads(clean)
        def clean_items(lst, require_fix=True):
            out = []
            for item in lst[:2]:
                if isinstance(item, dict) and "issue" in item:
                    entry = {"issue": str(item["issue"]), "file": str(item.get("file", ""))}
                    if require_fix and item.get("fix"):
                        entry["fix"] = str(item["fix"])
                    out.append(entry)
            return out

        return {
            "HIGH":   clean_items(parsed.get("HIGH",   []), require_fix=True),
            "MEDIUM": clean_items(parsed.get("MEDIUM", []), require_fix=True),
            "LOW":    clean_items(parsed.get("LOW",    []), require_fix=False),
        }
    except Exception:
        return {"HIGH": [], "MEDIUM": [{"issue": "Could not parse review output", "file": ""}], "LOW": []}
