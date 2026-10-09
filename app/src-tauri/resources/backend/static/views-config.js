/* 配置中心页面：引擎（听写）+ 翻译（服务商）— 双栏树布局（按 design-pic/引擎.png、翻译.png）
 * 依赖 app.js 全局：$, VIEWS, ICONS, PROVIDERS, currentSettings, envStatus,
 *   getJSON, postJSON, escHtml, refreshEnv, loadSettings
 */

/* ---------- 双栏布局骨架 ---------- */
function splitLayout(leftHtml, rightHtml) {
  return `<div class="split">
    <aside class="pane-left">${leftHtml}</aside>
    <section class="pane-right" id="paneRight">${rightHtml}</section>
  </div>`;
}

function treeItem(id, label, opts = {}) {
  const badges = (opts.badges || []).map((b) => `<span class="tree-badge">${escHtml(b)}</span>`).join("");
  const dot = opts.status ? `<span class="env-dot ${opts.status}"></span>` : "";
  const cls = ["tree-item", opts.active ? "active" : "", opts.disabled ? "disabled" : ""].join(" ");
  return `<div class="${cls}" data-tree="${escHtml(id)}" data-section="${escHtml(opts.section || "")}">
    ${dot}<span class="tree-label">${escHtml(label)}</span>${badges}
    ${opts.planned ? '<span class="tree-soon">规划中</span>' : ""}
  </div>`;
}

function bindTree(onSelect) {
  document.querySelectorAll("#paneLeft .tree-item, .pane-left .tree-item").forEach((el) =>
    el.addEventListener("click", () => {
      if (el.classList.contains("disabled")) return;
      document.querySelectorAll(".tree-item").forEach((t) => t.classList.remove("active"));
      el.classList.add("active");
      onSelect(el.dataset.tree);
    })
  );
}

function plannedDetail(title, desc) {
  return `<div class="placeholder" style="height:50%">
    <div class="ph-title">${escHtml(title)} · 规划中</div>
    <div class="muted">${escHtml(desc)}</div>
  </div>`;
}

/* ================================================================
 * 引擎页：听写引擎树 + 模型市场
 * ================================================================ */
const ASR_TIERS = [
  { id: "fast", name: "快速档", desc: "速度优先，适合先快速试试效果", mem: "内存 ≥ 2GB", models: ["tiny", "base"] },
  { id: "balanced", name: "均衡档", desc: "日常推荐，准确度与速度兼顾", mem: "内存 ≥ 6GB", models: ["small", "medium"] },
  { id: "hq", name: "高精度档", desc: "准确度优先，对电脑配置要求高", mem: "内存 ≥ 10GB", models: ["large-v3"] },
];
// 云端听写（设计稿列出，本项目尚未接入 → 规划中占位）
const CLOUD_ASR = ["OpenAI", "Groq", "SiliconFlow 硅基流动", "ElevenLabs", "Deepgram", "腾讯云", "阿里云", "Gladia"];

let engineState = { selected: "overview", models: [], filterInstalled: false, search: "" };

