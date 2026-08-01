from __future__ import annotations

import logging
from unittest import mock

from calendar_planner.participants.ews_directory_gateway import (
    EWSDirectoryGateway,
    _escape_xml,
    _mask_email,
    _mask_for_log,
)

SOAP_RESPONSE_1_PERSON = (
    '<?xml version="1.0" encoding="utf-8"?>'
    '<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/">'
    "<s:Body>"
    '<m:ResolveNamesResponse xmlns:m="http://schemas.microsoft.com/exchange/services/2006/messages"'
    ' xmlns:t="http://schemas.microsoft.com/exchange/services/2006/types">'
    "<m:ResolutionSet TotalItemsInView=\"1\" IncludesLastItemInRange=\"true\">"
    "<t:Resolution>"
    "<t:Mailbox>"
    "<t:Name>Иванов Иван Иванович</t:Name>"
    "<t:EmailAddress>ivanov@1cbit.ru</t:EmailAddress>"
    "<t:MailboxType>Mailbox</t:MailboxType>"
    "</t:Mailbox>"
    "<t:Contact>"
    "<t:CompanyName>1С:БИТ</t:CompanyName>"
    "<t:Department>Разработка</t:Department>"
    "<t:JobTitle>Ведущий разработчик</t:JobTitle>"
    "</t:Contact>"
    "</t:Resolution>"
    "</m:ResolutionSet>"
    "</m:ResolveNamesResponse>"
    "</s:Body>"
    "</s:Envelope>"
)

SOAP_RESPONSE_0_PEOPLE = (
    '<?xml version="1.0" encoding="utf-8"?>'
    '<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/">'
    "<s:Body>"
    '<m:ResolveNamesResponse xmlns:m="http://schemas.microsoft.com/exchange/services/2006/messages"'
    ' xmlns:t="http://schemas.microsoft.com/exchange/services/2006/types">'
    '<m:ResolutionSet TotalItemsInView="0" IncludesLastItemInRange="true">'
    "</m:ResolutionSet>"
    "</m:ResolveNamesResponse>"
    "</s:Body>"
    "</s:Envelope>"
)

SOAP_RESPONSE_2_PEOPLE = (
    '<?xml version="1.0" encoding="utf-8"?>'
    '<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/">'
    "<s:Body>"
    '<m:ResolveNamesResponse xmlns:m="http://schemas.microsoft.com/exchange/services/2006/messages"'
    ' xmlns:t="http://schemas.microsoft.com/exchange/services/2006/types">'
    '<m:ResolutionSet TotalItemsInView="2" IncludesLastItemInRange="true">'
    "<t:Resolution>"
    "<t:Mailbox>"
    "<t:Name>Иванов Иван</t:Name>"
    "<t:EmailAddress>ivanov@1cbit.ru</t:EmailAddress>"
    "<t:MailboxType>Mailbox</t:MailboxType>"
    "</t:Mailbox>"
    "<t:Contact>"
    "<t:CompanyName>1С:БИТ</t:CompanyName>"
    "<t:Department>Разработка</t:Department>"
    "<t:JobTitle>Разработчик</t:JobTitle>"
    "</t:Contact>"
    "</t:Resolution>"
    "<t:Resolution>"
    "<t:Mailbox>"
    "<t:Name>Иванов Петр</t:Name>"
    "<t:EmailAddress>ivanov_p@1cbit.ru</t:EmailAddress>"
    "<t:MailboxType>Mailbox</t:MailboxType>"
    "</t:Mailbox>"
    "<t:Contact>"
    "<t:CompanyName>1С:БИТ</t:CompanyName>"
    "<t:Department>Тестирование</t:Department>"
    "<t:JobTitle>Тестировщик</t:JobTitle>"
    "</t:Contact>"
    "</t:Resolution>"
    "</m:ResolutionSet>"
    "</m:ResolveNamesResponse>"
    "</s:Body>"
    "</s:Envelope>"
)

SOAP_RESPONSE_MALFORMED = (
    '<?xml version="1.0" encoding="utf-8"?>'
    '<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/">'
    "<s:Body>"
    '<m:ResolveNamesResponse xmlns:m="http://schemas.microsoft.com/exchange/services/2006/messages">'
    "<m:ResolutionSet>"
    "<t:Resolution>"
    "<t:Mailbox>"
    "<t:Name>Broken"
    "</t:Mailbox>"  # unclosed tag — makes XML invalid
    "</m:ResolutionSet>"
    "</m:ResolveNamesResponse>"
    "</s:Body>"
    "</s:Envelope>"
)


class _FakeResponse:
    def __init__(self, status_code, text):
        self.status_code = status_code
        self.text = text


