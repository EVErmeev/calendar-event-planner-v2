# Exchange MCP — vendored component (Calendar Event Planner)

This directory vendors a pinned version of the internal `exchange-mcp` MCP
server used to read/write the Exchange calendar.

## Upstream

- Source: internal distribution server `https://mcp.1bitai.ru/dist` (area `exchange`).
- Wrapper: `%LOCALAPPDATA%\exchange-mcp\exchange-mcp.ps1`.
- Server module: `server/server.py` + `server/pyproject.toml`.

## Local changes (v1.1.0)

The single local patch is the **send_meeting_invitations fix**:

| Upstream | Bundled |
|---|---|
| `SEND_AND_SAVE_COPY` | `SEND_TO_ALL_AND_SAVE_COPY` |

Rationale: `SEND_AND_SAVE_COPY` ('SendAndSaveCopy') is not a valid value for
`CalendarItem.save(send_meeting_invitations=...)`. Allowed values are
`['SendOnlyToAll', 'SendToAllAndSaveCopy', 'SendToNone']`. As a result the
upstream server rejected any event that had attendees. This bundle ships the
fix pre-applied so the end user never edits `server.py`.

## Version

- Bundle version: `1.0.0-cep.1` (see `calendar_planner/app/component_manifest.py`).
- Upstream commit pinned: see `component-manifest.json` /
  `calendar_planner.app.component_manifest.EXCHANGE_MCP_UPSTREAM_COMMIT`.

## License / attribution

The upstream is an internal component of «Первый Бит» (1cbit). Redistribution
inside Calendar Event Planner is governed by internal licensing. This vendored
copy keeps the upstream `pyproject.toml` and documents local changes here.
See `THIRD_PARTY_NOTICES.md` at the repository root for the full inventory.