# Contributing

Open an issue with a reproducible case before expanding the protocol or adding a provider.

Run `python3 -m unittest discover -s tests -v`. Tests must not require accounts or make model calls. Use temporary directories and fake CLI subprocesses for transport behavior.

Preserve these contracts:

- Initial answers cannot see each other.
- Failed, empty or malformed responses cannot advance a session.
- Input or model changes cannot silently reuse an existing experiment.
- A round limit must leave unresolved findings visible.
- Claimed source support is not independently verified truth.
- Live CLI metadata must distinguish requested models from observed identities.
- No implicit model fallback, permission bypass, API credit purchase or public publishing.

Do not attach private session diagnostics to public issues. A minimal source packet and sanitized error are usually enough. If adapting third-party code, preserve its required license notices.
