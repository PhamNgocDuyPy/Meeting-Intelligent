"""Sinh 12 cuộc họp tổng hợp g01..g12 (transcript + brief + expected.json + labels_oracle.json).

Mỗi kịch bản có đáp án tham chiếu "by construction" (ta biết chắc điều gì đã/không chốt vì ta viết ra nó).
Chạy:  python scripts/gen_synthetic.py        (cố định seed -> kết quả lặp lại được)
"""
from __future__ import annotations

import json
import random
import sys
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from src.textnorm import normalize  # noqa: E402

MEET = ROOT / "data" / "meetings"
NAME_ID = {"Hà": "ha", "Minh": "minh", "Quân": "quan", "Nam": "nam", "Lan": "lan", "Trang": "trang",
           "Huy": "huy", "Phúc": "phuc", "Vy": "vy", "Đạt": "dat"}
CAST = {
    "aurora": {"tech": "Minh", "devs": ["Quân", "Nam"], "extra": ["Vy", "Đạt"]},
    "helios": {"tech": "Quân", "devs": ["Nam", "Minh"], "extra": ["Vy", "Đạt"]},
}
AUTH = {"scope": "Hà", "design": "Lan", "budget": "Huy", "release": "Huy"}  # technical -> cast["tech"]
PAIRS = {
    "technical": [("Chọn cơ sở dữ liệu", "PostgreSQL", "MySQL"), ("Chọn công cụ CI/CD", "GitHub Actions", "Jenkins"),
                  ("Chọn thư viện biểu đồ", "Chart.js", "ECharts"), ("Chọn dịch vụ gửi email", "SendGrid", "Amazon SES"),
                  ("Chọn framework kiểm thử giao diện", "Playwright", "Cypress")],
    "design": [("Phong cách minh họa onboarding", "minh họa phẳng", "ảnh chụp thật"),
               ("Kiểu điều hướng chính", "thanh tab dưới", "menu ngăn kéo")],
    "scope": [("Hình thức khuyến mãi tháng 11", "giảm giá phần trăm", "tặng voucher"),
              ("Tính năng ưu tiên sprint tới", "lịch sử đơn hàng", "đánh giá sản phẩm")],
    "budget": [("Gói hạ tầng tháng tới", "gói Standard", "gói Premium"),
               ("Kênh quảng cáo chính", "quảng cáo mạng xã hội", "quảng cáo tìm kiếm")],
    "process": [("Giờ họp daily", "9 giờ sáng", "4 giờ chiều"), ("Quy ước đặt tên nhánh git", "feature/tên-việc", "tên-người/tên-việc")],
}


def L(stance, option, quote, topic="T1", **kw):
    d = {"topic_id": topic, "option_id": option, "stance": stance, "quote": quote}
    d.update(kw)
    return d


