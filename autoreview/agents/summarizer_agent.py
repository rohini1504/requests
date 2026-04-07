from llm_client import call_llm

def run(diff):
    if not diff or diff.strip() == "":
        return "No code changes to summarize."

    prompt = f"""Summarize this PR diff in 2 lines max:
Line 1: What changed (start with a verb, e.g. "Replaces X with Y")
Line 2: Impact in one short phrase (e.g. "Affects auth middleware")

No fluff. No headers.

DIFF:
{diff[:4000]}"""

    return call_llm(prompt, system_prompt="You are a senior engineer. Be extremely brief.")
