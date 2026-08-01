from __future__ import annotations

import logging
import uuid
from xml.etree import ElementTree

import requests
from requests_ntlm import HttpNtlmAuth

logger = logging.getLogger(__name__)

SOAP_HEADERS = {
    "Content-Type": "text/xml; charset=utf-8",
    "SOAPAction": "http://schemas.microsoft.com/exchange/services/2006/messages/ResolveNames",
}

SOAP_ENVELOPE_TEMPLATE = (
    '<?xml version="1.0" encoding="utf-8"?>'
    '<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/"'
    ' xmlns:t="http://schemas.microsoft.com/exchange/services/2006/types"'
    ' xmlns:m="http://schemas.microsoft.com/exchange/services/2006/messages">'
    "<soap:Header>"
    '<t:RequestServerVersion Version="Exchange2010_SP2"/>'
    "</soap:Header>"
    "<soap:Body>"
    '<m:ResolveNames ReturnFullContactData="true" SearchScope="ActiveDirectory" ContactDataShape="Default">'
    "<m:UnresolvedEntry>{query}</m:UnresolvedEntry>"
    "</m:ResolveNames>"
    "</soap:Body>"
    "</soap:Envelope>"
)


class EWSDirectoryGateway:
    """Searches corporate directory via EWS ResolveNames."""

    def __init__(
        self,
        endpoint: str = "https://mail.1cbit.ru/EWS/Exchange.asmx",
        username: str | None = None,
        password: str | None = None,
        timeout: int = 15,
    ):
        self.endpoint = endpoint
        self._username = username
        self._password = password
        self._timeout = timeout

    def is_available(self) -> bool:
        return bool(self.endpoint and self._username)

    def get_capability(self) -> str:
        return "exchange_ews_gal"

    def search(self, query: str, limit: int = 20) -> dict:
        correlation_id = str(uuid.uuid4())
        base_result = {
            "query": query,
            "source": "exchange_ews_gal",
            "correlation_id": correlation_id,
        }

        if not self.is_available():
            logger.warning(
                "EWSDirectoryGateway: endpoint or username not configured",
                extra={"correlation_id": correlation_id},
            )
            return {**base_result, "status": "failed", "people": [], "error": "Gateway not configured"}

        masked_user = self._username[:2] + "***" if self._username else "***"
        logger.info(
            "EWSDirectoryGateway: resolving name=%s via EWS, user=%s",
            _mask_for_log(query),
            masked_user,
            extra={"correlation_id": correlation_id},
        )

        soap_body = SOAP_ENVELOPE_TEMPLATE.format(query=_escape_xml(query))
        auth = HttpNtlmAuth(self._username, self._password or "")

        try:
            response = requests.post(
                self.endpoint,
                data=soap_body.encode("utf-8"),
                headers=SOAP_HEADERS,
                auth=auth,
                timeout=self._timeout,
            )
        except requests.Timeout as exc:
            logger.warning(
                "EWSDirectoryGateway: request timed out after %ds",
                self._timeout,
                exc_info=True,
                extra={"correlation_id": correlation_id},
            )
            return {
                **base_result,
                "status": "timeout",
                "people": [],
                "error": f"Request timed out after {self._timeout}s",
            }
        except requests.ConnectionError as exc:
            logger.warning(
                "EWSDirectoryGateway: connection error: %s",
                exc,
                exc_info=True,
                extra={"correlation_id": correlation_id},
            )
            return {
                **base_result,
                "status": "failed",
                "people": [],
                "error": str(exc),
            }
        except requests.RequestException as exc:
            logger.warning(
                "EWSDirectoryGateway: request failed: %s",
                exc,
                exc_info=True,
                extra={"correlation_id": correlation_id},
            )
            return {
                **base_result,
                "status": "failed",
                "people": [],
                "error": str(exc),
            }

        if response.status_code == 401:
            logger.warning(
                "EWSDirectoryGateway: authentication failed (HTTP 401)",
                extra={"correlation_id": correlation_id},
            )
            return {
                **base_result,
                "status": "auth_failed",
                "people": [],
                "error": "Authentication failed (HTTP 401)",
            }

        if response.status_code != 200:
            logger.warning(
                "EWSDirectoryGateway: unexpected HTTP status %d",
                response.status_code,
                extra={"correlation_id": correlation_id},
            )
            return {
                **base_result,
                "status": "failed",
                "people": [],
                "error": f"HTTP {response.status_code}",
            }

        try:
            root = ElementTree.fromstring(response.text)
        except ElementTree.ParseError as exc:
            logger.warning(
                "EWSDirectoryGateway: XML parse error: %s",
                exc,
                extra={"correlation_id": correlation_id},
            )
            return {
                **base_result,
                "status": "failed",
                "people": [],
                "error": f"XML parse error: {exc}",
            }

        ns = {
            "t": "http://schemas.microsoft.com/exchange/services/2006/types",
            "m": "http://schemas.microsoft.com/exchange/services/2006/messages",
        }

        resolution_set = root.find(".//m:ResolutionSet", ns)
        if resolution_set is None:
            logger.warning(
                "EWSDirectoryGateway: no m:ResolutionSet in SOAP response",
                extra={"correlation_id": correlation_id},
            )
            return {
                **base_result,
                "status": "failed",
                "people": [],
                "error": "No ResolutionSet in response",
            }

        resolution_entries = resolution_set.findall("t:Resolution", ns)
        people = self._parse_resolutions(resolution_entries, ns, correlation_id)

        people = people[:limit]

        if len(people) == 0:
            status = "not_found"
        elif len(people) == 1:
            status = "success"
        else:
            status = "ambiguous"

        logger.info(
            "EWSDirectoryGateway: resolved %d match(es), status=%s",
            len(people),
            status,
            extra={"correlation_id": correlation_id},
        )

        return {**base_result, "status": status, "people": people, "error": None}

    def _parse_resolutions(self, resolution_entries, ns, correlation_id):
        people = []
        for entry in resolution_entries:
            try:
                person = {
                    "full_name": _deep_get_text(entry, "t:Mailbox/t:Name", ns),
                    "email": _deep_get_text(entry, "t:Mailbox/t:EmailAddress", ns),
                    "mailbox_type": _deep_get_text(entry, "t:Mailbox/t:MailboxType", ns),
                    "company": _deep_get_text(entry, "t:Contact/t:CompanyName", ns),
                    "department": _deep_get_text(entry, "t:Contact/t:Department", ns),
                    "job_title": _deep_get_text(entry, "t:Contact/t:JobTitle", ns),
                }
                people.append(person)

                masked_email = _mask_email(person["email"])
                logger.debug(
                    "EWSDirectoryGateway: resolved person name=%s email=%s",
                    _mask_for_log(person["full_name"]),
                    masked_email,
                    extra={"correlation_id": correlation_id},
                )
            except Exception as exc:
                logger.warning(
                    "EWSDirectoryGateway: failed to parse resolution entry: %s",
                    exc,
                    extra={"correlation_id": correlation_id},
                )
        return people


def _deep_get_text(element, xpath: str, ns) -> str:
    child = element.find(xpath, ns)
    return child.text if child is not None and child.text is not None else ""


def _escape_xml(value: str) -> str:
    return value.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def _mask_email(email: str) -> str:
    if not email or "@" not in email:
        return "***"
    parts = email.split("@", 1)
    local = parts[0]
    if len(local) <= 2:
        masked_local = local[0] + "***"
    else:
        masked_local = local[:2] + "***"
    return f"{masked_local}@{parts[1]}"


def _mask_for_log(value: str) -> str:
    if not value:
        return ""
    if len(value) <= 3:
        return value[:1] + "***"
    return value[:3] + "***"