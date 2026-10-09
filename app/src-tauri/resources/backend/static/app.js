/* AI 配音工作台 — 启动台壳 + 多视图（0008）
 * 布局按 design-pic/index.png 一比一；功能沿用 0007 provider 抽象。
 */
const $ = (id) => document.getElementById(id);

/* ---------- SVG 图标（lucide 风格） ---------- */
const svg = (paths) =>
  `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">${paths}</svg>`;

const ICONS = {
  home: svg('<path d="m3 9 9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/>'),
  download: svg('<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/>'),
  subtitle: svg('<rect x="2" y="4" width="20" height="16" rx="2"/><path d="M6 12h4M14 12h4M6 16h2M12 16h6"/>'),
  pen: svg('<path d="M17 3a2.85 2.83 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5Z"/><path d="m15 5 4 4"/>'),
  mic: svg('<rect x="9" y="2" width="6" height="12" rx="3"/><path d="M5 10a7 7 0 0 0 14 0"/><line x1="12" y1="19" x2="12" y2="22"/>'),
  engine: svg('<rect x="4" y="4" width="16" height="16" rx="2"/><rect x="9" y="9" width="6" height="6"/><path d="M9 2v2M15 2v2M9 20v2M15 20v2M2 9h2M2 15h2M20 9h2M20 15h2"/>'),
  translate: svg('<path d="m5 8 6 6"/><path d="m4 14 6-6 2-3"/><path d="M2 5h12"/><path d="M7 2h1"/><path d="m22 22-5-10-5 10"/><path d="M14 18h6"/>'),
  book: svg('<path d="M4 19.5v-15A2.5 2.5 0 0 1 6.5 2H20v20H6.5a2.5 2.5 0 0 1 0-5H20"/>'),
  wave: svg('<path d="M2 12h2l2-7 3 14 3-10 2 5 2-2h6"/>'),
  gear: svg('<circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 1 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 1 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 1 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 1 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/>'),
  search: svg('<circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/>'),
  film: svg('<rect x="2" y="2" width="20" height="20" rx="2.2"/><path d="M7 2v20M17 2v20M2 12h20M2 7h5M2 17h5M17 17h5M17 7h5"/>'),
  doc: svg('<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="9" y1="13" x2="15" y2="13"/><line x1="9" y1="17" x2="15" y2="17"/>'),
  docCheck: svg('<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><path d="m9 15 2 2 4-4"/>'),
  globe: svg('<circle cx="12" cy="12" r="10"/><path d="M2 12h20"/><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/>'),
  plus: svg('<line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/>'),
  clock: svg('<circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>'),
  zap: svg('<polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>'),
  keyboard: svg('<rect x="2" y="6" width="20" height="12" rx="2"/><path d="M6 10h.01M10 10h.01M14 10h.01M18 10h.01M6 14h.01M18 14h.01M9 14h6"/>'),
  cursor: svg('<path d="m4 4 7.07 16.97 2.51-7.39 7.39-2.51z"/>'),
  layers: svg('<polygon points="12 2 2 7 12 12 22 7 12 2"/><polyline points="2 17 12 22 22 17"/><polyline points="2 12 12 17 22 12"/>'),
  play: svg('<polygon points="6 3 20 12 6 21 6 3"/>'),
  upload: svg('<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/>'),
  check: svg('<polyline points="20 6 9 17 4 12"/>'),
  link: svg('<path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/>'),
  sliders: svg('<line x1="4" y1="21" x2="4" y2="14"/><line x1="4" y1="10" x2="4" y2="3"/><line x1="12" y1="21" x2="12" y2="12"/><line x1="12" y1="8" x2="12" y2="3"/><line x1="20" y1="21" x2="20" y2="16"/><line x1="20" y1="12" x2="20" y2="3"/><line x1="1" y1="14" x2="7" y2="14"/><line x1="9" y1="8" x2="15" y2="8"/><line x1="17" y1="16" x2="23" y2="16"/>'),
};

/* 视图注册表：分页渲染器在 views-*.js 中挂载（VIEWS.xxx = renderFn） */
const VIEWS = {};

