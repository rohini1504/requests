from llm_client import call_llm

SYSTEM = "You are a senior engineering lead. Be concise and direct."

def _box(agent, subtitle, body):
    return f"### {agent}\n*{subtitle}*\n\n---\n{body}\n"


# ── Per-agent formatters ───────────────────────────────────────────────────────

def format_ingestion(result):
    return _box("INGESTION AGENT", "Pull Request Snapshot", result["metadata"])

def format_early_policy(result):
    return _box("EARLY POLICY AGENT", "Pre-Flight Checks", result)

def format_waiting_approval(step):
    body = (
        f"**STATUS:** Awaiting reviewer sign-off on Step {step}\n\n"
        f"| Action      | Command                |\n"
        f"|-------------|------------------------|\n"
        f"| To Continue | `/approve-step {step}` |\n"
        f"| To Halt     | `/reject-step {step}`  |"
    )
    return _box("APPROVAL AGENT", f"Waiting on Your Decision — Step {step}", body)

def format_approval_granted(step, user):
    return _box("APPROVAL AGENT", f"Step {step} Approved by {user}", "Pipeline continuing.")

def format_summary(result):
    return _box("SUMMARIZER AGENT", "What Changed", result)

def format_review(result):
    def render_items(lst, show_fix):
        if not lst:
            return "_None_"
        lines = []
        for idx, item in enumerate(lst, 1):
            if isinstance(item, dict):
                issue = item.get("issue", "")
                fname = item.get("file", "")
                fix   = item.get("fix", "")
                lines.append(f"**{idx}.** {issue}")
                if fname:
                    lines.append(f"   File: `{fname}`")
                if show_fix and fix:
                    lines.append(f"   Fix:\n   ```\n   {fix}\n   ```")
            else:
                lines.append(f"**{idx}.** {item}")
        return "\n".join(lines)

    high   = result.get("HIGH",   [])
    medium = result.get("MEDIUM", [])
    low    = result.get("LOW",    [])
    h, m, l = len(high), len(medium), len(low)

    scorecard = (
        f"| High | Medium | Low |\n"
        f"|------|--------|-----|\n"
        f"| {h}    | {m}      | {l}   |\n"
    )

    body = (
        f"**Severity Summary**\n\n{scorecard}\n"
        f"---\n\n"
        f"**HIGH SEVERITY**\n{render_items(high, show_fix=True)}\n\n"
        f"**MEDIUM SEVERITY**\n{render_items(medium, show_fix=True)}\n\n"
        f"**LOW SEVERITY**\n{render_items(low, show_fix=False)}"
    )
    return _box("REVIEWER AGENT", "Code Review Findings", body)

def format_deep_policy(result):
    return _box("DEEP POLICY AGENT", "Policy & Security Scan", result)


# ── internal helpers ───────────────────────────────────────────────────────────

def _flatten_issues(lst):
    return [i.get("issue", "") if isinstance(i, dict) else str(i) for i in lst if i]

def _join(items, sep=", "):
    cleaned = [s.strip() for s in items if s.strip()]
    return sep.join(cleaned) if cleaned else ""

def _policy_prose(raw):
    if not raw or not raw.strip():
        return "No policy issues were detected."
    lines = [ln.strip().lstrip("[CRITICALWARN]-•").strip() for ln in raw.splitlines() if ln.strip()]
    lines = [l for l in lines if l and l.lower() != "no issues found."]
    if not lines:
        return "No policy issues were detected."
    return "Policy checks flagged: " + "; ".join(lines) + "."


# ── APPROVED — full narrative report ──────────────────────────────────────────