VIEWS.engines = async function renderEngines() {
  const asrProviders = (PROVIDERS.asr || []);
  const current = (currentSettings.asr || {}).provider || "faster-whisper";
  engineState.selected = engineState.selected === "overview" ? "overview" : engineState.selected;

  const localItems = asrProviders.map((p) =>
    treeItem(p.name, p.label, {
      section: "本地引擎",
      badges: p.name === "whisper.cpp" ? ["内置", "轻量"] : ["高速", "高精度"],
      active: engineState.selected === p.name,
    })
  ).join("");
  const cloudItems = CLOUD_ASR.map((n) => treeItem(`cloud-${n}`, n, { planned: true, disabled: true })).join("");

  const left = `
    <div class="tree" id="paneLeft">
      <div class="tree-title">听写引擎</div>
      ${treeItem("overview", "总览", { active: engineState.selected === "overview" })}
      <div class="tree-section">本地引擎</div>
      ${localItems}
      <div class="tree-section">云端听写</div>
      ${cloudItems}
      ${treeItem("custom", "添加自定义", { planned: true, disabled: true })}
    </div>`;

  $("view").innerHTML = splitLayout(left, '<div class="muted" style="padding:20px">加载中…</div>');
  bindTree((id) => { engineState.selected = id; renderEngineDetail(); });

  const models = await getJSON("/api/models").catch(() => []);
  engineState.models = models;
  renderEngineDetail();

  function renderEngineDetail() {
    const pane = $("paneRight");
    const sel = engineState.selected;
    if (sel === "overview") {
      pane.innerHTML = engineOverview(current, models);
    } else if (sel.startsWith("cloud-") || sel === "custom") {
      pane.innerHTML = plannedDetail(sel.replace("cloud-", ""), "云端听写服务将在后续版本接入，当前请使用本地引擎。");
    } else {
      pane.innerHTML = engineDetail(sel, models);
      bindEngineDetail(sel);
    }
  }
};

function engineOverview(current, models) {
  const asrRow = envStatus ? envStatus.rows.asr : null;
  const installed = models.filter((m) => m.installed);
  const rows = (PROVIDERS.asr || []).map((p) => {
    const pModels = models.filter((m) => m.provider === p.name);
    const inst = pModels.filter((m) => m.installed);
    const ok = inst.length > 0;
    const cur = current === p.name ? '<span class="badge ok">当前引擎</span>' : "";
    return `<div class="env-row">
      <span class="env-name" style="width:auto;min-width:110px">${escHtml(p.label)}</span>
      <span class="env-status"><span class="env-dot ${ok ? "ok" : "pending"}"></span>${ok ? `已安装 ${inst.length} 个模型` : "未下载模型"}</span>
      ${cur}
    </div>`;
  }).join("");
  return `<div class="pane-body">
    <div class="pane-title">听写引擎总览</div>
    <div class="pane-sub">就绪状态与起步建议</div>
    <div class="rp-card" style="margin-bottom:14px">
      <div class="rp-card-title">就绪状态
        <span class="badge ${asrRow && asrRow.ready ? "ok" : "warn"}">${asrRow ? asrRow.label : "…"}</span>
      </div>
      ${rows}
    </div>
    <div class="rp-card">
      <div class="rp-card-title">起步建议</div>
      <div class="muted" style="line-height:1.8">
        ${installed.length
          ? `已安装 ${installed.map((m) => `${m.provider_label} ${m.model}`).join("、")}，可直接开始转写。`
          : "还没有安装任何模型。建议选择 faster-whisper 的 small 模型起步（约 466MB，CPU 可用）。"}
        <br>追求最高准确度且内存充足（≥10GB）时，可下载 large-v3。
      </div>
    </div>
  </div>`;
}

function recommendModel(models) {
  const mem = envStatus ? envStatus.memory_gb || 0 : 0;
  let name = "base";
  if (mem >= 16) name = "large-v3";
  else if (mem >= 8) name = "medium";
  else if (mem >= 4) name = "small";
  return { name, mem };
}

