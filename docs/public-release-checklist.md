# Public-release checklist

Repository visibility must remain private until every blocking item is complete. This document is
a release gate, not a claim that legal or company approval has already been obtained.

## Blocking approval

- [ ] The company or other actual copyright owner has confirmed in writing that this extracted
  algorithm may be released under Apache-2.0.
- [ ] The approver has confirmed that naming RideAssign as the origin of the technical extraction
  is acceptable.

An automated tool cannot establish ownership or grant company approval. Record the approver and
date in the private release record; do not commit confidential agreement details here.

## Completed repository preparation

- [x] The repository uses the Apache License 2.0.
- [x] The package metadata declares the SPDX identifier `Apache-2.0`.
- [x] Examples, tests, and benchmarks use synthetic inputs only.
- [x] Public contribution, conduct, and security policies are present.
- [x] Benchmark claims state their methodology and limits.

## Final technical verification

Complete these against the exact commit proposed for publication:

- [x] `make check` passes.
- [x] `make audit` reports no known vulnerable Python dependencies.
- [x] a full Git-history secret scan reports no findings.
- [x] a full Git-history proprietary-content review reports no customer data, credentials,
  production coordinates, copied provider payloads, private infrastructure, or application policy.
- [x] dependency licenses have been reviewed for compatibility with Apache-2.0 distribution.

Record exact commands, versions, commit, and results in `docs/release-audit.md`.

## Publication

- [ ] Confirm a temporary private security contact for the visibility-change window.
- [ ] Review the public repository description, topics, and social preview.
- [ ] Change visibility to public.
- [ ] Immediately enable GitHub private vulnerability reporting, then confirm the security and
  conduct reporting links work without repository write access. Do not announce the repository
  until this succeeds; GitHub exposes this setting only for public repositories.
- [ ] Create a signed or annotated version tag and GitHub release from the audited commit.