class Meeting:
    def __init__(self, rng, mid, project, title, purpose, agenda, when, attendees):
        self.rng, self.mid, self.project, self.title = rng, mid, project, title
        self.purpose, self.agenda, self.when, self.attendees = purpose, agenda, when, attendees
        self.lines, self.labels, self.items, self.topics = [], [], [], []
        self.gold = {"topics": [], "tasks": [], "items": []}
        self.t = rng.randint(5, 20)

    def say(self, who, text, *labels):
        self.t += self.rng.randint(15, 70)
        self.lines.append((self.t, who, text))
        uid = f"U{len(self.lines):03d}"
        for lb in labels:
            assert normalize(lb["quote"]) in normalize(text), (self.mid, lb["quote"], text)
            self.labels.append({"utterance_id": uid, **lb})
        return uid

    def topic(self, tid, title, cat, opts):
        self.topics.append({"topic_id": tid, "title": title, "category": cat,
                            "options": [{"option_id": k, "label": v} for k, v in opts.items()]})

    def item(self, kind, title, uids, quote, assignee=None, basis="none", deadline=None):
        for u in uids:
            pass
        assert any(normalize(quote) in normalize(self.lines[int(u[1:]) - 1][2]) for u in uids), (self.mid, quote)
        self.items.append({"kind": kind, "title": title, "utterance_ids": uids, "quote": quote,
                           "assignee": assignee, "assignee_basis": basis, "deadline_text": deadline})

    def write(self, difficulty):
        d = MEET / self.mid
        d.mkdir(parents=True, exist_ok=True)
        tr = ["# Dữ liệu tổng hợp (scripts/gen_synthetic.py). Kịch bản: " + difficulty]
        for t, who, text in self.lines:
            h, r = divmod(t, 3600)
            m, s = divmod(r, 60)
            tr.append(f"[{h:02d}:{m:02d}:{s:02d}] {who}: {text}")
        (d / "transcript.txt").write_text("\n".join(tr) + "\n", encoding="utf-8")
        ids = [NAME_ID.get(a, a) for a in self.attendees]
        brief = (f'id: {self.mid}\ntitle: {json.dumps(self.title, ensure_ascii=False)}\ndate: "{self.when.isoformat()}"\nproject: {self.project}\n'
                 f'purpose: {json.dumps(self.purpose, ensure_ascii=False)}\nagenda: {json.dumps(self.agenda, ensure_ascii=False)}\n'
                 f'attendees: {json.dumps(ids, ensure_ascii=False)}\n')
        (d / "brief.yaml").write_text(brief, encoding="utf-8")
        self.gold["difficulty"] = difficulty
        (d / "expected.json").write_text(json.dumps(self.gold, ensure_ascii=False, indent=2), encoding="utf-8")
        (d / "labels_oracle.json").write_text(json.dumps(
            {"topics": self.topics, "labels": self.labels, "items": self.items}, ensure_ascii=False, indent=2), encoding="utf-8")


# ------------------------------------------------------------------ kịch bản
def setup(rng, i, cat, n_att=5, extra_att=()):
    project = rng.choice(["aurora", "helios"])
    cast = CAST[project]
    title, A, B = rng.choice(PAIRS[cat])
    auth = cast["tech"] if cat == "technical" else AUTH.get(cat)
    pool = ["Hà", cast["tech"], *cast["devs"], "Trang", "Lan", "Huy", "Vy", "Đạt"]
    att = list(dict.fromkeys([auth, "Hà", *cast["devs"], "Trang", *pool]))[:n_att] if auth else list(dict.fromkeys(["Hà", *pool]))[:n_att]
    if auth and auth not in att:
        att.append(auth)
    att += [a for a in extra_att if a not in att]
    when = date(2026, 9, 7) + timedelta(days=7 * (i - 1))
    return project, cast, title, A, B, auth, att, when


def pick(rng, att, exclude):
    return rng.choice([a for a in att if a not in exclude and a in NAME_ID])


def sc_ab_switch(rng, i, cat):
    project, cast, title, A, B, auth, att, when = setup(rng, i, cat, 5)
    m = Meeting(rng, f"g{i:02d}", project, f"Họp chốt: {title}", f"Chốt {title.lower()}", [title], when, att)
    m.topic("T1", title, cat, {"A": A, "B": B})
    d1 = pick(rng, att, {auth, "Hà"})
    d2 = pick(rng, att, {auth, "Hà", d1})
    m.say("Hà", f"Hôm nay mình cần chốt: {title.lower()}.")
    m.say(auth, f"Ban đầu mình đề xuất {A}, quen tay và triển khai nhanh.", L("propose", "A", f"đề xuất {A}"))
    m.say(d1, f"Mình lo về {A}, rủi ro và chi phí dài hạn cao hơn dự kiến. {B} có vẻ hợp hơn.",
          L("oppose", "A", f"Mình lo về {A}"), L("propose", "B", f"{B} có vẻ hợp hơn"))
    m.say(d2, f"Mình ủng hộ {B}, dễ kiểm soát hơn.", L("support", "B", f"ủng hộ {B}"))
    m.say(auth, f"Ok, mình đổi ý. Chốt {B}, bỏ {A}.", L("reverse", "A", f"bỏ {A}"), L("conclude", "B", f"Chốt {B}"))
    m.say("Hà", f"Đồng ý, ghi nhận {B}.", L("support", "B", f"ghi nhận {B}"))
    m.gold["topics"].append({"keywords": [A, B], "status": "decided", "final_option_keywords": [B],
                             "not_final_keywords": [A], "superseded_keywords": [A]})
    return m, "A đổi thành B, người có thẩm quyền chốt"