function engineDetail(providerName, models) {
  const p = (PROVIDERS.asr || []).find((x) => x.name === providerName);
  if (!p) return plannedDetail(providerName, "");
  const pModels = models.filter((m) => m.provider === providerName);
  const installedAny = pModels.some((m) => m.installed);
  const saved = currentSettings.asr || {};
  const isCurrent = (saved.provider || "faster-whisper") === providerName;
  const rec = recommendModel(pModels);
  const recModel = pModels.find((m) => m.model === rec.name);

  const filter = (m) =>
    (!engineState.filterInstalled || m.installed) &&
    (!engineState.search || `${m.model} ${m.description}`.toLowerCase().includes(engineState.search));

  const tiers = ASR_TIERS.map((tier) => {
    const tModels = pModels.filter((m) => tier.models.includes(m.model)).filter(filter);
    if (!tModels.length) return "";
    const rowsHtml = tModels.map((m) => `
      <div class="model-row">
        <span class="model-info"><b>${escHtml(m.model)}</b> <small>${escHtml(m.description)}</small></span>
        <span class="model-size">${escHtml(m.size)}</span>
        ${m.installed
          ? '<span class="model-state installed">✓ 已安装</span>'
          : `<button class="btn model-dl" data-provider="${m.provider}" data-model="${m.model}">下载</button>
             <span class="model-state" id="dl-${m.provider}-${m.model}"></span>`}
      </div>`).join("");
    return `<div class="tier">
      <div class="tier-head"><b>${tier.name}</b><span class="muted">${tier.desc} · ${tier.mem}</span></div>
      ${rowsHtml}
    </div>`;
  }).join("");

  const cfgFields = (p.config_fields || []).map((f) => {
    const val = saved[f.key] || "";
    if (f.type === "select") {
      const opts = (f.options || []).map((o) => `<option value="${o}" ${o === val ? "selected" : ""}>${o}</option>`).join("");
      return `<label class="field"><span>${escHtml(f.label)}</span><select data-acfg="${f.key}">${opts}</select></label>`;
    }
    return `<label class="field"><span>${escHtml(f.label)}</span><input type="text" data-acfg="${f.key}" value="${escHtml(val)}"></label>`;
  }).join("");

  return `<div class="pane-body">
    <div class="pane-title">${escHtml(p.label)}
      <span class="badge ${installedAny ? "ok" : "warn"}" style="margin-left:8px">${installedAny ? "已就绪" : "需下载模型"}</span>
      ${isCurrent ? '<span class="badge ok" style="margin-left:6px">当前引擎</span>' : ""}
    </div>
    <div class="pane-sub">${p.kind === "local" ? "本地引擎，离线运行，素材不出本机。" : "云端引擎"}</div>

    ${recModel && !recModel.installed ? `
    <div class="rec-card">
      <div>为这台电脑推荐：<b>${escHtml(recModel.model)}</b>
        <div class="muted">${escHtml(recModel.description)} · 依据：本机内存 ${rec.mem}GB</div>
      </div>
      <button class="btn primary model-dl" data-provider="${recModel.provider}" data-model="${recModel.model}">一键下载 (${escHtml(recModel.size)})</button>
    </div>` : ""}

    <div class="model-toolbar">
      <div class="search-box" style="max-width:280px;margin:0">
        <span class="search-icon">${ICONS.search}</span>
        <input id="modelSearch" type="text" placeholder="搜索模型名称或描述" value="${escHtml(engineState.search)}" />
      </div>
      <label class="toggle-row"><input type="checkbox" id="filterInstalled" ${engineState.filterInstalled ? "checked" : ""}/> 只看已安装</label>
      <span class="muted" style="margin-left:auto;font-size:12px">模型目录：数据目录 models/</span>
    </div>

    ${tiers || '<p class="muted">无匹配模型</p>'}

    <div class="rp-card" style="margin-top:18px">
      <div class="rp-card-title">引擎配置</div>
      ${cfgFields}
      <div class="row">
        <button class="btn primary" id="saveAsrBtn">保存并设为当前引擎</button>
        <span id="asrSaveStatus" class="status"></span>
      </div>
    </div>
  </div>`;
}

