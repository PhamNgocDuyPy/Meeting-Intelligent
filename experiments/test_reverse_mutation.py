import sys, json
sys.stdout.reconfigure(encoding='utf-8')
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.schema import LabelerOutput
from src.parser import parse_transcript
from src.context import load_context
from src.assemble import validate_labels
from src.rules import evaluate_all
from src.judge import judge_topic, apply_judge

print("==================================================")
print("TEST ĐỘT BIẾN NGƯỢC: LLM BỎ SÓT CỜ CONDITIONAL")
print("==================================================")

for mid in ['m05', 'g06']:
    m_dir = ROOT / f"data/meetings/{mid}"
    raw = json.loads((m_dir / "labels_oracle.json").read_text(encoding="utf-8"))
    out = LabelerOutput.model_validate(raw)
    
    # Đột biến ngược: Xóa cờ conditional khỏi nhãn (giả lập LLM bỏ sót điều kiện)
    for lb in out.labels:
        lb.conditional = False
        lb.condition_text = None
            
    utts = parse_transcript(m_dir / "transcript.txt")
    by_id = {u.id: u for u in utts}
    ctx = load_context(ROOT, m_dir)
    labels, _ = validate_labels(out, by_id)
    
    # 1. Chạy luật thuần (không có Jev)
    topics_none = evaluate_all(out.topics, labels, by_id, ctx)
    t_none = topics_none[0]
    
    # 2. Chạy với Jev
    topics_jev = evaluate_all(out.topics, labels, by_id, ctx)
    t_jev = topics_jev[0]
    verdict = judge_topic("jev", t_jev, utts, ctx)
    apply_judge(t_jev, verdict)
    
    print(f"\n--- Meeting {mid} ---")
    print(f"Luật thuần (không Jev): status = '{t_none.status}' -> {'LỖI NGHIÊM TRỌNG: Chốt nhầm' if t_none.status == 'decided' else 'An toàn'}")
    print(f"Có Jev System One:     status = '{t_jev.status}' -> {'CỨU THÀNH CÔNG: Hạ về leaning' if t_jev.status == 'leaning' else 'Không cứu được'}")
    print(f"Jev conditional check:  p = {verdict.conditional.p:.3f}, answer = {verdict.conditional.answer}")
