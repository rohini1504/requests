from llm_client import call_llm

def run(diff):
    """Generate 3 seed questions based on the diff."""
    prompt = f"""Generate 3 review questions for this PR.
Format: numbered list 1. 2. 3.
Each question: one short sentence, max 15 words.
Ask about the riskiest or most unclear parts only.
No preamble.

DIFF:
{diff[:3000]}"""

    response = call_llm(
        prompt,
        system_prompt="You are a senior reviewer. Ask sharp, specific questions."
    )

    lines = [
        line.strip() for line in response.strip().splitlines()
        if line.strip() and line.strip()[0].isdigit()
    ]
    return "\n".join(lines[:3]) if lines else response.strip().splitlines()[0]


def answer(question, diff):
    """Answer a follow-up question from the PR author about the diff."""
    prompt = f"""A developer asked this question about their PR:

Question: {question}

Answer it directly and concisely in 2-3 sentences max.
Reference specific code from the diff where relevant.
No preamble, no sign-off.

DIFF:
{diff[:3000]}"""

    return call_llm(
        prompt,
        system_prompt="You are a senior code reviewer answering a developer's question."
    )
