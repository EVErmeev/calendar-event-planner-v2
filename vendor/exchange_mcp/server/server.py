#!/usr/bin/env python3
"""MCP server for MS Exchange (EWS) — email access and calendar."""

import base64
import datetime
import os
import sys
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import AsyncIterator

from dotenv import load_dotenv
from exchangelib import (
    Account,
    CalendarItem,
    Configuration,
    Credentials,
    DELEGATE,
    EWSDateTime,
    FileAttachment,
    HTMLBody,
    Mailbox,
    Message,
    NTLM,
    FaultTolerance,
    Q,
)
from exchangelib.items import SEND_TO_ALL_AND_SAVE_COPY, SEND_TO_NONE
from mcp.server.fastmcp import FastMCP, Context

def env_file() -> Path:
    """Path to this server's own .env (standalone — no project-root fallback)."""
    return Path(__file__).resolve().parent / ".env"


_REQUIRED_ENV = ("EXCHANGE_USER", "EXCHANGE_PASSWORD", "EXCHANGE_SERVER", "EXCHANGE_EMAIL")


def require_exchange_env(environ) -> dict:
    """Return the 4 required vars or exit(1) with an actionable message."""
    missing = [k for k in _REQUIRED_ENV if not environ.get(k)]
    if missing:
        raise SystemExit(
            "Exchange MCP: missing required env var(s): "
            + ", ".join(missing)
            + ". Copy mcp/exchange-server/.env.example to .env "
            + "(same directory) and fill in your values."
        )
    return {k: environ[k] for k in _REQUIRED_ENV}


def safe_attachment_path(save_dir: str, name: str) -> Path:
    """Resolve a safe save path for an attachment.

    The attachment name is attacker-controlled (set by the email sender),
    so strip any directory component and confirm the result stays inside
    the target directory.
    """
    base = os.path.basename((name or "").replace("\\", "/")).strip()
    if not base or base in (".", ".."):
        raise ValueError(f"Unsafe attachment name: {name!r}")
    target_dir = (Path(save_dir) if save_dir else Path.home() / "Downloads").resolve()
    target = (target_dir / base).resolve()
    if target.parent != target_dir:
        raise ValueError(f"Refusing to write outside {target_dir}: {name!r}")
    return target


load_dotenv(env_file())


def _log(msg: str) -> None:
    """Log to stderr — stdout is reserved for MCP stdio transport."""
    print(msg, file=sys.stderr, flush=True)


@dataclass
class ExchangeContext:
    """Lifespan context holding the Exchange connection."""

    account: Account


@asynccontextmanager
async def lifespan(server: FastMCP) -> AsyncIterator[ExchangeContext]:
    """Connect to Exchange on startup, cleanup on shutdown."""
    _log("Connecting to Exchange...")
    env = require_exchange_env(os.environ)
    credentials = Credentials(
        username=env["EXCHANGE_USER"],
        password=env["EXCHANGE_PASSWORD"],
    )
    config = Configuration(
        server=env["EXCHANGE_SERVER"],
        credentials=credentials,
        auth_type=NTLM,
        retry_policy=FaultTolerance(max_wait=600),
    )
    account = Account(
        primary_smtp_address=env["EXCHANGE_EMAIL"],
        config=config,
        autodiscover=False,
        access_type=DELEGATE,
    )
    _log(f"Connected as {account.primary_smtp_address}")
    try:
        yield ExchangeContext(account=account)
    finally:
        _log("Exchange MCP server stopped")


mcp = FastMCP("Exchange", lifespan=lifespan)


def _get_account(ctx: Context) -> Account:
    """Extract Exchange account from MCP lifespan context."""
    return ctx.request_context.lifespan_context.account


def _format_header(index: int, item) -> str:
    """Format a single email as a one-line summary."""
    sender = item.sender.email_address if item.sender else "unknown"
    date = (
        item.datetime_received.strftime("%Y-%m-%d %H:%M")
        if item.datetime_received
        else ""
    )
    subject = item.subject or "(без темы)"
    return f"{index}. [{date}] {sender} — {subject}"


def _event_categories(item) -> str:
    """Категории события через запятую (пусто, если их нет)."""
    return ", ".join(item.categories or [])


def _event_importance(item) -> str:
    """Важность события; у EWS по умолчанию — Normal."""
    return item.importance or "Normal"