def sc_late_confirm(rng, i, cat):
    project, cast, title, A, B, auth, att, when = setup(rng, i, cat, 5)
    m = Meeting(rng, f"g{i:02d}", project, f"Họp bàn: {title}", f"Chốt {title.lower()}", [title], when, att)
    m.topic("T1", title, cat, {"A": A, "B": B})
    d1 = pick(rng, att, {auth, "Hà"})
    d2 = pick(rng, att, {auth, "Hà", d1})
    m.say("Hà", f"Mình bàn nốt chuyện {title.lower()}.")
    m.say(d1, f"Mình đề xuất {A}.", L("propose", "A", f"đề xuất {A}"))
    m.say(d2, f"Mình thấy {B} ổn hơn.", L("propose", "B", f"{B} ổn hơn"))
    m.say(d1, f"Ừ, {B} cũng được, mình theo.", L("support", "B", f"{B} cũng được"))
    m.say(d2, f"Vậy chốt {B} nhé.", L("conclude", "B", f"chốt {B}"))
    m.say(auth, f"Ừ, mình đồng ý {B}.", L("support", "B", f"đồng ý {B}"))
    m.gold["topics"].append({"keywords": [A, B], "status": "decided", "final_option_keywords": [B], "superseded_keywords": [A]})
    return m, "người chốt không có thẩm quyền nhưng người có thẩm quyền xác nhận sau"


def sc_consensus_ok(rng, i, _cat):
    project, cast, title, A, B, auth, att, when = setup(rng, i, "process", 5)
    m = Meeting(rng, f"g{i:02d}", project, f"Họp nhóm: {title}", f"Thống nhất {title.lower()}", [title], when, att)
    m.topic("T1", title, "process", {"A": A, "B": B})
    x, y, z, w = rng.sample([a for a in att if a in NAME_ID], 4)
    m.say("Hà" if "Hà" in att else x, f"Mình cần cả nhóm thống nhất: {title.lower()}.")
    m.say(w, f"Mình đề xuất {B}.", L("propose", "B", f"đề xuất {B}"))
    m.say(x, f"Mình thì muốn {A}, hợp lý hơn với cả nhóm.", L("propose", "A", f"muốn {A}"))
    m.say(y, f"{A} ok với mình.", L("support", "A", f"{A} ok"))
    m.say(z, f"Mình cũng chọn {A}.", L("support", "A", f"chọn {A}"))
    m.say(w, f"Ok, mình theo {A}.", L("support", "A", f"theo {A}"))
    m.say(x, f"Vậy thống nhất {A} nhé.", L("conclude", "A", f"thống nhất {A}"))
    m.gold["topics"].append({"keywords": [A, B], "status": "decided", "final_option_keywords": [A], "superseded_keywords": [B]})
    return m, "quy trình: đồng thuận đủ số người (kiểu consensus)"


def sc_consensus_short(rng, i, _cat):
    project, cast, title, A, B, auth, att, when = setup(rng, i, "process", 6)
    m = Meeting(rng, f"g{i:02d}", project, f"Họp nhóm: {title}", f"Thống nhất {title.lower()}", [title], when, att)
    m.topic("T1", title, "process", {"A": A, "B": B})
    x, y, z = rng.sample([a for a in att if a in NAME_ID], 3)
    m.say(z, f"Mình bàn chuyện {title.lower()}.")
    m.say(x, f"Mình đề xuất {A}.", L("propose", "A", f"đề xuất {A}"))
    m.say(y, f"{A} ok.", L("support", "A", f"{A} ok"))
    m.say(x, f"Vậy chốt {A} nhé.", L("conclude", "A", f"chốt {A}"))
    m.say(z, "Mình chưa có ý kiến, để mình nghĩ thêm.", L("info", None, "chưa có ý kiến"))
    m.gold["topics"].append({"keywords": [A, B], "status": ["leaning", "open"]})
    return m, "chỉ 2/6 người ủng hộ -> chưa đủ đồng thuận"


