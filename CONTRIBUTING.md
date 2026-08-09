# Contributing

Thank you for considering a contribution. The project welcomes narrowly scoped bug reports,
documentation improvements, tests, and changes to the provider-neutral matching core.

## Before opening work

- Search existing issues and pull requests.
- For substantial API or algorithm changes, open an issue before implementation.
- Do not submit RideAssign application policy, production adapters, customer data, production
  coordinates, provider payloads, credentials, private infrastructure, or proprietary fixtures.
- Follow the [Code of Conduct](CODE_OF_CONDUCT.md) and report security issues through the private
  process in [SECURITY.md](SECURITY.md).

## Development

Requirements: Python 3.12 through 3.14.

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -e ".[dev]"
make check
make audit
```

Use synthetic, deterministic fixtures. Add the smallest test that proves each changed behavior.
Keep OR-Tools integration isolated from the public domain models and matrix-provider contract.
Update `README.md`, `docs/architecture.md`, and `docs/algorithm.md` when the public contract changes.

## Pull requests

Explain the user-visible or API outcome, the modeled risk, and the verification performed. Keep
pull requests focused. Every required check must pass before review.

Unless explicitly stated otherwise, any contribution intentionally submitted for inclusion is
provided under the Apache License 2.0, consistent with section 5 of that license.