def _format_event(index: int, item) -> str:
    """Format a single calendar event as a one-line summary."""
    if item.is_all_day:
        time_range = "весь день"
    else:
        start = item.start.strftime("%H:%M") if item.start else "?"
        end = item.end.strftime("%H:%M") if item.end else "?"
        time_range = f"{start}–{end}"
    subject = item.subject or "(без темы)"
    organizer = item.organizer.email_address if item.organizer else ""
    location = f" ({item.location})" if item.location else ""
    # В одну строку списка выносим только то, что отличает встречу от прочих:
    # непустые категории и важность, отличную от дефолтной Normal.
    categories = _event_categories(item)
    categories = f" [{categories}]" if categories else ""
    importance = _event_importance(item)
    importance = f" !{importance}" if importance != "Normal" else ""
    return f"{index}. [{time_range}] {subject} — {organizer}{location}{categories}{importance}"


# У событий «весь день» exchangelib кладёт в start/end EWSDate (подкласс date), а у
# обычных — EWSDateTime (подкласс datetime). Смешивать их нельзя: сравнение падает
# TypeError, а .date() у EWSDate просто нет. Обе функции ниже приводят к общему типу.
# Порядок проверки важен: datetime — подкласс date, поэтому datetime проверяем первым.


def _event_day(item):
    """Дата события как datetime.date (None, если начала нет)."""
    start = item.start
    if start is None:
        return None
    return start.date() if isinstance(start, datetime.datetime) else start


def _event_start_dt(item, tz):
    """Начало события как aware-datetime; «весь день» — полночь своего дня."""
    start = item.start
    if start is None:
        return None
    if isinstance(start, datetime.datetime):
        return start
    return datetime.datetime(start.year, start.month, start.day, tzinfo=tz)


def _sort_events(items, tz):
    """Хронологический порядок; события «весь день» идут первыми в своём дне,
    события без начала — в конец списка."""
    last = datetime.datetime.max.replace(tzinfo=tz)
    return sorted(items, key=lambda e: _event_start_dt(e, tz) or last)


# ---------------------------------------------------------------------------
# search_emails helpers
# ---------------------------------------------------------------------------

# Стабильный адрес письма для будущих move/read (Волна 2): EWS id+changekey.
def make_handle(item) -> str:
    raw = f"{item.id}|{item.changekey}".encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii")


def decode_handle(handle: str) -> tuple[str, str]:
    id_, changekey = base64.urlsafe_b64decode(handle.encode("ascii")).decode("utf-8").split("|", 1)
    return id_, changekey


def _snippet(item, n: int = 200) -> str:
    text = (getattr(item, "text_body", None) or "")
    return " ".join(text.split())[:n]


def _split_addresses(raw: str) -> list:
    """Адреса «через запятую» -> список. Пустые куски отбрасываем."""
    if not raw:
        return []
    return [addr.strip() for addr in raw.split(",") if addr.strip()]


def _mailboxes(raw: str) -> list:
    """Адреса «через запятую» -> [Mailbox] для полей письма."""
    return [Mailbox(email_address=addr) for addr in _split_addresses(raw)]


_NAMED_FOLDERS = {
    "inbox": "Входящие",
    "sent": "Отправленные",
    "drafts": "Черновики",
    "deleted": "Корзина",
    "junk": "Спам",
}
_MAX_FOLDERS = 50


def _resolve_folders(account, folders: list[str]) -> list[tuple]:
    """[(folder, display_name)] по списку: named / 'all' (все mail-папки) / имя папки.

    'all' и поиск по имени идут через account.root.walk() и берут только mail-папки
    (folder_class == 'IPF.Note'); число папок ограничено _MAX_FOLDERS.
    """
    std = {
        "inbox": account.inbox,
        "sent": account.sent,
        "drafts": account.drafts,
        "deleted": account.trash,
        "junk": account.junk,
    }
    out: list[tuple] = []
    seen: set = set()

    def add(folder, name):
        fid = getattr(folder, "id", None)
        if fid in seen:
            return
        seen.add(fid)
        out.append((folder, name))

    def mail_folders():
        for f in account.root.walk():
            if getattr(f, "folder_class", None) == "IPF.Note" and hasattr(f, "filter"):
                yield f

    for spec in folders:
        key = (spec or "").lower().strip()
        if not key:
            continue
        if key == "all":
            try:
                for f in mail_folders():
                    add(f, getattr(f, "name", "?"))
                    if len(out) >= _MAX_FOLDERS:
                        break
            except Exception:
                add(account.inbox, _NAMED_FOLDERS["inbox"])
            continue
        if key in std:
            add(std[key], _NAMED_FOLDERS[key])
            continue
        # произвольное имя папки — ищем в дереве по имени
        try:
            for f in mail_folders():
                if (getattr(f, "name", "") or "").lower() == key:
                    add(f, f.name)
                    break
        except Exception:
            pass

    return out[:_MAX_FOLDERS]


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------


