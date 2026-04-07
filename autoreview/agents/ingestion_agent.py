def run(pr):
    changed_files = list(pr.get_files())

    file_list = []
    for f in changed_files[:10]:
        status_icon = {"added": "✚", "removed": "✖", "modified": "✎", "renamed": "➜"}.get(f.status, "•")
        additions = f.additions
        deletions = f.deletions
        file_list.append(f"{status_icon} `{f.filename}` (+{additions} / -{deletions})")

    # Collect diffs for downstream agents
    diffs = []
    for f in changed_files[:10]:
        if f.patch:
            diffs.append(f.patch[:1500])

    diff_text = "\n\n".join(diffs) if diffs else "No code changes detected"

    metadata = (
        f"**Title:** {pr.title}\n"
        f"**Author:** {pr.user.login}\n"
        f"**Branch:** `{pr.head.label}` → `{pr.base.label}`\n"
        f"**Changed files:** {len(changed_files)}  |  "
        f"**Additions:** +{pr.additions}  |  "
        f"**Deletions:** -{pr.deletions}\n\n"
        + "\n".join(file_list)
    )

    return {"metadata": metadata, "diff": diff_text}
