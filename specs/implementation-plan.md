# Implementation plan

Status: draft. Implements [technical-specifications.md](technical-specifications.md).

Each step lists the acceptance criteria it delivers (`Delivers`, from [functional-specifications.md](functional-specifications.md)) and its exit condition (`Done when`). A step is checked only when its exit condition holds. `scripts/check_traceability.py` reads this file: every criterion is delivered by exactly one step, and the `[test]` and `[live]` criteria of checked steps must be cited by tests.

From step 3 on, every step ships its code with its tests, and all local checks pass before it is checked.

- [ ] **1. Proof of concept**
  A throwaway script, outside the repository. It answers open questions Q1 to Q3 and confirms:
  - the `app_id` extraction patterns;
  - the unvalidated endpoints of the endpoint mapping;
  - the HTTP headers Qobuz requires, including `User-Agent`;
  - whether any in-scope endpoint needs `user_id`.

  It also records the observed response structures for step 2.
  Delivers: none.
  Done when: Q1 to Q3 are resolved and removed, and the specifications are updated with the results.
- [ ] **2. Output models**
  Complete the "Output models" section of the technical specifications from the structures observed in step 1.
  Delivers: none.
  Done when: every model has its field list, and all specifications are set to `approved`.
- [ ] **3. Project scaffold**
  `pyproject.toml` (build backend, dependency groups, uv, ruff, mypy, coverage and pytest configuration), `.python-version`, CLI skeleton with its tests, in-memory `keyring` backend for tests.
  Delivers: none.
  Done when: all local checks pass, including the coverage threshold.
- [ ] **4. Continuous integration**
  `ci.yml`, `dependabot.yml`, `scripts/check_traceability.py`.
  Delivers: none.
  Done when: every required job passes on `main`.
- [ ] **5. Publication**
  The publication version of `README.md`, `codeql.yml`, `CONTRIBUTING.md`, `SECURITY.md`, issue and pull request templates, repository settings, switch to public (technical specifications, "Publication").
  Delivers: none.
  Done when: the repository is public with every setting applied.
- [ ] **6. Credentials, `app_id` extraction, `login` and `logout`**
  Includes the live test harness and its write guard.
  Delivers: AC-SETUP-01, AC-SETUP-02, AC-SETUP-03, AC-SETUP-04, AC-SETUP-05, AC-SETUP-07, AC-SETUP-10, AC-LIVE-01, AC-LIVE-05.
  Done when: the criteria are covered and all checks pass.
- [ ] **7. API client and error mapping**
  Delivers: AC-SETUP-06, AC-BEH-13.
  Done when: the criteria are covered and all checks pass.
- [ ] **8. MCP server and catalog tools**
  Delivers: AC-SETUP-08, AC-SETUP-09, AC-BEH-02, AC-BEH-03, AC-BEH-04, AC-BEH-05, AC-BEH-06, AC-BEH-07, AC-BEH-08, AC-BEH-10, AC-BEH-11, AC-BEH-12, AC-BEH-14, AC-CAT-01, AC-CAT-02, AC-CAT-03, AC-CAT-04, AC-LIVE-02, AC-LIVE-03.
  Done when: the criteria are covered and all checks pass.
- [ ] **9. Library read tools**
  Delivers: AC-LIB-01, AC-LIVE-04.
  Done when: the criteria are covered and all checks pass.
- [ ] **10. Write tools**
  The AC-BEH-11 tests from step 8 are extended to the AC-BEH-09 error case.
  Delivers: AC-BEH-01, AC-BEH-09, AC-LIB-02, AC-LIB-03, AC-PL-01, AC-PL-02, AC-PL-03, AC-PL-04, AC-PL-05, AC-PL-06, AC-PL-07.
  Done when: the criteria are covered, all checks pass, and the full tool catalog of the functional specifications is exposed.
- [ ] **11. README usage sections**
  Prerequisites, login, client configuration.
  Delivers: AC-SETUP-11, AC-BEH-15.
  Done when: both manual criteria have been checked by hand with Claude Desktop and Claude Code.
