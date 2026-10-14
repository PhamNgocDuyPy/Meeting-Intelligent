/**
 * Meeting Intel · Web UI Application Logic
 * Phong cách Monkeytype: tối giản, mượt mà, phân loại ngữ nghĩa thuận/nghịch.
 */

// Các từ khóa tương quan thuận (ủng hộ, chốt, khả thi) -> Màu xanh dịu
const POSITIVE_KEYWORDS = [
  "chốt", "đồng ý", "ủng hộ", "hợp lý", "làm theo", "triển khai", "làm được",
  "thống nhất", "quyết định cuối", "xác nhận", "tự nhận", "phê duyệt", "chọn",
  "đồng thuận", "nhất trí", "hoàn tất"
];

// Các từ khóa tương quan nghịch (phản đối, mâu thuẫn, rút lại) -> Màu đỏ san hô
const NEGATIVE_KEYWORDS = [
  "không đồng ý", "phản đối", "rủi ro lớn", "rủi ro", "tốn kém", "bỏ", "lùi lịch",
  "hủy", "không scale", "vendor lock-in", "mất phí", "không chấp nhận", "chưa duyệt",
  "chưa thống nhất", "bất đồng", "lo lắng", "vẫn lo"
];

// Các từ khóa điều kiện / thận trọng -> Màu vàng hổ phách
const WARN_KEYWORDS = [
  "nếu", "phụ thuộc", "điều kiện", "feature flag", "chưa chắc chắn", "tạm thời",
  "chờ", "xem xét lại", "chưa rõ", "hoãn"
];

let state = {
  meetings: [],
  currentMeetingId: "m01",
  meetingData: null,
  activeFilter: "all",
  searchQuery: "",
  reviews: {}, // item_id -> 'approved' | 'rejected' | 'edited'
};

function getAccessCode() {
  const modalEl = document.getElementById("inp-modal-access-code");
  const headerEl = document.getElementById("access-code-input");
  return (modalEl && modalEl.value.trim()) || (headerEl && headerEl.value.trim()) || (localStorage.getItem("meeting_intel_access_code") || "");
}

function setAccessCode(val) {
  const trimmed = (val || "").trim();
  localStorage.setItem("meeting_intel_access_code", trimmed);
  const headerEl = document.getElementById("access-code-input");
  const modalEl = document.getElementById("inp-modal-access-code");
  if (headerEl && headerEl.value !== trimmed) headerEl.value = trimmed;
  if (modalEl && modalEl.value !== trimmed) modalEl.value = trimmed;
}

function getAuthHeaders(extraHeaders = {}) {
  const code = getAccessCode();
  const headers = { ...extraHeaders };
  if (code) {
    headers["X-Access-Code"] = code;
  }
  return headers;
}

document.addEventListener("DOMContentLoaded", () => {
  initApp();
});

async function initApp() {
  const savedCode = localStorage.getItem("meeting_intel_access_code") || "";
  const headerEl = document.getElementById("access-code-input");
  const modalEl = document.getElementById("inp-modal-access-code");
  if (headerEl) {
    headerEl.value = savedCode;
    headerEl.addEventListener("input", (e) => setAccessCode(e.target.value));
  }
  if (modalEl) {
    modalEl.value = savedCode;
    modalEl.addEventListener("input", (e) => setAccessCode(e.target.value));
  }

  setupEventListeners();
  await fetchMeetingList();
  if (state.meetings.length > 0) {
    const defaultMid = state.meetings.find(m => m.id === "m01") ? "m01" : state.meetings[0].id;
    await loadMeeting(defaultMid);
  }
}

