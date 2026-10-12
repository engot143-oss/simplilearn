import json
import shutil
import tempfile
import unittest
from pathlib import Path

from study_agent.__main__ import main
from study_agent.agent import advise, run
from study_agent.progress import assess, mark_done
from study_agent.search import describe_change, diff_facts, extract_facts, syllabus_gap
from study_agent.store import Store

ROOT = Path(__file__).resolve().parents[1]

CLASS_PAGE = """
<html><head><title>Free Python Course</title></head>
<body>
<h1>Free Python Course with Certificate</h1>
<p>11 Hours Of self-paced video lessons</p>
<h3>Lesson 1 : Introduction to Python</h3>
<h3>Lesson 2 : Datatypes in Python</h3>
<h3>Lesson 8 : Python Libraries: NumPy</h3>
</body></html>
"""

UPDATED_PAGE = """
<html><head><title>Free Python Course</title></head>
<body>
<h1>Free Python Course with Certificate</h1>
<p>12 Hours Of self-paced video lessons</p>
<h3>Lesson 1 : Introduction to Python</h3>
<h3>Lesson 2 : Datatypes in Python</h3>
<h3>Lesson 3 : Strings in Python</h3>
<p>Application closes on 12 Aug 2026</p>
</body></html>
"""

BOOTCAMP_PAGE = """
<html><head><title>Applied Agentic AI</title></head>
<body>
<h1>Applied Agentic AI</h1>
<p>10 weeks of live training</p>
<p>Application closes on 20 Oct 2026</p>
<h3>Lesson 1 : Python Refresher</h3>
</body></html>
"""


class StudyAgentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp())
        shutil.copytree(ROOT / "data", self.root / "data")
        shutil.rmtree(self.root / "data" / "snapshots", ignore_errors=True)
        report = self.root / "data" / "latest_report.md"
        if report.exists():
            report.unlink()
        self.store = Store(self.root)

    def tearDown(self) -> None:
        shutil.rmtree(self.root, ignore_errors=True)

    def test_new_learner_starts_at_lesson_one(self) -> None:
        view = assess(self.store.curriculum(), self.store.progress(), self.store.profile())
        self.assertEqual(view["finished"], 0)
        self.assertEqual(view["total"], 13)
        self.assertEqual(view["next"]["id"], "1")
        self.assertEqual(view["phase"], "foundations")
        self.assertGreater(view["sessions_left"], 0)

    def test_marking_a_lesson_moves_the_checklist(self) -> None:
        progress, message = mark_done(self.store.progress(), "1", {"1", "2"})
        self.assertIn("Marked lesson 1", message)
        view = assess(self.store.curriculum(), progress, self.store.profile())
        self.assertEqual(view["finished"], 1)
        self.assertEqual(view["next"]["id"], "2")

    def test_extracts_lessons_hours_and_dates(self) -> None:
        facts = extract_facts(UPDATED_PAGE, "https://example.test/python")
        self.assertEqual(
            facts["lessons"],
            [
                "1 Introduction to Python",
                "2 Datatypes in Python",
                "3 Strings in Python",
            ],
        )
        self.assertEqual(facts["hours"], ["12"])
        self.assertIn("Application closes 12 Aug 2026", facts["highlights"])
        unrelated = """
        <h1>Free Python Course</h1>
        <p>This Course Includes 11 Hours Of self-paced video lessons</p>
        <h2>Get Ahead with Professional Certificate Programs</h2>
        <p>Duration: 20 weeks</p>
        """
        kept = extract_facts(unrelated, "https://example.test/python")
        self.assertEqual(kept["hours"], ["11"])
        self.assertEqual(kept["weeks"], [])

    def test_second_check_reports_what_changed(self) -> None:
        first = extract_facts(CLASS_PAGE, "https://example.test/python")
        second = extract_facts(UPDATED_PAGE, "https://example.test/python")
        change = diff_facts(first, second)
        self.assertEqual(change["status"], "changed")
        self.assertIn("3 Strings in Python", change["added_lessons"])
        text = describe_change({**change, "name": "Free Python Course", "error": None})
        self.assertIn("added 3 Strings in Python", text)
        self.assertIn("hours changed from 11 to 12", text)

    def test_syllabus_gap_flags_a_new_lesson_number(self) -> None:
        curriculum = self.store.curriculum()["lessons"]
        gap = syllabus_gap(curriculum, ["1 Introduction", "14 Extra Topic"])
        self.assertIn("14", gap)

    def test_agent_checks_progress_and_saves_a_first_copy(self) -> None:
        pages = {
            "https://www.simplilearn.com/learn-python-basics-free-course-skillup": CLASS_PAGE,
            "https://www.simplilearn.com/mobile-and-software-development/python-development-training": CLASS_PAGE,
            "https://www.simplilearn.com/big-data-and-analytics/python-for-data-science-training": CLASS_PAGE,
            "https://www.simplilearn.com/agentic-ai-course-training": BOOTCAMP_PAGE,
        }

        def fetcher(url: str) -> str:
            return pages[url]

        report = run(self.store, fetcher=fetcher, online=True)
        self.assertIn("Finished 0 of 13 lessons", report)
        self.assertIn("Next lesson: 1. Introduction to Python", report)
        self.assertIn("I saved a first copy", report)
        self.assertIn("20 Oct 2026", report)
        self.assertIn("Stay on lesson 1", report)
        self.assertTrue((self.root / "data" / "snapshots" / "python-skillup.json").exists())
        saved = (self.root / "data" / "latest_report.md").read_text(encoding="utf-8")
        self.assertIn("Finished 0 of 13", saved)

    def test_finished_checklist_points_at_later_bootcamps(self) -> None:
        view = {
            "finished": 13,
            "total": 13,
            "next": None,
            "phase": "finished",
            "phase_note": "Your Python checklist is complete.",
        }
        text = advise(view, [])
        self.assertIn("Data Science with Python", text)
        self.assertIn("not marked you enrolled", text)

    def test_done_command_updates_the_log(self) -> None:
        code = main(["done", "1"], root=self.root)
        self.assertEqual(code, 0)
        progress = json.loads((self.root / "data" / "progress.json").read_text(encoding="utf-8"))
        self.assertEqual(progress["completed"], ["1"])
        code = main(["offline"], root=self.root)
        self.assertEqual(code, 0)
        report = (self.root / "data" / "latest_report.md").read_text(encoding="utf-8")
        self.assertIn("Finished 1 of 13 lessons", report)
        self.assertIn("Next lesson: 2. Datatypes in Python", report)
        self.assertIn("Skipped the live page check", report)


if __name__ == "__main__":
    unittest.main()
