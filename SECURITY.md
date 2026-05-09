# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| 1.x     | ✅ Yes    |

## Reporting a Vulnerability

**Please do not open a public GitHub issue for security vulnerabilities.**

Report vulnerabilities privately via one of the following channels:

- **GitHub Security Advisories** — use the "Report a vulnerability" button on the repository's Security tab
- **Email** — send details to the repository maintainer (see profile for contact)

### What to include

- A clear description of the vulnerability
- Steps to reproduce (proof of concept if possible)
- Affected version(s)
- Potential impact

### Response timeline

- **Acknowledgement**: within 48 hours
- **Status update**: within 7 days
- **Fix / advisory**: within 30 days for critical issues

We follow [responsible disclosure](https://en.wikipedia.org/wiki/Responsible_disclosure) — please give us reasonable time to address the issue before any public disclosure.

## Security Considerations

- File operations (move, rename, delete) require explicit client confirmation.
- The delete endpoint requires `confirm: true` in the request body.
- File names are sanitised before rename operations.
- System directories (`Windows`, `System32`, `/proc`, `/sys`, etc.) are excluded from scanning.
- The application is designed for **local/trusted network** use. Do not expose it to the public internet without adding authentication and HTTPS.
