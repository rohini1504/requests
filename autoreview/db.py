"""
State persistence via GitHub PR labels.

Labels used:
  pr-review:step={N}          — last completed step
  pr-review:status=running    — pipeline in progress
  pr-review:status=qa         — waiting for Q&A interaction
  pr-review:status=rejected   — PR was rejected

All public functions now accept a pr object directly instead of a pr_number,
eliminating the redundant get_repo().get_pull() call that was happening inside
every db function even though main.py already held a pr reference.
"""

from github_client import get_repo

LABEL_PREFIX = "pr-review:"

LABEL_COLORS = {
    "running":  "0075ca",
    "qa":       "e4e669",
    "rejected": "d93f0b",
}


def _ensure_label_exists(repo, name, color="ededed"):
    try:
        repo.get_label(name)
    except Exception:
        repo.create_label(name, color)


def _get_review_labels(pr):
    return [l.name for l in pr.get_labels() if l.name.startswith(LABEL_PREFIX)]


def _remove_labels_with_prefix(pr, prefix):
    """Remove matching labels in a single get_labels() call (already fetched above)."""
    for name in _get_review_labels(pr):
        if name.startswith(prefix):
            try:
                pr.remove_from_labels(name)
            except Exception:
                pass


def init_db():
    pass  # labels created on demand


def get_state(pr):
    """
    Accept pr object directly.
    Previously called get_repo().get_pull(pr_number) internally — that was
    a redundant API call since main.py already had a pr reference.
    """
    labels = _get_review_labels(pr)

    last_step = 0
    status = "running"

    for name in labels:
        key = name[len(LABEL_PREFIX):]
        if key.startswith("step="):
            try:
                last_step = int(key.split("=")[1])
            except ValueError:
                pass
        elif key.startswith("status="):
            status = key.split("=")[1]

    return last_step, status


def update_state(pr, step, status="running"):
    """
    Accept pr object directly and fetch repo once.
    Old version: called get_repo().get_pull() AND get_repo() separately,
    plus called _get_review_labels() twice (once per prefix removal).
    Now: one get_repo() call, one get_labels() call per removal.
    Also ensures both new labels exist before adding them in one add_to_labels()
    call, which is unchanged but now runs against an already-held pr object.
    """
    repo = get_repo()

    _remove_labels_with_prefix(pr, LABEL_PREFIX + "step=")
    _remove_labels_with_prefix(pr, LABEL_PREFIX + "status=")

    step_label   = f"{LABEL_PREFIX}step={step}"
    status_label = f"{LABEL_PREFIX}status={status}"
    color = LABEL_COLORS.get(status, "ededed")

    _ensure_label_exists(repo, step_label,   "0075ca")
    _ensure_label_exists(repo, status_label, color)

    pr.add_to_labels(step_label, status_label)


def save_output(pr_number, step, content):
    pass  # outputs live in PR comments


def get_all_outputs(pr_number):
    return {}