/* ---------- 导航与工具箱配置（顺序按 design-pic：启动台/下载/字幕/校对/合成/配音/引擎/翻译/词库/音色） ---------- */
const NAV = [
  { id: "home", label: "启动台", icon: "home", route: "#/home" },
  { id: "download", label: "下载", icon: "download", route: "#/download" },
  { id: "subtitles", label: "字幕", icon: "subtitle", route: "#/subtitles" },
  { id: "proofread", label: "校对", icon: "pen", route: "#/proofread" },
  { id: "mux", label: "合成", icon: "layers", route: "#/mux" },
  { id: "voice", label: "配音", icon: "mic", route: "#/voice" },
  { id: "engines", label: "引擎", icon: "engine", route: "#/engines" },
  { id: "translate", label: "翻译", icon: "translate", route: "#/translate" },
  { id: "glossary", label: "词库", icon: "book", route: "#/glossary" },
  { id: "voices", label: "音色", icon: "wave", route: "#/voices" },
];
const NAV_BOTTOM = [{ id: "settings", label: "设置", icon: "gear", route: "#/settings" }];

const CREATE_CARDS = [
  {
    mode: "dub", title: "视频 → 配音成片", icon: "film", color: "purple", featured: true,
    desc: "听写、翻译、配音、合成一条龙，全自动出成品视频",
    link: { text: "配置配音引擎 →", route: "#/engines" },
  },
  {
    mode: "bilingual", title: "视频 → 双语字幕", icon: "doc", color: "blue",
    desc: "转写人声并翻译成目标语言，一步到位",
  },
  {
    mode: "srcsrt", title: "视频 → 原文字幕", icon: "subtitle", color: "teal",
    desc: "只转写人声，不翻译",
  },
  {
    mode: "srt", title: "翻译已有字幕", icon: "globe", color: "green",
    desc: "把 SRT 等字幕文件翻译成其它语言",
  },
  {
    mode: "custom", title: "自定义流程", icon: "plus", color: "gray", wide: true,
    desc: "打开向导，自由组合目标与配置，可存为配方",
  },
];

const TOOLS = [
  { id: "download", title: "视频下载", desc: "粘贴链接批量下载在线视频", icon: "download", color: "blue", route: "#/download" },
  { id: "proofread", title: "校对字幕", desc: "逐句检查修改，AI 润色", icon: "docCheck", color: "purple", route: "#/proofread" },
  { id: "mux", title: "合成到视频", desc: "把字幕烧录进画面", icon: "film", color: "teal", route: "#/mux" },
  { id: "tts", title: "配音", desc: "字幕逐条合成语音", icon: "mic", color: "green", route: "#/voice" },
];

const VIEW_TITLES = {
  home: "启动台", download: "下载", subtitles: "字幕", proofread: "校对",
  mux: "合成", voice: "配音", engines: "引擎", translate: "翻译", glossary: "词库",
  voices: "音色", settings: "设置", run: "新建任务",
};

/* ---------- 全局状态 ---------- */
const PROVIDERS = {};
let currentSettings = {};
let currentTask = null;
let eventsClosed = false;
let envStatus = null;
let tasksCache = [];

/* ---------- 初始化 ---------- */
window.addEventListener("load", async () => {
  renderNav();
  bindShell();
  await Promise.all([loadProviders(), loadSettings(), refreshEnv(), refreshTasks(), loadVersion()]);
  route();
});
window.addEventListener("hashchange", route);

function renderNav() {
  $("nav").innerHTML = NAV.map(
    (n) => `<a class="nav-item" data-id="${n.id}" href="${n.route}">${ICONS[n.icon]}<span>${n.label}</span></a>`
  ).join("");
  $("navBottom").innerHTML = NAV_BOTTOM.map(
    (n) => `<a class="nav-item" data-id="${n.id}" href="${n.route}">${ICONS[n.icon]}<span>${n.label}</span></a>`
  ).join("");
}

function setActiveNav(id) {
  document.querySelectorAll(".nav-item").forEach((el) =>
    el.classList.toggle("active", el.dataset.id === id)
  );
}

/* ---------- 路由 ---------- */
function route() {
  const hash = location.hash || "#/home";
  const [path, query] = hash.slice(2).split("?");
  const params = new URLSearchParams(query || "");
  const view = path || "home";

  $("viewTitle").textContent = VIEW_TITLES[view] || "启动台";
  setActiveNav(view === "run" ? "home" : view);
  $("rightPanel").classList.toggle("hidden", view !== "home");

  if (view === "home") renderHome();
  else if (view === "run") renderRun(params);
  else if (view === "settings") renderSettings();
  else if (VIEWS[view]) VIEWS[view](params); // 分页渲染器（views-*.js）
  else renderHome();
}