function bindEngineDetail(providerName) {
  $("modelSearch")?.addEventListener("input", (e) => {
    engineState.search = e.target.value.toLowerCase();
    VIEWS.engines.refreshDetail?.(providerName);
  });
  $("filterInstalled")?.addEventListener("change", (e) => {
    engineState.filterInstalled = e.target.checked;
    VIEWS.engines.refreshDetail?.(providerName);
  });
  document.querySelectorAll(".model-dl").forEach((btn) =>
    btn.addEventListener("click", () => startModelDownload(btn.dataset.provider, btn.dataset.model))
  );
  $("saveAsrBtn")?.addEventListener("click", async () => {
    const cfg = { provider: providerName };
    document.querySelectorAll("[data-acfg]").forEach((el) => { cfg[el.dataset.acfg] = el.value; });
    await postJSON("/api/settings", { asr: cfg });
    await loadSettings();
    const s = $("asrSaveStatus");
    if (s) { s.textContent = "✓ 已保存"; s.className = "status ok"; }
    refreshEnv();
  });
}

// 供 toolbar 局部刷新
VIEWS.engines.refreshDetail = function (providerName) {
  const pane = $("paneRight");
  if (pane) {
    pane.innerHTML = engineDetail(providerName, engineState.models);
    bindEngineDetail(providerName);
  }
};

async function startModelDownload(provider, model) {
  const stateEl = $(`dl-${provider}-${model}`);
  const btn = document.querySelector(`.model-dl[data-provider="${provider}"][data-model="${model}"]`);
  if (btn) btn.disabled = true;
  if (stateEl) stateEl.textContent = "下载中…";
  const { key } = await postJSON("/api/models", { provider, model });
  const poll = setInterval(async () => {
    const st = await getJSON(`/api/models/state/${key}`).catch(() => null);
    if (!st) { clearInterval(poll); return; }
    if (stateEl) stateEl.textContent = `${st.progress}% ${st.message || ""}`;
    if (st.status === "done") {
      clearInterval(poll);
      engineState.models = await getJSON("/api/models").catch(() => []);
      VIEWS.engines.refreshDetail?.(provider);
      refreshEnv();
    } else if (st.status === "failed") {
      clearInterval(poll);
      if (stateEl) stateEl.textContent = "下载失败";
      if (btn) btn.disabled = false;
    }
  }, 1500);
}

/* ================================================================
 * 翻译页：服务商树 + 配置表单
 * ================================================================ */
const TRANSLATE_GROUPS = [
  { name: "免费起步", items: ["自动免费翻译", "必应免费翻译", "谷歌免费翻译", "DeepLX", "Ollama"], planned: true },
  { name: "AI 翻译", items: ["深度求索"], planned: false },
  { name: "传统机翻", items: ["百度翻译", "阿里云翻译", "火山翻译", "豆包翻译", "腾讯翻译", "讯飞翻译", "微软翻译"], planned: true },
];

let translateState = { selected: "deepseek", search: "", onlyConfigured: false };

VIEWS.translate = function renderTranslate() {
  const saved = currentSettings.translate || {};
  translateState.selected = saved.provider === "deepseek" ? "deepseek" : translateState.selected;

  const sections = TRANSLATE_GROUPS.map((g) => {
    const items = g.items
      .filter((n) => !translateState.search || n.toLowerCase().includes(translateState.search))
      .map((n) => {
        const isReal = !g.planned;
        const configured = isReal && saved.api_key;
        return treeItem(`tr-${n}`, n, {
          badges: isReal && configured ? ["已配置"] : [],
          planned: !isReal,
          disabled: !isReal,
          active: isReal && translateState.selected === "deepseek",
        });
      }).join("");
    if (!items) return "";
    return `<div class="tree-section">${g.name}</div>${items}`;
  }).join("");

  const left = `
    <div class="tree" id="paneLeft">
      <div class="tree-title">翻译服务</div>
      <div class="search-box" style="margin:0 0 8px;max-width:none">
        <span class="search-icon">${ICONS.search}</span>
        <input id="trSearch" type="text" placeholder="搜索服务商" value="${escHtml(translateState.search)}" />
      </div>
      ${treeItem("overview", "总览", {})}
      ${sections}
    </div>`;

  $("view").innerHTML = splitLayout(left, '<div class="muted" style="padding:20px">加载中…</div>');
  bindTree((id) => {
    translateState.selected = id === "tr-深度求索" ? "deepseek" : id;
    renderTranslateDetail();
  });
  $("trSearch")?.addEventListener("input", (e) => {
    translateState.search = e.target.value.toLowerCase();
    VIEWS.translate();
  });
  renderTranslateDetail();

  function renderTranslateDetail() {
    const pane = $("paneRight");
    if (translateState.selected === "deepseek") {
      pane.innerHTML = deepseekDetail(saved);
      bindDeepseek();
    } else {
      pane.innerHTML = translateOverview(saved);
    }
  }
};

