"""Command line for the Simplilearn study agent."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from study_agent.agent import run
from study_agent.progress import add_note, assess, mark_done, mark_undo
from study_agent.store import Store


def main(argv: list[str] | None = None, root: Path | None = None, fetcher=None) -> int:
    parser = argparse.ArgumentParser(
        description="Check your Python progress and search Simplilearn for class and bootcamp updates."
    )
    parser.add_argument(
        "command",
        nargs="?",
        default="check",
        choices=["check", "offline", "done", "undo", "note"],
    )
    parser.add_argument("rest", nargs="*", help="Lesson number, or the text of a note.")
    args = parser.parse_args(argv)
    store = Store(root or Path(__file__).resolve().parents[1])

    if args.command in {"done", "undo"}:
        if len(args.rest) != 1:
            print("Give one lesson number, for example: python3 -m study_agent done 1")
            return 2
        return _update_lesson(store, args.command, args.rest[0])
    if args.command == "note":
        text = " ".join(args.rest).strip()
        if not text:
            print("Add a note, for example: python3 -m study_agent note Finished the print exercise")
            return 2
        progress = add_note(store.progress(), text)
        store.save_progress(progress)
        print("Saved your note.")
        return 0

    report = run(store, fetcher=fetcher, online=args.command != "offline")
    print(report)
    return 0


def _update_lesson(store: Store, command: str, lesson_id: str) -> int:
    curriculum = store.curriculum()
    known = {lesson["id"] for lesson in curriculum["lessons"]}
    progress = store.progress()
    if command == "done":
        progress, message = mark_done(progress, lesson_id, known)
    else:
        progress, message = mark_undo(progress, lesson_id)
    if message.startswith("Lesson") and "not" in message:
        print(message)
        return 2
    store.save_progress(progress)
    view = assess(curriculum, progress, store.profile())
    print(message)
    print(f"Finished {view['finished']} of {view['total']} lessons.")
    if view["next"]:
        print(f"Next: {view['next']['id']}. {view['next']['title']}")
    else:
        print(view["phase_note"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