/* ---------- 启动台首页 ---------- */
function greeting() {
  const h = new Date().getHours();
  if (h < 5) return "凌晨好";
  if (h < 9) return "早上好";
  if (h < 11) return "上午好";
  if (h < 13) return "中午好";
  if (h < 18) return "下午好";
  return "晚上好";
}

function dateLine() {
  const d = new Date();
  const week = ["日", "一", "二", "三", "四", "五", "六"][d.getDay()];
  return `${d.getMonth() + 1}月${d.getDate()}日星期${week}`;
}

function renderHome() {
  const view = $("view");
  view.innerHTML = `
    <div class="greeting">${greeting()}</div>
    <div class="greeting-sub">${dateLine()} · 选择一个任务开始，文件也可以直接拖到卡片上</div>

    <div class="section-title">开始创作</div>
    <div class="cards-grid">
      ${CREATE_CARDS.map((c) => `
        <div class="task-card ${c.featured ? "featured" : ""} ${c.wide ? "wide" : ""}"
             data-mode="${c.mode}" data-drop="1">
          <div class="card-icon ${c.color}">${ICONS[c.icon]}</div>
          <div class="card-title">${c.title}</div>
          <div class="card-desc">${c.desc}</div>
          ${c.link ? `<a class="card-link" href="${c.link.route}" data-link="1">${c.link.text}</a>` : ""}
        </div>`).join("")}
    </div>

    <div class="section-title">最近任务</div>
    <div id="recentTasks"></div>
  `;

  view.querySelectorAll(".task-card").forEach((card) =>
    card.addEventListener("click", (e) => {
      if (e.target.dataset.link) return; // 卡片内链接独立跳转
      location.hash = `#/run?mode=${card.dataset.mode}`;
    })
  );

  renderRecentTasks();
  renderRightPanel();
}

function renderRecentTasks() {
  const wrap = $("recentTasks");
  if (!wrap) return;
  if (!tasksCache.length) {
    wrap.innerHTML = `
      <div class="empty-state">
        ${ICONS.clock}
        <div class="es-title">还没有任务记录，从上面选一个任务开始吧</div>
        <div class="es-sub">完成的任务会出现在这里，把文件拖到上方卡片即可开始</div>
      </div>`;
    return;
  }
  const STATUS_LABEL = { queued: "排队中", running: "运行中", done: "已完成", failed: "失败", cancelled: "已取消" };
  wrap.innerHTML = `<div class="recent-list">
    ${tasksCache.map((t) => {
      const file = t.result ? t.result.split("/").pop() : "";
      const when = new Date(t.created_at * 1000);
      const hh = String(when.getHours()).padStart(2, "0");
      const mm = String(when.getMinutes()).padStart(2, "0");
      return `
      <div class="recent-row">
        <span class="r-status ${t.status}">${STATUS_LABEL[t.status] || t.status}</span>
        <span class="r-name">${t.video_name || "字幕翻译"}</span>
        <span class="r-time">${hh}:${mm}</span>
        <span class="r-msg">${t.message || ""}${t.status === "running" ? ` · ${t.progress}%` : ""}</span>
        ${t.status === "done" && file ? `<a class="r-open" href="/api/output/${file}" target="_blank">查看产物</a>` : ""}
      </div>`;
    }).join("")}
  </div>`;
}

