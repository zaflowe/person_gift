"""Read-only Alipay browser collector. Never downloads bills or performs payments."""
from __future__ import annotations

import asyncio
import fcntl
import gzip
import json
import logging
import os
import re
import signal
import socket
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from ledger import Ledger, parse_row
from schedule import allowed, next_slot

RECORD_URL = "https://consumeprod.alipay.com/record/advanced.htm"
TABLE = "#tradeRecordsIndex"
LOG = logging.getLogger("alipay-collector")

READ_TABLE = """table => {
 const rows = [...table.querySelectorAll('tr')];
 const headerRow = rows.find(r => r.querySelector('th')) || rows[0];
 const headers = [...(headerRow?.querySelectorAll('th,td') || [])].map(c => c.innerText.trim());
 return rows.filter(r => r !== headerRow && r.querySelector('td')).map(r => ({
   headers, cells: [...r.querySelectorAll('td')].map(c => c.innerText.trim()),
   links: [...r.querySelectorAll('a[href]')].map(a => ({text:a.innerText.trim(),href:a.href}))
 }));
}"""


def now():
    return datetime.now(timezone.utc).isoformat()


def error_code(exc):
    match = re.search(r"net::[A-Z_]+", str(exc))
    return match[0] if match else type(exc).__name__


class Agent:
    def __init__(self, data: Path, interval: int = 14400, max_pages: int = 20):
        self.data = data
        self.data.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.interval = max(60, interval)
        self.max_pages = max_pages
        self.lock = open(data / "agent.lock", "a+")
        fcntl.flock(self.lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        self.ledger = Ledger(data / "ledger.sqlite3")
        self.status_file = data / "status.json"
        try:
            self.status = json.loads(self.status_file.read_text())
        except (FileNotFoundError, ValueError):
            self.status = {}
        self.status.update({"process_started_at": now(), "interval_seconds": self.interval,
                            "mode": "read_only_list", "state": "starting",
                            "timezone": "Asia/Shanghai", "scheduled_hours": [12, 16, 20],
                            "quiet_hours": "00:00-12:00"})
        self.stop = asyncio.Event()
        self.authenticated = False
        self.last_capture = 0.0
        self.context = self.page = None
        self.publish(state="starting")

    def publish(self, **fields):
        previous = self.status.get("state")
        self.status.update(fields)
        self.status["heartbeat_at"] = now()
        temp = self.status_file.with_suffix(".tmp")
        temp.write_text(json.dumps(self.status, ensure_ascii=False, indent=2))
        temp.replace(self.status_file)
        if fields.get("state") and fields["state"] != previous:
            self.ledger.record("session_events", now(), fields["state"], {
                k: self.status.get(k) for k in ("session_observed_at", "last_success_at", "first_auth_required_at", "query_error")
            })
            LOG.info("state=%s", fields["state"])

    async def capture_login(self):
        if time.monotonic() - self.last_capture < 15:
            return
        self.last_capture = time.monotonic()
        screenshot = self.data / "login.png"
        await self.page.screenshot(path=str(screenshot))
        (self.data / "login-view.json").write_text(json.dumps({
            "observed_at": now(), "url": self.page.url,
            "visible_text": (await self.page.locator("body").inner_text())[:12000],
        }, ensure_ascii=False))
        try:
            from PIL import Image
            from pyzbar.pyzbar import decode
            codes = decode(Image.open(screenshot))
            uri = next((x.data.decode() for x in codes if "alipay.com" in x.data.decode()), None)
            # Only official Alipay QR destinations; stored on the server, never logged.
            host = (urlparse(uri).hostname or "") if uri else ""
            if uri and urlparse(uri).scheme == "https" and (host == "alipay.com" or host.endswith(".alipay.com")):
                (self.data / "login-qr.json").write_text(json.dumps({"observed_at": now(), "url": uri}))
        except Exception:
            pass

    async def has_table(self):
        return await self.page.locator(TABLE).is_visible()

    async def auth_state(self):
        visible = await self.page.locator("body").inner_text(timeout=10000)
        frames = [visible]
        for frame in self.page.frames:
            if frame == self.page.main_frame:
                continue
            try:
                element = await frame.frame_element()
                if await element.is_visible():
                    frames.append(await frame.locator("body").inner_text(timeout=2000))
            except Exception:
                continue
        compact = re.sub(r"\s+", "", "\n".join(frames))
        if self.page.url.startswith("chrome-error:") or ("ERR_" in visible and any(x in visible for x in ("无法访问", "无法连接", "This site can’t be reached", "This site can't be reached"))):
            return "network_error"
        if any(x in compact for x in ("扫码验证身份", "二维码验证身份", "请完成安全验证", "请完成验证", "人机验证")):
            return "verification_required"
        if urlparse(self.page.url).hostname in {"auth.alipay.com", "authet2.alipay.com", "authgtj.alipay.com"} or "请使用手机支付宝扫码" in visible:
            return "login_required"
        if await self.has_table():
            return "authenticated"
        return "page_unrecognized"

    async def wait_for_query_result(self):
        for _ in range(40):
            state = await self.auth_state()
            if state != "page_unrecognized":
                return state
            await asyncio.sleep(0.5)
        return "page_unrecognized"

    async def capture_rows(self):
        return await self.page.locator(TABLE).evaluate(READ_TABLE)

    async def collect(self):
        start = now()
        raw_pages, parsed, errors = [], {}, []
        complete, finish_reason = False, "page_limit"
        state = await self.wait_for_query_result()
        if state != "authenticated":
            return {"state": state}
        seen_pages = set()
        for number in range(1, self.max_pages + 1):
            rows = await self.capture_rows()
            signature = json.dumps(rows, ensure_ascii=False, sort_keys=True)
            if signature in seen_pages:
                finish_reason = "repeated_page"
                break
            seen_pages.add(signature)
            raw_pages.append({"page": number, "rows": rows})
            for row in rows:
                try:
                    item = parse_row(row)
                    parsed[item["external_id"]] = item
                except ValueError as exc:
                    errors.append({"page": number, "reason": str(exc)})
            links = self.page.get_by_role("link", name=re.compile(r"^下一页[>＞]?$"))
            next_link = None
            for link in await links.all():
                if await link.is_visible() and await link.get_attribute("aria-disabled") != "true" and "disabled" not in (await link.get_attribute("class") or "").lower():
                    next_link = link
                    break
            if next_link is None:
                complete, finish_reason = True, "last_page"
                break
            old_text = await self.page.locator(TABLE).inner_text()
            await next_link.click(timeout=15000)
            try:
                await self.page.wait_for_function("({selector,old}) => {const t=document.querySelector(selector);return t && t.innerText !== old;}", arg={"selector": TABLE, "old": old_text}, timeout=20000)
            except Exception:
                auth = await self.auth_state()
                finish_reason = auth if auth != "authenticated" else "pagination_not_changed"
                break
            await asyncio.sleep(1)
        finished = now()
        snapshot = self.data / "snapshots"
        snapshot.mkdir(exist_ok=True, mode=0o700)
        name = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ") + ".json.gz"
        with gzip.open(snapshot / name, "wt", encoding="utf-8") as stream:
            json.dump({"started_at": start, "finished_at": finished, "pages": raw_pages}, stream, ensure_ascii=False)
        counts = self.ledger.save(list(parsed.values()), finished)
        report = {"state": "collected" if complete and not errors else "partial", "pages": len(raw_pages),
                  "rows": len(parsed), "parse_errors": errors, "complete": complete,
                  "finish_reason": finish_reason, "last_snapshot": name, **counts}
        self.ledger.record("runs", finished, report["state"], report, started_at=start)
        return report

    async def run(self):
        from playwright.async_api import async_playwright
        async with async_playwright() as playwright:
            profile = self.data / "profile"
            lock = profile / "SingletonLock"
            if lock.is_symlink():
                target = os.readlink(lock)
                host, _, pid = target.rpartition("-")
                if host != socket.gethostname() or (pid.isdigit() and not Path(f"/proc/{pid}").exists()):
                    for name in ("SingletonLock", "SingletonCookie", "SingletonSocket"):
                        (profile / name).unlink(missing_ok=True)
            proxy = os.environ.get("COLLECTOR_PROXY")
            self.context = await playwright.chromium.launch_persistent_context(
                str(profile), headless=True, chromium_sandbox=True,
                viewport={"width": 1280, "height": 900}, locale="zh-CN",
                timezone_id="Asia/Shanghai", accept_downloads=False,
                proxy={"server": proxy} if proxy else None,
                args=["--disable-dev-shm-usage"],
            )
            self.context.set_default_timeout(15000)
            self.publish(state="browser_ready")
            self.page = self.context.pages[0] if self.context.pages else await self.context.new_page()
            navigation_failed = False
            try:
                await self.page.goto(RECORD_URL, wait_until="domcontentloaded", timeout=60000)
            except Exception as exc:
                navigation_failed = True
                self.publish(state="network_error", query_error=error_code(exc))
            else:
                self.publish(query_error=None)
            due = next_slot(datetime.now(timezone.utc)) if navigation_failed else datetime.now(timezone.utc)
            while not self.stop.is_set():
                try:
                    request = self.data / "request.json"
                    if request.exists():
                        command = json.loads(request.read_text())
                        request.unlink()
                        if command.get("action") == "refresh_login" and not await self.has_table():
                            # Refresh a QR login, never a CAPTCHA or identity challenge.
                            if (await self.page.get_by_text("二维码失效", exact=True).is_visible()):
                                await self.page.get_by_role("button", name="刷新", exact=True).click()
                            self.last_capture = 0
                        elif command.get("action") == "open_login":
                            await self.page.goto(RECORD_URL, wait_until="domcontentloaded", timeout=60000)
                            self.last_capture = 0
                    current = await self.auth_state()
                    if current in {"network_error", "page_unrecognized"} and datetime.now(timezone.utc) >= due and allowed(datetime.now(timezone.utc)):
                        self.publish(state="retrying_query", last_attempt_at=now())
                        try:
                            await self.page.goto(RECORD_URL, wait_until="domcontentloaded", timeout=60000)
                            current = await self.wait_for_query_result()
                        except Exception as exc:
                            current = "network_error"
                            self.publish(query_error=error_code(exc))
                        due = next_slot(datetime.now(timezone.utc))
                    if current == "authenticated" and not self.authenticated:
                        self.authenticated = True
                        self.publish(state="authenticated", session_observed_at=now(), first_auth_required_at=None,
                                     last_auth_required_at=None, query_error=None)
                        for path in (self.data / "login-qr.json", self.data / "login.png", self.data / "login-view.json"):
                            path.unlink(missing_ok=True)
                        due = datetime.now(timezone.utc)
                    if current != "authenticated":
                        if self.authenticated:
                            self.authenticated = False
                            self.publish(first_auth_required_at=now(), last_auth_required_at=now())
                        self.publish(state=current)
                        await self.capture_login()
                    elif datetime.now(timezone.utc) >= due and allowed(datetime.now(timezone.utc)):
                        self.publish(state="querying", last_attempt_at=now())
                        await self.page.goto(RECORD_URL, wait_until="domcontentloaded", timeout=60000)
                        result = await self.collect()
                        if result["state"] in {"collected", "partial"}:
                            self.publish(**result, last_success_at=now(), query_error=None)
                            LOG.info("query=%s pages=%s rows=%s new=%s changed=%s", result["state"], result["pages"], result["rows"], result["new"], result["changed"])
                        else:
                            self.authenticated = False
                            self.publish(**result, first_auth_required_at=now(), last_auth_required_at=now())
                            await self.capture_login()
                        due = next_slot(datetime.now(timezone.utc))
                        self.publish(next_query_at=due.isoformat())
                    else:
                        if not allowed(datetime.now(timezone.utc)):
                            due = next_slot(datetime.now(timezone.utc))
                            self.publish(state="quiet_hours", next_query_at=due.isoformat())
                        else:
                            self.publish(next_query_at=due.isoformat())
                except Exception as exc:
                    # Avoid credentials, QR links, account identifiers and full URLs in journal.
                    kind = error_code(exc)
                    self.publish(state="error", query_error=kind)
                    LOG.warning("cycle_error=%s", kind)
                    if kind in {"TargetClosedError", "BrowserClosedError"}:
                        raise
                    due = next_slot(datetime.now(timezone.utc))
                    self.publish(next_query_at=due.isoformat())
                try:
                    await asyncio.wait_for(self.stop.wait(), timeout=5 if not self.authenticated else 15)
                except asyncio.TimeoutError:
                    pass
            await self.context.close()
            self.publish(state="stopped")


async def main():
    os.umask(0o077)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    agent = Agent(Path(os.environ.get("COLLECTOR_DATA", "/data")),
                  int(os.environ.get("COLLECT_INTERVAL_SECONDS", "14400")),
                  int(os.environ.get("COLLECT_MAX_PAGES", "20")))
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, agent.stop.set)
    await agent.run()


if __name__ == "__main__":
    asyncio.run(main())
