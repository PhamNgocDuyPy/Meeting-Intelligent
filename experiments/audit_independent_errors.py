import sys
import json
from collections import Counter
from math import comb

sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

data = json.load(open('outputs/independent_sentences_60_results.json', encoding='utf-8'))
details = data['details']

print("======================================================================")
print("RÀ SOÁT TỔNG THỂ 15 CA LỖI TRÊN TẬP 60 CÂU ĐỘC LẬP (AUDIT REPORT)")
print("======================================================================")

print("\n--- 1. JEV FALSE NEGATIVE (1 ca) ---")
for d in details:
    if d['is_conditional'] and not d['jev_flagged']:
        print(f"[{d['id']}] Jev p={d['jev_p']:.2f} | Gemini p={d['gem_p']:.2f} (Gem flag={d['gem_flagged']})")
        print(f"  Văn bản: \"{d['text']}\"")
        print(f"  Phân loại: {d['category']} | Giải thích gold: {d['rationale']}")

print("\n--- 2. JEV FALSE POSITIVES (3 ca) ---")
for d in details:
    if not d['is_conditional'] and d['jev_flagged']:
        print(f"[{d['id']}] Jev p={d['jev_p']:.2f} | Gemini p={d['gem_p']:.2f} (Gem flag={d['gem_flagged']})")
        print(f"  Văn bản: \"{d['text']}\"")
        print(f"  Phân loại: {d['category']} | Giải thích gold: {d['rationale']}")

print("\n--- 3. GEMINI FALSE POSITIVES (11 ca) ---")
for d in details:
    if not d['is_conditional'] and d['gem_flagged']:
        print(f"[{d['id']}] Gemini p={d['gem_p']:.2f} | Jev p={d['jev_p']:.2f} (Jev flag={d['jev_flagged']})")
        print(f"  Văn bản: \"{d['text']}\"")
        print(f"  Phân loại: {d['category']} | Giải thích gold: {d['rationale']}")

print("\n--- 4. GEMINI FALSE NEGATIVES (2 ca) ---")
for d in details:
    if d['is_conditional'] and not d['gem_flagged']:
        print(f"[{d['id']}] Gemini p={d['gem_p']:.2f} | Jev p={d['jev_p']:.2f} (Jev flag={d['jev_flagged']})")
        print(f"  Văn bản: \"{d['text']}\"")
        print(f"  Phân loại: {d['category']} | Giải thích gold: {d['rationale']}")

print("\n--- 5. KIỂM TRA TRÙNG LẶP / GẦN GIỐNG TRONG 60 CÂU ---")
texts = [d['text'] for d in details]
duplicates = [t for t, c in Counter(texts).items() if c > 1]
print(f"Số câu trùng lặp nguyên văn (exact duplicate): {len(duplicates)}")

# Jaccard similarity between all pairs to find near duplicates
near_dups = []
for i in range(len(details)):
    w1 = set(details[i]['text'].lower().split())
    for j in range(i + 1, len(details)):
        w2 = set(details[j]['text'].lower().split())
        jaccard = len(w1 & w2) / len(w1 | w2)
        if jaccard > 0.65:
            near_dups.append((details[i]['id'], details[j]['id'], jaccard, details[i]['text'], details[j]['text']))

print(f"Số cặp câu gần giống nhau (Jaccard > 0.65): {len(near_dups)}")
for id1, id2, sim, t1, t2 in near_dups:
    print(f"  * {id1} <-> {id2} (sim={sim:.2f}):\n    1: {t1}\n    2: {t2}")

print("\n--- 6. KIỂM ĐỊNH MCNEMAR GHÉP CẶP CHÍNH XÁC (EXACT PAIRED TEST) ---")
# McNemar on overall Accuracy (60 sentences)
# b: Jev correct & Gemini wrong
# c: Gemini correct & Jev wrong
a = sum(1 for d in details if d['jev_correct'] and d['gem_correct'])
b = sum(1 for d in details if d['jev_correct'] and not d['gem_correct'])
c = sum(1 for d in details if not d['jev_correct'] and d['gem_correct'])
d = sum(1 for d in details if not d['jev_correct'] and not d['gem_correct'])

print(f"Bảng tiếp liên 2x2 Tổng thể (Accuracy, N=60):")
print(f"  Cả 2 cùng đúng (a): {a}")
print(f"  Jev đúng, Gemini sai (b): {b}")
print(f"  Gemini đúng, Jev sai (c): {c}")
print(f"  Cả 2 cùng sai (d): {d}")