/* ---------- 右侧面板 ---------- */
function renderRightPanel() {
  const panel = $("rightPanel");
  const rows = envStatus ? envStatus.rows : {};
  const envRow = (name, key, linkText, linkRoute) => {
    const r = rows[key] || { ready: false, label: "…", detail: "" };
    const dot = r.ready ? "ok" : "pending";
    return `
      <div class="env-row">
        <span class="env-name">${name}</span>
        <span class="env-status"><span class="env-dot ${dot}"></span>${r.label}</span>
        <a class="env-link" href="${linkRoute}">${linkText} &gt;</a>
      </div>`;
  };

  panel.innerHTML = `
    <div class="rp-bar">🗔 ${tasksCache.length} 条任务</div>

    <div class="rp-card">
      <div class="rp-card-title">环境就绪度
        <span class="badge ${envStatus && envStatus.workable ? "ok" : "warn"}">
          ${envStatus ? (envStatus.workable ? "✓ 可开工" : "待配置") : "…"}
        </span>
      </div>
      ${envRow("语音模型", "asr", "管理", "#/engines")}
      ${envRow("GPU 加速", "gpu", "详情", "#/settings")}
      ${envRow("翻译服务", "translate", "管理", "#/engines")}
      ${envRow("配音服务", "tts", (rows.tts && rows.tts.ready) ? "管理" : "去配置", "#/engines")}
    </div>

    <div class="rp-card">
      <div class="rp-card-title">工具箱</div>
      ${TOOLS.map((t) => `
        <a class="tool-row" href="${t.route}">
          <span class="tool-icon card-icon ${t.color}" style="margin:0">${ICONS[t.icon]}</span>
          <span><div class="tool-name">${t.title}</div><div class="tool-desc">${t.desc}</div></span>
        </a>`).join("")}
    </div>

    <div class="rp-card">
      <div class="rp-card-title">快速上手</div>
      <div class="hint-row">${ICONS.search}全局搜索功能与任务，随处可唤起<kbd>Ctrl K</kbd></div>
      <div class="hint-row">${ICONS.cursor}把文件直接拖到任务卡上，立即开始</div>
      <div class="hint-row">${ICONS.keyboard}查看全部键盘快捷键<kbd>?</kbd></div>
      <div class="hint-row" id="hintSettings" style="cursor:pointer">${ICONS.gear}打开设置<kbd>Ctrl ,</kbd></div>
    </div>
  `;
  const hs = $("hintSettings");
  if (hs) hs.addEventListener("click", () => (location.hash = "#/settings"));
}

/* ---------- 环境就绪度 / 状态栏 / 版本 ---------- */
async function refreshEnv() {
  try {
    const resp = await fetch("/api/env/status");
    envStatus = await resp.json();
  } catch (e) {
    envStatus = null;
  }
  const tts = envStatus ? envStatus.rows.tts : null;
  const gpu = envStatus ? envStatus.rows.gpu : null;
  $("sbEngine").textContent = tts ? `引擎：${tts.ready ? "已就绪" : "未就绪"}` : "引擎：检测失败";
  $("sbGpu").textContent = gpu ? `GPU：${gpu.label}` : "GPU：待检测";
  if (!$("rightPanel").classList.contains("hidden")) renderRightPanel();
}

async function refreshTasks() {
  try {
    const resp = await fetch("/api/tasks");
    const data = await resp.json();
    tasksCache = data.items || [];
  } catch (e) {
    tasksCache = [];
  }
  $("modeHint").textContent = tasksCache.length ? `${tasksCache.length} 条任务` : "待首次任务";
  if ($("recentTasks")) renderRecentTasks();
  if (!$("rightPanel").classList.contains("hidden")) renderRightPanel();
}

async function loadVersion() {
  try {
    const resp = await fetch("/api/health");
    const data = await resp.json();
    $("sbVersion").textContent = `v${data.version}`;
  } catch (e) { /* 忽略 */ }
}

/* ---------- 新建任务页（卡片流程） ---------- */
const RUN_MODES = {
  dub: { title: "视频 → 配音成片", sub: "听写、翻译、配音、合成一条龙，全自动出成品视频", kind: "video", outputMode: "video", options: true },
  bilingual: { title: "视频 → 双语字幕", sub: "转写人声并翻译成目标语言，输出译文字幕（SRT），不配音", kind: "video", outputMode: "bilingual-srt", options: false },
  srcsrt: { title: "视频 → 原文字幕", sub: "只转写人声，不翻译，输出原文字幕（SRT）", kind: "video", outputMode: "src-srt", options: false },
  srt: { title: "翻译已有字幕", sub: "把 SRT 等字幕文件翻译成其它语言", kind: "srt", outputMode: null, options: false },
  custom: { title: "自定义流程", sub: "自由组合目标与配置", kind: "video", outputMode: null, options: true, custom: true },
};