function translateOverview(saved) {
  const configured = !!saved.api_key;
  return `<div class="pane-body">
    <div class="pane-title">翻译服务总览</div>
    <div class="pane-sub">配置状态与起步建议</div>
    <div class="rp-card" style="margin-bottom:14px">
      <div class="rp-card-title">配置状态
        <span class="badge ${configured ? "ok" : "warn"}">${configured ? "已配置" : "未配置"}</span>
      </div>
      <div class="env-row"><span class="env-name" style="width:auto;min-width:110px">深度求索 DeepSeek</span>
        <span class="env-status"><span class="env-dot ${configured ? "ok" : "pending"}"></span>${configured ? "API Key 已配置" : "缺少 API Key"}</span>
      </div>
    </div>
    <div class="rp-card">
      <div class="rp-card-title">起步建议</div>
      <div class="muted" style="line-height:1.8">
        ${configured
          ? "翻译服务已就绪。字幕翻译、配音成片流程会自动使用。"
          : "1. 前往 DeepSeek 开放平台注册并创建 API Key<br>2. 在左侧选择「深度求索」填入 Key 并保存<br>3. 之后所有翻译流程自动生效"}
      </div>
    </div>
  </div>`;
}

function deepseekDetail(saved) {
  return `<div class="pane-body">
    <div class="pane-title">深度求索
      <span class="badge ${saved.api_key ? "ok" : "warn"}" style="margin-left:8px">${saved.api_key ? "已配置" : "未配置"}</span>
    </div>
    <div class="pane-sub">AI 翻译 · OpenAI 兼容接口</div>
    <div class="rp-card" style="max-width:560px">
      <label class="field"><span>Base URL *</span>
        <input type="text" id="dsBaseUrl" value="${escHtml(saved.base_url || "https://api.deepseek.com/v1")}" />
        <small class="muted">DeepSeek API 地址，默认为 https://api.deepseek.com/v1。注册请前往 DeepSeek 开放平台。</small>
      </label>
      <label class="field"><span>API Key *</span>
        <input type="password" id="dsApiKey" value="${escHtml(saved.api_key || "")}" placeholder="sk-..." autocomplete="off" />
        <small class="muted">DeepSeek API Key，可在开放平台创建。仅存本机，不上传。</small>
      </label>
      <label class="field"><span>模型名称 *</span>
        <input type="text" id="dsModel" value="${escHtml(saved.model || "deepseek-chat")}" />
      </label>
      <div class="row" style="margin-top:16px">
        <button class="btn primary" id="dsSave">保存配置</button>
        <span id="dsStatus" class="status"></span>
      </div>
    </div>
  </div>`;
}

function bindDeepseek() {
  $("dsSave")?.addEventListener("click", async () => {
    const cfg = {
      provider: "deepseek",
      base_url: $("dsBaseUrl").value.trim(),
      api_key: $("dsApiKey").value.trim(),
      model: $("dsModel").value.trim(),
    };
    await postJSON("/api/settings", { translate: cfg, deepseek_api_key: cfg.api_key });
    await loadSettings();
    const s = $("dsStatus");
    if (s) { s.textContent = "✓ 已保存"; s.className = "status ok"; }
    refreshEnv();
  });
}