@mcp.tool()
async def find_emails(
    query: str = "",
    sender: str = "",
    days: int = 30,
    unread_only: bool = False,
    count: int = 20,
    ctx: Context = None,
) -> str:
    """Поиск писем во входящих. Без параметров — последние 20 писем.
    Возвращает: дата, отправитель, тема. Макс. 50 результатов.

    Примеры: find_emails(query='отчёт'), find_emails(unread_only=True),
    find_emails(sender='ivan@', days=7).

    Args:
        query: Подстрока в теме (без учёта регистра)
        sender: Email или часть email отправителя
        days: За сколько дней искать (по умолчанию 30)
        unread_only: Только непрочитанные
        count: Максимум результатов (макс. 50)
    """
    account = _get_account(ctx)
    count = min(count, 50)

    qs = account.inbox.all()
    if unread_only:
        qs = qs.filter(is_read=False)
    if query:
        qs = qs.filter(subject__icontains=query)
    if days < 365:
        start = datetime.datetime.now(tz=account.default_timezone) - datetime.timedelta(days=days)
        qs = qs.filter(datetime_received__gte=start)

    items = qs.order_by("-datetime_received").only(
        "subject", "sender", "datetime_received"
    )

    # Sender filtering in Python — EWS has limited substring matching on Mailbox
    results = []
    sender_lower = sender.lower() if sender else ""
    for idx, item in enumerate(items):
        if idx >= 500:
            break
        if sender_lower:
            item_sender = (item.sender.email_address or "") if item.sender else ""
            if sender_lower not in item_sender.lower():
                continue
        results.append(item)
        if len(results) >= count:
            break

    header = ""
    if unread_only:
        header = f"Непрочитанных всего: {account.inbox.unread_count}\n"

    lines = [_format_header(i, item) for i, item in enumerate(results, 1)]
    body = "\n".join(lines) if lines else "Ничего не найдено."

    if len(results) >= count:
        body += f"\n\n(Показаны первые {count}. Уточни запрос для сужения.)"

    return header + body


