# SentinelFlow AI — STAR Behavioral Interview Stories

## 1. Catching AI output that silently lied about being real

**Situation:** The platform's Mastra workflow had a fallback path for when a live LLM call failed, returning template-generated output.
**Task:** Determine whether this fallback was safe to ship, given the project's entire value proposition rests on showing genuine AI decision-making.
**Action:** I traced what happened when a fallback triggered and found the response included a fabricated confidence score and no indication anywhere — not in the API response, not in the UI — that it wasn't a real model decision. I added an explicit `is_simulated` flag to every fallback path, threaded it through the workflow aggregation logic across all four agents, and verified the frontend actually reads and renders it as a visible badge, not just that the flag existed in a backend response.
**Result:** The system now makes an honest, verifiable claim about when it's showing real vs. simulated output — closing what I consider the single most important integrity gap in the whole project.

## 2. Finding a "PDF" that wasn't a PDF

**Situation:** A postmortem PDF export feature had been implemented and reported as working.
**Task:** Verify the claim before accepting it.
**Action:** Instead of trusting the "Content-Type: application/pdf" response header, I checked the actual response bytes for the real PDF magic header (`%PDF-`). It was plain text — the file would fail to open in any real PDF viewer despite looking correct at a glance.
**Result:** Flagged it precisely (wrong artifact, not "PDF export is broken" vaguely), which let it get fixed correctly the first time with a real binary PDF generator — and I independently re-derived the fix myself before accepting it, running the exact generation code standalone and confirming valid output with the system's `file` command.

## 3. Catching fabricated evidence in a status report

**Situation:** A status report claimed a specific file's line count had been measured via a real terminal command, with the output pasted to look authentic.
**Task:** Decide whether to accept the claim.
**Action:** I ran the identical command against the identical commit myself. The numbers didn't match — and this happened multiple times across different reports, with different fabricated numbers each time. I kept the standard consistent: never accept a number I hadn't independently reproduced, regardless of how convincingly it was formatted.
**Result:** Eventually traced to a real, understandable root cause (measuring an uncommitted local file instead of the committed one) rather than malice — but the discipline of re-deriving every claim, not just reading it, is what actually caught it, and is the habit I'd bring to any codebase.

## 4. Finding a test that could pass while the feature it tested was broken

**Situation:** An end-to-end test for the core "trigger incident" flow had been added and was passing in CI.
**Task:** Verify it was actually testing what it claimed to test.
**Action:** I read the test and the endpoint it called side by side. The test sent the wrong request field name, and separately, silently defaulted to a hardcoded incident ID if the real one was missing from the response — meaning a genuinely broken backend could still produce a green test.
**Result:** Fixed both issues (correct field name, explicit assertion instead of silent fallback), turning a false sense of security into an actual safety net.

## 5. A stale assertion that no longer matched the code it tested

**Situation:** Running the full backend test suite for real (not just trusting a "all tests pass" claim) turned up one genuine failure.
**Task:** Determine whether this was a real bug or a stale test.
**Action:** Traced the assertion (checking a model name contained the substring "fast") against the actual current routing logic, which had since moved to real provider model names like `gpt-4o-mini`. The test hadn't been updated when the underlying service changed.
**Result:** Fixed the assertion to check the real, current mapping. Small fix, but it's a good example of test debt accumulating silently — a "passing" CI badge had actually been failing for some time before I ran the suite directly.

## 6. Diagnosing a CI tool collision

**Situation:** After adding a Playwright end-to-end test, the frontend's Jest test suite started failing in a way that had nothing to do with any actual application bug.
**Task:** Find the real cause rather than treat it as a flaky test.
**Action:** Traced it to Jest's default file-matching picking up the Playwright spec file and trying to execute it with Jest's runtime, which fails because Playwright needs its own CLI context to initialize.
**Result:** A one-line config fix (excluding the e2e directory from Jest's test matching) resolved it — but finding it required understanding both tools' internals well enough to recognize the symptom wasn't a real regression.

## 7. Tracking down a test-isolation bug to a module-level singleton

**Situation:** Tests touching the vector database intermittently hung, and a naive fix (pointing test config at an isolated temp directory) didn't actually solve it.
**Task:** Find the real root cause.
**Action:** Discovered the vector-store client was instantiated once at module import time — before any test fixture had a chance to override its storage path — so the "isolated" test config was being set after the real client already existed pointing at the real project directory.
**Result:** Converted the client to a lazy singleton behind a proxy object, and verified the fix with a stress test: ran the same test files three times consecutively without cleanup, confirming the real project directory was never touched.

## 8. Refactoring a 6,000-line file without breaking anything

**Situation:** A single React component had grown to over 6,000 lines with 111 separate state hooks, a clear liability for anyone reviewing the codebase.
**Task:** Reduce it safely, without introducing regressions in a system with no live browser testing available during the refactor.
**Action:** Broke the work into the smallest safe increments: extract one domain's state into its own store, verify the build/type-check/tests still pass, commit, and only then move to the next domain — repeating for component extraction, and only after that, for full route-based restructuring.
**Result:** The file went from 6,058 lines to 155 lines across the full process, verified at every increment rather than in one large, risky change — with zero regressions found in the final verification pass.

## 9. Choosing to fail loudly instead of degrading silently

**Situation:** The rate-limiting middleware fell back to an in-memory limiter whenever Redis was unreachable — including in production, silently.
**Task:** Decide whether this was acceptable.
**Action:** Recognized that a silent fallback in production quietly changes rate limits from "shared across all workers" to "per worker," a security-relevant behavior change nobody would notice until it mattered. Implemented an explicit boot-time check that fails fast in production if Redis is unset or unreachable, while preserving the convenient in-memory fallback for local development.
**Result:** Verified with tests covering all three paths (unset, unreachable, dev-mode passthrough) — turned an invisible degradation into an observable, intentional failure mode.

## 10. Raising coverage on the modules that mattered most, not the easiest ones

**Situation:** Test coverage was uneven across the codebase, and the weakest modules happened to be the safety/reliability layer — idempotency protection, observability, and third-party guardrail validation — exactly where gaps matter most.
**Task:** Improve this meaningfully, not just move an aggregate number.
**Action:** Targeted the three specific modules by name, wrote tests covering their actual failure and edge paths (duplicate-key handling, export failure, validation rejection) rather than just happy-path lines.
**Result:** Coverage on those three modules went from 33%/48%/31% to 93%/100%/100%, independently measured — a concrete example of prioritizing risk over raw coverage percentage.
