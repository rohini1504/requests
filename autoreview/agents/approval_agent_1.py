from db import get_state, update_state
from approval import check_approval

STEP = 3

def run(pr):
    """
    Accepts pr object directly — no pr_number needed.
    check_approval still uses pr_number internally (it's called from
    outside the qa flow where we may not have a pr object), so we
    pass pr.number here.
    """
    last_step, status = get_state(pr)

    decision, user = check_approval(pr.number, STEP)

    if decision == "approved":
        update_state(pr, STEP, "running")
        return True, f"Approved by {user}"

    if decision == "rejected":
        update_state(pr, STEP, "rejected")
        return False, f"Rejected by {user}"

    if status == "rejected":
        return False, "PR already rejected"

    if last_step >= STEP:
        return True, "Already approved"

    return False, (
        "Waiting for approval\n\n"
        "Comment `/approve-step 3` to continue\n"
        "Comment `/reject-step 3` to halt"
    )
