# Knowledge Ocean production hardening

## Environment settings
- APP_PASSWORD: strong unique VIP access passcode. If unset, VIP is disabled.
- ELSEVIER_API_KEY: server-side secret; only VIP may use this platform key. Guests and Access Code holders may use Scopus with their own personal keys.
- KO_SESSION_SECRET: strong persistent server-side secret; must remain identical across restarts and workers.
- OTHER_PASSWORD: optional Access Code with a 250-credit daily allowance; no default codes.
- UNPAYWALL_EMAIL: legitimate researcher contact address.
- LOCAL_INSTANCE=1: explicitly enable only on private, trusted single-user machines. Never enable for publicly accessible deployments.

## Deployment and limitations
- Run one worker/instance until background queues and SQLite are replaced with shared workers and persistence.
- Ensure HTTPS is used in production and that reverse-proxy scheme forwarding correctly marks signed cookies Secure.
- Do not disclose ELSEVIER_API_KEY to browsers or in returned API responses.
- Downloading full-text papers is a separate CLI module, not integrated into the API search pipeline. The frontend no longer claims to activate full-text retrieval.
- Full production acceptance still requires end-to-end tests against real provider APIs and a staging Hugging Face Space.

## Checks
Run: python -m compileall -q .
Run: python -m unittest discover -s tests -p "test_*.py"

Check guests and Access Code holders can use only their own Scopus keys, VIP can use the platform key, cookies authorize task and file access, two unrelated clients cannot access each other's documents, and both keyword and author search return relevant records.

## Personal Elsevier credentials
- Optional login-modal field saves the user key in browser localStorage. It can be removed there independently of signing out.
- Searches from every tier send a supplied personal key in the POST body over HTTPS; the worker forwards it only to Elsevier in X-ELS-APIKey.
- Personal keys never change process environment, task records, SQLite, or reports. Authentication/rate-limit circuit breakers are isolated per credential.
- Invalid requests are rejected before quota consumption; repeat submissions resume the existing task. Queue rejection, timeouts, and failed exports refund reserved quota.
- DOI lookup network calls and title-search collection run outside the event loop.
- Docker runs as UID 1000, and the build context excludes local config, credentials, and downloaded files.

## Conservative Scopus requests
- STANDARD metadata only, at most 25 records per call, no hidden transport retries, and at least two seconds between Scopus calls per running instance.
- Honor X-RateLimit-Remaining, X-RateLimit-Reset, Retry-After, and X-ELS-Status independently per key. Do not assume a universal free-account quota.
- Report access denials and exhausted quota without falling back to another credential. Personal keys never upgrade platform quota or priority.
## Search collection budgets
- Numeric requests allow 10 seconds per requested record after the result quota is applied. The all-available option allows at most 3 hours, including when its result count is capped by the guest or Access Code quota.
- Both modes stop after 5 minutes without a newly accepted, unique matching record. Duplicates, rejected records, and provider responses without matches do not reset this clock.
- The earliest deadline applies. Target completion, exhausted sources, and cancellation can stop collection earlier; partial results remain exportable and existing unused-quota refunds apply.
- Queue waiting and report generation are outside collection budgets. Individual provider request timeouts and Scopus rate-limit controls remain in force; collection has no fixed four-round or two-empty-round cutoff.
