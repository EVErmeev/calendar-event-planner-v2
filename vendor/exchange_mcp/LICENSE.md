LICENSE — vendored exchange-mcp (ATTRIBUTION NOTICE)

The `server/` directory contains an internal component of «Первый Бит» (1cbit)
("upstream"), distributed internally at `https://mcp.1bitai.ru/dist`.

The redistribution terms of this internal component MUST be confirmed by the
owner before shipping Calendar Event Planner. This placeholder is NOT a
granted license.

Required before v1.1.0 release:
  - confirm upstream license / redistribution rights;
  - replace this file with the upstream LICENSE (or mark the component
    internal-only and restricted accordingly);
  - update THIRD_PARTY_NOTICES.md.

Local change applied on top of upstream:
  - `server/server.py`: `send_meeting_invitations` fix
    (`SEND_AND_SAVE_COPY` -> `SEND_TO_ALL_AND_SAVE_COPY`).