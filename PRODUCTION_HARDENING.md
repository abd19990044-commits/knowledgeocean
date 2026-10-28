# Knowledge Ocean production hardening

## Environment settings
- APP_PASSWORD: strong unique VIP access passcode. If unset, VIP is disabled.
- ELSEVIER_API_KEY: server-side secret; Scopus requires an authenticated VIP access code. Other users, including secondary-tier users, cannot select Scopus.
- KO_SESSION_SECRET: strong persistent server-side secret; must remain identical across restarts and workers.
- OTHER_PASSWORD: optional secondary non-VIP access code; no default secondary codes.
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

Check guests cannot use Scopus, the VIP passcode can, cookies authorize task and file access, two unrelated clients cannot access each other's documents, and both keyword and author search return relevant records.

## Personal Elsevier credentials
- Optional login-modal field saves the user key in browser localStorage. It can be removed there independently of signing out.
- VIP searches send the key in the POST body over HTTPS; the worker forwards it only to Elsevier in X-ELS-APIKey.
- Personal keys never change process environment, task records, SQLite, or reports. Authentication/rate-limit circuit breakers are isolated per credential.
- Invalid requests are rejected before quota consumption; repeat submissions resume the existing task. Queue rejection, timeouts, and failed exports refund reserved quota.
- DOI lookup network calls and title-search collection run outside the event loop.
- Docker runs as UID 1000, and the build context excludes local config, credentials, and downloaded files.