@mcp.tool()
async def search_emails(
    query: str,
    folders: list[str] = ["inbox"],
    search_in: list[str] = ["subject", "body"],
    sender: str = "",
    unread_only: bool = False,
    days: int = 0,
    max_results: int = 25,
    offset: int = 0,
    ctx: Context = None,
) -> str:
    """Полнотекстовый поиск писем по ТЕМЕ и ТЕЛУ (подстрока, без учёта регистра).

    В отличие от find_emails (только тема, только Входящие) — ищет ВНУТРИ сообщений
    и по нескольким/всем папкам. Каждый результат содержит стабильный `handle`
    (для будущих move/read). Только чтение.

    Примеры: search_emails(query='договор'), search_emails(query='счёт', folders=['all']),
    search_emails(query='отпуск', folders=['inbox','sent'], unread_only=True).

    Args:
        query: Подстрока для поиска в теме/теле (обязательно).
        folders: Где искать: 'inbox'/'sent'/'drafts'/'deleted'/'junk' / имя папки / ['all'] = все папки.
        search_in: Где именно: ['subject','body'] (по умолчанию оба).
        sender: Доп. фильтр — подстрока email отправителя.
        unread_only: Только непрочитанные.
        days: За сколько дней (0 = без ограничения).
        max_results: Сколько вернуть (макс. 100).
        offset: Пагинация (работает только для ОДНОЙ папки; для нескольких/['all'] игнорируется).
    """
    account = _get_account(ctx)
    if not query or not query.strip():
        return "Укажи строку поиска (query)."
    max_results = min(max(1, max_results), 100)
    offset = max(0, offset)

    # Текстовое ограничение: subject__icontains | body__contains (оба регистронезависимы — проверено).
    parts = []
    if "subject" in search_in:
        parts.append(Q(subject__icontains=query))
    if "body" in search_in:
        parts.append(Q(body__contains=query))
    if not parts:
        return "search_in должен содержать 'subject' и/или 'body'."
    filt = parts[0]
    for p in parts[1:]:
        filt |= p
    if unread_only:
        filt &= Q(is_read=False)
    if days and days > 0:
        start = datetime.datetime.now(tz=account.default_timezone) - datetime.timedelta(days=days)
        filt &= Q(datetime_received__gte=start)

    targets = _resolve_folders(account, folders)
    if not targets:
        return "Папки не найдены: " + ", ".join(folders)
    multi = len(targets) > 1
    per_cap = max_results if multi else (offset + max_results)
    sender_lower = sender.lower().strip() if sender else ""
    only_fields = ("subject", "sender", "datetime_received", "is_read", "has_attachments", "text_body")

    collected: list[tuple] = []
    errors: list[tuple] = []
    truncated = False
    t0 = time.monotonic()
    BUDGET_S = 30.0

    for folder, fname in targets:
        if time.monotonic() - t0 > BUDGET_S:
            truncated = True
            break
        try:
            qs = folder.filter(filt).order_by("-datetime_received").only(*only_fields)
            taken = 0
            scan_cap = per_cap + (300 if sender_lower else 0)
            for item in qs[:scan_cap]:
                if sender_lower:
                    s = (item.sender.email_address or "") if item.sender else ""
                    if sender_lower not in s.lower():
                        continue
                collected.append((item, fname))
                taken += 1
                if taken >= per_cap:
                    break
        except Exception as e:
            errors.append((fname, type(e).__name__))
            continue

    collected.sort(
        key=lambda t: t[0].datetime_received or datetime.datetime.min.replace(tzinfo=datetime.timezone.utc),
        reverse=True,
    )
    found = len(collected)
    page = collected[:max_results] if multi else collected[offset:offset + max_results]

    blocks = []
    for item, fname in page:
        sender_email = item.sender.email_address if item.sender else "unknown"
        date = item.datetime_received.strftime("%Y-%m-%d %H:%M") if item.datetime_received else ""
        flags = []
        if not item.is_read:
            flags.append("•непрочит")
        if item.has_attachments:
            flags.append("📎")
        flag_str = (" " + " ".join(flags)) if flags else ""
        blocks.append(
            f"[{date}] {sender_email} — {item.subject or '(без темы)'}{flag_str}\n"
            f"    папка: {fname} | handle: {make_handle(item)}\n"
            f"    {_snippet(item)}"
        )

    summary = [f"Найдено (в просмотренном): {found}, показано {len(page)}; папок: {len(targets)}."]
    if multi:
        summary.append("Несколько папок → самые свежие, offset не применяется.")
    elif offset:
        summary.append(f"offset={offset}.")
    if truncated:
        summary.append("⚠ просмотрены не все папки (таймаут 30с).")
    if errors:
        summary.append("ошибки папок: " + ", ".join(f"{n}({e})" for n, e in errors[:5]))

    body = "\n\n".join(blocks) if blocks else "Ничего не найдено."
    return " ".join(summary) + "\n\n" + body


@mcp.tool()
async def read_email(subject: str, index: int = 1, ctx: Context = None) -> str:
    """Прочитать письмо по теме. Возвращает полный текст.

    Args:
        subject: Подстрока в теме письма (без учёта регистра)
        index: Какое совпадение вернуть, 1 = самое свежее
    """
    account = _get_account(ctx)
    index = max(1, min(index, 10))
    items = (
        account.inbox.filter(subject__icontains=subject)
        .order_by("-datetime_received")
        .only("subject", "sender", "datetime_received", "body", "to_recipients")
    )

    item = None
    for i, candidate in enumerate(items, 1):
        if i == index:
            item = candidate
            break
        if i > 10:
            break

    if not item:
        return f"Письмо не найдено: '{subject}' (индекс {index})"

    sender = item.sender.email_address if item.sender else "unknown"
    date = (
        item.datetime_received.strftime("%Y-%m-%d %H:%M")
        if item.datetime_received
        else ""
    )
    to = ", ".join(r.email_address for r in (item.to_recipients or []))
    body = item.body or "(пустое тело)"

    return (
        f"Тема: {item.subject}\n"
        f"От: {sender}\n"
        f"Кому: {to}\n"
        f"Дата: {date}\n"
        f"---\n"
        f"{body}"
    )


