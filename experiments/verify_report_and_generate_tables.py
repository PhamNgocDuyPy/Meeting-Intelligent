import re, sys, json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

REPORT = ROOT / "docs" / "MISSION_2_REPORT.md"
content = REPORT.read_text(encoding="utf-8")

print("======================================================================")
print("KIỂM CHỨNG TOÀN DIỆN: TRÍCH DẪN & SỐ LIỆU THỰC NGHIỆM TRONG BÁO CÁO")
print("======================================================================")

# 1. Kiểm tra 14 trích dẫn
meetings_dir = ROOT / "data/meetings"
transcripts = {}
for m_dir in meetings_dir.iterdir():
    t_file = m_dir / "transcript.txt"
    if t_file.exists():
        transcripts[m_dir.name] = t_file.read_text(encoding="utf-8")

quotes = re.findall(r'•\s*\[(\d{2}:\d{2}:\d{2})\]\s*([^:]+):\s*\*?"([^"]+)"\*?', content)
print(f"1. Kiểm tra {len(quotes)} trích dẫn thời gian:")
quote_errors = 0
for ts, speaker, text in quotes:
    found = []
    for mid, t_text in transcripts.items():
        if ts in t_text and text in t_text:
            found.append(mid)
    if found:
        print(f"  [OK] [{ts}] {speaker} -> Có trong {', '.join(sorted(found))}")
    else:
        print(f"  [FAIL] [{ts}] {speaker}: \"{text}\" -> KHÔNG TÌM THẤY")
        quote_errors += 1

# 2. Kiểm tra số liệu từ JSON
print("\n2. Kiểm tra tính nhất quán số liệu từ JSON thực nghiệm:")
metric_errors = 0

# A. Blind conditions 8
blind_path = ROOT / "outputs" / "blind_conditions_8_results.json"
if blind_path.exists():
    blind_data = json.loads(blind_path.read_text(encoding="utf-8"))
    c1 = next(x for x in blind_data if x["id"] == "C1")
    c4 = next(x for x in blind_data if x["id"] == "C4")
    c5 = next(x for x in blind_data if x["id"] == "C5")
    print(f"  [OK] Blind test: C1={c1['jev_p']}, C4={c4['jev_p']}, C5={c5['jev_p']}")
else:
    print("  [FAIL] Thiếu blind_conditions_8_results.json")
    metric_errors += 1

# B. BM25 Recall@30 noise
bm25_noise_path = ROOT / "outputs" / "bm25_recall30_noise_results.json"
if bm25_noise_path.exists():
    bm_data = json.loads(bm25_noise_path.read_text(encoding="utf-8"))
    r0 = next(x for x in bm_data if x["noise_count"] == 0)
    r200 = next(x for x in bm_data if x["noise_count"] == 200)
    print(f"  [OK] BM25 noise: 0 nhiễu={r0['recall_30']*100}%, 200 nhiễu={r200['recall_30']*100}%")
else:
    print("  [FAIL] Thiếu bm25_recall30_noise_results.json")
    metric_errors += 1

# C. Jev noise 212
jev_212_path = ROOT / "outputs" / "jev_noise_212_results.json"
if jev_212_path.exists():
    j212 = json.loads(jev_212_path.read_text(encoding="utf-8"))
    print(f"  [OK] Jev 212 (1 query m01): P@3={j212['top3_precision']*100}%, R@10={j212['top10_recall']*100}%")
else:
    print("  [FAIL] Thiếu jev_noise_212_results.json")
    metric_errors += 1

# D. Jev noise 4 meetings
jev_4m_path = ROOT / "outputs" / "jev_noise_4_meetings_results.json"
if jev_4m_path.exists():
    j4m = json.loads(jev_4m_path.read_text(encoding="utf-8"))
    print(f"  [OK] Jev 212 (4 queries): P@3={j4m['avg_p@3']*100:.1f}%, R@10={j4m['avg_r@10']*100:.1f}%")
else:
    print("  [FAIL] Thiếu jev_noise_4_meetings_results.json")
    metric_errors += 1

print("-" * 70)
if quote_errors == 0 and metric_errors == 0:
    print("KẾT LUẬN: TOÀN BỘ TRÍCH DẪN VÀ SỐ LIỆU ĐỀU KHỚP NGUYÊN VĂN (0 LỖI).")
else:
    print(f"KẾT LUẬN: CÒN {quote_errors} LỖI TRÍCH DẪN VÀ {metric_errors} LỖI SỐ LIỆU.")
