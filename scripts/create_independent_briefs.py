import yaml
import json
import hashlib
from pathlib import Path

BASE = Path("data/independent_tests/meetings")

BRIEFS = {
    "indep_m01": {
        "id": "indep_m01",
        "title": "Họp lựa chọn CSDL cho dự án mới",
        "date": "2026-10-15",
        "project": "nova",
        "purpose": "Quyết định công nghệ CSDL cho dự án mới",
        "agenda": ["Đánh giá MongoDB vs MySQL", "Chốt CSDL chính", "Phân công dựng DB staging"],
        "attendees": ["hoang", "son", "tuan", "binh", "mai"]
    },
    "indep_m02": {
        "id": "indep_m02",
        "title": "Họp ngân sách tài trợ Marketing Q4",
        "date": "2026-10-16",
        "project": "nova",
        "purpose": "Quyết định gói tài trợ Marketing Q4",
        "agenda": ["Đánh giá gói tài trợ 200 triệu", "Xác nhận điều kiện phê duyệt BOD"],
        "attendees": ["huong", "long", "trang"]
    },
    "indep_m03": {
        "id": "indep_m03",
        "title": "Họp sprint planning và phân công sửa lỗi",
        "date": "2026-10-17",
        "project": "nova",
        "purpose": "Phân công nhiệm vụ sprint và ghi nhận góp ý giao diện",
        "agenda": ["Phân công fix bug payment gateway", "Góp ý UI"],
        "attendees": ["dung", "thang", "linh"]
    },
    "indep_m04": {
        "id": "indep_m04",
        "title": "Họp rà soát phạm vi màn hình Onboarding",
        "date": "2026-10-18",
        "project": "nova",
        "purpose": "Thống nhất phạm vi màn hình Onboarding",
        "agenda": ["Thảo luận loại bỏ màn onboarding", "Quyết định giữ lại màn onboarding"],
        "attendees": ["viet_pm", "an", "huy_des"]
    },
    "indep_m05": {
        "id": "indep_m05",
        "title": "Họp chốt phạm vi tính năng MVP",
        "date": "2026-10-19",
        "project": "nova",
        "purpose": "Chốt tính năng release MVP và hoãn tính năng trả góp",
        "agenda": ["Cắt giảm tính năng trả góp sang Phase 2", "Chốt thanh toán QR cho MVP"],
        "attendees": ["viet_ho", "dung", "nga"]
    },
    "indep_m06": {
        "id": "indep_m06",
        "title": "Họp khẩn cấp xử lý sự cố tràn bộ nhớ release v1.4",
        "date": "2026-10-20",
        "project": "nova",
        "purpose": "Xử lý sự cố tràn bộ nhớ và rollback phiên bản",
        "agenda": ["Rollback về bản v1.3", "Phân công theo dõi metrics và điều tra root-cause"],
        "attendees": ["bach", "quang", "thanh"]
    }
}

for m_id, b_data in BRIEFS.items():
    m_dir = BASE / m_id
    b_file = m_dir / "brief.yaml"
    b_file.write_text(yaml.dump(b_data, allow_unicode=True, sort_keys=False), encoding="utf-8")
    print(f"Written {b_file}")

# Update MANIFEST.json
hashes = {}
for p in sorted(BASE.glob("**/*")):
    if p.is_file() and p.name != "MANIFEST.json":
        rel = str(p.relative_to(BASE)).replace("\\", "/")
        hashes[rel] = hashlib.sha256(p.read_bytes()).hexdigest()

manifest_file = BASE / "MANIFEST.json"
manifest_file.write_text(json.dumps(hashes, indent=2, ensure_ascii=False), encoding="utf-8")
print(f"Updated Manifest with {len(hashes)} files at {manifest_file}")
