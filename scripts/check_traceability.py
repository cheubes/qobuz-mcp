"""Check that acceptance criteria, implementation plan steps and tests stay linked (ADR-0026)."""

import ast
import re
from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FUNCTIONAL_SPEC = ROOT / "specs" / "functional-specifications.md"
PLAN = ROOT / "specs" / "implementation-plan.md"
TESTS = ROOT / "tests"

CRITERION_LINE = re.compile(r"^- \*\*AC-", re.MULTILINE)
CRITERION = re.compile(r"^- \*\*(AC-[A-Z]+-\d+)\*\* \[(test|live|manual|retired)\]", re.MULTILINE)
CRITERION_ID = re.compile(r"\bAC-[A-Z]+-\d+\b")
STEP = re.compile(r"^- \[( |x)\] \*\*(\d+)\. ", re.MULTILINE)
DELIVERS = re.compile(r"^\s+Delivers: (.*)$", re.MULTILINE)
AUTOMATED_TAGS = {"test", "live"}


@dataclass(frozen=True)
class Step:
    number: int
    checked: bool
    delivers: tuple[str, ...]


def parse_criteria(functional_spec: str) -> tuple[dict[str, str], list[str]]:
    criteria: dict[str, str] = {}
    problems: list[str] = []
    matches = CRITERION.findall(functional_spec)
    if len(matches) != len(CRITERION_LINE.findall(functional_spec)):
        problems.append("functional specifications: a criterion line has no valid ID and tag")
    for criterion_id, tag in matches:
        if criterion_id in criteria:
            problems.append(f"{criterion_id}: defined more than once")
        criteria[criterion_id] = tag
    return criteria, problems


def parse_steps(plan: str) -> list[Step]:
    starts = list(STEP.finditer(plan))
    steps = []
    for index, start in enumerate(starts):
        end = starts[index + 1].start() if index + 1 < len(starts) else len(plan)
        delivers = DELIVERS.search(plan, start.end(), end)
        ids = tuple(CRITERION_ID.findall(delivers.group(1))) if delivers else ()
        steps.append(Step(number=int(start.group(2)), checked=start.group(1) == "x", delivers=ids))
    return steps


def cited_ids(test_sources: Iterable[str]) -> set[str]:
    cited: set[str] = set()
    for source in test_sources:
        for node in ast.walk(ast.parse(source)):
            if isinstance(node, ast.Module | ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef):
                cited.update(CRITERION_ID.findall(ast.get_docstring(node) or ""))
    return cited


def find_problems(criteria: dict[str, str], steps: list[Step], cited: set[str]) -> list[str]:
    problems: list[str] = []
    delivered = Counter(criterion_id for step in steps for criterion_id in step.delivers)
    for criterion_id, tag in criteria.items():
        if tag == "retired":
            if criterion_id in delivered:
                problems.append(f"{criterion_id}: retired but delivered by a plan step")
            if criterion_id in cited:
                problems.append(f"{criterion_id}: retired but cited by a test")
        elif delivered[criterion_id] == 0:
            problems.append(f"{criterion_id}: delivered by no plan step")
        elif delivered[criterion_id] > 1:
            problems.append(f"{criterion_id}: delivered by {delivered[criterion_id]} plan steps")
    for criterion_id in sorted(set(delivered) - set(criteria)):
        problems.append(f"{criterion_id}: delivered by a plan step but not defined")
    for criterion_id in sorted(cited - set(criteria)):
        problems.append(f"{criterion_id}: cited by a test but not defined")
    for step in steps:
        if not step.checked:
            continue
        for criterion_id in step.delivers:
            if criteria.get(criterion_id) in AUTOMATED_TAGS and criterion_id not in cited:
                problems.append(
                    f"{criterion_id}: step {step.number} is checked but no test cites it"
                )
    return problems


def main() -> int:
    criteria, problems = parse_criteria(FUNCTIONAL_SPEC.read_text())
    steps = parse_steps(PLAN.read_text())
    cited = cited_ids(path.read_text() for path in sorted(TESTS.rglob("*.py")))
    problems += find_problems(criteria, steps, cited)
    for problem in problems:
        print(problem)
    if problems:
        return 1
    checked = sum(step.checked for step in steps)
    print(f"{len(criteria)} criteria, {len(steps)} plan steps ({checked} checked): traceability OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