@mcp.tool()
async def mark_as_read(
    subject: str = "",
    all_unread: bool = False,
    older_than_days: int = 0,
    ctx: Context = None,
) -> str:
    """Отметить письма как прочитанные.

    Args:
        subject: Подстрока в теме (без учёта регистра). Если пусто + all_unread=True — все непрочитанные.
        all_unread: Отметить все непрочитанные (используется если subject пуст)
        older_than_days: Отметить только письма старше N дней (0 = все)
    """
    account = _get_account(ctx)

    qs = account.inbox.filter(is_read=False)

    if subject:
        qs = qs.filter(subject__icontains=subject)
    elif not all_unread:
        return "Укажи subject или all_unread=True."

    if older_than_days > 0:
        cutoff = datetime.datetime.now(tz=account.default_timezone) - datetime.timedelta(
            days=older_than_days
        )
        qs = qs.filter(datetime_received__lte=cutoff)

    items = list(qs.only("subject", "is_read", "datetime_received")[:200])

    if not items:
        return "Нет подходящих непрочитанных писем."

    count = 0
    try:
        for item in items:
            item.is_read = True
            item.save(update_fields=["is_read"])
            count += 1
    except Exception as e:
        return (
            f"Ошибка при отметке писем как прочитанных (обработано {count}): {e}\n"
            f"Возможные причины: проблемы с сетью или сервер Exchange недоступен.\n"
            f"Попробуй повторить операцию."
        )

    return f"Отмечено как прочитанные: {count} писем."


@mcp.tool()
async def list_folders(ctx: Context = None) -> str:
    """Список почтовых папок с количеством сообщений."""
    account = _get_account(ctx)
    lines = []
    for folder in account.root.walk():
        if folder.total_count and folder.total_count > 0:
            unread = (
                f" ({folder.unread_count} непрочит.)" if folder.unread_count else ""
            )
            lines.append(f"- {folder.name}: {folder.total_count}{unread}")
    return "\n".join(lines) if lines else "Папки не найдены."


@mcp.tool()
async def send_email(
    to: str,
    subject: str,
    body: str,
    cc: str = "",
    ctx: Context = None,
) -> str:
    """Отправить письмо.

    Args:
        to: Адреса получателей через запятую
        subject: Тема письма
        body: Текст письма (HTML)
        cc: Адреса в копии через запятую (необязательно)
    """
    account = _get_account(ctx)

    to_list = _mailboxes(to)
    cc_list = _mailboxes(cc) or None

    try:
        msg = Message(
            account=account,
            folder=account.sent,
            subject=subject,
            body=HTMLBody(body),
            to_recipients=to_list,
            cc_recipients=cc_list,
        )
        msg.send_and_save()
    except Exception as e:
        return (
            f"Ошибка отправки письма: {e}\n"
            f"Возможные причины: неверный адрес получателя, проблемы с сетью или сервером Exchange.\n"
            f"Проверь адреса и попробуй снова."
        )

    to_str = ", ".join(m.email_address for m in to_list)
    cc_str = ", ".join(m.email_address for m in (cc_list or []))
    return (
        f"Письмо отправлено:\n"
        f"Кому: {to_str}\n"
        f"Копия: {cc_str or '—'}\n"
        f"Тема: {subject}"
    )


@mcp.tool()
async def save_draft(
    subject: str,
    body: str,
    to: str = "",
    cc: str = "",
    ctx: Context = None,
) -> str:
    """Сохранить письмо в «Черновики» — НЕ отправляя его.

    Письмо ложится в папку черновиков, откуда пользователь дописывает и
    отправляет его сам из Outlook. Адресаты можно не указывать.

    Args:
        subject: Тема письма
        body: Текст письма (HTML)
        to: Адреса получателей через запятую (необязательно)
        cc: Адреса в копии через запятую (необязательно)
    """
    account = _get_account(ctx)

    to_list = _mailboxes(to)
    cc_list = _mailboxes(cc)

    try:
        msg = Message(
            account=account,
            folder=account.drafts,
            subject=subject,
            body=HTMLBody(body),
            to_recipients=to_list or None,
            cc_recipients=cc_list or None,
        )
        # .save() — только сохранение; .send()/.send_and_save() здесь недопустимы:
        # инструмент по контракту ничего не отправляет адресатам.
        msg.save()
    except Exception as e:
        return (
            f"Ошибка сохранения черновика: {e}\n"
            f"Возможные причины: проблемы с сетью или сервер Exchange недоступен.\n"
            f"Попробуй повторить операцию."
        )

    to_str = ", ".join(m.email_address for m in to_list)
    cc_str = ", ".join(m.email_address for m in cc_list)
    return (
        f"Черновик сохранён (не отправлен):\n"
        f"Кому: {to_str or '—'}\n"
        f"Копия: {cc_str or '—'}\n"
        f"Тема: {subject}"
    )


