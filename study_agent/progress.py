"""Compare the lesson log with the current Python class."""

from __future__ import annotations

import math
from datetime import date


PHASE_NOTE = {
    "foundations": "This is still core Python. The AI libraries in this class start at lesson 8, NumPy.",
    "ai_tools": "This is the part of the class that AI work uses.",
    "practice": "The library lessons are done. These last lessons are practice.",
    "finished": "Your Python checklist is complete.",
}


def assess(curriculum: dict, progress: dict, profile: dict) -> dict:
    lessons = curriculum["lessons"]
    known = {lesson["id"]: lesson for lesson in lessons}
    completed_ids = [str(item) for item in progress.get("completed", [])]
    unknown = [item for item in completed_ids if item not in known]
    done = [lesson for lesson in lessons if lesson["id"] in set(completed_ids)]
    remaining = [lesson for lesson in lessons if lesson["id"] not in set(completed_ids)]
    nxt = remaining[0] if remaining else None
    minutes_left = sum(lesson["minutes"] for lesson in remaining)
    pace = profile["pace"]
    session_minutes = pace["minutes_per_session"]
    sessions_left = math.ceil(minutes_left / session_minutes) if minutes_left else 0
    phase = nxt["phase"] if nxt else "finished"
    notes = progress.get("notes", [])
    return {
        "class_name": curriculum["name"],
        "finished": len(done),
        "total": len(lessons),
        "next": nxt,
        "minutes_left": minutes_left,
        "sessions_left": sessions_left,
        "sessions_per_week": pace["sessions_per_week"],
        "minutes_per_session": session_minutes,
        "phase": phase,
        "phase_note": PHASE_NOTE[phase],
        "latest_note": notes[-1] if notes else None,
        "unknown_completed": unknown,
    }


def mark_done(progress: dict, lesson_id: str, known_ids: set[str]) -> tuple[dict, str]:
    lesson_id = str(lesson_id)
    if lesson_id not in known_ids:
        return progress, f"Lesson {lesson_id} is not on the Python checklist."
    completed = [str(item) for item in progress.get("completed", [])]
    if lesson_id in completed:
        return progress, f"Lesson {lesson_id} was already marked done."
    completed.append(lesson_id)
    progress = dict(progress)
    progress["completed"] = completed
    progress["updated_at"] = date.today().isoformat()
    return progress, f"Marked lesson {lesson_id} done."


def mark_undo(progress: dict, lesson_id: str) -> tuple[dict, str]:
    lesson_id = str(lesson_id)
    completed = [str(item) for item in progress.get("completed", [])]
    if lesson_id not in completed:
        return progress, f"Lesson {lesson_id} was not marked done."
    progress = dict(progress)
    progress["completed"] = [item for item in completed if item != lesson_id]
    progress["updated_at"] = date.today().isoformat()
    return progress, f"Cleared lesson {lesson_id}."


def add_note(progress: dict, text: str) -> dict:
    progress = dict(progress)
    notes = list(progress.get("notes", []))
    notes.append({"date": date.today().isoformat(), "text": text})
    progress["notes"] = notes
    progress["updated_at"] = date.today().isoformat()
    return progress