function renderRun(params) {
  const mode = params.get("mode") || "dub";
  const cfg = RUN_MODES[mode] || RUN_MODES.dub;
  const prefill = params.get("path") || "";
  const isSrt = cfg.kind === "srt";

  $("view").innerHTML = `
    <div class="page">
      <div class="page-title">${cfg.title}</div>
      <div class="page-sub">${cfg.sub}</div>

      <section class="card">
        <h2>1. 导入${isSrt ? "字幕" : "视频"}</h2>
        <div class="row">
          <input type="text" id="inputPath" value="${prefill}"
                 placeholder="${isSrt ? "输入 SRT 字幕路径，如 /home/me/subs.srt" : "输入视频路径，如 /home/me/video.mp4"}" />
          <button id="browseBtn" class="btn" title="在桌面上浏览文件">浏览…</button>
        </div>
        ${isSrt ? "" : `
        <div class="row quick">
          <span>快速选择:</span>
          <button class="chip" data-path="assets/demo.mp4">demo.mp4</button>
          <button class="chip" data-path="assets/demo_multi.mp4">demo_multi.mp4</button>
          <button class="chip" data-path="assets/demo_real.mp4">demo_real.mp4</button>
        </div>`}
      </section>

      ${cfg.custom ? `
      <section class="card">
        <h2>2. 输出目标</h2>
        <label class="field">
          <span>产物类型</span>
          <select id="outputMode">
            <option value="video" selected>配音成片（MP4）</option>
            <option value="bilingual-srt">译文字幕（SRT，不配音）</option>
            <option value="src-srt">原文字幕（SRT，不翻译）</option>
          </select>
        </label>
      </section>` : ""}

      ${cfg.options ? `
      <section class="card">
        <h2>${cfg.custom ? "3" : "2"}. 处理选项</h2>
        <label class="field">
          <span>说话人模式</span>
          <select id="multiSpeaker">
            <option value="false" selected>单说话人（默认）</option>
            <option value="true">多说话人（自动分离 + 各自克隆）</option>
          </select>
        </label>
        <label class="field">
          <span>时间轴</span>
          <select id="elasticTimeline">
            <option value="true" selected>弹性时间轴（中文语速自然，推荐）</option>
            <option value="false">硬对齐（按原时间轴）</option>
          </select>
        </label>
        <label class="field">
          <span>预期说话人数（多说话人模式，留空自动检测）</span>
          <input type="number" id="numSpeakers" placeholder="自动检测" min="1" />
        </label>
      </section>` : ""}

      <section class="card">
        <h2>${cfg.custom ? "4" : cfg.options ? "3" : "2"}. 开始处理</h2>
        <div class="row">
          <button id="startBtn" class="btn primary">开始</button>
          <span id="status" class="status">就绪</span>
        </div>
        <div id="progressWrap" class="progress-wrap hidden">
          <div class="progress-bar"><div id="progressFill" class="progress-fill"></div></div>
          <div class="progress-info">
            <span id="progressPct">0%</span>
            <span id="progressMsg"></span>
          </div>
        </div>
        <div id="result" class="result hidden"></div>
        <div id="error" class="error hidden"></div>
      </section>
    </div>
  `;

  $("startBtn").addEventListener("click", () => startTask(cfg));
  $("browseBtn").addEventListener("click", () => browseFile(isSrt));
  document.querySelectorAll(".chip").forEach((btn) =>
    btn.addEventListener("click", () => { $("inputPath").value = btn.dataset.path; })
  );
}

async function browseFile(isSrt) {
  if (window.__TAURI__ && window.__TAURI__.dialog) {
    try {
      const selected = await window.__TAURI__.dialog.open({
        multiple: false,
        filters: [isSrt
          ? { name: "字幕", extensions: ["srt", "ass", "vtt"] }
          : { name: "视频", extensions: ["mp4", "webm", "mov", "mkv"] }],
      });
      if (typeof selected === "string") $("inputPath").value = selected;
      return;
    } catch (e) { /* fall through */ }
  }
  alert("请在输入框中填入文件的完整路径（浏览器环境无文件系统访问）。");
}

async function startTask(cfg) {
  const inputPath = $("inputPath").value.trim();
  if (!inputPath) { showError("请先输入文件路径"); return; }

  try { await saveSettings(); } catch (e) { /* 设置未保存不阻塞任务 */ }

  const payload = {};
  if (cfg.kind === "srt") {
    payload.srt_path = inputPath;
  } else {
    payload.video_path = inputPath;
    payload.output_mode = cfg.custom ? $("outputMode").value : cfg.outputMode;
    if (cfg.options) {
      payload.multi_speaker = $("multiSpeaker").value === "true";
      payload.elastic_timeline = $("elasticTimeline").value === "true";
      const numSpeakers = parseInt($("numSpeakers").value, 10);
      if (Number.isInteger(numSpeakers) && numSpeakers > 0) payload.num_speakers = numSpeakers;
    }
  }

  $("startBtn").disabled = true;
  showProgress(true);
  setProgress(0, "提交任务…");
  setStatus("处理中…", "active");

  try {
    const resp = await fetch("/api/tasks", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!resp.ok) {
      const err = await resp.json().catch(() => ({}));
      throw new Error(err.detail || "提交失败");
    }
    const { task_id } = await resp.json();
    currentTask = task_id;
    await subscribeEvents(task_id);
  } catch (e) {
    showError(String(e.message || e));
  } finally {
    $("startBtn").disabled = false;
  }
}

