"""
Publishes one GitHub release for everything that reached main during a Malaysia-time day.

Each release covers main's history from the previous v* tag up to the last commit made on
main before 23:59:59 that day, so the next release always starts where the last one ended.
The version is bumped from the Conventional Commit types: a breaking change (`type!:` or a
BREAKING CHANGE footer) is a major, a feature is a minor, anything else is a patch.

Environment:
  RELEASE_DATE  YYYY-MM-DD in Malaysia time to release just that day. Without it, every day
                from the latest release up to yesterday is released in order, so a run that
                GitHub skipped is caught up on the next one
  BUMP          auto (default), patch, minor or major; only applies with RELEASE_DATE
  DRY_RUN       "true" prints the releases instead of publishing them
  REPO          owner/name, for links and the GitHub CLI
"""

from __future__ import annotations

import datetime as dt
import os
import re
import subprocess
import sys
import tempfile

MALAYSIA = dt.timezone(dt.timedelta(hours=8), "MYT")
VERSION_TAG = re.compile(r"v(\d+)\.(\d+)\.(\d+)")
CONVENTIONAL = re.compile(
    r"^(?P<type>[a-z]+)(?:\((?P<scope>[^)]*)\))?(?P<breaking>!)?: (?P<summary>.+)$"
)
# GitHub cuts pull request titles over 72 characters with "…", which can leave half an issue
# reference such as "(#…" in front of the pull request number
CUT_OFF_REFERENCE = re.compile(r"\s*\((?:#\d*)?…(?=\s*\(#\d+\)$)")
SECTIONS = [
    ("Features", {"feat"}),
    ("Fixes", {"fix"}),
    ("Performance", {"perf"}),
    ("Data", {"data"}),
    ("Documentation", {"docs"}),
    ("Maintenance", {"refactor", "test", "build", "ci", "chore", "style", "revert"}),
]

Version = tuple[int, int, int]


def git(*args: str) -> str:
    result = subprocess.run(["git", *args], check=True, capture_output=True, encoding="utf-8")
    return result.stdout.strip()


def is_ancestor(older: str, newer: str) -> bool:
    return subprocess.run(["git", "merge-base", "--is-ancestor", older, newer]).returncode == 0


def parse_version(tag: str) -> Version | None:
    m = VERSION_TAG.fullmatch(tag)
    return (int(m[1]), int(m[2]), int(m[3])) if m else None


def latest_tag() -> tuple[str, Version]:
    versions = [
        (tag, version)
        for tag in git("tag", "--list", "v*").split()
        if (version := parse_version(tag)) is not None
    ]
    if not versions:
        sys.exit("No v<major>.<minor>.<patch> tag to continue from.")
    return max(versions, key=lambda v: v[1])


def commits(since: str, until: str) -> list[tuple[str, str]]:
    """Subject and body of each change; release merge commits are left out."""
    # str.strip() treats the ASCII separator characters as whitespace, so use marker strings
    log_format = "--format=%s<<BODY>>%b<<END>>"
    raw = git("log", "--no-merges", "--reverse", log_format, f"{since}..{until}")
    changes = []
    for entry in raw.split("<<END>>"):
        subject, _, body = entry.partition("<<BODY>>")
        if subject.strip():
            changes.append((subject.strip(), body.strip()))
    return changes


def next_version(current: Version, changes: list[tuple[str, str]], bump: str) -> str:
    if bump == "auto":
        parsed = [CONVENTIONAL.match(subject) for subject, _ in changes]
        if any(m and m["breaking"] for m in parsed) or any(
            "BREAKING CHANGE" in body for _, body in changes
        ):
            bump = "major"
        elif any(m and m["type"] == "feat" for m in parsed):
            bump = "minor"
        else:
            bump = "patch"
    major, minor, patch = current
    if bump == "major":
        return f"v{major + 1}.0.0"
    if bump == "minor":
        return f"v{major}.{minor + 1}.0"
    return f"v{major}.{minor}.{patch + 1}"