function setupEventListeners() {
  const select = document.getElementById("meeting-select");
  select.addEventListener("change", (e) => {
    loadMeeting(e.target.value);
  });

  const searchInput = document.getElementById("search-input");
  searchInput.addEventListener("input", (e) => {
    state.searchQuery = e.target.value.trim().toLowerCase();
    renderInspector();
    highlightSearchInTranscript();
  });

  // Phím tắt / hoặc Ctrl+K để focus tìm kiếm
  window.addEventListener("keydown", (e) => {
    if ((e.ctrlKey && e.key.toLowerCase() === "k") || (e.key === "/" && document.activeElement !== searchInput)) {
      e.preventDefault();
      searchInput.focus();
    }
  });

  // Filter tabs
  const tabGroup = document.getElementById("filter-tabs");
  tabGroup.addEventListener("click", (e) => {
    const btn = e.target.closest(".tab-btn");
    if (!btn) return;
    document.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
    btn.classList.add("active");
    state.activeFilter = btn.dataset.filter;
    renderInspector();
  });

  // Export buttons
  document.getElementById("btn-export-md").addEventListener("click", () => exportData("markdown"));
  document.getElementById("btn-export-csv").addEventListener("click", () => exportData("csv"));
  document.getElementById("btn-re-eval").addEventListener("click", () => {
    showToast("Đang kích hoạt Jev 1.13 phân xử...");
    loadMeeting(state.currentMeetingId);
  });

  document.getElementById("btn-batch-approve").addEventListener("click", () => {
    batchApproveSafeItems();
  });

  // Upload modal handlers
  const uploadModal = document.getElementById("upload-modal");
  const btnOpenModal = document.getElementById("btn-open-modal");
  const btnCloseModal = document.getElementById("btn-close-modal");
  const btnCancelModal = document.getElementById("btn-cancel-modal");
  const selMode = document.getElementById("sel-mode");
  const leaderGroup = document.getElementById("leader-group");
  const inpFile = document.getElementById("inp-file");
  const btnSubmitUpload = document.getElementById("btn-submit-upload");

  if (btnOpenModal) {
    btnOpenModal.addEventListener("click", () => {
      uploadModal.classList.remove("hidden");
    });
  }

  if (btnCloseModal) {
    btnCloseModal.addEventListener("click", () => {
      uploadModal.classList.add("hidden");
    });
  }

  if (btnCancelModal) {
    btnCancelModal.addEventListener("click", () => {
      uploadModal.classList.add("hidden");
    });
  }

  if (selMode) {
    selMode.addEventListener("change", (e) => {
      leaderGroup.style.display = e.target.value === "authority" ? "block" : "none";
    });
  }

  const inpTranscript = document.getElementById("inp-transcript");
  if (inpTranscript) {
    inpTranscript.addEventListener("input", () => updateSpeakerRolesList());
    inpTranscript.addEventListener("change", () => updateSpeakerRolesList());
  }

  if (inpFile) {
    inpFile.addEventListener("change", (e) => {
      const file = e.target.files[0];
      if (!file) return;
      const reader = new FileReader();
      reader.onload = (ev) => {
        document.getElementById("inp-transcript").value = ev.target.result;
        updateSpeakerRolesList();
        showToast(`Đã nạp file ${file.name}`);
      };
      reader.readAsText(file, "UTF-8");
    });
  }

  if (btnOpenModal) {
    btnOpenModal.addEventListener("click", () => {
      uploadModal.classList.remove("hidden");
      updateSpeakerRolesList();
    });
  }

  if (btnSubmitUpload) {
    btnSubmitUpload.addEventListener("click", async () => {
      const title = document.getElementById("inp-title").value.trim() || "Cuộc họp mới";
      const transcript = document.getElementById("inp-transcript").value.trim();

      if (!transcript) {
        showToast("Vui lòng nhập hoặc chọn file lời thoại.");
        return;
      }

      // Thu thập vai trò của từng người nói (chỉ dùng cho lần chạy này, không ghi file)
      const roles = {};
      document.querySelectorAll(".speaker-role-select").forEach(sel => {
        roles[sel.dataset.speaker] = sel.value;
      });

      btnSubmitUpload.disabled = true;
      btnSubmitUpload.textContent = "đang phân tích...";

      try {
        const res = await fetch("/api/upload", {
          method: "POST",
          headers: getAuthHeaders({ "Content-Type": "application/json" }),
          body: JSON.stringify({ title, transcript, roles, access_code: getAccessCode() })
        });

        if (res.status === 401) {
          showToast("Mã truy cập không hợp lệ (401). Vui lòng nhập đúng ACCESS_CODE.");
          const modalEl = document.getElementById("inp-modal-access-code");
          if (modalEl) {
            modalEl.focus();
            modalEl.style.borderColor = "#ef4444";
          }
          btnSubmitUpload.disabled = false;
          btnSubmitUpload.textContent = "phân tích ngay";
          return;
        }

        const data = await res.json();
        if (data.error) {
          showToast("Lỗi: " + data.error);
          btnSubmitUpload.disabled = false;
          btnSubmitUpload.textContent = "phân tích ngay";
          return;
        }

        uploadModal.classList.add("hidden");
        btnSubmitUpload.disabled = false;
        btnSubmitUpload.textContent = "phân tích ngay";

        await fetchMeetingList();
        if (data.new_meeting_id) {
          state.currentMeetingId = data.new_meeting_id;
          document.getElementById("meeting-select").value = data.new_meeting_id;
          state.meetingData = data;
          renderTranscript();
          renderInspector();
          updateSummaryStats();
          showToast(`Đã phân tích thành công [${data.new_meeting_id}]!`);
        }
      } catch (err) {
        showToast("Lỗi kết nối máy chủ: " + err.message);
        btnSubmitUpload.disabled = false;
        btnSubmitUpload.textContent = "phân tích ngay";
      }
    });
  }
}