class TestSOAPRequestFormat:
    def test_soap_envelope_contains_required_elements(self):
        from calendar_planner.participants.ews_directory_gateway import (
            SOAP_ENVELOPE_TEMPLATE,
        )

        envelope = SOAP_ENVELOPE_TEMPLATE.format(query="test")
        assert "ResolveNames" in envelope
        assert "ReturnFullContactData=\"true\"" in envelope
        assert "SearchScope=\"ActiveDirectory\"" in envelope
        assert "Exchange2010_SP2" in envelope
        assert "<m:UnresolvedEntry>test</m:UnresolvedEntry>" in envelope

    def test_soap_envelope_escapes_query(self):
        from calendar_planner.participants.ews_directory_gateway import (
            SOAP_ENVELOPE_TEMPLATE,
        )

        envelope = SOAP_ENVELOPE_TEMPLATE.format(query=_escape_xml("a<b>&c"))
        assert "&amp;" in envelope
        assert "&lt;" in envelope

    def test_http_headers_are_correct(self):
        from calendar_planner.participants.ews_directory_gateway import SOAP_HEADERS

        assert SOAP_HEADERS["Content-Type"] == "text/xml; charset=utf-8"
        assert SOAP_HEADERS["SOAPAction"].endswith("ResolveNames")


class TestResolveOnePerson:
    def test_resolve_1_person_returns_success(self):
        fake_resp = _FakeResponse(200, SOAP_RESPONSE_1_PERSON)
        with mock.patch("requests.post", return_value=fake_resp) as mock_post:
            gw = EWSDirectoryGateway(username="user", password="pass")
            result = gw.search("Иванов")

        assert result["status"] == "success"
        assert result["source"] == "exchange_ews_gal"
        assert len(result["people"]) == 1
        person = result["people"][0]
        assert person["full_name"] == "Иванов Иван Иванович"
        assert person["email"] == "ivanov@1cbit.ru"
        assert person["mailbox_type"] == "Mailbox"
        assert person["company"] == "1С:БИТ"
        assert person["department"] == "Разработка"
        assert person["job_title"] == "Ведущий разработчик"
        assert result["error"] is None
        assert result["correlation_id"] is not None

        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args.kwargs
        assert "auth" in call_kwargs
        assert call_kwargs["timeout"] == 15

    def test_resolve_1_person_sets_correct_status(self):
        fake_resp = _FakeResponse(200, SOAP_RESPONSE_1_PERSON)
        with mock.patch("requests.post", return_value=fake_resp):
            gw = EWSDirectoryGateway(username="user", password="pass")
            result = gw.search("Иванов")
        assert result["status"] == "success"


class TestResolveZeroPeople:
    def test_resolve_0_people_returns_not_found(self):
        fake_resp = _FakeResponse(200, SOAP_RESPONSE_0_PEOPLE)
        with mock.patch("requests.post", return_value=fake_resp):
            gw = EWSDirectoryGateway(username="user", password="pass")
            result = gw.search("Неизвестный")

        assert result["status"] == "not_found"
        assert len(result["people"]) == 0
        assert result["error"] is None


class TestResolveAmbiguous:
    def test_resolve_2_people_returns_ambiguous(self):
        fake_resp = _FakeResponse(200, SOAP_RESPONSE_2_PEOPLE)
        with mock.patch("requests.post", return_value=fake_resp):
            gw = EWSDirectoryGateway(username="user", password="pass")
            result = gw.search("Иванов")

        assert result["status"] == "ambiguous"
        assert len(result["people"]) == 2
        assert result["people"][0]["full_name"] == "Иванов Иван"
        assert result["people"][1]["full_name"] == "Иванов Петр"


class TestAuthFailed:
    def test_http_401_returns_auth_failed(self):
        fake_resp = _FakeResponse(401, "Unauthorized")
        with mock.patch("requests.post", return_value=fake_resp):
            gw = EWSDirectoryGateway(username="user", password="pass")
            result = gw.search("Иванов")

        assert result["status"] == "auth_failed"
        assert len(result["people"]) == 0
        assert "401" in result["error"]


class TestTimeout:
    def test_timeout_returns_timeout_status(self):
        import requests as requests_lib

        with mock.patch(
            "requests.post",
            side_effect=requests_lib.Timeout("Connection timed out"),
        ):
            gw = EWSDirectoryGateway(username="user", password="pass", timeout=5)
            result = gw.search("Иванов")

        assert result["status"] == "timeout"
        assert len(result["people"]) == 0
        assert "5s" in result["error"]


class TestXMLParseError:
    def test_malformed_xml_returns_failed(self):
        fake_resp = _FakeResponse(200, "not valid xml {{{")
        with mock.patch("requests.post", return_value=fake_resp):
            gw = EWSDirectoryGateway(username="user", password="pass")
            result = gw.search("Иванов")

        assert result["status"] == "failed"
        assert "XML parse error" in result["error"]

    def test_no_resolution_set_element_returns_failed(self):
        resp_text = (
            '<?xml version="1.0" encoding="utf-8"?>'
            '<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/">'
            "<s:Body>"
            '<m:SomethingElse xmlns:m="http://schemas.microsoft.com/exchange/services/2006/messages"/>'
            "</s:Body>"
            "</s:Envelope>"
        )
        fake_resp = _FakeResponse(200, resp_text)
        with mock.patch("requests.post", return_value=fake_resp):
            gw = EWSDirectoryGateway(username="user", password="pass")
            result = gw.search("Иванов")

        assert result["status"] == "failed"
        assert "ResolutionSet" in result["error"]