async function subscribeEvents(taskId) {
  eventsClosed = false;
  const resp = await fetch(`/api/tasks/${taskId}/events`);
  if (!resp.ok || !resp.body) throw new Error("无法连接进度流");
  const reader = resp.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (!eventsClosed) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const parts = buffer.split("\n\n");
    buffer = parts.pop() || "";
    for (const block of parts) {
      let type = "message";
      let data = "";
      for (const line of block.split("\n")) {
        if (line.startsWith("event:")) type = line.slice(6).trim();
        else if (line.startsWith("data:")) data += line.slice(5).trim();
      }
      if (data) handleEvent(type, JSON.parse(data));
    }
  }
}

function handleEvent(type, data) {
  if (type === "progress") {
    if (data.status === "failed") { showError(data.message || "任务失败"); return; }
    setProgress(data.progress || 0, data.message || "");
  } else if (type === "end" && data.status === "done") {
    eventsClosed = true;
    fetchResult();
  }
}

async function fetchResult() {
  const resp = await fetch(`/api/tasks/${currentTask}`);
  if (!resp.ok) return;
  const task = await resp.json();
  if (task.status === "done" && task.result) {
    const filename = task.result.split("/").pop();
    const url = `/api/output/${filename}`;
    const isVideo = filename.endsWith(".mp4");
    const box = $("result");
    box.innerHTML = `
      <p class="ok">✓ 产物已生成</p>
      ${isVideo ? `<video controls src="${url}"></video>` : `<p class="muted">字幕文件：${filename}</p>`}
      <div class="row">
        <a class="btn" href="${url}" target="_blank" ${isVideo ? "" : "download"}>${isVideo ? "打开成片" : "下载字幕"}</a>
        <a class="btn" href="#/home">返回启动台</a>
      </div>`;
    box.classList.remove("hidden");
    setProgress(100, "完成");
    setStatus("完成", "");
    refreshTasks();
  }
}

/* ---------- 设置读写（通用，任务页/配置页共用） ---------- */
function collectSettings() {
  const settings = {};
  for (const stage of ["asr", "translate", "tts"]) {
    const sel = $(`sel-${stage}`);
    if (sel) settings[stage] = { provider: sel.value };
  }
  document.querySelectorAll("[data-stage][data-key]").forEach((el) => {
    const stage = el.dataset.stage;
    if (settings[stage]) settings[stage][el.dataset.key] = el.value;
  });
  const keyEl = $("apiKey");
  if (keyEl) {
    const key = keyEl.value.trim();
    if (key) settings.deepseek_api_key = key;
  }
  return settings;
}

async function saveSettings() {
  const payload = collectSettings();
  if (!Object.keys(payload).length) return;
  const resp = await fetch("/api/settings", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!resp.ok) throw new Error("保存设置失败");
  const s = $("settingsStatus");
  if (s) { s.textContent = "✓ 已保存"; s.className = "status ok"; }
  refreshEnv();
}

async function loadProviders() {
  const resp = await fetch("/api/providers");
  const data = await resp.json();
  Object.assign(PROVIDERS, data);
}

async function loadSettings() {
  const resp = await fetch("/api/settings");
  const data = await resp.json();
  currentSettings = data.providers || {};
}

/* ---------- 设置页 ---------- */
function renderSettings() {
  const gpu = envStatus ? envStatus.rows.gpu : null;
  $("view").innerHTML = `
    <div class="page">
      <div class="page-title">设置</div>
      <div class="page-sub">应用信息与运行环境</div>

      <section class="card">
        <h2>关于</h2>
        <div class="kv-row"><span class="k">产品</span><span>AI 配音工作台 — 本地视频翻译配音</span></div>
        <div class="kv-row"><span class="k">版本</span><span id="kvVersion">…</span></div>
        <div class="kv-row"><span class="k">GPU 加速</span><span>${gpu ? `${gpu.label}（${gpu.detail}）` : "待检测"}</span></div>
      </section>

      <section class="card">
        <h2>键盘快捷键</h2>
        <div class="kv-row"><span class="k">Ctrl K</span><span>全局搜索功能与任务</span></div>
        <div class="kv-row"><span class="k">Ctrl ,</span><span>打开设置</span></div>
        <div class="kv-row"><span class="k">Esc</span><span>返回启动台 / 关闭搜索</span></div>
      </section>

      <section class="card">
        <h2>数据</h2>
        <div class="kv-row"><span class="k">数据目录</span><span id="kvDataDir">…</span></div>
        <div class="kv-row"><span class="k">素材安全</span><span>全部本地处理，素材不出本机</span></div>
      </section>
    </div>
  `;
  fetch("/api/health").then((r) => r.json()).then((d) => { $("kvVersion").textContent = `v${d.version}`; });
  fetch("/api/settings").then((r) => r.json()).then((d) => { $("kvDataDir").textContent = d.data_dir; });
}