function extractSpeakers(text) {
  const lines = text.split("\n");
  const speakers = new Set();
  const pattern = /^(?:\[[\d:.]+\]\s*)?([A-ZÀ-Ỵa-zà-ỹ0-9_.\- ]+?)\s*[:：]/;
  for (const line of lines) {
    const match = line.trim().match(pattern);
    if (match && match[1]) {
      const name = match[1].trim();
      if (name && name.length <= 40 && !name.toLowerCase().startsWith("http")) {
        speakers.add(name);
      }
    }
  }
  return Array.from(speakers);
}

function updateSpeakerRolesList() {
  const transcriptEl = document.getElementById("inp-transcript");
  const listEl = document.getElementById("speaker-roles-list");
  if (!transcriptEl || !listEl) return;
  const speakers = extractSpeakers(transcriptEl.value);
  if (!speakers.length) {
    listEl.innerHTML = `<span class="roles-empty-hint">Nhập hoặc dán transcript ở trên để tự động nhận diện người nói...</span>`;
    return;
  }
  // Giữ lại vai trò đã chọn trước đó nếu có
  const prev = {};
  listEl.querySelectorAll(".speaker-role-select").forEach(sel => {
    prev[sel.dataset.speaker] = sel.value;
  });

  listEl.innerHTML = speakers.map(spk => {
    const cur = prev[spk] || "member";
    return `
      <div class="speaker-role-row">
        <span class="speaker-name">${escapeHtml(spk)}</span>
        <select class="speaker-role-select" data-speaker="${escapeHtml(spk)}">
          <option value="member" ${cur === "member" ? "selected" : ""}>Thành viên (mặc định - không quyền chốt)</option>
          <option value="pm" ${cur === "pm" ? "selected" : ""}>PM (Quản lý sản phẩm - chốt Scope)</option>
          <option value="tech_lead" ${cur === "tech_lead" ? "selected" : ""}>Tech Lead (Trưởng nhóm kỹ thuật - chốt Technical)</option>
          <option value="design_lead" ${cur === "design_lead" ? "selected" : ""}>Design Lead (Trưởng nhóm thiết kế - chốt Design)</option>
          <option value="head_of_product" ${cur === "head_of_product" ? "selected" : ""}>Head of Product (GĐ sản phẩm - chốt Scope/Design/Release/Budget)</option>
          <option value="finance" ${cur === "finance" ? "selected" : ""}>Tài chính (chốt Budget)</option>
        </select>
      </div>
    `;
  }).join("");
}

async function fetchMeetingList() {
  try {
    const res = await fetch("/api/meetings");
    const data = await res.json();
    state.meetings = data.meetings || [];

    const select = document.getElementById("meeting-select");
    if (!select) return;

    const categories = [
      { key: "base", label: "Bộ kiểm thử cơ sở (Base · m01–m08)" },
      { key: "edge", label: "Bộ tình huống ranh giới (Edge Cases · g01–g12)" },
      { key: "independent", label: "Bộ kiểm thử độc lập (Blind / Independent · 6 ca)" },
      { key: "custom", label: "Cuộc họp tùy biến người dùng nạp" }
    ];

    let html = "";
    categories.forEach(cat => {
      const groupMeetings = state.meetings.filter(m => m.category === cat.key);
      if (groupMeetings.length > 0) {
        html += `<optgroup label="${escapeHtml(cat.label)}">`;
        groupMeetings.forEach(m => {
          let title = m.title || m.id;
          let diff = m.difficulty ? ` [${m.difficulty}]` : "";
          if (diff.length > 40) diff = diff.slice(0, 37) + "...]";
          html += `<option value="${m.id}">${m.id} · ${escapeHtml(title)}${escapeHtml(diff)}</option>`;
        });
        html += `</optgroup>`;
      }
    });

    select.innerHTML = html;
  } catch (err) {
    console.error("Lỗi tải danh sách cuộc họp:", err);
    showToast("Lỗi tải danh sách cuộc họp");
  }
}

