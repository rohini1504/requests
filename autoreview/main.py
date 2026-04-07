import sys
import os
import time
import json
sys.path.append(os.getcwd())

from github_client import (
    get_pr, post_agent_box, post_comment, read_all_outputs, _agent_marker
)
from db import init_db, get_state, update_state
from approval import check_qa_comment

from agents import (
    ingestion,
    early_policy,
    summarizer,
    reviewer,
    deep_policy,
    ask_agent,
    coordinator,
    approval_step_3,
    approval_step_8
)

DELAY = 2

init_db()

PR_NUMBER = int(os.getenv("PR_NUMBER"))
pr = get_pr(PR_NUMBER)
state_step, status = get_state(pr)

def _already_posted(agent_name):
    marker = _agent_marker(agent_name)
    return any(marker in c.body for c in pr.get_issue_comments())

def post_box(agent_name, content, raw_data=None):
    if not _already_posted(agent_name):
        post_agent_box(pr, agent_name, content, raw_data=raw_data)
        time.sleep(DELAY)

def post_new(content):
    post_comment(pr, content)
    time.sleep(DELAY)

def load_cached_outputs():
    outputs = read_all_outputs(pr, ["summary", "review", "deep_policy", "ask_agent"])
    review_raw = outputs.get("review")
    review = json.loads(review_raw) if review_raw else {"HIGH": [], "MEDIUM": [], "LOW": []}
    return {
        "summary":     outputs.get("summary") or "",
        "review":      review,
        "deep_policy": outputs.get("deep_policy") or "",
        "ask_agent":   outputs.get("ask_agent") or "",
    }


# ── GUARD: pipeline already completed ─────────────────────────────────────────
if state_step >= 8 and status == "running":
    exit(0)


# ── REJECTED ──────────────────────────────────────────────────────────────────
if status == "rejected":
    ingested = ingestion.run(pr)
    stage = "Step 3 (Early Policy)" if state_step < 8 else "Step 8 (Final Approval)"
    post_new(coordinator.build_rejection_summary(stage, {"early_policy": early_policy.run(pr)}))
    exit(0)


# ── Q&A MODE ──────────────────────────────────────────────────────────────────
if status == "qa":

    # Guard against duplicate GitHub Actions runs firing for the same comment.
    # If state already moved to step 8, a second run snuck in — bail out early.
    if state_step >= 8:
        exit(0)

    ingested = ingestion.run(pr)
    diff = ingested["diff"]

    qa_status, payload = check_qa_comment(pr)

    if qa_status == "approved":
        # Load cached outputs BEFORE updating state so a concurrent second run
        # hits the guard above and exits instead of racing us here.
        data = load_cached_outputs()
        update_state(pr, 8, "running")
        post_new(coordinator.build_approval_summary(data))

    elif qa_status == "rejected":
        # Same order — load first, then update state, then post.
        data = load_cached_outputs()
        update_state(pr, 8, "rejected")
        post_new(coordinator.build_rejection_summary("Step 8 (Final Approval)", data))

    elif qa_status == "done":
        post_new(coordinator.format_qa_done(payload))
        # Keep status="qa" so the NEXT comment (/approve-step 8) re-enters
        # this same block. Previously set status="running" which caused the
        # pipeline to fall through to the bottom and loop back to qa forever.
        update_state(pr, 3, "qa")
        post_box("approval_step_8", coordinator.format_waiting_approval(8))

    elif qa_status == "question":
        answer = ask_agent.answer(payload, diff)
        post_new(coordinator.format_qa_answer(payload, answer))

    exit(0)


# ── STEP 1: Ingestion ─────────────────────────────────────────────────────────
ingested = ingestion.run(pr)
diff = ingested["diff"]
post_box("ingestion", coordinator.format_ingestion(ingested))

# ── STEP 2: Early Policy ──────────────────────────────────────────────────────
early = early_policy.run(pr)
post_box("early_policy", coordinator.format_early_policy(early))

# ── APPROVAL GATE 1 (Step 3) ──────────────────────────────────────────────────
approved_3, msg_3 = approval_step_3.run(pr)

if not approved_3:
    if "Rejected" in msg_3:
        post_new(coordinator.build_rejection_summary("Step 3 (Early Policy)", {"early_policy": early}))
    else:
        post_box("approval_step_3", coordinator.format_waiting_approval(3))
    exit(0)

approver_3 = msg_3.split("by ")[-1] if "by " in msg_3 else "reviewer"
post_box("approval_step_3", coordinator.format_approval_granted(3, approver_3))

# ── STEP 3: Analysis agents ───────────────────────────────────────────────────
summary = summarizer.run(diff)
post_box("summary", coordinator.format_summary(summary), raw_data=summary)

review = reviewer.run(diff)
post_box("review", coordinator.format_review(review), raw_data=json.dumps(review))

dp = deep_policy.run(diff)
post_box("deep_policy", coordinator.format_deep_policy(dp), raw_data=dp)

questions = ask_agent.run(diff)
post_box("ask_agent", coordinator.format_ask_agent(questions), raw_data=questions)

# ── Enter Q&A mode ────────────────────────────────────────────────────────────
update_state(pr, 3, "qa")