def sc_unknown_speaker(rng, i, cat):
    project, cast, title, A, B, auth, att, when = setup(rng, i, "technical", 4, extra_att=("Khách 1",))
    m = Meeting(rng, f"g{i:02d}", project, f"Họp với đối tác: {title}", f"Bàn {title.lower()}", [title], when, att)
    m.topic("T1", title, "technical", {"A": A, "B": B})
    d1 = pick(rng, att, {auth, "Hà"})
    m.say("Hà", f"Hôm nay có khách bên đối tác tham gia, mình bàn {title.lower()}.")
    m.say(d1, f"Mình đề xuất {A}.", L("propose", "A", f"đề xuất {A}"))
    m.say(auth, f"Mình thì nghiêng về {B}, nhưng cần xem thêm.", L("support", "B", f"nghiêng về {B}"))
    m.say("Khách 1", f"Thôi làm {B} đi cho nhanh.", L("conclude", "B", f"làm {B} đi"))
    m.say("Hà", "Ok, ghi nhận ý kiến của bên mình.", L("info", None, "ghi nhận ý kiến"))
    m.gold["topics"].append({"keywords": [A, B], "status": ["leaning", "open"]})
    return m, "người nói là khách, không nhận diện được thẩm quyền"


def sc_conditional(rng, i, cat):
    project, cast, title, A, B, auth, att, when = setup(rng, i, cat, 5)
    m = Meeting(rng, f"g{i:02d}", project, f"Họp quyết định: {title}", f"Chốt {title.lower()}", [title], when, att)
    m.topic("T1", title, cat, {"A": A, "B": B})
    d1 = pick(rng, att, {auth, "Hà"})
    m.say("Hà", f"Mình cần quyết định: {title.lower()}.")
    m.say(d1, f"Mình đề xuất {B}.", L("propose", "B", f"đề xuất {B}"))
    m.say(auth, f"Ok, chốt {B}, nhưng chỉ khi bên đối tác xác nhận được điều kiện hợp đồng.",
          L("conclude", "B", f"chốt {B}", conditional=True, condition_text="bên đối tác xác nhận điều kiện hợp đồng"))
    m.say("Hà", "Vậy tạm ghi là chờ đối tác xác nhận.", L("info", None, "chờ đối tác xác nhận"))
    m.gold["topics"].append({"keywords": [A, B], "status": ["leaning", "open"], "not_final_keywords": [B]})
    return m, "chốt có điều kiện chưa xảy ra"


def sc_reversal_no_new(rng, i, cat):
    project, cast, title, A, B, auth, att, when = setup(rng, i, cat, 5)
    m = Meeting(rng, f"g{i:02d}", project, f"Họp: {title}", f"Chốt {title.lower()}", [title], when, att)
    m.topic("T1", title, cat, {"A": A, "B": B})
    d1 = pick(rng, att, {auth, "Hà"})
    m.say("Hà", f"Mình bàn {title.lower()}.")
    m.say(d1, f"Mình đề xuất {A}.", L("propose", "A", f"đề xuất {A}"))
    m.say(auth, f"Ok, chốt {A}.", L("conclude", "A", f"chốt {A}"))
    m.say(d1, "Nhưng mình vừa nhận được thông tin mới từ khách, có thể ảnh hưởng.", L("info", None, "thông tin mới từ khách"))
    m.say(auth, f"Khoan, hủy {A} đi, mình chưa chắc, để xem lại.", L("reverse", "A", f"hủy {A}"), L("defer", None, "để xem lại"))
    m.gold["topics"].append({"keywords": [A, B], "status": "open", "not_final_keywords": [A]})
    return m, "kết luận bị rút lại, chưa có kết luận mới"


def sc_deferred(rng, i, cat):
    project, cast, title, A, B, auth, att, when = setup(rng, i, cat, 5)
    m = Meeting(rng, f"g{i:02d}", project, f"Họp: {title}", f"Bàn {title.lower()}", [title], when, att)
    m.topic("T1", title, cat, {"A": A, "B": B})
    d1 = pick(rng, att, {auth, "Hà"})
    d2 = pick(rng, att, {auth, "Hà", d1})
    m.say("Hà", f"Mình bàn {title.lower()}.")
    m.say(d1, f"Mình đề xuất {A}.", L("propose", "A", f"đề xuất {A}"))
    m.say(d2, f"Mình lại thấy {B} hợp hơn.", L("propose", "B", f"{B} hợp hơn"))
    m.say("Hà", "Chưa đủ thông tin để quyết, để họp sau mình quyết nhé.", L("defer", None, "để họp sau mình quyết"))
    m.gold["topics"].append({"keywords": [A, B], "status": "open", "not_final_keywords": [A, B]})
    return m, "hai phương án, hoãn sang họp sau"