async function loadMeeting(mid) {
  state.currentMeetingId = mid;
  const select = document.getElementById("meeting-select");
  if (select) select.value = mid;

  document.getElementById("transcript-feed").innerHTML = `<div class="loading-state">đang tải lời thoại ${mid}...</div>`;
  document.getElementById("inspector-content").innerHTML = `<div class="loading-state">đang phân tích dữ liệu cuộc họp...</div>`;

  try {
    const res = await fetch(`/api/meeting/${mid}?oracle=0&judge=jev&backend=gemini`, {
      headers: getAuthHeaders()
    });

    if (res.status === 401) {
      showToast("Yêu cầu mã truy cập hợp lệ (401). Vui lòng nhập ACCESS_CODE.");
      document.getElementById("transcript-feed").innerHTML = `<div class="loading-state">Vui lòng nhập đúng ACCESS_CODE trên thanh điều khiển để xem cuộc họp.</div>`;
      document.getElementById("inspector-content").innerHTML = `<div class="loading-state">Chưa được cấp quyền truy cập (401 Unauthorized).</div>`;
      return;
    }

    const data = await res.json();
    if (data.error) {
      showToast("Lỗi: " + data.error);
      return;
    }
    state.meetingData = data;

    renderTranscript();
    renderInspector();
    updateSummaryStats();
  } catch (err) {
    console.error("Lỗi nạp dữ liệu cuộc họp:", err);
    showToast("Lỗi nạp cuộc họp: " + err.message);
    document.getElementById("transcript-feed").innerHTML = `<div class="loading-state">Không thể tải dữ liệu cuộc họp (${escapeHtml(err.message)}). Vui lòng thử lại.</div>`;
    document.getElementById("inspector-content").innerHTML = `<div class="loading-state">Lỗi kết nối máy chủ.</div>`;
  }
}

/* ==========================================================================
   RENDER TRANSCRIPT & SEMANTIC HIGHLIGHTING
   ========================================================================== */
function renderTranscript() {
  const feed = document.getElementById("transcript-feed");
  const utts = state.meetingData.transcript || [];

  document.getElementById("utt-count").textContent = `${utts.length} phát biểu`;

  if (!utts.length) {
    feed.innerHTML = `<div class="loading-state">không có lời thoại nào.</div>`;
    return;
  }

  feed.innerHTML = utts.map(u => {
    const highlightedText = highlightKeywords(u.text);
    return `
      <div class="utterance-card" id="utt-${u.id}" data-uid="${u.id}">
        <div class="utt-meta">
          <span class="utt-ts">[${u.ts_label || "--:--:--"}]</span>
          <span class="utt-speaker">${escapeHtml(u.speaker)}</span>
          <span class="utt-id">${u.id}</span>
        </div>
        <div class="utt-text">${highlightedText}</div>
      </div>
    `;
  }).join("");

  // Bấm vào utterance để hiển thị liên kết
  feed.querySelectorAll(".utterance-card").forEach(card => {
    card.addEventListener("click", () => {
      clearHighlights();
      card.classList.add("highlighted");
    });
  });
}

function highlightKeywords(text) {
  let escaped = escapeHtml(text);

  // Tô màu các từ khóa tương quan thuận (xanh)
  POSITIVE_KEYWORDS.forEach(kw => {
    const regex = new RegExp(`(${escapeRegex(kw)})`, "gi");
    escaped = escaped.replace(regex, `<span class="w-pos">$1</span>`);
  });

  // Tô màu các từ khóa tương quan nghịch (đỏ)
  NEGATIVE_KEYWORDS.forEach(kw => {
    const regex = new RegExp(`(${escapeRegex(kw)})`, "gi");
    escaped = escaped.replace(regex, `<span class="w-neg">$1</span>`);
  });

  // Tô màu các từ khóa điều kiện (amber)
  WARN_KEYWORDS.forEach(kw => {
    const regex = new RegExp(`(${escapeRegex(kw)})`, "gi");
    escaped = escaped.replace(regex, `<span class="w-warn">$1</span>`);
  });

  return escaped;
}

