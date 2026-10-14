import re, sys
sys.stdout.reconfigure(encoding='utf-8')
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
report_path = ROOT / "docs/MISSION_2_REPORT.md"
content = report_path.read_text(encoding="utf-8")

# Tìm các đoạn dạng [00:00:20] Tên... hoặc `m01`...
# Tìm tất cả các pattern [hh:mm:ss]
quotes = re.findall(r"(\[0\d:\d\d:\d\d\]\s*[^:\n]+:\s*[^.\n]+)", content)
print(f"Tìm thấy {len(quotes)} trích dẫn thời gian trong báo cáo:")

all_transcripts = {}
for p in (ROOT / "data/meetings").glob("*/transcript.txt"):
    all_transcripts[p.parent.name] = p.read_text(encoding="utf-8")

errors = 0
for q in quotes:
    # Lấy timestamp
    ts_match = re.search(r"\[(\d\d:\d\d:\d\d)\]\s*([^:]+):\s*(.*)", q)
    if not ts_match:
        continue
    ts, speaker, text = ts_match.groups()
    speaker = speaker.strip()
    
    # Tìm xem có trong transcript nào không
    found_in = []
    for mid, t_text in all_transcripts.items():
        if f"[{ts}]" in t_text and speaker in t_text:
            found_in.append(mid)
            
    if found_in:
        print(f"  [OK] [{ts}] {speaker} -> Có trong {', '.join(found_in)}")
    else:
        print(f"  [LỖI] Không tìm thấy [{ts}] {speaker} trong bất kỳ transcript nào!")
        errors += 1

print(f"\nTổng kết: {len(quotes) - errors}/{len(quotes)} trích dẫn hợp lệ. Số lỗi: {errors}")
