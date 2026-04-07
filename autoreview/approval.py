from github_client import get_pr

BOT_MARKER = "<!-- AUTO_REVIEW_BOT -->"

def _human_comments(pr):
    return [c for c in pr.get_issue_comments() if BOT_MARKER not in c.body]

def check_approval(pr_number, step):
    pr = get_pr(pr_number)
    comments = _human_comments(pr)
    if not comments:
        return None, None
    latest = comments[-1]
    body = latest.body.strip()
    user = latest.user.login
    if body.startswith(f"/approve-step {step}"):
        return "approved", user
    if body.startswith(f"/reject-step {step}"):
        return "rejected", user
    return None, None


def check_qa_comment(pr):
    """
    Now accepts a pr object directly instead of a pr_number.
    Previously called get_pr(pr_number) internally — that was a redundant
    get_repo().get_pull() API call since main.py already held a pr reference.

    Returns:
      ("approved", user)  — user typed /approve-step 8
      ("rejected", user)  — user typed /reject-step 8
      ("done", user)      — user typed /done
      ("question", text)  — user asked a question
      (None, None)        — no new human comment since last bot post
    """
    all_comments = list(pr.get_issue_comments())

    if not all_comments:
        return None, None

    last_bot_idx = -1
    for i, c in enumerate(all_comments):
        if BOT_MARKER in c.body:
            last_bot_idx = i

    new_human = [
        c for c in all_comments[last_bot_idx + 1:]
        if BOT_MARKER not in c.body
    ]

    if not new_human:
        return None, None

    latest = new_human[-1]
    body = latest.body.strip()
    user = latest.user.login

    if body.startswith("/approve-step 8"):
        return "approved", user
    if body.startswith("/reject-step 8"):
        return "rejected", user
    if body.lower().startswith("/done"):
        return "done", user

    return "question", body
