from github import Github
import os
import base64

BOT_MARKER = "<!-- PR_REVIEW_BOT -->"

def get_client():
    return Github(os.getenv("GITHUB_TOKEN"))

def get_repo():
    return get_client().get_repo(os.getenv("GITHUB_REPOSITORY"))

def get_pr(pr_number):
    return get_repo().get_pull(pr_number)

def get_latest_comment(pr):
    comments = list(pr.get_issue_comments())
    return comments[-1].body if comments else ""

def _agent_marker(agent_name):
    return f"<!-- PR_BOT_AGENT:{agent_name} -->"

def _data_marker(agent_name):
    return f"<!-- PR_BOT_DATA:{agent_name}:"

def post_agent_box(pr, agent_name, content, raw_data=None):
    """
    Post a comment box for this agent. Skip if already posted.
    Returns True if a new comment was created, False if skipped.
    """
    marker = _agent_marker(agent_name)
    for c in pr.get_issue_comments():
        if marker in c.body:
            return False

    hidden = ""
    if raw_data is not None:
        encoded = base64.b64encode(raw_data.encode()).decode()
        hidden = f"\n{_data_marker(agent_name)}{encoded}-->"

    pr.create_issue_comment(f"{BOT_MARKER}\n{marker}{hidden}\n{content}")
    return True

def read_output(pr, agent_name):
    """
    Retrieve raw_data for a single agent.
    Prefer read_all_outputs() when you need multiple agents — it only
    calls get_issue_comments() once instead of once per agent.
    """
    marker = _agent_marker(agent_name)
    data_prefix = _data_marker(agent_name)

    for c in pr.get_issue_comments():
        if marker not in c.body:
            continue
        for line in c.body.splitlines():
            if line.startswith(data_prefix):
                encoded = line[len(data_prefix):].rstrip("-->").strip()
                try:
                    return base64.b64decode(encoded.encode()).decode()
                except Exception:
                    return None
    return None

def read_all_outputs(pr, agent_names):
    """
    Retrieve raw_data for multiple agents in a SINGLE get_issue_comments() call.
    Returns a dict {agent_name: decoded_string_or_None}.
    Previously load_cached_outputs() called get_issue_comments() 4 separate
    times (once per agent), adding ~12-40s of API latency on Actions.
    """
    results = {name: None for name in agent_names}
    remaining = set(agent_names)

    for c in pr.get_issue_comments():
        if not remaining:
            break
        for name in list(remaining):
            marker = _agent_marker(name)
            if marker not in c.body:
                continue
            data_prefix = _data_marker(name)
            for line in c.body.splitlines():
                if line.startswith(data_prefix):
                    encoded = line[len(data_prefix):].rstrip("-->").strip()
                    try:
                        results[name] = base64.b64decode(encoded.encode()).decode()
                    except Exception:
                        results[name] = None
            remaining.discard(name)

    return results

def post_comment(pr, content):
    """Always post a new comment (used for coordinator summaries)."""
    pr.create_issue_comment(f"{BOT_MARKER}\n{content}")

def upsert_comment(pr, body):
    post_comment(pr, body)