/* ==========================================================================
   RENDER INSPECTOR & DECISIONS
   ========================================================================== */
function renderInspector() {
  const container = document.getElementById("inspector-content");
  if (!state.meetingData) return;

  const { topics = [], items = [], review_queue = [] } = state.meetingData;

  // Lọc theo filter tab & search query
  let filteredTopics = topics.filter(t => matchesFilter(t, "topic") && matchesSearch(t.title + " " + (t.final_option || "")));
  let filteredItems = items.filter(it => matchesFilter(it, "item") && matchesSearch(it.title + " " + (it.assignee || "")));

  let html = "";

  // 1. CHỦ ĐỀ & DIỄN BIẾN QUYẾT ĐỊNH
  if (filteredTopics.length > 0) {
    html += `
      <section class="inspector-section">
        <div class="sec-title"><span>🎯</span> chủ đề & diễn biến quyết định (${filteredTopics.length})</div>
        ${filteredTopics.map(t => renderTopicCard(t)).join("")}
      </section>
    `;
  }

  // 2. VIỆC CẦN LÀM (TASKS)
  const taskItems = filteredItems.filter(it => it.kind === "task");
  if (taskItems.length > 0) {
    html += `
      <section class="inspector-section">
        <div class="sec-title"><span>📋</span> việc cần làm (${taskItems.length})</div>
        ${taskItems.map((it, idx) => renderTaskCard(it, idx)).join("")}
      </section>
    `;
  }

  // 3. VƯỚNG MẮC / YÊU CẦU / TRI THỨC MỚI
  const otherItems = filteredItems.filter(it => it.kind !== "task");
  if (otherItems.length > 0) {
    html += `
      <section class="inspector-section">
        <div class="sec-title"><span>💡</span> vướng mắc & yêu cầu & tri thức (${otherItems.length})</div>
        ${otherItems.map((it, idx) => renderOtherItemCard(it, idx)).join("")}
      </section>
    `;
  }

  if (!html) {
    html = `<div class="loading-state">không tìm thấy kết quả phù hợp với bộ lọc hiện tại.</div>`;
  }

  container.innerHTML = html;
  bindInspectorInteractions();
}

