from llm_client import call_llm

def run(pr):
    flags = []

    if not pr.title or len(pr.title.strip()) < 5:
        flags.append("[FAIL] Title too short")

    if not pr.body or len(pr.body.strip()) < 10:
        flags.append("[FAIL] Description missing")

    changed_files = list(pr.get_files())
    if len(changed_files) > 20:
        flags.append(f"[WARN] Large PR — {len(changed_files)} files (consider splitting)")

    if pr.additions + pr.deletions > 500:
        flags.append(f"[WARN] High churn — {pr.additions + pr.deletions} lines changed")

    if flags:
        return "\n".join(flags)
    return "[PASS] Passes all checks"