/* ---------- 搜索（Ctrl K） ---------- */
const SEARCH_INDEX = [
  ...NAV.map((n) => ({ label: n.label, hint: "页面", icon: n.icon, route: n.route })),
  { label: "设置", hint: "页面", icon: "gear", route: "#/settings" },
  ...CREATE_CARDS.map((c) => ({ label: c.title, hint: "开始创作", icon: c.icon, route: `#/run?mode=${c.mode}` })),
  ...TOOLS.map((t) => ({ label: t.title, hint: "工具箱", icon: t.icon, route: t.route })),
];

function bindShell() {
  $("searchIcon").innerHTML = ICONS.search;
  const input = $("globalSearch");
  input.addEventListener("input", () => renderSearchResults(input.value.trim()));
  input.addEventListener("focus", () => renderSearchResults(input.value.trim()));
  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      const first = $("searchResults").querySelector(".sr-item");
      if (first) { location.hash = first.dataset.route; closeSearch(); }
    } else if (e.key === "Escape") {
      closeSearch(); input.blur();
    }
  });
  document.addEventListener("click", (e) => {
    if (!$("searchBox").contains(e.target)) closeSearch();
  });

  document.addEventListener("keydown", (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") {
      e.preventDefault();
      input.focus(); input.select();
    } else if ((e.ctrlKey || e.metaKey) && e.key === ",") {
      e.preventDefault();
      location.hash = "#/settings";
    } else if (e.key === "Escape" && document.activeElement !== input) {
      location.hash = "#/home";
    }
  });

  $("helpBtn").addEventListener("click", () => (location.hash = "#/settings"));
  $("themeBtn").addEventListener("click", () => { /* 深色主题为唯一主题，保留按钮对齐设计 */ });

  bindDragDrop();
}

function renderSearchResults(q) {
  const box = $("searchResults");
  const items = q
    ? SEARCH_INDEX.filter((i) => i.label.toLowerCase().includes(q.toLowerCase()))
    : SEARCH_INDEX;
  if (!items.length) { box.innerHTML = '<div class="sr-item">无匹配结果</div>'; box.classList.remove("hidden"); return; }
  box.innerHTML = items.slice(0, 10).map((i) => `
    <div class="sr-item" data-route="${i.route}">${ICONS[i.icon]}<span>${i.label}</span><span class="sr-hint">${i.hint}</span></div>
  `).join("");
  box.classList.remove("hidden");
  box.querySelectorAll(".sr-item").forEach((el) =>
    el.addEventListener("click", () => { location.hash = el.dataset.route; closeSearch(); })
  );
}

function closeSearch() {
  $("searchResults").classList.add("hidden");
}

/* ---------- 拖拽文件到卡片 ---------- */
let dropTarget = null;

function bindDragDrop() {
  // 记录鼠标悬停的创作卡片（Tauri 拖放事件只有坐标，无 DOM target）
  document.addEventListener("dragover", (e) => {
    const card = e.target.closest ? e.target.closest("[data-drop]") : null;
    dropTarget = card || null;
    if (card) { e.preventDefault(); card.classList.add("dragover"); }
  });
  document.addEventListener("dragleave", (e) => {
    const card = e.target.closest ? e.target.closest("[data-drop]") : null;
    if (card) card.classList.remove("dragover");
  });
  document.addEventListener("drop", (e) => {
    document.querySelectorAll(".task-card.dragover").forEach((c) => c.classList.remove("dragover"));
    if (dropTarget) e.preventDefault();
  });

  // Tauri 环境：原生拖放事件带真实文件路径
  if (window.__TAURI__ && window.__TAURI__.event) {
    window.__TAURI__.event.listen("tauri://drag-drop", (ev) => {
      const paths = (ev.payload && ev.payload.paths) || [];
      if (!paths.length || !dropTarget) return;
      const mode = dropTarget.dataset.mode;
      location.hash = `#/run?mode=${mode}&path=${encodeURIComponent(paths[0])}`;
      dropTarget = null;
    });
  } else {
    // 浏览器环境：无法取完整路径，提示手动输入
    document.addEventListener("drop", (e) => {
      if (!dropTarget) return;
      alert("浏览器环境无法获取文件完整路径，请在任务页手动输入路径。桌面应用内支持拖放。");
    });
  }
}