function renderTopicCard(t) {
  const isAtoB = t.superseded && t.superseded.length > 0;
  const statusClass = t.status;
  const statusText = t.status_vi || t.status;
  const tid = t.topic_id;

  // Outcome string
  let outcomeHtml = "";
  if (t.final_option) {
    outcomeHtml = `<span class="final-choice">chốt: ${escapeHtml(t.final_option)}</span>`;
  } else if (t.leaning_option) {
    outcomeHtml = `<span style="color: var(--accent-gold);">nghiêng về: ${escapeHtml(t.leaning_option)}</span>`;
  } else {
    outcomeHtml = `<span style="color: var(--text-muted);">chưa ngã ngũ</span>`;
  }

  // Superseded pills (Phương án A đã bị thay thế)
  let supersededHtml = "";
  if (t.superseded && t.superseded.length) {
    supersededHtml = t.superseded.map(s => `<span class="superseded-pill" title="Đã bị thay thế">~~${escapeHtml(s)}~~</span>`).join(" ");
  }

  // Timeline events
  const timelineHtml = (t.timeline || []).map(e => `
    <div class="timeline-step" data-uid="${e.utterance_id}">
      <span class="step-ts">[${e.ts_label}]</span>
      <span class="step-speaker">${escapeHtml(e.speaker)}</span>
      <span class="step-stance-badge ${e.stance}">${e.stance}</span>
      <span class="step-quote">“${escapeHtml(e.quote)}”</span>
    </div>
  `).join("");

  // Jev telemetry
  let jevTelemetryHtml = "";
  if (t.judge) {
    const j = t.judge;
    const pConclude = j.explicit_conclusion?.p ?? 0.5;
    const pObj = j.objection_remaining?.p ?? 0.0;
    const pCond = j.conditional?.p ?? 0.0;
    const pAuth = j.authority_ok?.p ?? 1.0;

    jevTelemetryHtml = `
      <div class="jev-telemetry">
        <span>telemetry (jev 1.13):</span>
        <div class="jev-telemetry-scores">
          <span class="tev-item"><span class="tev-label">chốt:</span><span class="tev-val ${pConclude >= 0.5 ? 'pass' : 'fail'}">${(pConclude * 100).toFixed(0)}%</span></span>
          <span class="tev-item"><span class="tev-label">phản đối:</span><span class="tev-val ${pObj >= 0.6 ? 'fail' : 'pass'}">${(pObj * 100).toFixed(0)}%</span></span>
          <span class="tev-item"><span class="tev-label">điều kiện:</span><span class="tev-val ${pCond >= 0.7 ? 'fail' : 'pass'}">${(pCond * 100).toFixed(0)}%</span></span>
          <span class="tev-item"><span class="tev-label">thẩm quyền:</span><span class="tev-val ${pAuth >= 0.4 ? 'pass' : 'fail'}">${(pAuth * 100).toFixed(0)}%</span></span>
        </div>
      </div>
    `;
  }

  // Review status
  const currentReview = state.reviews[tid] || "";
  const isApproved = currentReview === "approved";
  const isEdited = currentReview === "edited";
  const isRejected = currentReview === "rejected";

  return `
    <div class="topic-card ${isAtoB ? 'has-atob' : ''}" id="topic-${tid}">
      <div class="topic-header">
        <div class="topic-title-wrap">
          <span class="topic-category">${t.category}</span>
          <span class="topic-title">${escapeHtml(t.title)}</span>
        </div>
        <span class="status-badge ${statusClass}">${statusText}</span>
      </div>

      <div class="outcome-block">
        ${outcomeHtml}
        ${supersededHtml ? `<span style="color:var(--text-muted);font-size:11px;">đã thay thế:</span> ${supersededHtml}` : ''}
      </div>

      ${t.flags && t.flags.length ? `
        <div style="display:flex;gap:4px;flex-wrap:wrap;">
          ${t.flags.map(f => `<span class="flag-chip">cờ: ${f}</span>`).join("")}
        </div>
      ` : ''}

      <div class="timeline-stepper">
        ${timelineHtml}
      </div>

      ${jevTelemetryHtml}

      <div class="review-actions">
        <button class="btn-review approve ${isApproved ? 'approved' : ''}" data-target="${tid}" data-action="approve" title="Xác nhận quyết định này">
          ${isApproved ? 'đã xác nhận' : 'xác nhận'}
        </button>
        <button class="btn-review edit ${isEdited ? 'edited' : ''}" data-target="${tid}" data-action="edit" title="Chỉnh sửa nội dung quyết định">
          ${isEdited ? 'đã sửa' : 'sửa'}
        </button>
        <button class="btn-review reject ${isRejected ? 'rejected' : ''}" data-target="${tid}" data-action="reject" title="Từ chối quyết định này">
          ${isRejected ? 'đã từ chối' : 'từ chối'}
        </button>
      </div>
    </div>
  `;
}

function renderTaskCard(it, idx) {
  const iid = `item-task-${idx}`;
  const isAssigneeVerified = it.assignee && it.assignee_basis in { assigned: 1, self_accepted: 1 };
  const assigneeBadge = it.assignee 
    ? `<span class="badge-assignee ${isAssigneeVerified ? '' : 'unverified'}" title="Căn cứ: ${it.assignee_basis}">${escapeHtml(it.assignee)}</span>`
    : `<span class="badge-assignee unverified">chưa xác định</span>`;

  const deadlineBadge = it.deadline_date
    ? `<span class="badge-deadline known">hạn: ${it.deadline_date}</span>`
    : `<span class="badge-deadline">hạn: ${it.deadline_text || 'chưa rõ'}</span>`;

  const primaryUid = it.utterance_ids && it.utterance_ids[0] ? it.utterance_ids[0] : "";

  return `
    <div class="task-item" id="${iid}">
      <div class="task-top">
        <span class="task-title">${escapeHtml(it.title)}</span>
        <div class="task-badges">
          ${assigneeBadge}
          ${deadlineBadge}
        </div>
      </div>
      <div class="task-quote" data-uid="${primaryUid}" title="Bấm để cuộn đến phát biểu nguồn trong transcript">
        “${escapeHtml(it.quote)}” <span style="font-size:11px;color:var(--text-muted)">(${it.utterance_ids.join(", ")})</span>
      </div>
      ${it.flags && it.flags.length ? `
        <div style="display:flex;gap:4px;flex-wrap:wrap;margin-top:2px;">
          ${it.flags.map(f => `<span class="flag-chip">${f}</span>`).join("")}
        </div>
      ` : ''}
    </div>
  `;
}