def build_approval_summary(data):
    summary     = (data.get("summary") or "").replace("\n", " ").strip()
    deep_policy = (data.get("deep_policy") or "").strip()
    review      = data.get("review") or {}

    high   = review.get("HIGH",   []) if isinstance(review, dict) else []
    medium = review.get("MEDIUM", []) if isinstance(review, dict) else []
    low    = review.get("LOW",    []) if isinstance(review, dict) else []
    h, m, l = len(high), len(medium), len(low)

    if h > 0:
        verdict_line = "Approved — high-severity findings should be resolved before next production deployment."
    elif m > 0:
        verdict_line = "Approved — no blocking issues, medium-severity observations worth addressing in a follow-up."
    else:
        verdict_line = "Approved — no critical or blocking issues found. Safe to merge."

    verdict = (
        f"| Field   | Value                                 |\n"
        f"|---------|---------------------------------------|\n"
        f"| Verdict | {verdict_line} |\n"
        f"| Stage   | Step 8 — Final Review                 |\n"
        f"| Issues  | {h} High · {m} Medium · {l} Low       |"
    )

    change_para = f"**Changes:** {summary}" if summary else ""

    all_high   = _join(_flatten_issues(high))
    all_medium = _join(_flatten_issues(medium))
    all_low    = _join(_flatten_issues(low))

    review_parts = []
    if h > 0:
        review_parts.append(f"{h} high-severity issue(s) were raised: {all_high}")
    if m > 0:
        review_parts.append(f"{m} medium-severity observation(s): {all_medium}")
    if l > 0:
        review_parts.append(f"{l} minor/low item(s): {all_low}")

    if review_parts:
        review_para = "**Code review:** " + ". ".join(review_parts) + "."
    else:
        review_para = "**Code review:** No issues were identified in the diff."

    policy_para = f"**Policy:** {_policy_prose(deep_policy)}"

    paragraphs = [p for p in [verdict, change_para, review_para, policy_para] if p]
    body = "\n\n".join(paragraphs) + "\n\n---\n_Reviewed by PR Review Bot. Merge at your discretion._"

    return _box("COORDINATOR AGENT", "Review Complete, Approved", body)


# ── REJECTED — clear narrative explaining exactly why ─────────────────────────

def build_rejection_summary(stage, data):
    early_policy = (data.get("early_policy") or "").strip()
    summary      = (data.get("summary") or "").replace("\n", " ").strip()
    deep_policy  = (data.get("deep_policy") or "").strip()
    review       = data.get("review") or {}

    high   = review.get("HIGH",   []) if isinstance(review, dict) else []
    medium = review.get("MEDIUM", []) if isinstance(review, dict) else []
    h, m   = len(high), len(medium)

    reasons = []

    if early_policy:
        for line in early_policy.splitlines():
            line = line.strip().lstrip("[FAILWARN]").strip()
            if line:
                reasons.append(line)

    for item in high:
        issue = item.get("issue", "") if isinstance(item, dict) else str(item)
        fname = item.get("file", "")  if isinstance(item, dict) else ""
        text  = issue + (f" (in `{fname}`)" if fname else "")
        if text.strip():
            reasons.append(text)

    if not high:
        for item in medium:
            issue = item.get("issue", "") if isinstance(item, dict) else str(item)
            if issue.strip():
                reasons.append(issue)

    for ln in deep_policy.splitlines():
        ln = ln.strip().lstrip("[CRITICALWARN]-•").strip()
        if ln and ln.lower() != "no issues found.":
            reasons.append(ln)

    if reasons:
        if len(reasons) == 1:
            reason_sentence = f"This PR was rejected because {reasons[0].lower()}."
        else:
            joined = "; ".join(r.rstrip(".") for r in reasons[:-1])
            reason_sentence = f"This PR was rejected because of the following: {joined}; and {reasons[-1].rstrip('.')}."
    else:
        reason_sentence = "This PR was rejected at reviewer discretion."

    change_sentence = f" The PR {summary.lower()}" if summary else ""

    body = (
        f"This PR did not pass the review at **{stage}**.{change_sentence}\n\n"
        f"{reason_sentence}\n\n"
        f"Please address the issues above, push a new commit, or re-open this PR to restart the review pipeline."
    )

    return _box("COORDINATOR AGENT", "Review Complete, Rejected", body)


# ── Q&A formatters ────────────────────────────────────────────────────────────

def format_ask_agent(questions):
    lines = [l.strip() for l in questions.strip().splitlines() if l.strip()]
    formatted_questions = []
    for i, line in enumerate(lines, 1):
        clean = line.lstrip("0123456789.-) ").strip()
        formatted_questions.append(f"**QUESTION {i}**\n{clean}")

    questions_block = "\n\n---\n\n".join(formatted_questions)

    body = (
        f"_I've reviewed the diff and put together some questions based on the riskiest "
        f"or most unclear parts of this PR. You can also ask me anything about the code "
        f"— I'll answer based on the diff._\n\n"
        f"---\n\n"
        f"**Example Questions from the Review**\n\n"
        f"{questions_block}\n\n"
        f"---\n\n"
        f"Have your own question? Reply directly in this comment thread.\n\n"
        f"Type `/done` when you're ready to move to final approval."
    )
    return _box("ASK AGENT", "Questions About This PR", body)

def format_qa_answer(question, answer):
    body = f"**Q:** {question}\n\n**A:** {answer}"
    return _box("ASK AGENT", "Here's What I Found", body)

def format_qa_done(user):
    return _box("ASK AGENT", "Moving to Final Approval", f"Q&A complete. Thanks {user}. Proceeding to final approval.")