/* ---------- 任务页通用工具 ---------- */
function setStatus(msg, cls) {
  const el = $("status");
  if (!el) return;
  el.textContent = msg;
  el.className = "status" + (cls ? " " + cls : "");
}
function showProgress(show) {
  const wrap = $("progressWrap");
  if (!wrap) return;
  wrap.classList.toggle("hidden", !show);
  if (show) { $("result").classList.add("hidden"); $("error").classList.add("hidden"); }
}
function setProgress(pct, msg) {
  if (!$("progressFill")) return;
  $("progressFill").style.width = pct + "%";
  $("progressPct").textContent = pct + "%";
  $("progressMsg").textContent = msg || "";
}
function showError(msg) {
  showProgress(false);
  if (!$("error")) return;
  $("error").textContent = msg;
  $("error").classList.remove("hidden");
  setStatus("失败", "");
}

/* ---------- 视图共享辅助（views-*.js 使用） ---------- */
function escHtml(s) {
  return String(s ?? "").replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c])
  );
}

async function getJSON(url) {
  const resp = await fetch(url);
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({}));
    throw new Error(err.detail || `请求失败 ${resp.status}`);
  }
  return resp.json();
}

async function postJSON(url, body) {
  const resp = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body || {}),
  });
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({}));
    throw new Error(err.detail || `请求失败 ${resp.status}`);
  }
  return resp.json();
}

/* 文件选择：Tauri 原生对话框；浏览器退化 prompt 输入路径 */
async function pickFile(kind) {
  const filters = {
    video: [{ name: "视频", extensions: ["mp4", "webm", "mov", "mkv", "avi", "flv"] }],
    audio: [{ name: "音频", extensions: ["mp3", "wav", "m4a", "aac", "flac", "ogg"] }],
    srt: [{ name: "字幕", extensions: ["srt", "ass", "vtt"] }],
    media: [{ name: "媒体", extensions: ["mp4", "webm", "mov", "mkv", "mp3", "wav", "m4a"] }],
  }[kind] || [];
  if (window.__TAURI__ && window.__TAURI__.dialog) {
    try {
      const selected = await window.__TAURI__.dialog.open({ multiple: false, filters });
      return typeof selected === "string" ? selected : null;
    } catch (e) { /* fall through */ }
  }
  const input = window.prompt("请输入文件完整路径（浏览器环境无文件选择框）:");
  return input && input.trim() ? input.trim() : null;
}

/* 通用任务 SSE 流：onProgress(data) / onEnd(data) */
async function streamTask(taskId, { onProgress, onEnd } = {}) {
  const resp = await fetch(`/api/tasks/${taskId}/events`);
  if (!resp.ok || !resp.body) throw new Error("无法连接进度流");
  const reader = resp.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const parts = buffer.split("\n\n");
    buffer = parts.pop() || "";
    for (const block of parts) {
      let type = "message";
      let data = "";
      for (const line of block.split("\n")) {
        if (line.startsWith("event:")) type = line.slice(6).trim();
        else if (line.startsWith("data:")) data += line.slice(5).trim();
      }
      if (!data) continue;
      const parsed = JSON.parse(data);
      if (type === "progress" && onProgress) onProgress(parsed);
      else if (type === "end" && onEnd) onEnd(parsed);
    }
  }
}

/* 秒 → SRT 时间轴显示 */
function fmtTime(sec) {
  const ms = Math.round(sec * 1000);
  const h = String(Math.floor(ms / 3600000)).padStart(2, "0");
  const m = String(Math.floor((ms % 3600000) / 60000)).padStart(2, "0");
  const s = String(Math.floor((ms % 60000) / 1000)).padStart(2, "0");
  const msec = String(ms % 1000).padStart(3, "0");
  return `${h}:${m}:${s},${msec}`;
}
