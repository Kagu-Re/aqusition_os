from pathlib import Path


def migrate_work_queue_add_client_id(path: str) -> bool:
    """Add client_id column to WORK_QUEUE.md if missing (safe, idempotent)."""
    p = Path(path)
    if not p.exists():
        return False

    lines = p.read_text(encoding="utf-8").splitlines()
    if not lines:
        return False

    header_idx = None
    for i,l in enumerate(lines):
        if l.startswith("|") and "work_id" in l and "patch_id" in l:
            header_idx = i
            break

    if header_idx is None:
        return False

    header = lines[header_idx]
    if "client_id" in header:
        return True  # already migrated

    sep = lines[header_idx+1]

    cols = [c.strip() for c in header.strip("|").split("|")]
    new_cols = cols[:2] + ["client_id"] + cols[2:]

    new_header = "| " + " | ".join(new_cols) + " |"

    sep_cols = ["---"] * len(new_cols)
    new_sep = "| " + " | ".join(sep_cols) + " |"

    new_lines = lines[:]
    new_lines[header_idx] = new_header
    new_lines[header_idx+1] = new_sep

    # update rows
    for i in range(header_idx+2, len(new_lines)):
        l = new_lines[i]
        if not l.startswith("|"):
            continue
        cells = [c.strip() for c in l.strip("|").split("|")]
        if len(cells) == len(cols):
            cells = cells[:2] + [""] + cells[2:]
            new_lines[i] = "| " + " | ".join(cells) + " |"

    p.write_text("\n".join(new_lines), encoding="utf-8")
    return True