def notes(day: dt.date, previous: str, tag: str, changes: list[tuple[str, str]], repo: str) -> str:
    grouped: dict[str, list[str]] = {title: [] for title, _ in SECTIONS}
    other: list[str] = []
    for subject, _ in changes:
        subject = CUT_OFF_REFERENCE.sub("", subject)
        m = CONVENTIONAL.match(subject)
        if m is None:
            other.append(f"- {subject}")
            continue
        summary = m["summary"][0].upper() + m["summary"][1:]
        line = f"- **{m['scope']}:** {summary}" if m["scope"] else f"- {summary}"
        section = next((title for title, types in SECTIONS if m["type"] in types), None)
        (grouped[section] if section else other).append(line)

    parts = [f"Changes that reached production on {day:%d %B %Y} (Malaysia time)."]
    for title, lines in [*grouped.items(), ("Other changes", other)]:
        if lines:
            parts.append(f"### {title}\n\n" + "\n".join(lines))
    parts.append(f"**Full changelog:** https://github.com/{repo}/compare/{previous}...{tag}")
    return "\n\n".join(parts) + "\n"


def release_day(
    day: dt.date, previous: str, current: Version, bump: str, repo: str, dry_run: bool
) -> tuple[str, Version] | None:
    """Release one day; returns the new tag and version, or None if nothing reached main."""
    end_of_day = dt.datetime.combine(day, dt.time(23, 59, 59), MALAYSIA).isoformat()
    target = git("rev-list", "-1", "--first-parent", f"--before={end_of_day}", "origin/main")
    previous_sha = git("rev-list", "-n", "1", previous)
    if not target or is_ancestor(target, previous_sha):
        print(f"{day}: nothing new reached main since {previous}.")
        return None
    if not is_ancestor(previous_sha, target):
        sys.exit(f"{previous} is not in main's history before {day}. Release earlier days first.")

    changes = commits(previous_sha, target)
    tag = next_version(current, changes, bump)
    title = f"Free Stop {tag} ({day:%d %b %Y})"
    body = notes(day, previous, tag, changes, repo)

    print(f"{title}\nTarget: {target}\n\n{body}")
    if summary := os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(summary, "a", encoding="utf-8") as f:
            f.write(f"## {title}{' (dry run)' if dry_run else ''}\n\n{body}\n")

    if dry_run:
        git("tag", tag, target)  # local only, so a dry run shows the whole chain
    else:
        with tempfile.NamedTemporaryFile(
            "w", suffix=".md", delete=False, encoding="utf-8"
        ) as notes_file:
            notes_file.write(body)
        subprocess.run(
            ["gh", "release", "create", tag, "--repo", repo, "--target", target,
             "--title", title, "--notes-file", notes_file.name],
            check=True,
        )  # fmt: skip
        # The next day continues from this release's commit
        git("fetch", "--quiet", "origin", f"refs/tags/{tag}:refs/tags/{tag}")

    version = parse_version(tag)
    assert version is not None
    return tag, version


def main() -> None:
    repo = os.environ["REPO"]
    bump = os.environ.get("BUMP", "auto") or "auto"
    dry_run = os.environ.get("DRY_RUN", "false") == "true"
    yesterday = dt.datetime.now(MALAYSIA).date() - dt.timedelta(days=1)
    requested = os.environ.get("RELEASE_DATE", "").strip()
    previous, current = latest_tag()

    if requested:
        day = dt.date.fromisoformat(requested)
        if day > yesterday:
            sys.exit(f"{day} has not ended yet in Malaysia time, so it cannot be released.")
        days = [day]
    else:
        # Catch up on every day since the latest release, so a skipped run repairs itself
        tagged = dt.datetime.fromisoformat(git("log", "-1", "--format=%cI", previous))
        first = tagged.astimezone(MALAYSIA).date()
        days = [first + dt.timedelta(days=i) for i in range((yesterday - first).days + 1)]
        bump = "auto"

    created: list[str] = []
    for day in days:
        released = release_day(day, previous, current, bump, repo, dry_run)
        if released:
            previous, current = released
            created.append(previous)
    if dry_run and created:
        git("tag", "--delete", *created)


if __name__ == "__main__":
    main()
