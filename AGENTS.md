# Repository guidance

- Keep the matching core provider-neutral, deterministic, and independent from application databases, web frameworks, billing, authentication, and vendor SDKs.
- Reject invalid inputs and invalid routing-provider responses with explicit errors. Do not add silent fallbacks.
- Keep production code modular and business assertions at the smallest proving test layer.
- Use synthetic fixtures only. Never add customer data, production coordinates, credentials, private prompts, or provider responses copied from production.
- Update `README.md` and `docs/algorithm.md` when the public contract or algorithm changes.
- Use pnpm and run `pnpm check` before completing changes.
