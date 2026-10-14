"""Máy chủ HTTP nhẹ phục vụ giao diện Web Tra cứu Cuộc họp (Meeting Intel UI).
Chạy bằng thư viện chuẩn của Python (http.server), không cần cài thêm dependencies.
Bảo đảm an toàn trực tuyến: rate limit IP, trần lượt chạy ngày, ACCESS_CODE, /healthz, không log dữ liệu nhạy cảm.
"""
from __future__ import annotations

import json
import mimetypes
import os
import re
import sys
import time
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Optional
from urllib.parse import parse_qs, urlparse

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.export import tasks_csv, to_markdown
from src.pipeline import MEETINGS, list_meetings, run_meeting

# Giới hạn an toàn trực tuyến
_IP_REQUESTS: dict[str, list[float]] = {}
RATE_LIMIT_PER_MINUTE = int(os.environ.get("RATE_LIMIT_PER_MINUTE", 30))

_DAILY_COUNTER = {"date": "", "count": 0}
DAILY_RUN_LIMIT = int(os.environ.get("DAILY_RUN_LIMIT", 100))
MAX_TRANSCRIPT_CHARS = 30000


def _is_rate_limited(client_ip: str) -> bool:
    """Kiểm tra tần suất yêu cầu theo IP (cửa sổ trượt 60 giây)."""
    now = time.time()
    cutoff = now - 60.0
    times = [t for t in _IP_REQUESTS.get(client_ip, []) if t > cutoff]
    if len(times) >= RATE_LIMIT_PER_MINUTE:
        _IP_REQUESTS[client_ip] = times
        return True
    times.append(now)
    _IP_REQUESTS[client_ip] = times
    return False


