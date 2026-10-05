# Security Policy

Please report potential vulnerabilities privately to the repository owner rather than opening a public issue. Include a minimal reproduction, the affected commit, and the impact.

Quantum Claims Evidence Passport is an offline, standard-library-only CLI: it makes no network requests and starts no server by design. In scope:

- any change that introduces a network call, a remote asset, or a script in the generated report;
- HTML injection: ledger text that is rendered without escaping;
- a ledger that passes `validate` while citing an unknown source, using an unknown label, or labelling a fenced claim type (consciousness mechanism, current operation, direct measurement, proof) as anything other than `hypothesis` or `unsupported_inference`.

Factual corrections to the claim ledger (for example, a source page that has changed since the audit snapshot) are welcome as ordinary issues.
