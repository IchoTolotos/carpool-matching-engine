# Contributing

The repository is private and not accepting external contributions yet.

For internal changes:

1. keep the core provider-neutral and synthetic-data-only
2. add the smallest deterministic test that proves each business assertion
3. keep application policy compilation and routing-provider adapters outside the optimization core
4. update the API and architecture documentation when contracts change
5. run `make check` and `make audit`
