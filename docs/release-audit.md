# Release audit

## Scope

- Audit date: 2026-08-09
- Base commit: `a4d2e738367c5ddd979c04f4085f1d9eef94aefb`
- Release-polish diff SHA-256, excluding this audit record:
  `1ed239f73d27f463f3fc44b79082946b1abb20b122d166379d29043f5b127783`
- Repository visibility during the audit: private

The base commit plus the recorded diff hash identifies the audited source change set without a
self-referential commit hash. Publication must still use a reviewed commit containing exactly that
change set and pass CI at its final SHA.

## Verification results

| Check | Tool or command | Result |
| --- | --- | --- |
| Format and lint | Ruff 0.16.2 through `make check` | Passed |
| Static typing | mypy 2.3.0 strict mode through `make check` | Passed |
| Tests | pytest 9.1.1 through `make check` | 64 passed |
| Coverage | pytest-cov 7.0.0 | 99.69% branch-aware coverage |
| Distribution | `python -m build` | sdist and wheel built successfully |
| Package metadata | wheel `METADATA` inspection | `License-Expression: Apache-2.0` |
| Dependency vulnerabilities | pip-audit 2.10.1 | No known vulnerabilities found |
| License text | `diff` against Apache's official `LICENSE-2.0.txt` | Exact match |
| Reachable Git history | Gitleaks 8.30.1 with `git --log-opts='--all'` | 0 findings across all refs |
| Working tree | Gitleaks 8.30.1 `dir` scan | 0 findings |
| Proprietary-content review | all-ref term, URL, email, path, and coordinate review | No prohibited material found |
| Fixed synthetic benchmark | `python -m benchmarks.run` | Documented deterministic outcomes reproduced |
| Seeded scale benchmark | 5 repetitions, 1-second bound, Apple M4 | All cases served every shipment |

Gitleaks reported seven commit diffs scanned across eight reachable commits; the extra reachable
commit is a merge commit with no independent content diff. The all-ref review included stale remote
dependency branches as well as `main` and the solver feature branch.

The proprietary-content review found only intentional references to RideAssign and Valhalla in
boundary documentation, synthetic Munich-area coordinates in examples/fixtures, repository-owned
GitHub URLs, and an historical Biome schema URL. It found no emails, customer identifiers,
credentials, production hosts, copied provider payloads, database schemas, or application policy.

## Runtime dependency licenses

The installed runtime dependency graph was traversed from the pinned `ortools==9.15.6755`
distribution metadata.

| Distribution | Version | Declared license family |
| --- | --- | --- |
| ortools | 9.15.6755 | Apache-2.0 |
| absl-py | 2.5.0 | Apache-2.0 |
| numpy | 2.5.1 | BSD-3-Clause and other permissive component licenses |
| pandas | 3.0.5 | BSD-3-Clause |
| protobuf | 6.33.6 | BSD-3-Clause |
| typing-extensions | 4.16.0 | PSF-2.0 |
| immutabledict | 4.3.1 | MIT |
| python-dateutil | 2.9.0.post0 | Apache-2.0/BSD-3-Clause dual licensing |
| six | 1.17.0 | MIT |

No reciprocal or source-disclosure license was observed in the runtime dependency metadata. These
licenses are commonly distributed alongside Apache-2.0 projects, but this engineering review is
not a legal opinion. The actual copyright owner must approve publication and licensing.

## Remaining blockers

1. Obtain and record written approval from the company or actual copyright owner.
2. Confirm permission to name RideAssign as the source of the technical extraction.
3. Review the final committed SHA and its GitHub Actions run.
4. Configure the public-only private vulnerability reporting feature during the controlled
   visibility change, before announcing the repository.
