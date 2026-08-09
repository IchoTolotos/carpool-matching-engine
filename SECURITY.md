# Security policy

## Supported versions

Until the first public release, security fixes are applied only to the latest commit on `main`.
After versioned releases begin, this table will list the supported release lines.

## Reporting a vulnerability

Do not open a public issue. Use GitHub private vulnerability reporting:

`https://github.com/IchoTolotos/carpool-matching-engine/security/advisories/new`

Include the affected version or commit, impact, reproduction conditions, and any suggested
mitigation. Do not include real customer data, production credentials, or sensitive provider
payloads. The maintainer will acknowledge the report, assess severity, coordinate a fix, and credit
the reporter unless anonymity is requested.

## Scope

The repository contains an in-process optimization library. Routing providers, HTTP services,
authentication, persistence, and deployment infrastructure are outside its security boundary.
Reports about RideAssign or another integrating application must use that application's private
security channel instead.