def sc_unresolved_objection(rng, i, cat):
    project, cast, title, A, B, auth, att, when = setup(rng, i, cat, 5)
    m = Meeting(rng, f"g{i:02d}", project, f"Họp: {title}", f"Chốt {title.lower()}", [title], when, att)
    m.topic("T1", title, cat, {"A": A, "B": B})
    d1 = pick(rng, att, {auth, "Hà"})
    m.say("Hà", f"Mình cần chốt {title.lower()}.")
    m.say(auth, f"Mình đề xuất {B}.", L("propose", "B", f"đề xuất {B}"))
    m.say(auth, f"Vậy chốt {B}.", L("conclude", "B", f"chốt {B}"))
    m.say(d1, f"Mình không đồng ý, {B} rủi ro lớn lắm.", L("oppose", "B", f"không đồng ý"))
    m.say("Hà", "Ghi nhận, mình sẽ quay lại sau.", L("info", None, "quay lại sau"))
    m.gold["topics"].append({"keywords": [A, B], "status": ["leaning", "open"], "not_final_keywords": [B]})
    return m, "phản đối sau khi chốt, chưa ai giải quyết"


def sc_task_matrix(rng, i, _cat):
    project = rng.choice(["aurora", "helios"])
    cast = CAST[project]
    when = date(2026, 9, 7) + timedelta(days=7 * (i - 1))
    d1, d2 = cast["devs"]
    dl = when + timedelta(days=9)
    att = ["Hà", d1, d2, "Trang", "Đạt"]
    m = Meeting(rng, f"g{i:02d}", project, "Họp phân việc sprint", "Phân việc cho sprint", ["Phân việc"], when, att)
    u1 = m.say("Hà", f"{d1} làm phần đăng nhập, xong trước ngày {dl.day}/{dl.month} nhé.")
    u2 = m.say(d1, "Ok, mình nhận.")
    u3 = m.say(d2, "Mình sẽ viết tài liệu cho phần giao diện.")
    u4 = m.say("Hà", "Còn phần kiểm thử tự động thì chắc Đạt làm được nhỉ.")
    u5 = m.say("Đạt", "Để em xem đã.")
    u6 = m.say("Hà", "Trang cập nhật test case cho luồng thanh toán nhé.")
    m.item("task", "Làm phần đăng nhập", [u1, u2], "làm phần đăng nhập", d1, "assigned", f"ngày {dl.day}/{dl.month}")
    m.item("task", "Viết tài liệu phần giao diện", [u3], "viết tài liệu cho phần giao diện", d2, "self_accepted", None)
    m.item("task", "Phần kiểm thử tự động", [u4, u5], "kiểm thử tự động", None, "mentioned_only", None)
    m.item("task", "Cập nhật test case luồng thanh toán", [u6], "cập nhật test case", "Trang", "assigned", None)
    m.gold["tasks"] += [
        {"keywords": ["đăng nhập"], "assignee": d1, "deadline": dl.isoformat()},
        {"keywords": ["tài liệu"], "assignee": d2, "deadline": None},
        {"keywords": ["kiểm thử tự động"], "assignee": None, "deadline": None},
        {"keywords": ["test case"], "assignee": "Trang", "deadline": None}]
    return m, "đủ loại việc: giao+hạn, tự nhận, chỉ nhắc tên, giao không hạn"


