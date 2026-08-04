# Third Party Notices

Calendar Event Planner bundles and depends on third-party components. This
document lists their licenses and attribution as required by the distribution
policy (see section 17 of the installer TZ).

## Python runtime dependencies

Installed from `requirements.txt` at build time. Key ones:

| Package | Purpose | License |
|---|---|---|
| openpyxl | XLSX parsing | MIT |
| python-docx | DOCX parsing | MIT |
| PyPDF2 | PDF text extraction | BSD-3-Clause |
| python-pptx | PPTX parsing | MIT |
| beautifulsoup4 | HTML parsing | MIT |
| python-dateutil | date parsing | Apache-2.0 / BSD |
| fuzzywuzzy | fuzzy matching | GPL-2.0 (optional) |
| python-Levenshtein | string distance | GPL-2.0 |
| tzdata | timezone data | Apache-2.0 |
| requests | HTTP | Apache-2.0 |
| requests-ntlm | NTLM auth | ISC |
| keyring | credential storage | MIT / BSD |
| pytest, ruff, mypy, coverage | dev/test | MIT |

NOTE: `fuzzywuzzy` and `python-Levenshtein` are GPL-2.0 licensed. Confirm
redistribution compatibility for the closed distribution. If incompatible,
replace the matching engine with a permissive alternative before shipping.

## Exchange MCP (vendored component)

- Upstream: internal «Первый Бит» (1cbit) component, distributed at
  `https://mcp.1bitai.ru/dist`.
- Local change: `send_meeting_invitations` fix
  (`SEND_AND_SAVE_COPY` -> `SEND_TO_ALL_AND_SAVE_COPY`).
- Redistribution terms must be confirmed by the owner before shipping.
- See `vendor/exchange_mcp/README.md` and `vendor/exchange_mcp/LICENSE.md`.

## Inno Setup

- Used only at build time to produce the Windows installer. Not redistributed
  with the product. License: Inno Setup free-of-charge license
  (https://jrsoftware.org/islgpl.php).

## License inventory note

Full machine-generated inventory should be produced by a license checker
(e.g. `pip-licenses`) and attached to the release. This file is the human
reviewed subset for the v1.1.0 installer.