function renderOtherItemCard(it, idx) {
  const iid = `item-other-${idx}`;
  const primaryUid = it.utterance_ids && it.utterance_ids[0] ? it.utterance_ids[0] : "";
  const kindVi = { issue: "vướng mắc", request: "yêu cầu", feedback: "phản hồi", open_question: "câu hỏi mở", knowledge: "tri thức" }[it.kind] || it.kind;

  return `
    <div class="task-item" id="${iid}">
      <div class="task-top">
        <span class="task-title">${escapeHtml(it.title)}</span>
        <span class="status-badge open">${kindVi}</span>
      </div>
      <div class="task-quote" data-uid="${primaryUid}" title="Bấm để cuộn đến phát biểu nguồn trong transcript">
        “${escapeHtml(it.quote)}”
      </div>
    </div>
  `;
}

/* ==========================================================================
   INTERACTIONS & BIDIRECTIONAL HIGHLIGHTING
   ========================================================================== */
function bindInspectorInteractions() {
  // Click vào timeline step hoặc task quote -> Cuộn mượt và highlight transcript bên trái
  document.querySelectorAll("[data-uid]").forEach(el => {
    el.addEventListener("click", () => {
      const uid = el.dataset.uid;
      jumpToUtterance(uid);
    });
  });

  // Nút xác nhận / sửa / từ chối
  document.querySelectorAll(".btn-review").forEach(btn => {
    btn.addEventListener("click", (e) => {
      e.stopPropagation();
      const targetId = btn.dataset.target;
      const action = btn.dataset.action;
      const t = (state.meetingData?.topics || []).find(item => item.topic_id === targetId);

      if (action === "edit") {
        const curVal = t ? (t.final_option || t.leaning_option || "") : "";
        const newVal = prompt("Nhập nội dung/phương án đã chỉnh sửa:", curVal);
        if (newVal !== null && newVal.trim() !== "") {
          if (t) {
            t.final_option = newVal.trim();
            t.status = "decided";
            t.status_vi = "Đã chốt (đã sửa)";
          }
          state.reviews[targetId] = "edited";
          renderInspector();
          updateSummaryStats();
          showToast(`Đã sửa chủ đề [${targetId}]: "${newVal.trim()}"`);
        }
        return;
      }

      state.reviews[targetId] = action;
      if (t) {
        if (action === "approve") {
          t.status = "decided";
          t.status_vi = "Đã chốt (đã duyệt)";
        } else if (action === "reject") {
          t.status = "open";
          t.status_vi = "Từ chối (bác bỏ)";
        }
      }
      renderInspector();
      updateSummaryStats();
      showToast(action === "approve" ? `Đã xác nhận duyệt [${targetId}]` : `Đã từ chối [${targetId}]`);
    });
  });
}

function jumpToUtterance(uid) {
  if (!uid) return;
  const feed = document.getElementById("transcript-feed");
  const targetCard = document.getElementById(`utt-${uid}`);
  if (!targetCard || !feed) return;

  clearHighlights();
  targetCard.classList.add("highlighted");

  // Cuộn mượt chỉ trong khung transcript-feed, tuyệt đối không dịch chuyển window/body
  const feedRect = feed.getBoundingClientRect();
  const cardRect = targetCard.getBoundingClientRect();
  const offset = (cardRect.top - feedRect.top) + feed.scrollTop;
  const targetScroll = offset - (feed.clientHeight / 2) + (cardRect.height / 2);

  feed.scrollTo({
    top: Math.max(0, targetScroll),
    behavior: "smooth"
  });
}

