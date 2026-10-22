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
  return (modalEl && modalEl.value.trim()) || (localStorage.getItem("meeting_intel_access_code") || "");
}

function setAccessCode(val) {
  const trimmed = (val || "").trim();
  localStorage.setItem("meeting_intel_access_code", trimmed);
  const modalEl = document.getElementById("inp-modal-access-code");
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
  const modalEl = document.getElementById("inp-modal-access-code");
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
  if (select) {
    select.addEventListener("change", (e) => {
      loadMeeting(e.target.value);
    });
  }

  const searchInput = document.getElementById("search-input");
  if (searchInput) {
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
  }

  // Filter tabs
  const tabGroup = document.getElementById("filter-tabs");
  if (tabGroup) {
    tabGroup.addEventListener("click", (e) => {
      const btn = e.target.closest(".tab-btn");
      if (!btn) return;
      document.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      state.activeFilter = btn.dataset.filter;
      renderInspector();
    });
  }

  // Export dropdown menu
  const exportToggle = document.getElementById("btn-export-toggle");
  const exportMenu = document.getElementById("export-menu");
  if (exportToggle && exportMenu) {
    exportToggle.addEventListener("click", (e) => {
      e.stopPropagation();
      exportMenu.classList.toggle("hidden");
    });
    document.addEventListener("click", (e) => {
      if (!e.target.closest("#export-dropdown-wrap")) {
        exportMenu.classList.add("hidden");
      }
    });
  }

  const btnMd = document.getElementById("btn-export-md");
  if (btnMd) {
    btnMd.addEventListener("click", () => {
      if (exportMenu) exportMenu.classList.add("hidden");
      exportData("markdown");
    });
  }

  const btnCsv = document.getElementById("btn-export-csv");
  if (btnCsv) {
    btnCsv.addEventListener("click", () => {
      if (exportMenu) exportMenu.classList.add("hidden");
      exportData("csv");
    });
  }

  const btnReEval = document.getElementById("btn-re-eval");
  if (btnReEval) {
    btnReEval.addEventListener("click", () => {
      showToast("Đang kích hoạt Jev phân xử lại...");
      loadMeeting(state.currentMeetingId);
    });
  }

  const btnBatchApprove = document.getElementById("btn-batch-approve");
  if (btnBatchApprove) {
    btnBatchApprove.addEventListener("click", () => {
      batchApproveSafeItems();
    });
  }

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
      const date = (document.getElementById("inp-date")?.value || "2026-10-15").trim();
      const mode = document.getElementById("sel-mode")?.value || "consensus";
      const leader = document.getElementById("inp-leader")?.value.trim() || "";
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
      btnSubmitUpload.textContent = "Đang phân tích...";

      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 60000);

      try {
        const res = await fetch("/api/upload", {
          method: "POST",
          headers: getAuthHeaders({ "Content-Type": "application/json" }),
          body: JSON.stringify({
            title,
            date,
            mode,
            leader,
            transcript,
            roles,
            judge: state.judge || "jev",
            backend: state.backend || "gemini",
            access_code: getAccessCode()
          }),
          signal: controller.signal
        });
        clearTimeout(timeoutId);

        if (res.status === 401) {
          showToast("Mã truy cập không hợp lệ (401). Vui lòng nhập đúng ACCESS_CODE.");
          const modalEl = document.getElementById("inp-modal-access-code");
          if (modalEl) {
            modalEl.focus();
            modalEl.style.borderColor = "#ef4444";
          }
          btnSubmitUpload.disabled = false;
          btnSubmitUpload.textContent = "Phân Tích Ngay";
          return;
        }

        const contentType = res.headers.get("content-type") || "";
        let data = {};
        if (contentType.includes("application/json")) {
          data = await res.json();
        } else {
          const text = await res.text();
          throw new Error(`Máy chủ phản hồi HTTP ${res.status}: ${text.slice(0, 150)}`);
        }

        if (data.error) {
          showToast("Lỗi: " + data.error);
          btnSubmitUpload.disabled = false;
          btnSubmitUpload.textContent = "Phân Tích Ngay";
          return;
        }

        uploadModal.classList.add("hidden");
        btnSubmitUpload.disabled = false;
        btnSubmitUpload.textContent = "Phân Tích Ngay";

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
        clearTimeout(timeoutId);
        if (err.name === "AbortError") {
          showToast("Quá thời gian chờ (60s). Máy chủ hoặc mô hình AI phản hồi quá lâu.");
        } else {
          showToast("Lỗi kết nối máy chủ: " + err.message);
        }
        btnSubmitUpload.disabled = false;
        btnSubmitUpload.textContent = "Phân Tích Ngay";
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

  document.getElementById("transcript-feed").innerHTML = `<div class="loading-state">Đang tải dữ liệu lời thoại ${mid}...</div>`;
  document.getElementById("inspector-content").innerHTML = `<div class="loading-state">Đang phân tích dữ liệu cuộc họp...</div>`;

  try {
    const res = await fetch(`/api/meeting/${mid}?oracle=0&judge=jev&backend=gemini`, {
      headers: getAuthHeaders()
    });

    if (res.status === 401) {
      showToast("Yêu cầu mã truy cập hợp lệ (401). Vui lòng nhập ACCESS_CODE.");
      document.getElementById("transcript-feed").innerHTML = `<div class="loading-state">Vui lòng nhập đúng ACCESS_CODE khi nạp transcript mới.</div>`;
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
    feed.innerHTML = `<div class="loading-state">Không có dữ liệu lời thoại nào.</div>`;
    return;
  }

  feed.innerHTML = utts.map(u => {
    const formattedText = formatTranscriptText(u.text);
    return `
      <div class="utterance-card" id="utt-${u.id}" data-uid="${u.id}">
        <div class="utt-meta">
          <span class="utt-ts">[${u.ts_label || "--:--:--"}]</span>
          <span class="utt-speaker">${escapeHtml(u.speaker)}</span>
          <span class="utt-id">${u.id}</span>
        </div>
        <div class="utt-text">${formattedText}</div>
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

function formatTranscriptText(text) {
  let escaped = escapeHtml(text);
  if (state.searchQuery) {
    const q = escapeRegex(state.searchQuery);
    escaped = escaped.replace(new RegExp(`(${q})`, "gi"), `<mark class="search-highlight">$1</mark>`);
  }
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
        <div class="sec-title">Chủ Đề & Diễn Biến Quyết Định (${filteredTopics.length})</div>
        ${filteredTopics.map(t => renderTopicCard(t)).join("")}
      </section>
    `;
  }

  // 2. BẢNG VIỆC TÁC NGHIỆP (TASKS & REQUESTS)
  const taskItems = filteredItems.filter(it => it.kind === "task" || it.kind === "request");
  if (taskItems.length > 0) {
    html += `
      <section class="inspector-section">
        <div class="sec-title">Bảng Việc Tác Nghiệp (Sprint / Dự Án) (${taskItems.length})</div>
        ${taskItems.map((it, idx) => renderTaskCard(it, idx)).join("")}
      </section>
    `;
  }

  // 3. KHO TRI THỨC TỔ CHỨC (DÙNG LÂU DÀI - KNOWLEDGE)
  const knowledgeItems = filteredItems.filter(it => it.kind === "knowledge");
  if (knowledgeItems.length > 0) {
    html += `
      <section class="inspector-section">
        <div class="sec-title">Kho Tri Thức Tổ Chức (Dùng Lâu Dài) (${knowledgeItems.length})</div>
        ${knowledgeItems.map((it, idx) => renderKnowledgeCard(it, idx)).join("")}
      </section>
    `;
  }

  // 4. VẤN ĐỀ CHƯA CHỐT & TẮC NGHẼN (UNRESOLVED & BLOCKERS)
  const unresolvedItems = filteredItems.filter(it => it.kind === "open_question" || it.kind === "issue" || it.kind === "feedback");
  if (unresolvedItems.length > 0) {
    html += `
      <section class="inspector-section">
        <div class="sec-title">Vấn Đề Chưa Chốt & Tắc Nghẽn (Cần Làm Rõ) (${unresolvedItems.length})</div>
        ${unresolvedItems.map((it, idx) => renderOtherItemCard(it, idx)).join("")}
      </section>
    `;
  }

  if (!html) {
    html = `<div class="loading-state">Không tìm thấy kết quả phù hợp với bộ lọc hiện tại.</div>`;
  }

  container.innerHTML = html;
  bindInspectorInteractions();
}

function renderTopicCard(t) {
  const isAtoB = t.superseded && t.superseded.length > 0;
  const statusClass = t.status;
  const statusText = t.status === "decided" ? "ĐÃ CHỐT" : (t.status === "leaning" ? "NGHIÊNG VỀ" : "CHƯA CHỐT");
  const tid = t.topic_id;

  // Outcome string
  let outcomeHtml = "";
  if (t.final_option) {
    outcomeHtml = `<span class="final-choice">Chốt: ${escapeHtml(t.final_option)}</span>`;
  } else if (t.leaning_option) {
    outcomeHtml = `<span style="color: var(--accent-gold); font-weight: 600;">Nghiêng về: ${escapeHtml(t.leaning_option)}</span>`;
  } else {
    outcomeHtml = `<span style="color: var(--text-muted);">Chưa ngã ngũ</span>`;
  }

  // Superseded pills (Phương án A đã bị thay thế)
  let supersededHtml = "";
  if (t.superseded && t.superseded.length) {
    supersededHtml = t.superseded.map(s => `<span class="superseded-pill" title="Đã bị thay thế">~~${escapeHtml(s)}~~</span>`).join(" ");
  }

  // Stance labels mapping
  const stanceLabels = {
    propose: "Đề xuất",
    support: "Tán thành",
    oppose: "Phản đối",
    reverse: "Đổi ý",
    conclude: "Kết luận",
    defer: "Tạm hoãn",
    question: "Câu hỏi",
    info: "Thông tin"
  };

  // Timeline events
  const timelineHtml = (t.timeline || []).map(e => `
    <div class="timeline-step" data-uid="${e.utterance_id}">
      <span class="step-ts">[${e.ts_label}]</span>
      <span class="step-speaker">${escapeHtml(e.speaker)}</span>
      <span class="step-stance-badge ${e.stance}">${stanceLabels[e.stance] || e.stance}</span>
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
        <span class="jev-telemetry-header">ĐO LƯỜNG JEV (TELEMETRY):</span>
        <div class="jev-telemetry-scores">
          <span class="tev-item"><span class="tev-label">Chốt:</span><span class="tev-val ${pConclude >= 0.5 ? 'pass' : 'fail'}">${(pConclude * 100).toFixed(0)}%</span></span>
          <span class="tev-item"><span class="tev-label">Phản đối:</span><span class="tev-val ${pObj >= 0.6 ? 'fail' : 'pass'}">${(pObj * 100).toFixed(0)}%</span></span>
          <span class="tev-item"><span class="tev-label">Điều kiện:</span><span class="tev-val ${pCond >= 0.7 ? 'fail' : 'pass'}">${(pCond * 100).toFixed(0)}%</span></span>
          <span class="tev-item"><span class="tev-label">Thẩm quyền:</span><span class="tev-val ${pAuth >= 0.4 ? 'pass' : 'fail'}">${(pAuth * 100).toFixed(0)}%</span></span>
        </div>
      </div>
    `;
  }

  // Decision Journey
  let journeyHtml = "";
  if (t.decision_journey && t.decision_journey.length > 0) {
    const phaseIcons = {
      proposal: "💡",
      discussion: "💬",
      modification: "🔄",
      resolution: "⚖️"
    };
    journeyHtml = `
      <div class="decision-journey-wrap">
        <div class="decision-journey-title">TIẾN TRÌNH RA QUYẾT ĐỊNH (DECISION JOURNEY):</div>
        <div class="decision-journey-steps">
          ${t.decision_journey.map(step => `
            <div class="journey-step-row" data-uid="${step.utterance_id}">
              <span class="journey-phase-badge ${step.phase}">${phaseIcons[step.phase] || "•"} ${escapeHtml(step.phase_vi)}</span>
              <span class="journey-speaker">${escapeHtml(step.speaker)}</span>
              <span class="journey-action">${escapeHtml(step.action)}</span>
              <span class="journey-quote" title="Bấm để xem phát biểu gốc">“${escapeHtml(step.quote)}”</span>
            </div>
          `).join("")}
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
          <span class="topic-category">${(t.category || "").toUpperCase()}</span>
          <span class="topic-title">${escapeHtml(t.title)}</span>
        </div>
        <span class="status-badge ${statusClass}">${statusText}</span>
      </div>

      <div class="outcome-block">
        ${outcomeHtml}
        ${supersededHtml ? `<span style="color:var(--text-muted);font-size:12px;margin-left:8px;">Đã thay thế:</span> ${supersededHtml}` : ''}
      </div>

      ${journeyHtml}

      ${t.flags && t.flags.length ? `
        <div style="display:flex;gap:4px;flex-wrap:wrap;">
          ${t.flags.map(f => `<span class="flag-chip">Cờ: ${f}</span>`).join("")}
        </div>
      ` : ''}

      <div class="timeline-stepper">
        ${timelineHtml}
      </div>

      ${jevTelemetryHtml}

      <div class="review-actions">
        <button class="btn-review approve ${isApproved ? 'approved' : ''}" data-target="${tid}" data-action="approve" title="Xác nhận quyết định này">
          ${isApproved ? 'Đã xác nhận' : 'Xác nhận'}
        </button>
        <button class="btn-review edit ${isEdited ? 'edited' : ''}" data-target="${tid}" data-action="edit" title="Chỉnh sửa nội dung quyết định">
          ${isEdited ? 'Đã sửa' : 'Chỉnh sửa'}
        </button>
        <button class="btn-review reject ${isRejected ? 'rejected' : ''}" data-target="${tid}" data-action="reject" title="Từ chối quyết định này">
          ${isRejected ? 'Đã từ chối' : 'Từ chối'}
        </button>
      </div>
    </div>
  `;
}

function getUtteranceTs(uid) {
  if (!uid || !state.meetingData || !state.meetingData.transcript) return "";
  const u = state.meetingData.transcript.find(x => x.id === uid);
  return u && u.ts_label ? u.ts_label : "";
}

function renderTaskCard(it, idx) {
  const iid = `item-task-${idx}`;
  const isAssigneeVerified = it.assignee && it.assignee_basis in { assigned: 1, self_accepted: 1 };
  const assigneeBadge = it.assignee 
    ? `<span class="badge-assignee ${isAssigneeVerified ? '' : 'unverified'}" title="Căn cứ: ${it.assignee_basis}">Người nhận: ${escapeHtml(it.assignee)}</span>`
    : `<span class="badge-assignee unverified">Chưa xác định người nhận</span>`;

  const deadlineBadge = it.deadline_date
    ? `<span class="badge-deadline known">Hạn: ${it.deadline_date}</span>`
    : `<span class="badge-deadline">Hạn: ${it.deadline_text || 'Chưa rõ'}</span>`;

  const primaryUid = it.utterance_ids && it.utterance_ids[0] ? it.utterance_ids[0] : "";
  const ts = getUtteranceTs(primaryUid);
  const tsBadge = ts ? `<span class="quote-ts">[${ts}]</span> ` : "";

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
        ${tsBadge}“${escapeHtml(it.quote)}” <span style="font-size:11.5px;color:var(--text-muted)">(${it.utterance_ids.join(", ")})</span>
      </div>
      ${it.flags && it.flags.length ? `
        <div style="display:flex;gap:4px;flex-wrap:wrap;margin-top:2px;">
          ${it.flags.map(f => `<span class="flag-chip">Cờ: ${f}</span>`).join("")}
        </div>
      ` : ''}
    </div>
  `;
}

function renderKnowledgeCard(it, idx) {
  const iid = `item-k-${idx}`;
  const primaryUid = it.utterance_ids && it.utterance_ids[0] ? it.utterance_ids[0] : "";
  const ts = getUtteranceTs(primaryUid);
  const tsBadge = ts ? `<span class="quote-ts">[${ts}]</span> ` : "";
  const catNames = {
    architecture: "Kiến Trúc Kỹ Thuật (ADR)",
    policy: "Chính Sách & Quy Chuẩn",
    lesson_learned: "Bài Học Kinh Nghiệm",
    general: "Tri Thức Dài Hạn"
  };
  const catLabel = catNames[it.knowledge_category] || "Tri Thức Dài Hạn";

  return `
    <div class="knowledge-card" id="${iid}">
      <div class="k-header">
        <span class="badge-knowledge-cat">${escapeHtml(catLabel)}</span>
        <span class="k-title">${escapeHtml(it.title)}</span>
      </div>
      <div class="task-quote" data-uid="${primaryUid}" title="Bấm để cuộn đến nguồn trong transcript">
        ${tsBadge}“${escapeHtml(it.quote)}” <span style="font-size:11.5px;color:var(--text-muted)">(${it.utterance_ids.join(", ")})</span>
      </div>
      ${it.flags && it.flags.length ? `
        <div style="display:flex;gap:4px;flex-wrap:wrap;margin-top:4px;">
          ${it.flags.map(f => `<span class="flag-chip">Cờ: ${f}</span>`).join("")}
        </div>
      ` : ''}
    </div>
  `;
}

function renderOtherItemCard(it, idx) {
  const iid = `item-other-${idx}`;
  const primaryUid = it.utterance_ids && it.utterance_ids[0] ? it.utterance_ids[0] : "";
  const ts = getUtteranceTs(primaryUid);
  const tsBadge = ts ? `<span class="quote-ts">[${ts}]</span> ` : "";
  const kindVi = { issue: "Vướng mắc", request: "Yêu cầu", feedback: "Góp ý", open_question: "Câu hỏi mở", knowledge: "Tri thức mới" }[it.kind] || it.kind;

  return `
    <div class="task-item" id="${iid}">
      <div class="task-top">
        <span class="task-title">${escapeHtml(it.title)}</span>
        <span class="status-badge open">${kindVi}</span>
      </div>
      <div class="task-quote" data-uid="${primaryUid}" title="Bấm để cuộn đến phát biểu nguồn trong transcript">
        ${tsBadge}“${escapeHtml(it.quote)}” <span style="font-size:11.5px;color:var(--text-muted)">(${it.utterance_ids.join(", ")})</span>
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
    return type === "item" && (item.kind === "task" || item.kind === "request");
  }
  if (state.activeFilter === "knowledge") {
    return type === "item" && item.kind === "knowledge";
  }
  if (state.activeFilter === "unresolved") {
    if (type === "topic") return item.status === "open" || item.status === "leaning";
    if (type === "item") return item.kind === "open_question" || item.kind === "issue";
    return false;
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
  const tasksCount = items.filter(it => it.kind === "task" || it.kind === "request").length;
  const knowledgeCount = items.filter(it => it.kind === "knowledge").length;
  const supersededCount = topics.filter(t => t.superseded && t.superseded.length > 0).length;
  const reviewCount = topics.filter(t => t.status === "leaning" || (t.flags && t.flags.length > 0)).length +
                      items.filter(it => it.flags && it.flags.length > 0).length;

  const elDecided = document.getElementById("stat-decided");
  if (elDecided) elDecided.textContent = decidedCount;
  const elTasks = document.getElementById("stat-tasks");
  if (elTasks) elTasks.textContent = tasksCount;
  const elKnowledge = document.getElementById("stat-knowledge");
  if (elKnowledge) elKnowledge.textContent = knowledgeCount;
  const elSuperseded = document.getElementById("stat-superseded");
  if (elSuperseded) elSuperseded.textContent = supersededCount;
  const elReview = document.getElementById("review-count");
  if (elReview) elReview.textContent = reviewCount;
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
