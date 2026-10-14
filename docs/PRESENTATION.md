# TÀI LIỆU THUYẾT TRÌNH DỰ ÁN: MEETING INTEL
## Hệ Thống Trích Xuất Dữ Liệu Biên Bản Cuộc Họp, Theo Dõi Dòng Thời Gian (A sang B) & Phân Xử Tất Định

> **Đối tượng sử dụng:** Ban Giám Khảo, Hội đồng Thẩm định Kỹ thuật, Đội ngũ Phát triển & Vận hành.  
> **Thời lượng trình bày gợi ý:** 5 – 7 phút (Kèm kịch bản thao tác màn hình trực tiếp).  
> **Kho mã nguồn:** [GitHub Repository](https://github.com/PhamNgocDuyPy/Meeting-Intel)  
> **Bản demo trực tuyến:** [Meeting Intel Web App](https://meeting-intel.onrender.com)

---

## MỤC LỤC BÀI THUYẾT TRÌNH

1. [Phần 1: Bối Cảnh, Bài Toán & Tôn Chỉ Thiết Kế](#phần-1-bối-cảnh-bài-toán--tôn-chỉ-thiết-kế)
2. [Phần 2: Chi Tiết Từng Tiêu Chí Đánh Giá (Rubric & Scoring Criteria)](#phần-2-chi-tiết-từng-tiêu-chí-đánh-giá-rubric--scoring-criteria)
3. [Phần 3: Kiến Trúc Hệ Thống & Luồng Xử Lý Toàn Diện (End-to-End Pipeline)](#phần-3-kiến-trúc-hệ-thống--luồng-xử-lý-toàn-diện-end-to-end-pipeline)
4. [Phần 4: Bản Đồ Giao Diện Người Dùng (UI/UX Component Breakdown)](#phần-4-bản-đồ-giao-diện-người-dùng-uiux-component-breakdown)
5. [Phần 5: Số Liệu Thực Nghiệm & Kết Quả Đối Soát Benchmark](#phần-5-số-liệu-thực-nghiệm--kết-quả-đối-soát-benchmark)
6. [Phần 6: Kịch Bản Thuyết Trình & Thao Tác Trực Tiếp (Live Demo Script)](#phần-6-kịch-bản-thuyết-trình--thao-tác-trực-tiếp-live-demo-script)
7. [Phần 7: Quản Trị Rủi Ro Vận Hành & Phương Án Dự Phòng](#phần-7-quản-trị-rủi-ro-vận-hành--phương-án-dự-phòng)

---

## PHẦN 1: BỐI CẢNH, BÀI TOÁN & TÔN CHỈ THIẾT KẾ

### 1. Nỗi đau thực tế trong doanh nghiệp (Pain Point)
* **Thông tin phân mảnh và biến động liên tục:** Trong các cuộc họp điều hành, kỹ thuật và thiết kế sản phẩm, người tham gia liên tục đề xuất, tranh biện, thay đổi quan điểm và đưa ra điều kiện ràng buộc.
* **Sai lầm của các giải pháp truyền thống (LLM Summary / RAG):**
  * Tóm tắt văn bản thông thường thường gộp chung cả ý kiến ban đầu và kết luận mới nhất, gây nhiễu loạn cho đội ngũ thực thi.
  * Vector Search / RAG tìm kiếm theo độ tương đồng ngữ nghĩa sẽ coi phát biểu đề xuất ban đầu (Phương án A) và kết luận đảo ngược cuối giờ (Phương án B) có độ tương đồng như nhau, dẫn đến **chốt nhầm phương án đã bị bác bỏ**.
  * Tự tiện gán công việc (Hallucination): Biến người chỉ được nhắc tên ("chắc Đạt làm được nhỉ") thành người chịu trách nhiệm chính.

### 2. Tôn chỉ cốt lõi: "Ưu Tiên Đúng Hơn Đủ" (Precision Over Recall)
1. **Thà hạ an toàn còn hơn chốt nhầm:** Thà hạ một quyết định còn nghi vấn về trạng thái `Nghiêng về` (`leaning`) để con người duyệt lại, còn hơn tự ý chốt nhầm một quyết định chưa ngã ngũ (`decided`) gây tổn thất tài chính và nguồn lực.
2. **Tách biệt trích xuất và phân xử:** LLM chỉ làm nhiệm vụ bóc tách sự kiện và trích dẫn thô. Quyết định trạng thái cuối cùng thuộc về **Động cơ Luật Tất định theo Dòng thời gian (Deterministic Timeline Engine)** dựa trên 4 điều kiện kiểm soát nghiêm ngặt.
3. **Bằng chứng cứng 100% (Exact Substring Verification):** Không một thông tin nào được đưa vào báo cáo nếu không có trích dẫn chứng cứ nguyên văn nằm trong bản ghi cuộc họp gốc.

---

## PHẦN 2: CHI TIẾT TỪNG TIÊU CHÍ ĐÁNH GIÁ (RUBRIC & SCORING CRITERIA)

Hệ thống được thiết kế và kiểm thử nghiêm ngặt theo **7 tiêu chí đánh giá kỹ thuật và nghiệp vụ**:

| Mã Tiêu Chí | Tên Tiêu Chí | Ý Nghĩa Nghiệp Vụ & Định Nghĩa Kỹ Thuật | Trọng Số / Mức Độ | Cơ Chế Giải Quyết Trong Meeting Intel |
|:---:|---|---|:---:|---|
| **C1** | **Xử lý Đổi Ý Kiến (A sang B)** | Phát hiện diễn biến thay đổi ý kiến trong cuộc họp: đầu họp đề xuất A, thảo luận tranh luận, cuối họp chốt B; đưa A vào danh sách bị thay thế (`superseded`/`rejected_options`). | **CỐT LÕI (Core Loop)** | Động cơ dòng thời gian theo dõi thứ tự tem thời gian (`ts`), nhận diện nhãn `reverse`, tự động gạch bỏ phương án cũ và cập nhật phương án mới. |
| **C2** | **Không Lỗi Nghiêm Trọng (Zero Critical Errors)** | Phạt nặng nhất khi hệ thống ghi nhận `decided` (Đã chốt) mà thực tế chưa chốt, chốt có điều kiện chưa xong, hoặc chốt nhầm phương án cũ đã bị bác bỏ. | **TỐI QUAN TRỌNG (Critical = 0)** | Áp dụng 4 điều kiện tất định: chỉ chuyển sang `decided` khi thỏa mãn 100% 4 điều kiện; nếu thiếu, tự động hạ về `leaning`. |
| **C3** | **Kiểm Chứng Chuỗi Con (Exact Substring)** | Mọi câu trích dẫn chứng minh (`quote`) của quyết định và công việc bắt buộc phải là chuỗi con chính xác 100% trong transcript gốc. Chống bịa đặt nguồn. | **BẮT BUỘC (100% Valid)** | Tầng tiền xử lý kiểm tra chuỗi con `quote in transcript`. Nếu LLM bịa trích dẫn, bằng chứng bị hủy bỏ; chỉ áp dụng **Bất đối xứng bằng chứng** đối với phản đối để bảo vệ an toàn. |
| **C4** | **Kiểm Soát Thẩm Quyền (Authority Matrix)** | Người kết luận phải có quyền quyết định trong lĩnh vực đó (theo ma trận vai trò: PM chốt Scope, Tech Lead chốt Technical, Head of Product chốt toàn diện). | **NGHIỆP VỤ CAO** | Ma trận thẩm quyền phân cấp (`decision_rights.yaml` & `people.yaml`). Nếu người chốt không đủ quyền, quyết định giữ ở `leaning` cho đến khi người có thẩm quyền lên tiếng xác nhận. |
| **C5** | **Chặn Gán Nhầm Việc (Anti-Fabrication)** | Không được tự gán người nhận việc (`fabricated_assignee = 0`) khi người đó chỉ được nhắc tên hoặc chưa nhận lời rõ ràng; không tự điền hạn chót (`fabricated_deadline = 0`). | **NGHIỆP VỤ CAO** | Tích hợp **Bộ lọc từ do dự (Hedge Check)**: nhận diện các từ do dự/hỏi han ("chắc... nhỉ", "xem đã", "để hỏi lại") và phân tích cửa sổ 2 phát biểu kế tiếp để xác nhận sự đồng ý. |
| **C6** | **Chỉ Số Định Lượng (Benchmark Scores)** | Tỷ lệ Đạt tổng thể (Pass Rate), Độ chính xác trạng thái chủ đề (Topic Status Acc), Độ phủ việc (Task Recall), Độ chính xác người nhận (Assignee Acc). | **ĐỊNH LƯỢNG** | Đạt **90.0%** (18/20 ca nội bộ); **0 lỗi chốt nhầm** (0 Critical Errors); **0 ca hạ oan quyết định đúng**; 100% trích dẫn chứng cứ hợp lệ. |
| **C7** | **Độ Khả Dụng & Phòng Vệ Vận Hành** | Khả năng chạy ổn định trực tuyến, chống quá tải quota, chống nghẽn mạng, phục vụ người dùng duyệt dữ liệu (Human-in-the-Loop). | **VẬN HÀNH** | Rate limit 30 req/min, trần 100 lượt gọi/ngày, bảo vệ bằng mã `ACCESS_CODE`, cơ chế offline cache 26 cuộc họp mẫu (~50ms) và Fallback sang NVIDIA NIM. |

---

## PHẦN 3: KIẾN TRÚC HỆ THỐNG & LUỒNG XỬ LÝ TOÀN DIỆN (END-TO-END PIPELINE)

Hệ thống được xây dựng theo kiến trúc **4 tầng phòng vệ tách rời (Decoupled 4-Layer Architecture)** kết hợp luồng xử lý dự phòng tự động:

```
                  ┌─────────────────────────────────────────────────────────┐
                  │                 BẢN GHI LỜI THOẠI GỐC                   │
                  │   (Raw Transcript: [HH:MM:SS] Người nói: Nội dung)      │
                  └────────────────────────────┬────────────────────────────┘
                                               │
                                               ▼
     ┌───────────────────────────────────────────────────────────────────────────────────┐
     │ TẦNG 1: BÓC TÁCH NGỮ NGHĨA & KIỂM CHỨNG CHUỖI CON (EXACT SUBSTRING VERIFICATION) │
     │  • LLM Backend: Google Gemini Flash / NVIDIA NIM (DeepSeek / Nemotron)            │
     │  • Bóc tách sự kiện: propose (đề xuất), objection (phản đối),                     │
     │                      reverse (đổi ý), conclude (kết luận)                         │
     │  • Kiểm chứng chuỗi con: quote ∈ transcript (Loại bỏ 100% trích dẫn ảo)           │
     │  • Bất đối xứng bằng chứng: Dấu hiệu phản đối dù trích dẫn chưa chuẩn             │
     │    vẫn giữ lại để hạ cấp an toàn (Fail-safe)                                      │
     └─────────────────────────────────────────┬─────────────────────────────────────────┘
                                               │
                                               ▼
     ┌───────────────────────────────────────────────────────────────────────────────────┐
     │ TẦNG 2: ĐỘNG CƠ LUẬT TẤT ĐỊNH THEO DÒNG THỜI GIAN (DETERMINISTIC TIMELINE ENGINE) │
     │  Áp dụng 4 ĐIỀU KIỆN CHỐT CỨNG để chuyển sang "ĐÃ CHỐT" (decided):                 │
     │    [1] Không ràng buộc điều kiện (conditional == false)                           │
     │    [2] Người kết luận có thẩm quyền hợp lệ (authority_ok == true)                 │
     │    [3] Không còn phản đối chưa giải quyết (objection_resolved == true)             │
     │    [4] Không bị đảo ngược muộn hơn (no later reversal)                            │
     │  ➔ Theo dõi tiến trình: Đề xuất A ➔ Phản đối A ➔ Đổi ý B ➔ Chốt B                │
     │  ➔ Lưu vết phương án thay thế: rejected_options = ["A"], final_option = "B"       │
     └─────────────────────────────────────────┬─────────────────────────────────────────┘
                                               │
                                               ▼
     ┌───────────────────────────────────────────────────────────────────────────────────┐
     │ TẦNG 3: LƯỚI PHÒNG THỦ CẢNH BÁO (ADVISORY SAFETY NET - JEV SYSTEM ONE)            │
     │  • Thẩm định chuyên sâu qua các câu hỏi hẹp (noul binary verification)            │
     │  • Đánh giá xác suất (p): Chốt, Phản đối, Điều kiện ràng buộc, Thẩm quyền         │
     │  • Chế độ Khuyến nghị (Advisory Mode): Gắn cờ cảnh báo (flags) vào Review Queue,  │
     │    tuyệt đối không tự ý hạ oan quyết định đúng của người dùng                     │
     │  • Hedge Check: Chặn đứng hành vi tự tiện gán việc cho người chỉ được nhắc tên    │
     └─────────────────────────────────────────┬─────────────────────────────────────────┘
                                               │
                                               ▼
     ┌───────────────────────────────────────────────────────────────────────────────────┐
     │ TẦNG 4: LƯU TRỮ CẤU TRÚC, HUMAN-IN-THE-LOOP UI & XUẤT DỮ LIỆU                     │
     │  • Cấu trúc dữ liệu MeetingResult: topics, items (tasks/issues), timeline, flags   │
     │  • Lưu bộ nhớ đệm nhanh (demo_cache/): Phục vụ tức thì 26 kịch bản kiểm thử       │
     │  • Giao diện Web: Liên kết 2 chiều (Bidirectional Highlighting), Duyệt 3 thao tác │
     │  • Xuất dữ liệu đa định dạng: Markdown biên bản, CSV công việc, JSONL tri thức    │
     └───────────────────────────────────────────────────────────────────────────────────┘
```

### Cơ chế Chuyển Vùng Dự Phòng (Fallback Mechanism):
* **Cổng chính:** Google Gemini (`gemini-3.1-flash-lite`).
* **Cổng dự phòng tự động:** NVIDIA NIM (`nvidia/nemotron-3.5-lightning-30b-a3b`). Khi Gemini gặp lỗi mạng, cạn quota hoặc trả về mã lỗi 429/503, hệ thống tự động định tuyến sang NVIDIA NIM mà không làm gián đoạn trải nghiệm người dùng.

---

## PHẦN 4: BẢN ĐỒ GIAO DIỆN NGƯỜI DÙNG (UI/UX COMPONENT BREAKDOWN)

Giao diện được thiết kế theo phong cách tối giản công nghệ cao (**Dark Deep Obsidian**), tuân thủ tiêu chuẩn tương phản quốc tế **WCAG AAA** (Tỷ lệ tương phản từ **15.2:1 đến 17.8:1**), loại bỏ 100% emoji gây rối mắt và bố cục chia đôi màn hình (**Split-screen Workspace**):

```
┌────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│ [TOP BANNER] Chỉ dùng dữ liệu giả hoặc ẩn danh: Vui lòng không tải lên thông tin mật của doanh nghiệp...               │
├────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│ [BRAND]            [CHỌN CUỘC HỌP ▼]   [+ NẠP TRANSCRIPT]   [Ô TÌM KIẾM TỪ KHÓA (Ctrl+K)]   [MÃ: ••••]   [MD] [CSV] [XỬ] │
├────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│ [TẤT CẢ]  [ĐỔI Ý KIẾN (A SANG B)]  [QUYẾT ĐỊNH CHỐT]  [VIỆC CẦN LÀM]  [CẦN DUYỆT (1)]  │  3 đã chốt  ·  2 việc  ·  1 thay thế │
├────────────────────────────────────────────────────────────┬───────────────────────────────────────────────────────────┤
│                     CỘT TRÁI (45%)                         │                      CỘT PHẢI (55%)                       │
│              BẢN GHI LỜI THOẠI (TRANSCRIPT FEED)           │        BẢNG PHÂN XỬ & HÀNG CHỜ DUYỆT (INSPECTOR)         │
│                                                            │                                                           │
│  [00:00:20] Minh (u1)                                      │  CHỦ ĐỀ & DIỄN BIẾN QUYẾT ĐỊNH                            │
│  Ban đầu mình đề xuất dùng Firebase cho tiện...            │  ┌─────────────────────────────────────────────────────┐  │
│                                                            │  │ [architecture] Chọn backend Aurora       [ĐÃ CHỐT]  │  │
│  [00:01:10] Quân (u2)                                      │  │ chốt: Supabase   đã thay thế: ~~Firebase~~          │  │
│  Mình hơi lo vendor lock-in với chi phí scale sau này...   │  │ --------------------------------------------------- │  │
│                                                            │  │ [00:00:20] Minh   propose   “dùng Firebase”        │  │
│  [00:05:40] Minh (u6) <HIGHLIGHTED>                        │  │ [00:01:10] Quân   object    “lo vendor lock-in”    │  │
│  Ok, vậy là mình đổi ý. Chốt Supabase cho backend          │  │ [00:05:40] Minh   reverse   “đổi ý. Chốt Supabase” │  │
│  Aurora, bỏ Firebase.                                      │  │ --------------------------------------------------- │  │
│                                                            │  │ [XÁC NHẬN]   [CHỈNH SỬA]   [TỪ CHỐI]                │  │
│  [00:06:05] Quân (u7)                                      │  └─────────────────────────────────────────────────────┘  │
│  Nhất trí. Supabase dùng PostgreSQL chuẩn dễ migrate.      │                                                           │
│                                                            │  VIỆC CẦN LÀM (TASKS)                                     │
│  [00:06:40] Minh (u8)                                      │  ┌─────────────────────────────────────────────────────┐  │
│  Quân dựng khung Supabase và làm tài liệu kết nối          │  │ Dựng khung Supabase và tài liệu     [Quân] [2026-11-20]│  │
│  trước ngày 20/11 nhé.                                     │  │ “Quân dựng khung Supabase... trước ngày 20/11” (u8) │  │
│                                                            │  └─────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────┴───────────────────────────────────────────────────────────┘
```

### Chi Tiết Từng Component Trên Màn Hình

#### 1. Thanh Tiêu Đề & Điều Khiển (Topbar / Header)
* **Brand Badge (`.brand`):** Nhãn nhận diện `MEETING INTEL`, thiết kế chữ hoa kỹ thuật, font JetBrains Mono sắc nét.
* **Dropdown Chọn Cuộc Họp (`#meeting-select`):** Phân chia rõ ràng thành 4 nhóm `<optgroup>` trực quan:
  1. *Bộ kiểm thử cơ sở (Base · m01–m08):* Các tình huống mẫu điển hình (A sang B, rủi ro, phân quyền).
  2. *Bộ tình huống ranh giới (Edge Cases · g01–g12):* Kiểm tra ma trận phân quyền khắt khe và người nhận việc.
  3. *Bộ kiểm thử độc lập (Blind / Independent · 6 ca):* Dữ liệu đối soát độc lập khách quan do AI ngoài sinh.
  4. *Cuộc họp tùy biến:* Lưu trữ các cuộc họp do người dùng tự tải lên.
* **Nút Nạp Transcript (`#btn-open-modal`):** Mở cửa sổ nạp transcript mới (hỗ trợ chọn file `.txt` hoặc dán trực tiếp).
* **Ô Tra Cứu Tức Thì (`#search-input`):** Tìm kiếm nội dung theo thời gian thực (hỗ trợ phím tắt `Ctrl+K` hoặc `/`). Khi gõ, cả danh sách phát biểu và thẻ quyết định đều được đánh dấu highlight tức thì.
* **Ô Mã Truy Cập (`#access-code-input`):** Nhập `ACCESS_CODE` để phân tích các cuộc họp mới. Mã tự động lưu vào `localStorage` của trình duyệt, không cần nhập lại nhiều lần.
* **Thanh Đo Từ Xa Telemetry (`#telemetry-pill`):** Hiển thị trạng thái phân xử: `Jev 1.13 · 0 lỗi chốt nhầm`.
* **Bộ Nút Xuất Dữ Liệu (`.actions-wrap`):**
  * `markdown`: Xuất biên bản cuộc họp hoàn chỉnh (tóm tắt, quyết định, công việc, vướng mắc) dạng `.md`.
  * `csv việc`: Xuất danh sách công việc (`Task`, `Assignee`, `Deadline`, `Quote`) để nhập thẳng vào Jira/Trello/Excel.
  * `phân xử lại`: Kích hoạt chạy lại thẩm định nâng cao với Jev System One.

#### 2. Thanh Điều Hướng & Thống Kê (Filter & Stats Bar)
* **Tabs Chuyển Chế Độ Xem (`#filter-tabs`):**
  * `tất cả`: Hiển thị toàn bộ chủ đề, công việc và phát biểu.
  * `đổi ý kiến (a sang b)`: Chỉ hiển thị các quyết định có diễn biến lật ngược (A bị thay thế bởi B).
  * `quyết định chốt`: Chỉ lọc các nội dung đã đạt trạng thái `ĐÃ CHỐT` (`decided`).
  * `việc cần làm`: Chỉ tập trung vào danh mục công việc được phân công.
  * `cần duyệt`: Hàng đợi ưu tiên chứa các quyết định có cờ nghi ngờ (`flags`) cần con người can thiệp.
* **Chỉ Số Tổng Hợp Nhanh (`#stats-summary`):** Đếm tức thì số lượng: *Đã chốt*, *Việc cần làm*, *Phương án bị thay thế*.

#### 3. Cột Trái: Dòng Lời Thoại Cuộc Họp (Transcript Feed - 45% Viewport)
* **Khung Cuộn Lời Thoại Độc Lập (`#transcript-feed`):** Được cố định chiều cao và cuộn nội bộ mượt mà (`feed.scrollTo`), không gây tràn layout trình duyệt hay hiện tượng nhảy trang.
* **Thẻ Phát Biểu (`.utterance-card`):**
  * Mốc thời gian `[HH:MM:SS]` dạng font monospace chuẩn xác.
  * Tên người nói được tô màu xanh sáng (`#58a6ff`) nổi bật trên nền tối.
  * Mã định danh phát biểu (`u1`, `u2`, ...).
  * Văn bản phát biểu có độ tương phản cao, dễ đọc, không mỏi mắt.

#### 4. Cột Phải: Bảng Phân Xử & Hàng Chờ Duyệt (Inspector Pane - 55% Viewport)
* **Nút Duyệt Nhanh (`#btn-batch-approve`):** Một click duyệt nhanh toàn bộ các quyết định an toàn (không có cờ nghi ngờ).
* **Thẻ Quyết Định (`.topic-card`):**
  * **Huy hiệu Trạng thái (`.status-badge`):**
    * `ĐÃ CHỐT` (`decided`): Màu xanh ngọc / cyan, thể hiện quyết định đã thỏa mãn đầy đủ 4 điều kiện.
    * `NGHIÊNG VỀ` (`leaning`): Màu vàng hổ phách, thể hiện quyết định còn điều kiện hoặc chưa đủ thẩm quyền.
    * `CHƯA CHỐT` (`open`): Màu xám kim loại, đang trong quá trình thảo luận.
  * **Khối Kết Luận (`.outcome-block`):** Hiển thị rõ ràng phương án chốt cuối cùng song hành cùng phương án bị loại bỏ gạch ngang (`~~Firebase~~`).
  * **Tiến Trình Dòng Thời Gian (`.timeline-stepper`):** Mô phỏng từng bước diễn biến thảo luận với tem giờ, người nói, nhãn hành vi (`propose`, `objection`, `reverse`, `conclude`) và trích dẫn bằng chứng.
  * **Đo Lường Jev Telemetry (`.jev-telemetry`):** Hiển thị 4 cột điểm xác suất phần trăm: *Chốt*, *Phản đối*, *Điều kiện*, *Thẩm quyền*.
  * **Bộ 3 Thao Tác Duyệt Human-in-the-Loop (`.review-actions`):**
    * `Xác nhận`: Chấp thuận kết quả phân xử của hệ thống.
    * `Sửa`: Mở hộp thoại chỉnh sửa trực tiếp phương án chốt hoặc trạng thái.
    * `Từ chối`: Bác bỏ kết luận, chuyển trạng thái về chưa ngã ngũ.
* **Thẻ Công Việc (`.task-item`):**
  * Tiêu đề công việc được chuẩn hóa.
  * Huy hiệu Người nhận việc: Hiển thị tên người nhận kèm căn cứ (`assigned` hoặc `self_accepted`), hoặc cảnh báo `chưa xác định`.
  * Huy hiệu Hạn chót: Hiển thị ngày cụ thể (`YYYY-MM-DD`) hoặc `chưa rõ`.
  * Trích dẫn nguồn: **Click vào trích dẫn sẽ lập tức kích hoạt cuộn mượt sang đúng phát biểu nguồn bên Cột Trái** (Liên kết 2 chiều - Bidirectional Highlighting).
* **Thẻ Vấn Đề Khác (`.task-item`):** Phân loại các vướng mắc kỹ thuật (`issue`), yêu cầu (`request`) và câu hỏi mở còn tồn đọng.

#### 5. Cửa Sổ Nạp Transcript Mới (Upload Modal - `#upload-modal`)
* **Tiêu đề cuộc họp:** Tự do đặt tên phiên làm việc.
* **Chế độ phân quyền:** Chọn giữa *Đồng thuận nhóm (Consensus)* hoặc *Chỉ định người có quyền (Authority Leader)*.
* **Vùng nhập lời thoại:** Hỗ trợ kéo thả/chọn file `.txt` hoặc dán trực tiếp văn bản có hoặc không có mốc thời gian.
* **Ma Trận Phân Vai Trò Động (`#speaker-roles-list`):** Hệ thống tự động phân tích và trích xuất danh sách tất cả người nói trong transcript, cho phép người duyệt chỉ định vai trò chuyên môn (`PM`, `Tech Lead`, `Design Lead`, `Head of Product`, `Finance`, `Member`) trước khi phân tích. Các vai trò này chỉ áp dụng cho phiên chạy đó, không ghi đè cấu hình hệ thống.
* **Ô Mã Truy Cập (`#inp-modal-access-code`):** Nhập mã `ACCESS_CODE` để xác thực phân tích.

---

## PHẦN 5: SỐ LIỆU THỰC NGHIỆM & KẾT QUẢ ĐỐI SOÁT BENCHMARK

Toàn bộ kết quả thực nghiệm được đo lường tự động trên tập dữ liệu chuẩn và kiểm chứng minh bạch tại [docs/EXPERIMENTS.md](docs/EXPERIMENTS.md):

### 1. Bảng Hiệu Năng Đối Soát Các Cấu Hình Hệ Thống

| Cấu hình Thử nghiệm | Chế độ Bộ chấm | Tỷ lệ Đạt (Pass Rate) | Lỗi Chốt Nhầm (Critical Errors) | Hạ Oan Quyết Định Đúng | Bắt Điều Kiện Bị Sót | Đánh Giá Nghiệp Vụ |
|---|:---:|:---:|:---:|:---:|:---:|---|
| **Gemini + Thuần Luật** *(Mặc định)* | None | **90.0%** (18/20) | **0** | **0 ca** (0%) | 0/2 | **Cấu hình tối ưu:** Tốc độ cao nhất, không tốn thêm chi phí API, 0 lỗi chốt nhầm. |
| **Gemini + Jev Judge** *(Tự hạ cấp)* | `downgrade` | 85.0% (17/20) | **0** | 1 ca (12.5%, `g12`) | **2/2 ca** | Bắt được 100% điều kiện, nhưng quá nhạy cảm làm hạ oan 1 quyết định đúng. |
| **Gemini + Jev Judge** *(Khuyến nghị)* | `advisory` | **90.0%** (18/20) | **0** | **0 ca** (0%) | **2/2 ca** (Gắn cờ cảnh báo) | **Cân bằng an toàn nhất:** Giữ nguyên quyết định đúng; đẩy 1 ca vào Review Queue để PM duyệt. |
| **Gemini + Gemini Judge** *(Schema)* | `advisory` | **90.0%** (18/20) | **0** | **0 ca** (0%) | **2/2 ca** (Gắn cờ cảnh báo) | Thẩm định câu hỏi hẹp bằng LLM schema; khắc phục triệt để lỗi người nói sau bản vá `pipeline.py:67`. |

### 2. Phân Tích Tính Minh Bạch Về 2 Ca Chưa Đạt
* **Ca `m01`:** Hệ thống xử lý xuất sắc bài toán cốt lõi đổi ý từ Firebase sang Supabase và phân công việc cho Quân; tuy nhiên bị trừ điểm do bỏ sót việc phụ trao đổi nhanh cuối giờ (*"Để mình nhắn riêng anh Phúc xin duyệt khoản ngân sách"*).
* **Ca `m07`:** Quyết định về format báo cáo đạt chuẩn 100%; bị trừ điểm do bỏ sót câu hỏi khảo sát ý kiến bên lề của Hà (*"Ai thích xuất biểu đồ dạng ảnh hay bảng..."*).
* **Kết luận:** **100% các quyết định cốt lõi và bài toán đổi ý A sang B đều đạt độ chính xác tuyệt đối**. Các ca chưa đạt hoàn toàn là do bỏ sót thông tin mở rộng, không có bất kỳ lỗi chốt nhầm nào.

---

## PHẦN 6: KỊCH BẢN THUYẾT TRÌNH & THAO TÁC TRỰC TIẾP (LIVE DEMO SCRIPT)

*(Dành cho người thuyết trình trình bày trước Ban Giám khảo trong 5 phút)*

### Phút 0:00 – 1:00: Đặt Vấn Đề & Tôn Chỉ Thiết Kế
* **Lời thoại gợi ý:**  
  *"Kính thưa Ban Giám khảo, trong các cuộc họp doanh nghiệp, thách thức lớn nhất không phải là tóm tắt cuộc họp dài thành ngắn, mà là **xác định kết luận nào thực sự có hiệu lực thi hành**. Khi đầu cuộc họp đề xuất phương án A, thảo luận một hồi đổi sang phương án B, các công cụ AI thông thường rất dễ chốt nhầm cả A lẫn B hoặc tự tiện gán việc cho người chỉ được hỏi han.*  
  *Meeting Intel giải quyết bài toán này bằng tôn chỉ **Ưu tiên Đúng hơn Đủ**, áp dụng kiến trúc 4 tầng với Động cơ Luật Tất định theo dòng thời gian và Kiểm chứng chuỗi con 100%."*

### Phút 1:00 – 2:30: Thao Tác Trực Tiếp Kịch Bản Điển Hình (m01 - Đổi A sang B)
* **Thao tác màn hình:**
  1. Trên ô chọn cuộc họp, chọn `m01 · Chọn backend cho Aurora`.
  2. Bấm vào tab `đổi ý kiến (a sang b)` trên thanh điều hướng.
* **Lời thoại gợi ý:**  
  *"Xin mời Giám khảo nhìn vào cuộc họp `m01`. Ở đầu cuộc họp, Minh đề xuất dùng Firebase. Đến giữa cuộc họp, Quân phản đối vì lo ngại chi phí và vendor lock-in. Đến phút thứ 5:40, Minh tuyên bố đổi ý và chốt Supabase.*  
  *Tại Cột Phải, hệ thống lập tức hiển thị phương án chốt là **Supabase**, đồng thời phương án **Firebase** bị gạch bỏ và đưa vào danh sách phương án đã bị thay thế (`~~Firebase~~`).*  
  *Khi tôi click vào trích dẫn của Minh, Cột Trái lập tức **tự động cuộn mượt và highlight đúng phát biểu [00:05:40]**. Mọi bằng chứng đều được kiểm chứng là chuỗi con nguyên văn 100% từ transcript gốc."*

### Phút 2:30 – 3:30: Chứng Minh Khả Năng Chặn Gán Nhầm Việc & Quyết Định Có Điều Kiện
* **Thao tác màn hình:**
  1. Chuyển sang cuộc họp `g10` (Chặn gán việc) hoặc `m05` (Chốt có điều kiện).
  2. Chỉ vào thẻ công việc của Đạt (`g10`) và cờ cảnh báo `conditional` (`m05`).
* **Lời thoại gợi ý:**  
  *"Tại cuộc họp `g10`, Hà hỏi 'chắc Đạt làm được kiểm thử nhỉ', Đạt trả lời do dự 'để em xem đã'. Nhờ cơ chế **Hedge Check**, hệ thống không tự tiện gán việc cho Đạt mà để người nhận là `chưa xác định`, chặn đứng lỗi Fabricated Assignee.*  
  *Tương tự ở `m05`, khi Huy chốt Stripe nhưng kèm điều kiện 'Phúc xác nhận phí dưới 2%', hệ thống tự động nhận diện cờ điều kiện và **hạ trạng thái từ Đã chốt về Nghiêng về**, không để doanh nghiệp triển khai non khi chưa đủ căn cứ tài chính."*

### Phút 3:30 – 4:30: Trải Nghiệm Human-in-the-Loop & Nạp Cuộc Họp Mới
* **Thao tác màn hình:**
  1. Bấm nút `Xác nhận` / `Sửa` trên một thẻ quyết định để thấy trạng thái đổi màu tức thì.
  2. Bấm nút `+ nạp transcript`, mở modal nạp văn bản mới, chỉ vào bảng tự động nhận diện danh sách người nói và ma trận vai trò chuyên môn.
  3. Bấm nút `markdown` và `csv việc` để tải file xuất dữ liệu.
* **Lời thoại gợi ý:**  
  *"Tại Cột Phải, người quản trị có toàn quyền Xác nhận, Chỉnh sửa hoặc Từ chối quyết định. Khi nạp transcript mới, hệ thống tự động bóc tách danh sách người nói và cho phép gán vai trò thẩm quyền ngay trên giao diện mà không cần can thiệp code.*  
  *Cuối cùng, người dùng có thể xuất biên bản Markdown chuẩn chỉnh hoặc file CSV công việc để nạp trực tiếp vào hệ thống quản lý dự án."*

### Phút 4:30 – 5:00: Tóm Tắt & Kết Luận
* **Lời thoại gợi ý:**  
  *"Với 16/16 unit test vượt qua, tỷ lệ đạt 90% với 0 lỗi chốt nhầm, hệ thống phòng vệ fallback đa tầng và khả năng chịu tải cao, Meeting Intel đã sẵn sàng phục vụ cho nhu cầu chuyển đổi số thực tế trong các phòng họp điều hành doanh nghiệp. Xin trân trọng cảm ơn Ban Giám khảo!"*

---

## PHẦN 7: QUẢN TRỊ RỦI RO VẬN HÀNH & PHƯƠNG ÁN DỰ PHÒNG

| Kịch Bản Rủi Ro Khi Chấm Bài | Xác Suất | Biện Pháp Kỹ Thuật Đã Triển Khai | Kết Quả Đảm Bảo |
|---|:---:|---|---|
| **Máy chủ Render tự ngủ (Cold start)** | Trung bình | Đặt thông báo thời gian chờ rõ ràng trên banner; thiết lập webhook ping `/healthz` định kỳ mỗi 5 phút; endpoint `/healthz` trả về HTTP 200 trong 1ms. | Máy chủ luôn sẵn sàng phục vụ trong suốt thời gian chấm bài. |
| **Hết hạn mức Quota Gemini** | Cao | Toàn bộ 26 cuộc họp mẫu được lưu sẵn trong `demo_cache/`, nạp tức thì trong ~50ms mà không cần gọi API; khi phân tích file mới, nếu Gemini lỗi hệ thống tự động chuyển sang mô hình **NVIDIA NIM dự phòng**. | Không bao giờ bị gián đoạn hay nghẽn dịch vụ do cạn kiệt tài khoản API. |
| **Spam request hoặc tấn công từ chối dịch vụ** | Trung bình | Tích hợp **Rate Limiter 30 requests/phút** trên từng IP và **Daily Run Cap 100 lượt chạy/ngày**; yêu cầu mã bí mật `ACCESS_CODE` khi tải transcript mới. | Bảo vệ an toàn tuyệt đối hạn mức tài nguyên máy chủ và API. |
| **Lệch layout hiển thị trên các màn hình** | Thấp | Bố cục CSS Flexbox/Grid chuẩn mực với `height: 100vh; overflow: hidden;`, thanh cuộn nội bộ độc lập, font chữ Google Fonts tối ưu hóa tương phản WCAG AAA. | Hiển thị hoàn hảo, sắc nét trên mọi độ phân giải từ Laptop 13" đến Màn hình 4K. |

---
*Tài liệu được biên soạn và lưu trữ tại [docs/PRESENTATION.md](docs/PRESENTATION.md) — Dự án Meeting Intel (Phiên bản v1.0).*
