"""Fetch Simplilearn pages and compare them with the last saved copy."""

from __future__ import annotations

import re
from html import unescape
from html.parser import HTMLParser
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

LESSON_RE = re.compile(
    r"(?i)lesson\s*0*(\d{1,2})\s*[:.\-]\s*([A-Za-z][^<\n|]{2,80})"
)
HOURS_RE = re.compile(r"(?i)(\d{1,3})\s+hours?")
WEEKS_ONLY_RE = re.compile(r"(?i)^(\d{1,2})\s+weeks?\b")
WEEKS_OF_RE = re.compile(r"(?i)^(\d{1,2})\s+weeks?\s+of\s+(?:live|self-paced|instructor)")
DATE_RE = re.compile(
    r"\b(\d{1,2}(?:st|nd|rd|th)?\s+[A-Z][a-z]{2,8},?(?:\s+20\d{2})?)\b"
)


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.skip = 0
        self.parts: list[str] = []
        self.title_parts: list[str] = []
        self.h1_parts: list[str] = []
        self._in_title = False
        self._in_h1 = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style", "noscript"}:
            self.skip += 1
        elif tag == "title":
            self._in_title = True
        elif tag == "h1":
            self._in_h1 = True

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "noscript"} and self.skip:
            self.skip -= 1
        elif tag == "title":
            self._in_title = False
            self.parts.append("\n")
        elif tag == "h1":
            self._in_h1 = False
            self.parts.append("\n")
        elif tag in {"p", "li", "h2", "h3", "h4", "br", "div", "tr"}:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if self.skip:
            return
        if self._in_title:
            self.title_parts.append(data)
        if self._in_h1:
            self.h1_parts.append(data)
        self.parts.append(data)


def fetch_url(url: str, timeout: int = 20) -> str:
    request = Request(
        url,
        headers={
            "User-Agent": "SimplilearnStudyAgent/1.0 (learning progress checker)"
        },
    )
    with urlopen(request, timeout=timeout) as response:
        raw = response.read()
    return raw.decode("utf-8", errors="replace")


def extract_facts(html: str, url: str) -> dict:
    parser = _TextExtractor()
    parser.feed(html)
    text = unescape("".join(parser.parts))
    lines = [_clean(line) for line in text.splitlines() if _clean(line)]
    title = _clean(" ".join(parser.h1_parts)) or _clean(" ".join(parser.title_parts))
    lessons = _lessons(text)
    course_lines = _course_lines(lines)
    return {
        "url": url,
        "title": title[:120],
        "lessons": lessons,
        "hours": _labeled_numbers(course_lines, HOURS_RE, ("self-paced", "video", "instructor", "training")),
        "weeks": _program_weeks(course_lines),
        "highlights": _highlights(course_lines),
        "error": None,
    }


def diff_facts(previous: dict | None, current: dict) -> dict:
    if current.get("error"):
        return {
            "status": "error",
            "error": current["error"],
            "lessons": [],
            "added_lessons": [],
            "removed_lessons": [],
        }
    if previous is None:
        return {
            "status": "baseline",
            "lessons": current["lessons"],
            "added_lessons": current["lessons"],
            "removed_lessons": [],
            "title": current["title"],
            "hours": current["hours"],
            "weeks": current["weeks"],
            "highlights": current["highlights"],
        }
    added = [item for item in current["lessons"] if item not in previous.get("lessons", [])]
    removed = [item for item in previous.get("lessons", []) if item not in current["lessons"]]
    changed = any(
        [
            added,
            removed,
            previous.get("title") != current["title"],
            previous.get("hours") != current["hours"],
            previous.get("weeks") != current["weeks"],
            previous.get("highlights") != current["highlights"],
        ]
    )
    return {
        "status": "changed" if changed else "unchanged",
        "lessons": current["lessons"],
        "added_lessons": added,
        "removed_lessons": removed,
        "title_from": previous.get("title"),
        "title_to": current["title"],
        "hours_from": previous.get("hours", []),
        "hours_to": current["hours"],
        "weeks_from": previous.get("weeks", []),
        "weeks_to": current["weeks"],
        "highlights_from": previous.get("highlights", []),
        "highlights_to": current["highlights"],
    }


def refresh_source(source: dict, previous: dict | None, fetcher) -> tuple[dict, dict]:
    try:
        html = fetcher(source["url"])
        facts = extract_facts(html, source["url"])
    except (HTTPError, URLError, TimeoutError, OSError) as exc:
        facts = {
            "url": source["url"],
            "title": "",
            "lessons": [],
            "hours": [],
            "weeks": [],
            "highlights": [],
            "error": str(exc),
        }
    change = diff_facts(previous, facts)
    change["id"] = source["id"]
    change["name"] = source["name"]
    change["kind"] = source["kind"]
    change["enrolled"] = source["enrolled"]
    change["url"] = source["url"]
    return facts, change


def syllabus_gap(curriculum_lessons: list[dict], extracted: list[str]) -> str | None:
    if not extracted:
        return None
    expected = {lesson["id"] for lesson in curriculum_lessons}
    found = {_lesson_number(item) for item in extracted}
    missing = sorted(expected - found, key=int)
    extra = sorted(found - expected, key=int)
    if not missing and not extra:
        return None
    parts = []
    if extra:
        parts.append("new lesson numbers on the page: " + ", ".join(extra))
    if missing:
        parts.append("checklist lessons missing on the page: " + ", ".join(missing))
    return "; ".join(parts)