# Exact two-sided binomial p-value for McNemar
n_discordant = b + c
if n_discordant > 0:
    # 2 * sum(comb(n, k) * 0.5^n for k <= min(b, c))
    k_min = min(b, c)
    p_val_acc = 2 * sum(comb(n_discordant, k) * (0.5 ** n_discordant) for k in range(k_min + 1))
    p_val_acc = min(p_val_acc, 1.0)
    print(f"  -> McNemar Exact Test (Accuracy): b={b}, c={c}, Discordant={n_discordant}, p-value = {p_val_acc:.4f}")

# McNemar specifically on Unconditional sentences (FPR comparison, N=30)
neg_details = [d for d in details if not d['is_conditional']]
a_neg = sum(1 for d in neg_details if d['jev_correct'] and d['gem_correct'])
b_neg = sum(1 for d in neg_details if d['jev_correct'] and not d['gem_correct'])
c_neg = sum(1 for d in neg_details if not d['jev_correct'] and d['gem_correct'])
d_neg = sum(1 for d in neg_details if not d['jev_correct'] and not d['gem_correct'])

print(f"\nBảng tiếp liên 2x2 trên nhóm Không Điều kiện (FPR, N=30):")
print(f"  Cả 2 cùng không cắm cờ (a_neg): {a_neg}")
print(f"  Jev không cắm (đúng), Gemini cắm cờ (sai) (b_neg): {b_neg}")
print(f"  Gemini không cắm (đúng), Jev cắm cờ (sai) (c_neg): {c_neg}")
print(f"  Cả 2 cùng cắm cờ nhầm (d_neg): {d_neg}")

n_disc_neg = b_neg + c_neg
if n_disc_neg > 0:
    k_min_neg = min(b_neg, c_neg)
    p_val_fpr = 2 * sum(comb(n_disc_neg, k) * (0.5 ** n_disc_neg) for k in range(k_min_neg + 1))
    p_val_fpr = min(p_val_fpr, 1.0)
    print(f"  -> McNemar Exact Test (FPR): b={b_neg}, c={c_neg}, Discordant={n_disc_neg}, p-value = {p_val_fpr:.4f}")

print("\n--- 7. ĐỘ NHẠY VỚI NGƯỠNG (THRESHOLD SWEEP 0.3 -> 0.7) & AUC ---")
from math import sqrt

def evaluate_threshold(probs, labels, thresh):
    tp = sum(1 for p, y in zip(probs, labels) if p >= thresh and y)
    fp = sum(1 for p, y in zip(probs, labels) if p >= thresh and not y)
    tn = sum(1 for p, y in zip(probs, labels) if p < thresh and not y)
    fn = sum(1 for p, y in zip(probs, labels) if p < thresh and y)
    n_pos = sum(1 for y in labels if y)
    n_neg = sum(1 for y in labels if not y)
    rec = tp / n_pos if n_pos else 0
    fpr = fp / n_neg if n_neg else 0
    acc = (tp + tn) / len(labels)
    return rec, fpr, acc

y_true = [d['is_conditional'] for d in details]
jev_scores = [d['jev_p'] for d in details]
gem_scores = [d['gem_p'] for d in details]

print(f"{'Ngưỡng':<8} | {'Jev Rec':<9} | {'Jev FPR':<9} | {'Jev Acc':<9} | {'Gem Rec':<9} | {'Gem FPR':<9} | {'Gem Acc':<9}")
print("-" * 72)
for th in [0.30, 0.40, 0.50, 0.60, 0.70]:
    j_rec, j_fpr, j_acc = evaluate_threshold(jev_scores, y_true, th)
    g_rec, g_fpr, g_acc = evaluate_threshold(gem_scores, y_true, th)
    print(f"{th:<8.2f} | {j_rec*100:<8.1f}% | {j_fpr*100:<8.1f}% | {j_acc*100:<8.1f}% | {g_rec*100:<8.1f}% | {g_fpr*100:<8.1f}% | {g_acc*100:<8.1f}%")

# Compute ROC-AUC (Wilcoxon-Mann-Whitney U statistic)
def compute_auc(scores, labels):
    pos = [s for s, y in zip(scores, labels) if y]
    neg = [s for s, y in zip(scores, labels) if not y]
    u = 0
    for p in pos:
        for n in neg:
            if p > n:
                u += 1.0
            elif p == n:
                u += 0.5
    return u / (len(pos) * len(neg))

jev_auc = compute_auc(jev_scores, y_true)
gem_auc = compute_auc(gem_scores, y_true)
print(f"\nROC-AUC:")
print(f"  Jev System One ROC-AUC: {jev_auc:.4f}")
print(f"  Gemini (gemini-3.1-flash-lite) ROC-AUC: {gem_auc:.4f}")
