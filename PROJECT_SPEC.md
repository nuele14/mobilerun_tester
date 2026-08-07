# Project Specification – Mobilerun Testing Framework

## 📌 Purpose & Usage

This document is the **single source of truth** for the adaptation of the Mobilerun framework into a **mobile‑app testing platform** for Android. It is intended for developers, QA engineers, and product owners who need to:

1. **Understand the overall goal** of the project.
2. **Track the implementation progress** via a to‑do list.
3. **Add or modify features** as the project evolves.
4. **Keep the documentation in sync** with the codebase.

> **When to update**
> - After every sprint or milestone.
> - When a new feature is added or a requirement changes.
> - When a bug or design decision is resolved.
> - Whenever a to‑do item is completed.

The file should be edited manually; automated generation is not required.

---

## 🎯 Project Scope

- **Goal**: Build a **stand‑alone testing engine** that can run end‑to‑end tests on Android devices using the existing Mobilerun agent infrastructure.
- **Key Deliverables**:
  1. A **test scenario language** (JSON/YAML) describing actions, pre‑conditions, assertions, and post‑conditions.
  2. A **Test Runner** that orchestrates scenario execution via `MobileAgent`.
  3. An **Assertion Engine** for UI state verification.
  4. A **Report Generator** producing HTML and JUnit XML.
  5. A **CLI** for running tests locally.
  6. Optional advanced features (parameterization, visual regression, etc.) as future work.

---

## 🏗️ High‑Level Architecture

```
┌─────────────────────────────────────┐
│       Test Runner (Orchestrator)    │
├─────────────────────────────────────┤
│  - Load scenario files              │
│  - Manage test lifecycle            │
│  - Coordinate assertions            │
│  - Generate reports                 │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│      MobileAgent (Execution Engine) │
├─────────────────────────────────────┤
│  - Processes LLM‑driven actions     │
│  - Executes UI interactions         │
│  - Provides state & screenshots    │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│        Device Driver (ADB/Portal)   │
├─────────────────────────────────────┤
│  - Controls Android device           │
│  - Supplies UI tree & screenshots   │
└─────────────────────────────────────┘
```

---

## 📋 Implementation Plan (To‑Do List)

| # | Task | Owner | Status | Notes |
|---|------|-------|--------|-------|
| 1 | **Define scenario schema** (JSON/YAML) | QA Lead | ☐ | Include actions, preconditions, assertions, postconditions |
| 2 | Create `mobilerun_tester/testing/__init__.py` | Dev | ☐ | Package marker |
| 3 | Implement `test_runner.py` | Dev | ☐ | Orchestrator, loads scenarios, runs `MobileAgent` |
| 4 | Implement `assertions.py` | Dev | ☐ | Element visibility, value, screenshot comparison |
| 5 | Implement `report_generator.py` | Dev | ☐ | HTML + JUnit XML output |
| 6 | Implement `fixtures.py` | Dev | ☐ | Test data & environment setup |
| 7 | Implement `cli.py` | Dev | ☐ | Commands: run, report, parallel, debug |
| 8 | Integrate `AndroidDriver` with test runner | Dev | ☐ | Use existing driver, handle auto‑setup & portal mode |
| 9 | Add helper tools: install/uninstall app, clear data | Dev | ☐ | Expose via `mobilerun_tester/testing/tools.py` |
|10 | Write unit tests for new modules | QA | ☐ | Ensure coverage ≥ 80% |
|11 | Document usage examples in README | Docs | ☐ | Include CLI usage, scenario example |
|12 | Add advanced feature placeholders (parameterization, visual regression) | Dev | ☐ | Mark as future work |
|13 | Review & merge PRs | Team | ☐ | Code review checklist: tests, docs, lint |
|14 | Update this spec after each milestone | Owner | ☐ | Keep status current |

---

## 🚀 Feature Roadmap (Advanced Features)

1. **Parameterization** – Support variables in scenarios (`{{var}}`) resolved from environment or fixture files.
2. **Data‑Driven Testing** – Run the same scenario with multiple data sets.
3. **Visual Regression** – Capture baseline screenshots and compare with current run.
4. **Performance Metrics** – Record execution time, memory usage, and device CPU load.
5. **Retry Logic** – Automatic retries for flaky tests.
6. **Flaky Test Detection** – Analyze test history to flag unstable tests.

These features will be added after the core testing engine is stable.

---

## 📚 References & Resources

- [Mobilerun Core Repository](https://github.com/droidrun/mobilerun)
- [Mobilerun Documentation](https://docs.mobilerun.ai)
- [Python LLM Index](https://github.com/jerryjliu/llama_index)
- [ADB Tools](https://developer.android.com/studio/command-line/adb)
- [Pytest](https://docs.pytest.org)

---

## 📌 Revision History

| Date | Author | Change |
|------|--------|--------|
| 2026‑08‑07 | Emanuele | Initial draft |

---

*End of Document*