def describe_change(change: dict) -> str:
    name = change["name"]
    status = change["status"]
    if status == "error":
        return f"{name}: I could not open the page ({change['error']})."
    if status == "baseline":
        count = len(change["added_lessons"])
        detail = f"I saved a first copy and found {count} lesson lines."
        if change.get("hours"):
            detail += " Video length listed: " + ", ".join(change["hours"]) + " hours."
        if change.get("weeks"):
            detail += " Duration: " + ", ".join(change["weeks"]) + " weeks."
        if change.get("highlights"):
            detail += " " + "; ".join(change["highlights"]) + "."
        else:
            detail += " The next check will compare against this copy."
        return f"{name}: {detail}"
    if status == "unchanged":
        return f"{name}: no change since the last check."
    bits = []
    if change["added_lessons"]:
        bits.append("added " + "; ".join(change["added_lessons"]))
    if change["removed_lessons"]:
        bits.append("removed " + "; ".join(change["removed_lessons"]))
    if change["hours_from"] != change["hours_to"]:
        bits.append(f"hours changed from {_join(change['hours_from'])} to {_join(change['hours_to'])}")
    if change["weeks_from"] != change["weeks_to"]:
        bits.append(f"weeks changed from {_join(change['weeks_from'])} to {_join(change['weeks_to'])}")
    if change["highlights_from"] != change["highlights_to"]:
        bits.append(
            f"notes changed from {_join(change['highlights_from'])} to {_join(change['highlights_to'])}"
        )
    if change["title_from"] != change["title_to"]:
        bits.append(f"title changed from {change['title_from']} to {change['title_to']}")
    return f"{name}: " + "; ".join(bits) + "."


def _lessons(text: str) -> list[str]:
    found: dict[str, str] = {}
    for number, title in LESSON_RE.findall(text):
        number = str(int(number))
        cleaned = _clean(re.split(r"(?i)\blesson\s*\d", title)[0]).rstrip(" .-")
        if number not in found and cleaned:
            found[number] = cleaned
    return [f"{number} {found[number]}" for number in sorted(found, key=int)]


def _course_lines(lines: list[str]) -> list[str]:
    """Stop before related-program cards, webinars, and article dates."""
    stops = (
        "professional certificate programs",
        "on demand webinar",
        "articles and ebooks",
        "explore related",
    )
    for index, line in enumerate(lines):
        lowered = line.lower()
        if any(stop in lowered for stop in stops):
            return lines[:index]
    return lines


def _program_weeks(lines: list[str]) -> list[str]:
    found: list[str] = []
    for index, line in enumerate(lines):
        only = WEEKS_ONLY_RE.match(line)
        if only:
            previous = " ".join(lines[max(0, index - 2) : index]).lower()
            if "duration" in previous:
                found.append(only.group(1))
            continue
        of_training = WEEKS_OF_RE.match(line)
        if of_training:
            found.append(of_training.group(1))
    return _unique(found)[:2]


def _labeled_numbers(lines: list[str], pattern: re.Pattern[str], labels: tuple[str, ...]) -> list[str]:
    found: list[str] = []
    for index, line in enumerate(lines):
        match = pattern.search(line)
        if not match:
            continue
        window = " ".join(lines[max(0, index - 2) : index + 1]).lower()
        if any(label in window for label in labels):
            found.append(match.group(1))
    return _unique(found)[:3]


def _highlights(lines: list[str]) -> list[str]:
    found: list[str] = []
    for index, line in enumerate(lines):
        lowered = line.lower()
        if "application closes" in lowered or "admission closes" in lowered:
            when = _date_near(lines, index)
            if when:
                found.append(f"Application closes {when}")
        elif lowered == "next cohort":
            label = _next_label(lines, index)
            if label:
                found.append(f"Next cohort: {label}")
        elif "python refresher" in lowered:
            found.append(line[:90])
    closes = [item for item in found if item.startswith("Application closes") and re.search(r"20\d{2}", item)]
    if not closes:
        closes = [item for item in found if item.startswith("Application closes")][:1]
    else:
        closes = closes[:1]
    others = [item for item in found if not item.startswith("Application closes")]
    return _unique(closes + others)[:5]


def _date_near(lines: list[str], index: int) -> str:
    window = " ".join(lines[index : index + 3])
    match = DATE_RE.search(window)
    return match.group(1) if match else ""


def _next_label(lines: list[str], index: int) -> str:
    for line in lines[index + 1 : index + 4]:
        if line.lower() in {"date", "time", "apply", "apply now"}:
            continue
        if len(line) > 3:
            return line[:90]
    return ""


def _lesson_number(label: str) -> str:
    return label.split(" ", 1)[0]


def _unique(items: list[str]) -> list[str]:
    seen: list[str] = []
    for item in items:
        cleaned = _clean(item)
        if cleaned and cleaned not in seen:
            seen.append(cleaned)
    return seen


def _clean(value: str) -> str:
    return " ".join(value.split())


def _join(values: list[str]) -> str:
    return ", ".join(values) if values else "none"
