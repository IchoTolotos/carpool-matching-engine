# Repository guidance

- Preserve the provider-neutral boundary: no database, web framework, authentication, billing,
  analytics, HTTP service, or routing-vendor SDKs in the engine.
- Keep RideAssign business-rule compilation, Valhalla operations, persistence, and production
  configuration out of this repository.
- Keep OR-Tools integration isolated from the typed domain model and matrix-provider contract.
- Reject invalid inputs with explicit errors. Do not add silent fallbacks.
- Use synthetic fixtures only. Never add customer data, production coordinates, credentials,
  private prompts, or provider responses copied from production.
- Put business assertions at the smallest proving test layer and keep tests deterministic.
- Update `README.md` and `docs/architecture.md` when the public contract changes.
- Use Python 3.12 and run `make check` before completing changes.