def sc_task_dates(rng, i, _cat):
    project = rng.choice(["aurora", "helios"])
    cast = CAST[project]
    when = date(2026, 9, 7) + timedelta(days=7 * (i - 1))
    d1, d2 = cast["devs"]
    att = ["Hà", d1, d2, "Trang"]
    m = Meeting(rng, f"g{i:02d}", project, "Họp rà việc cuối tuần", "Rà việc và hạn", ["Rà việc"], when, att)
    fri = when + timedelta((4 - when.weekday()) % 7 or 7)
    u1 = m.say("Hà", f"{d1} gửi báo cáo cho mình trước ngày mai.")
    u2 = m.say(d1, "Ok.")
    u3 = m.say("Hà", f"{d2} hoàn thành phần giao diện trước thứ Sáu.")
    u4 = m.say("Hà", "Trang test xong cuối tháng nhé.")
    u5 = m.say("Hà", f"{d2} chuẩn bị bản demo tuần sau.")
    m.item("task", "Gửi báo cáo", [u1, u2], "gửi báo cáo", d1, "assigned", "ngày mai")
    m.item("task", "Hoàn thành phần giao diện", [u3], "hoàn thành phần giao diện", d2, "assigned", "thứ Sáu")
    m.item("task", "Test toàn bộ", [u4], "test xong", "Trang", "assigned", "cuối tháng")
    m.item("task", "Chuẩn bị bản demo", [u5], "chuẩn bị bản demo", d2, "assigned", "tuần sau")
    m.gold["tasks"] += [
        {"keywords": ["gửi báo cáo"], "assignee": d1, "deadline": (when + timedelta(days=1)).isoformat()},
        {"keywords": ["phần giao diện"], "assignee": d2, "deadline": fri.isoformat()},
        {"keywords": ["test toàn bộ", "test xong"], "assignee": "Trang", "deadline": None},
        {"keywords": ["bản demo"], "assignee": d2, "deadline": None}]
    return m, "hạn tương đối: ngày mai/thứ Sáu suy được; cuối tháng/tuần sau thì không"


def sc_interleaved(rng, i, _cat):
    project, cast, t1, A1, B1, auth, att, when = setup(rng, i, "technical", 5)
    t2, A2, B2 = rng.choice(PAIRS["design"])
    d1 = pick(rng, att, {auth, "Hà", "Lan"})
    att = list(dict.fromkeys(att + ["Lan"]))
    m = Meeting(rng, f"g{i:02d}", project, "Họp hai chủ đề đan xen", "Bàn hai chủ đề", [t1, t2], when, att)
    m.topic("T1", t1, "technical", {"A": A1, "B": B1})
    m.topic("T2", t2, "design", {"A": A2, "B": B2})
    m.say("Hà", f"Hôm nay hai việc: {t1.lower()} và {t2.lower()}.")
    m.say(auth, f"Về {t1.lower()}, mình đề xuất {B1}.", L("propose", "B", f"đề xuất {B1}"))
    m.say("Lan", f"Về {t2.lower()}, mình đề xuất {A2}.", L("propose", "A", f"đề xuất {A2}", topic="T2"))
    m.say(d1, f"Với {t1.lower()}, mình không đồng ý {B1}, rủi ro lớn.", L("oppose", "B", f"không đồng ý {B1}"))
    m.say(auth, f"Mình hiểu, nhưng chốt {B1} nhé.", L("conclude", "B", f"chốt {B1}"))
    m.say(d1, f"Về {t2.lower()}, {A2} nghe được đó.", L("support", "A", f"{A2} nghe được", topic="T2"))
    m.say(d1, "Ok, mình vẫn lo nhưng sẽ làm theo.", L("support", "B", "sẽ làm theo"))
    m.say("Hà", f"Còn {t2.lower()} thì mình ghi nhận, chưa chốt.", L("info", None, "chưa chốt", topic="T2"))
    m.gold["topics"] += [
        {"keywords": [A1, B1], "status": "decided", "final_option_keywords": [B1]},
        {"keywords": [A2, B2], "status": ["leaning", "open"], "not_final_keywords": [A2, B2]}]
    return m, "hai chủ đề đan xen: một chốt (phản đối đã được giải quyết), một chưa chốt"


SCENARIOS = [
    (sc_ab_switch, "technical"), (sc_late_confirm, "design"), (sc_consensus_ok, None), (sc_consensus_short, None),
    (sc_unknown_speaker, None), (sc_conditional, "budget"), (sc_reversal_no_new, "scope"), (sc_deferred, "technical"),
    (sc_unresolved_objection, "technical"), (sc_task_matrix, None), (sc_task_dates, None), (sc_interleaved, None),
]


def main():
    for k, (fn, cat) in enumerate(SCENARIOS, start=1):
        rng = random.Random(1000 + k)
        m, diff = fn(rng, k, cat)
        m.write(diff)
        print(f"g{k:02d}: {diff}")


if __name__ == "__main__":
    main()