function clearHighlights() {
  document.querySelectorAll(".utterance-card.highlighted").forEach(c => c.classList.remove("highlighted"));
}

function highlightSearchInTranscript() {
  if (!state.searchQuery) {
    document.querySelectorAll(".w-search-match").forEach(el => {
      el.outerHTML = el.textContent;
    });
    return;
  }
}

/* ==========================================================================
   FILTER & STATS LOGIC
   ========================================================================== */
function matchesFilter(item, type) {
  if (state.activeFilter === "all") return true;
  if (state.activeFilter === "a-to-b") {
    if (type === "topic") return item.superseded && item.superseded.length > 0;
    return false;
  }
  if (state.activeFilter === "decisions") {
    return type === "topic" && item.status === "decided";
  }
  if (state.activeFilter === "tasks") {
    return type === "item" && item.kind === "task";
  }
  if (state.activeFilter === "review-queue") {
    if (type === "topic") return item.status === "leaning" || item.needs_confirmation || (item.flags && item.flags.length > 0);
    if (type === "item") return item.flags && item.flags.length > 0;
  }
  return true;
}

function matchesSearch(text) {
  if (!state.searchQuery) return true;
  return text.toLowerCase().includes(state.searchQuery);
}

function updateSummaryStats() {
  if (!state.meetingData) return;
  const topics = state.meetingData.topics || [];
  const items = state.meetingData.items || [];

  const decidedCount = topics.filter(t => t.status === "decided").length;
  const tasksCount = items.filter(it => it.kind === "task").length;
  const supersededCount = topics.filter(t => t.superseded && t.superseded.length > 0).length;
  const reviewCount = topics.filter(t => t.status === "leaning" || (t.flags && t.flags.length > 0)).length +
                      items.filter(it => it.flags && it.flags.length > 0).length;

  document.getElementById("stat-decided").textContent = decidedCount;
  document.getElementById("stat-tasks").textContent = tasksCount;
  document.getElementById("stat-superseded").textContent = supersededCount;
  document.getElementById("review-count").textContent = reviewCount;
}

function batchApproveSafeItems() {
  if (!state.meetingData) return;
  const topics = state.meetingData.topics || [];
  let count = 0;
  topics.forEach(t => {
    if (t.status === "decided" && (!t.flags || t.flags.length === 0)) {
      state.reviews[t.topic_id] = "approved";
      count++;
    }
  });
  renderInspector();
  updateSummaryStats();
  showToast(`Đã duyệt nhanh ${count} mục an toàn.`);
}

/* ==========================================================================
   EXPORT & TOAST UTILITIES
   ========================================================================== */
async function exportData(format) {
  if (!state.meetingData) return;
  try {
    const res = await fetch("/api/export", {
      method: "POST",
      headers: getAuthHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify({
        meeting_id: state.currentMeetingId,
        format: format,
        approved_ids: Object.keys(state.reviews).filter(k => state.reviews[k] === "approved"),
        access_code: getAccessCode()
      })
    });

    if (res.status === 401) {
      showToast("Yêu cầu mã truy cập hợp lệ để xuất dữ liệu (401).");
      return;
    }

    const text = await res.text();

    if (format === "markdown") {
      try {
        await navigator.clipboard.writeText(text);
      } catch (e) {
        console.warn("Clipboard access denied:", e);
      }
      const blob = new Blob([text], { type: "text/markdown;charset=utf-8;" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${state.currentMeetingId}_bien_ban.md`;
      a.click();
      URL.revokeObjectURL(url);
      showToast("Đã tải xuống biên bản Markdown & copy vào Clipboard!");
    } else {
      const blob = new Blob([text], { type: "text/csv;charset=utf-8;" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${state.currentMeetingId}_tasks.csv`;
      a.click();
      URL.revokeObjectURL(url);
      showToast("Đã tải xuống file tasks.csv!");
    }
  } catch (err) {
    showToast("Lỗi xuất dữ liệu: " + err.message);
  }
}

function showToast(msg) {
  const toast = document.getElementById("toast");
  toast.textContent = msg;
  toast.classList.add("show");
  setTimeout(() => {
    toast.classList.remove("show");
  }, 2400);
}

function escapeHtml(str) {
  if (!str) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

function escapeRegex(str) {
  return str.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}