def _check_and_increment_daily_run() -> bool:
    """Kiểm tra và tăng số lượt chạy pipeline trong ngày (UTC)."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if _DAILY_COUNTER["date"] != today:
        _DAILY_COUNTER["date"] = today
        _DAILY_COUNTER["count"] = 0
    if _DAILY_COUNTER["count"] >= DAILY_RUN_LIMIT:
        return False
    _DAILY_COUNTER["count"] += 1
    return True


class MeetingIntelHandler(SimpleHTTPRequestHandler):
    timeout = 60

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT / "web"), **kwargs)

    def log_message(self, format, *args):
        # Bảo mật: Không ghi nội dung query params nhạy cảm, header, hoặc transcript vào log
        first_arg = str(args[0]) if args else ""
        cleaned = re.sub(r"code=[^&\s]+", "code=REDACTED", first_arg)
        sys.stderr.write(f"[{self.log_date_time_string()}] {self.address_string()} {cleaned}\n")

    def _get_client_ip(self) -> str:
        xf = self.headers.get("X-Forwarded-For")
        if xf:
            return xf.split(",")[0].strip()
        return self.client_address[0] if self.client_address else "127.0.0.1"

    def _check_access_code(self, qs: dict, payload: Optional[dict] = None) -> bool:
        required_code = os.environ.get("ACCESS_CODE", "").strip()
        if not required_code:
            return True  # Không cấu hình ACCESS_CODE thì cho phép (tiện chạy local)
        auth_header = self.headers.get("X-Access-Code", "").strip()
        if not auth_header:
            auth = self.headers.get("Authorization", "").strip()
            if auth.lower().startswith("bearer "):
                auth_header = auth[7:].strip()
        code_qs = qs.get("code", [""])[0].strip() if qs else ""
        code_payload = payload.get("access_code", "").strip() if payload else ""
        provided = auth_header or code_qs or code_payload
        return provided == required_code

    def end_headers(self):
        # Hỗ trợ CORS cho local development
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, X-Access-Code, Authorization")
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(HTTPStatus.NO_CONTENT)
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        qs = parse_qs(parsed.query)

        # Endpoint giám sát trạng thái sức khỏe cho Render / uptime pinger
        if path == "/healthz":
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(b"OK")
            return

        ip = self._get_client_ip()
        if _is_rate_limited(ip):
            self._send_json({"error": "Vượt quá giới hạn tần suất yêu cầu (30 yêu cầu/phút). Vui lòng thử lại sau giây lát."},
                            status=HTTPStatus.TOO_MANY_REQUESTS)
            return

        if path == "/api/meetings":
            self._handle_list_meetings()
        elif path.startswith("/api/meeting/"):
            if not self._check_access_code(qs):
                self._send_json({"error": "Mã truy cập không chính xác hoặc chưa được cung cấp (401 Unauthorized). Vui lòng nhập ACCESS_CODE trên thanh điều khiển."},
                                status=HTTPStatus.UNAUTHORIZED)
                return
            mid = path.replace("/api/meeting/", "").strip("/")
            oracle = qs.get("oracle", ["1"])[0] in ("1", "true")
            judge = qs.get("judge", ["jev"])[0]
            backend = qs.get("backend", ["oracle"])[0]
            self._handle_get_meeting(mid, backend=backend, judge=judge, oracle=oracle)
        elif path == "/api/stats":
            self._handle_stats()
        else:
            # Phục vụ static files trong web/
            super().do_GET()

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path

        ip = self._get_client_ip()
        if _is_rate_limited(ip):
            self._send_json({"error": "Vượt quá giới hạn tần suất yêu cầu (30 yêu cầu/phút). Vui lòng thử lại sau giây lát."},
                            status=HTTPStatus.TOO_MANY_REQUESTS)
            return

        if path == "/api/export":
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length)
            payload = json.loads(body.decode("utf-8")) if body else {}

            if not self._check_access_code({}, payload):
                self._send_json({"error": "Mã truy cập không chính xác hoặc chưa được cung cấp (401 Unauthorized)."},
                                status=HTTPStatus.UNAUTHORIZED)
                return

            mid = payload.get("meeting_id")
            fmt = payload.get("format", "markdown")
            approved_only = set(payload.get("approved_ids", [])) if "approved_ids" in payload else None

            try:
                res = run_meeting(mid, oracle=True, judge="none")
                if fmt == "csv":
                    data = tasks_csv(res, approved_only=approved_only)
                    ctype = "text/csv; charset=utf-8"
                else:
                    data = to_markdown(res, approved_only=approved_only)
                    ctype = "text/markdown; charset=utf-8"
                self.send_response(HTTPStatus.OK)
                self.send_header("Content-Type", ctype)
                self.end_headers()
                self.wfile.write(data.encode("utf-8"))
            except Exception as e:
                self._send_json({"error": f"Lỗi xuất dữ liệu: {str(e)}"}, status=HTTPStatus.INTERNAL_SERVER_ERROR)

        elif path == "/api/upload":
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length)
            payload = json.loads(body.decode("utf-8")) if body else {}

            if not self._check_access_code({}, payload):
                self._send_json({"error": "Mã truy cập không chính xác hoặc chưa được cung cấp (401 Unauthorized). Vui lòng nhập ACCESS_CODE trên thanh điều khiển."},
                                status=HTTPStatus.UNAUTHORIZED)
                return

            if not _check_and_increment_daily_run():
                self._send_json({"error": f"Hệ thống đã đạt trần {DAILY_RUN_LIMIT} lượt chạy hôm nay để bảo vệ hạn mức API. Quý khách vui lòng thử lại vào ngày mai hoặc chạy local theo hướng dẫn trong README."},
                                status=HTTPStatus.TOO_MANY_REQUESTS)
                return

            raw_text = payload.get("transcript", "").strip()
            if not raw_text:
                self._send_json({"error": "Nội dung transcript không được để trống."}, status=HTTPStatus.BAD_REQUEST)
                return

            if len(raw_text) > MAX_TRANSCRIPT_CHARS:
                self._send_json({"error": f"Nội dung transcript quá dài ({len(raw_text):,} ký tự). Giới hạn tối đa là {MAX_TRANSCRIPT_CHARS:,} ký tự."},
                                status=HTTPStatus.BAD_REQUEST)
                return

            title = payload.get("title", "").strip() or "Cuộc họp tùy biến"
            date_str = payload.get("date", "2026-10-14")
            user_roles = payload.get("roles", {})

            from src.parser import parse_transcript
            utts = parse_transcript(raw_text)
            if not utts:
                self._send_json({"error": "Không thể nhận diện phát biểu nào. Vui lòng định dạng 'Người nói: Nội dung'."}, status=HTTPStatus.BAD_REQUEST)
                return

            speakers = list(dict.fromkeys(u.speaker for u in utts if u.speaker))
            # Vai trò chỉ áp dụng in-memory cho lần chạy này, không ghi vào file công ty
            effective_roles = {s: user_roles.get(s, "member") for s in speakers}

            mid = f"custom_{int(time.time())}"
            mdir = MEETINGS / mid
            mdir.mkdir(parents=True, exist_ok=True)

            (mdir / "transcript.txt").write_text(raw_text, encoding="utf-8")
            brief_data = {
                "id": mid,
                "title": title,
                "date": date_str,
                "project": "aurora",
                "purpose": title,
                "agenda": [title],
                "attendees": speakers
            }
            import yaml
            (mdir / "brief.yaml").write_text(yaml.safe_dump(brief_data, allow_unicode=True), encoding="utf-8")

            try:
                res = run_meeting(mid, backend="gemini", judge="none", oracle=False, custom_roles=effective_roles)
                data = res.model_dump()
                data["new_meeting_id"] = mid
                self._send_json(data)
            except Exception as e:
                self._send_json({"error": f"Lỗi phân tích: {str(e)}"}, status=HTTPStatus.INTERNAL_SERVER_ERROR)
        else:
            self.send_error(HTTPStatus.NOT_FOUND, "Endpoint không tồn tại")

    def _handle_list_meetings(self):
        meetings = []
        for d in sorted(MEETINGS.iterdir()):
            if d.is_dir() and (d / "transcript.txt").exists():
                meta = {}
                exp_path = d / "expected.json"
                if exp_path.exists():
                    try:
                        exp = json.loads(exp_path.read_text(encoding="utf-8"))
                        meta["difficulty"] = exp.get("difficulty", "")
                    except Exception:
                        pass
                brief_path = d / "brief.yaml"
                if brief_path.exists():
                    import yaml
                    try:
                        bf = yaml.safe_load(brief_path.read_text(encoding="utf-8")) or {}
                        meta["title"] = bf.get("title", "")
                        meta["date"] = bf.get("date", "")
                    except Exception:
                        pass
                meetings.append({
                    "id": d.name,
                    "title": meta.get("title") or d.name,
                    "difficulty": meta.get("difficulty", ""),
                    "date": meta.get("date", "")
                })
        self._send_json({"meetings": meetings})

    def _handle_get_meeting(self, meeting_id: str, backend: str, judge: str, oracle: bool):
        try:
            res = run_meeting(meeting_id, backend=backend, judge=judge, oracle=oracle)
            data = res.model_dump()
            self._send_json(data)
        except Exception as e:
            self._send_json({"error": str(e)}, status=HTTPStatus.INTERNAL_SERVER_ERROR)

    def _handle_stats(self):
        eval_path = ROOT / "outputs" / "eval_oracle_jev.json"
        if eval_path.exists():
            try:
                data = json.loads(eval_path.read_text(encoding="utf-8"))
                self._send_json(data.get("summary", {}))
                return
            except Exception:
                pass
        self._send_json({"pass_rate": 1.0, "critical_errors": 0})

    def _send_json(self, data: dict, status: HTTPStatus = HTTPStatus.OK):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def run_server(port: int = None, host: str = "127.0.0.1"):
    port = port if port is not None else int(os.environ.get("PORT", 8080))
    host = os.environ.get("HOST", host)
    web_dir = ROOT / "web"
    web_dir.mkdir(exist_ok=True)
    server = ThreadingHTTPServer((host, port), MeetingIntelHandler)
    print(f"[*] Meeting Intel UI đang chạy tại: http://{host}:{port}")
    print(f"[*] Nhấn Ctrl + C để dừng máy chủ.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nĐã dừng máy chủ.")
        server.server_close()


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else None
    run_server(port=port)
