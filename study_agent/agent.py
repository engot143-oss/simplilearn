"""Decide what to check, then write a plain-language progress report."""

from __future__ import annotations

from study_agent.progress import assess
from study_agent.search import describe_change, refresh_source, syllabus_gap
from study_agent.store import Store


def run(store: Store, fetcher=None, online: bool = True) -> str:
    curriculum = store.curriculum()
    profile = store.profile()
    progress = store.progress()
    view = assess(curriculum, progress, profile)
    trace = ["Read your Python lesson log."]
    updates: list[dict] = []
    if online:
        fetch = fetcher or _default_fetcher()
        for source in profile["watching"]:
            trace.append(f"Opened {source['name']}.")
            previous = store.snapshot(source["id"])
            facts, change = refresh_source(source, previous, fetch)
            updates.append(change)
            if facts.get("error") is None:
                store.save_snapshot(source["id"], facts)
        trace.append("Compared each page with the last saved copy.")
    else:
        trace.append("Skipped the live page check.")
    trace.append("Wrote the next step from your lesson log and those page changes.")
    report = render(view, updates, curriculum, trace)
    store.save_report(report)
    return report


def render(view: dict, updates: list[dict], curriculum: dict, trace: list[str]) -> str:
    lines = ["# Python progress", ""]
    lines.append(f"Finished {view['finished']} of {view['total']} lessons in {view['class_name']}.")
    if view["unknown_completed"]:
        lines.append(
            "These log entries are not on the checklist: "
            + ", ".join(view["unknown_completed"])
            + "."
        )
    if view["latest_note"]:
        note = view["latest_note"]
        lines.append(f"Latest note ({note['date']}): {note['text']}")
    lines.append("")
    nxt = view["next"]
    if nxt is None:
        lines.append(view["phase_note"])
    else:
        lines.append(
            f"Next lesson: {nxt['id']}. {nxt['title']} (about {nxt['minutes']} minutes)."
        )
        lines.append(view["phase_note"])
        if nxt.get("hint"):
            lines.append(nxt["hint"])
        lines.append("")
        lines.append("Practice")
        lines.append("")
        if nxt.get("kind") == "writing":
            lines.append(nxt["practice"])
        else:
            lines.append("```python")
            lines.append(nxt["practice"])
            lines.append("```")
    lines.append("")
    lines.append(
        f"About {view['sessions_left']} sessions of {view['minutes_per_session']} minutes "
        f"are left, at {view['sessions_per_week']} sessions a week."
    )
    lines.append("")
    lines.append("## What I checked")
    lines.append("")
    for step in trace:
        lines.append(f"- {step}")
    lines.append("")
    lines.append("## Updates")
    lines.append("")
    if not updates:
        lines.append("No pages were checked.")
    else:
        for change in updates:
            lines.append(f"- {describe_change(change)}")
        class_update = next((item for item in updates if item["kind"] == "class"), None)
        if class_update and class_update["status"] != "error":
            if class_update["status"] == "changed" and (
                class_update["added_lessons"] or class_update["removed_lessons"]
            ):
                lines.append(
                    "- Your checklist may need an update because the class page lesson list changed."
                )
            gap = syllabus_gap(curriculum["lessons"], class_update.get("lessons", []))
            if gap:
                lines.append(f"- Checklist compared with the class page: {gap}.")
    lines.append("")
    lines.append("## Next step")
    lines.append("")
    lines.append(advise(view, updates))
    lines.append("")
    return "\n".join(lines)


def advise(view: dict, updates: list[dict]) -> str:
    errors = [item["name"] for item in updates if item["status"] == "error"]
    prefix = ""
    if errors:
        prefix = "I could not open " + ", ".join(errors) + ". "
    if view["next"] is None:
        return (
            prefix
            + "This Python class is finished. The bootcamps I am watching for a later step "
            + "are Data Science with Python and Applied Agentic AI. I have not marked you enrolled in them."
        )
    lesson = view["next"]
    if view["phase"] == "foundations":
        body = (
            f"Stay on lesson {lesson['id']}, {lesson['title']}. "
            "Run the practice, then mark it done. The watched bootcamps are later; "
            "Applied Agentic AI expects basic programming first."
        )
    elif view["phase"] == "ai_tools":
        body = (
            f"Stay on lesson {lesson['id']}, {lesson['title']}. "
            "This lesson is one of the Python tools used for AI. Install the library it imports if the practice fails, then mark the lesson done."
        )
    else:
        body = (
            f"Stay on lesson {lesson['id']}, {lesson['title']}. "
            "After lessons 12 and 13, the Python checklist for this class is complete."
        )
    return prefix + body


def _default_fetcher():
    from study_agent.search import fetch_url

    return fetch_url
