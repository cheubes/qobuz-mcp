from check_traceability import Step, cited_ids, find_problems, main, parse_criteria, parse_steps

SPEC = """
- **AC-ONE-01** [test] Given something, then something.
- **AC-ONE-02** [live] Given something real, then something.
- **AC-ONE-03** [manual] Checked by hand.
- **AC-ONE-04** [retired] No longer applies.
"""

PLAN = """
- [x] **1. First step**
  Delivers: AC-ONE-01, AC-ONE-02.
  Done when: done.
- [ ] **2. Second step**
  Delivers: AC-ONE-03.
- [ ] **3. Third step**
  Delivers: none.
"""

CRITERIA = {"AC-ONE-01": "test", "AC-ONE-02": "live", "AC-ONE-03": "manual"}


def test_parse_criteria_reads_ids_and_tags() -> None:
    criteria, problems = parse_criteria(SPEC)
    assert criteria == {**CRITERIA, "AC-ONE-04": "retired"}
    assert problems == []


def test_parse_criteria_reports_malformed_and_duplicate_lines() -> None:
    _, problems = parse_criteria(SPEC + "- **AC-ONE-01** [test] Again.\n- **AC-BAD** [test] No.\n")
    assert "AC-ONE-01: defined more than once" in problems
    assert any("no valid ID and tag" in problem for problem in problems)


def test_parse_steps_reads_checkboxes_and_delivered_criteria() -> None:
    assert parse_steps(PLAN) == [
        Step(number=1, checked=True, delivers=("AC-ONE-01", "AC-ONE-02")),
        Step(number=2, checked=False, delivers=("AC-ONE-03",)),
        Step(number=3, checked=False, delivers=()),
    ]


def test_cited_ids_reads_docstrings_only() -> None:
    source = '''
"""Module covering AC-ONE-01."""

DATA = "AC-ONE-03 in a string is not a citation"

def test_something():
    """Covers AC-ONE-02."""

class TestGroup:
    """Covers AC-ONE-04."""
'''
    assert cited_ids([source]) == {"AC-ONE-01", "AC-ONE-02", "AC-ONE-04"}


def test_no_problem_when_checked_steps_are_covered() -> None:
    steps = parse_steps(PLAN)
    assert find_problems(CRITERIA, steps, {"AC-ONE-01", "AC-ONE-02"}) == []


def test_unchecked_steps_need_no_tests() -> None:
    steps = [Step(number=1, checked=False, delivers=("AC-ONE-01", "AC-ONE-02", "AC-ONE-03"))]
    assert find_problems(CRITERIA, steps, set()) == []


def test_checked_step_with_uncited_automated_criterion_fails() -> None:
    problems = find_problems(CRITERIA, parse_steps(PLAN), {"AC-ONE-01"})
    assert problems == ["AC-ONE-02: step 1 is checked but no test cites it"]


def test_delivery_problems_are_reported() -> None:
    steps = [
        Step(number=1, checked=False, delivers=("AC-ONE-01", "AC-ONE-01", "AC-ONE-09")),
        Step(number=2, checked=False, delivers=("AC-ONE-04",)),
    ]
    problems = find_problems(
        {**CRITERIA, "AC-ONE-04": "retired"}, steps, {"AC-ONE-04", "AC-ONE-08"}
    )
    assert problems == [
        "AC-ONE-01: delivered by 2 plan steps",
        "AC-ONE-02: delivered by no plan step",
        "AC-ONE-03: delivered by no plan step",
        "AC-ONE-04: retired but delivered by a plan step",
        "AC-ONE-04: retired but cited by a test",
        "AC-ONE-09: delivered by a plan step but not defined",
        "AC-ONE-08: cited by a test but not defined",
    ]


def test_repository_traceability_is_consistent() -> None:
    assert main() == 0