@mcp.tool()
async def reply_to_email(
    subject: str,
    body: str,
    reply_all: bool = True,
    index: int = 1,
    ctx: Context = None,
) -> str:
    """Ответить на письмо по теме.

    Args:
        subject: Подстрока в теме исходного письма
        body: Текст ответа (HTML)
        reply_all: Ответить всем (True) или только отправителю (False)
        index: Какое совпадение, 1 = самое свежее
    """
    account = _get_account(ctx)
    index = max(1, min(index, 10))

    items = (
        account.inbox.filter(subject__icontains=subject)
        .order_by("-datetime_received")
        .only("subject", "sender", "to_recipients", "cc_recipients", "body", "datetime_received")
    )

    item = None
    for i, candidate in enumerate(items, 1):
        if i == index:
            item = candidate
            break
        if i > 10:
            break

    if not item:
        return f"Письмо не найдено: '{subject}' (индекс {index})"

    try:
        if reply_all:
            item.reply_all(subject=f"Re: {item.subject}", body=HTMLBody(body))
        else:
            item.reply(subject=f"Re: {item.subject}", body=HTMLBody(body))
    except Exception as e:
        return (
            f"Ошибка при ответе на письмо: {e}\n"
            f"Возможные причины: проблемы с сетью, сервер Exchange недоступен или письмо было удалено.\n"
            f"Попробуй найти письмо заново и повторить ответ."
        )

    return (
        f"Ответ отправлен:\n"
        f"На письмо: {item.subject}\n"
        f"От: {item.sender.email_address if item.sender else '?'}\n"
        f"Режим: {'всем' if reply_all else 'только отправителю'}"
    )


# ---------------------------------------------------------------------------
# Attachment tools
# ---------------------------------------------------------------------------


@mcp.tool()
async def get_attachments(
    subject: str,
    email_index: int = 1,
    save_index: int = 0,
    save_dir: str = "",
    ctx: Context = None,
) -> str:
    """Список вложений письма. Если указан save_index — сохраняет файл на диск.
    Возвращает: имя и размер каждого вложения.

    Примеры: get_attachments(subject='отчёт') — список,
    get_attachments(subject='отчёт', save_index=1) — сохранить первое.

    Args:
        subject: Подстрока в теме письма (без учёта регистра)
        email_index: Какое совпадение письма, 1 = самое свежее
        save_index: Номер вложения для сохранения (0 = только список)
        save_dir: Папка для сохранения (по умолчанию ~/Downloads)
    """
    account = _get_account(ctx)
    email_index = max(1, min(email_index, 10))
    items = (
        account.inbox.filter(subject__icontains=subject)
        .order_by("-datetime_received")
        .only("subject", "datetime_received", "attachments")
    )

    item = None
    for i, candidate in enumerate(items, 1):
        if i == email_index:
            item = candidate
            break
        if i > 10:
            break

    if not item:
        return f"Письмо не найдено: '{subject}' (индекс {email_index})"

    if not item.attachments:
        return f"Нет вложений в письме: {item.subject}"

    lines = [f"Вложения в письме: {item.subject}"]
    file_attachments = []
    for i, att in enumerate(item.attachments, 1):
        if isinstance(att, FileAttachment):
            file_attachments.append((i, att))
            size_kb = len(att.content) // 1024 if att.content else 0
            lines.append(f"{i}. {att.name} ({size_kb} КБ)")
        else:
            lines.append(f"{i}. {att.name or '(встроенное)'} [не файл]")

    if save_index > 0:
        match = None
        for idx, att in file_attachments:
            if idx == save_index:
                match = att
                break
        if not match:
            lines.append(f"\nВложение #{save_index} не найдено или не является файлом.")
        else:
            try:
                target_path = safe_attachment_path(save_dir, match.name)
            except ValueError as e:
                lines.append(f"\nНебезопасное имя вложения, сохранение отклонено: {e}")
                return "\n".join(lines)
            target_path.parent.mkdir(parents=True, exist_ok=True)
            with open(target_path, "wb") as f:
                f.write(match.content)
            size_kb = len(match.content) // 1024
            lines.append(f"\nСохранено: {target_path} ({size_kb} КБ)")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Calendar tools
# ---------------------------------------------------------------------------