class TestGatewayNotConfigured:
    def test_no_username_returns_failed(self, caplog):
        gw = EWSDirectoryGateway(username=None, password=None)
        result = gw.search("Иванов")

        assert result["status"] == "failed"
        assert "not configured" in result["error"]

    def test_no_endpoint_returns_failed(self):
        gw = EWSDirectoryGateway(endpoint="", username="user", password="pass")
        result = gw.search("Иванов")

        assert result["status"] == "failed"

    def test_not_available_returns_false(self):
        gw = EWSDirectoryGateway(username=None)
        assert gw.is_available() is False

        gw = EWSDirectoryGateway(username="user")
        assert gw.is_available() is True

        gw = EWSDirectoryGateway(endpoint="")
        assert gw.is_available() is False


class TestCredentialsNotInLogs:
    def test_password_not_in_logs(self, caplog):
        caplog.set_level(logging.DEBUG)
        fake_resp = _FakeResponse(200, SOAP_RESPONSE_1_PERSON)
        with mock.patch("requests.post", return_value=fake_resp):
            gw = EWSDirectoryGateway(username="user", password="secret123")
            gw.search("Иванов")

        log_text = " ".join(caplog.messages)
        assert "secret123" not in log_text

    def test_username_masked_in_logs(self, caplog):
        caplog.set_level(logging.DEBUG)
        fake_resp = _FakeResponse(200, SOAP_RESPONSE_1_PERSON)
        with mock.patch("requests.post", return_value=fake_resp):
            gw = EWSDirectoryGateway(username="domain\\user", password="pass")
            gw.search("Иванов")

        log_text = " ".join(caplog.messages)
        assert "domain\\user" not in log_text
        assert "do***" in log_text

    def test_email_masked_in_logs(self, caplog):
        caplog.set_level(logging.DEBUG)
        fake_resp = _FakeResponse(200, SOAP_RESPONSE_1_PERSON)
        with mock.patch("requests.post", return_value=fake_resp):
            gw = EWSDirectoryGateway(username="user", password="pass")
            gw.search("Иванов")

        log_text = " ".join(caplog.messages)
        assert "ivanov@1cbit.ru" not in log_text
        assert "iv***@1cbit.ru" in log_text


class TestHelperFunctions:
    def test_escape_xml(self):
        assert _escape_xml("a<b>c&d") == "a&lt;b&gt;c&amp;d"
        assert _escape_xml('quote"test') == "quote&quot;test"
        assert _escape_xml("normal") == "normal"

    def test_mask_email_normal(self):
        result = _mask_email("ivanov@1cbit.ru")
        assert result == "iv***@1cbit.ru"

    def test_mask_email_short_local(self):
        result = _mask_email("a@domain.com")
        assert result == "a***@domain.com"

    def test_mask_email_empty(self):
        assert _mask_email("") == "***"
        assert _mask_email("no-at-sign") == "***"

    def test_mask_for_log(self):
        assert _mask_for_log("Иванов") == "Ива***"
        assert _mask_for_log("АБ") == "А***"
        assert _mask_for_log("") == ""


class TestGetCapability:
    def test_get_capability_returns_ews_gal(self):
        gw = EWSDirectoryGateway()
        assert gw.get_capability() == "exchange_ews_gal"


class TestConnectionError:
    def test_connection_error_returns_failed(self):
        import requests as requests_lib

        with mock.patch(
            "requests.post",
            side_effect=requests_lib.ConnectionError("Refused"),
        ):
            gw = EWSDirectoryGateway(username="user", password="pass")
            result = gw.search("Иванов")

        assert result["status"] == "failed"
        assert "Refused" in result["error"]


class TestLimit:
    def test_results_respect_limit(self):
        fake_resp = _FakeResponse(200, SOAP_RESPONSE_2_PEOPLE)
        with mock.patch("requests.post", return_value=fake_resp):
            gw = EWSDirectoryGateway(username="user", password="pass")
            result = gw.search("Иванов", limit=1)

        assert len(result["people"]) == 1


class TestNTLMAuthUsed:
    def test_ntlm_auth_passed_to_request(self):
        from requests_ntlm import HttpNtlmAuth

        fake_resp = _FakeResponse(200, SOAP_RESPONSE_1_PERSON)
        with mock.patch("requests.post", return_value=fake_resp) as mock_post:
            gw = EWSDirectoryGateway(username="DOMAIN\\user", password="pass")
            gw.search("Иванов")

        auth_arg = mock_post.call_args.kwargs.get("auth")
        assert isinstance(auth_arg, HttpNtlmAuth)


class TestCustomTimeout:
    def test_custom_timeout_passed(self):
        fake_resp = _FakeResponse(200, SOAP_RESPONSE_1_PERSON)
        with mock.patch("requests.post", return_value=fake_resp) as mock_post:
            gw = EWSDirectoryGateway(username="user", password="pass", timeout=30)
            gw.search("Иванов")

        assert mock_post.call_args.kwargs["timeout"] == 30