@mcp.tool()
async def find_events(
    days_ahead: int = 1,
    days_back: int = 0,
    ctx: Context = None,
) -> str:
    """Встречи из календаря. По умолчанию — сегодня.
    Возвращает: время, тема, организатор, место, категории и важность.
    Категории показаны в квадратных скобках, важность — после «!» и только
    когда она не Normal. Макс. 50 событий.

    Примеры: find_events() — сегодня, find_events(days_ahead=7) — неделя вперёд,
    find_events(days_back=7) — прошлая неделя, find_events(days_ahead=3, days_back=3).

    Args:
        days_ahead: На сколько дней вперёд (по умолчанию 1, макс. 30)
        days_back: На сколько дней назад (по умолчанию 0, макс. 90)
    """
    account = _get_account(ctx)
    tz = account.default_timezone
    now = datetime.datetime.now(tz=tz)
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)

    start = today - datetime.timedelta(days=max(0, min(days_back, 90)))
    end = today + datetime.timedelta(days=max(1, min(days_ahead, 30)))

    items = account.calendar.view(start=start, end=end).only(
        "start", "end", "subject", "organizer", "location", "is_all_day",
        "categories", "importance",
    )

    events = _sort_events(items, tz)[:50]
    if not events:
        return "Нет встреч за указанный период."

    span = max(days_ahead, 1) + max(days_back, 0)
    if span > 1:
        # Group by date when spanning multiple days
        lines = []
        current_date = None
        idx = 1
        for event in events:
            event_date = _event_day(event)
            if event_date != current_date:
                current_date = event_date
                date_str = event_date.strftime("%Y-%m-%d (%A)") if event_date else "?"
                lines.append(f"\n### {date_str}")
            lines.append(_format_event(idx, event))
            idx += 1
        return "\n".join(lines).strip()
    else:
        lines = [_format_event(i, event) for i, event in enumerate(events, 1)]
        return "\n".join(lines)


@mcp.tool()
async def get_event(subject: str, days: int = 7, days_back: int = 0, ctx: Context = None) -> str:
    """Детали встречи по подстроке в теме.
    Возвращает: тема, время, организатор, место, категории, важность,
    участники, описание.

    Args:
        subject: Подстрока в теме встречи (без учёта регистра)
        days: За сколько дней вперёд искать (по умолчанию 7)
        days_back: За сколько дней назад искать (по умолчанию 0 = только вперёд)
    """
    account = _get_account(ctx)
    tz = account.default_timezone
    now = datetime.datetime.now(tz=tz)
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    start = today - datetime.timedelta(days=max(0, min(days_back, 90)))
    end = today + datetime.timedelta(days=max(1, min(days, 30)))

    items = account.calendar.view(start=start, end=end).only(
        "start", "end", "subject", "organizer", "location",
        "is_all_day", "required_attendees", "optional_attendees", "body",
        "categories", "importance",
    )

    subject_lower = subject.lower()
    match = None
    for item in items:
        if subject_lower in (item.subject or "").lower():
            match = item
            break

    if not match:
        return f"Встреча не найдена: '{subject}'"

    if match.is_all_day:
        time_str = "Весь день"
    else:
        s = match.start.strftime("%Y-%m-%d %H:%M") if match.start else "?"
        e = match.end.strftime("%H:%M") if match.end else "?"
        time_str = f"{s} – {e}"

    organizer = match.organizer.email_address if match.organizer else "—"
    location = match.location or "—"
    required = ", ".join(
        a.mailbox.email_address for a in (match.required_attendees or [])
    )
    optional = ", ".join(
        a.mailbox.email_address for a in (match.optional_attendees or [])
    )
    body = match.body or "(нет описания)"
    categories = _event_categories(match)

    return (
        f"Тема: {match.subject}\n"
        f"Время: {time_str}\n"
        f"Организатор: {organizer}\n"
        f"Место: {location}\n"
        f"Категории: {categories or '—'}\n"
        f"Важность: {_event_importance(match)}\n"
        f"Обязательные: {required or '—'}\n"
        f"Необязательные: {optional or '—'}\n"
        f"---\n"
        f"{body}"
    )


def _invitation_mode(attendees: list) -> str:
    """Режим сохранения встречи.

    ВАЖНО: у CalendarItem.save() дефолт — SEND_TO_NONE. То есть участники в списке
    будут, а приглашения им не уйдут. Поэтому как только участники есть, сохраняем
    с отправкой; встреча «только для себя» остаётся тихой.
    """
    return SEND_TO_ALL_AND_SAVE_COPY if attendees else SEND_TO_NONE


def _attendees_line(required: list, optional: list) -> str:
    """Строка подтверждения: кому ушли приглашения. Пусто, если звать некого."""
    if not required and not optional:
        return ""
    parts = []
    if required:
        parts.append(", ".join(required))
    if optional:
        parts.append(f"необязательные — {', '.join(optional)}")
    return f"Участники (приглашения отправлены): {'; '.join(parts)}"


@mcp.tool()
async def create_event(
    subject: str,
    start: str,
    end: str = "",
    duration_minutes: int = 60,
    location: str = "",
    body: str = "",
    attendees: str = "",
    optional_attendees: str = "",
    ctx: Context = None,
) -> str:
    """Создать встречу в календаре.

    Если указаны участники — им уходят приглашения на почту. Без участников
    встреча создаётся тихо, только в своём календаре.

    Args:
        subject: Тема встречи
        start: Начало в формате "YYYY-MM-DD HH:MM"
        end: Конец в формате "YYYY-MM-DD HH:MM" (если пусто — рассчитается из duration_minutes)
        duration_minutes: Длительность в минутах (по умолчанию 60, используется если end не указан)
        location: Место проведения
        body: Описание встречи
        attendees: Обязательные участники — адреса через запятую (им придёт приглашение)
        optional_attendees: Необязательные участники — адреса через запятую
    """
    account = _get_account(ctx)
    tz = account.default_timezone

    try:
        start_dt = EWSDateTime.from_datetime(
            datetime.datetime.strptime(start, "%Y-%m-%d %H:%M").replace(tzinfo=tz)
        )

        if end:
            end_dt = EWSDateTime.from_datetime(
                datetime.datetime.strptime(end, "%Y-%m-%d %H:%M").replace(tzinfo=tz)
            )
        else:
            end_dt = EWSDateTime.from_datetime(
                (start_dt + datetime.timedelta(minutes=duration_minutes)).replace(tzinfo=tz)
            )

        # Список строк — exchangelib сам приведёт их к Attendee. Mailbox сюда
        # передавать нельзя: поле требует Attendee и падает TypeError.
        required = _split_addresses(attendees)
        optional = _split_addresses(optional_attendees)

        item = CalendarItem(
            account=account,
            folder=account.calendar,
            subject=subject,
            start=start_dt,
            end=end_dt,
            location=location or None,
            body=body or None,
            required_attendees=required or None,
            optional_attendees=optional or None,
        )
        item.save(send_meeting_invitations=_invitation_mode(required + optional))
    except ValueError as e:
        return (
            f"Ошибка в формате даты/времени: {e}\n"
            f"Используй формат \"YYYY-MM-DD HH:MM\", например \"2026-04-15 10:00\"."
        )
    except Exception as e:
        return (
            f"Ошибка создания встречи: {e}\n"
            f"Возможные причины: проблемы с сетью, сервер Exchange недоступен или конфликт в календаре.\n"
            f"Проверь параметры и попробуй снова."
        )

    lines = [
        "Встреча создана:",
        f"Тема: {subject}",
        f"Время: {start_dt.strftime('%Y-%m-%d %H:%M')} – {end_dt.strftime('%H:%M')}",
        f"Место: {location or '—'}",
    ]
    invited = _attendees_line(required, optional)
    if invited:
        lines.append(invited)
    return "\n".join(lines)


@mcp.tool()
async def delete_event(subject: str, days: int = 7, ctx: Context = None) -> str:
    """Удалить встречу из календаря по подстроке в теме.

    Args:
        subject: Подстрока в теме встречи (без учёта регистра)
        days: За сколько дней вперёд искать (по умолчанию 7)
    """
    account = _get_account(ctx)
    tz = account.default_timezone
    now = datetime.datetime.now(tz=tz)
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end = today + datetime.timedelta(days=max(1, min(days, 30)))

    items = account.calendar.view(start=today, end=end).only(
        "start", "end", "subject",
    )

    subject_lower = subject.lower()
    match = None
    for item in items:
        if subject_lower in (item.subject or "").lower():
            match = item
            break

    if not match:
        return f"Встреча не найдена: '{subject}'"

    title = match.subject
    time_str = match.start.strftime("%Y-%m-%d %H:%M") if match.start else "?"
    match.delete()
    return f"Удалена встреча: {title} ({time_str})"


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    mcp.run(transport="stdio")
