/* 资源库页面：词库 + 音色 — 双栏树布局（按 design-pic/词库.png、音色.png）
 * 依赖 app.js 全局：$, VIEWS, ICONS, PROVIDERS, currentSettings,
 *   getJSON, postJSON, escHtml, pickFile, refreshEnv, loadSettings
 * 依赖 views-config.js：splitLayout, treeItem, bindTree, plannedDetail
 */

/* ================================================================
 * 词库页：多套词库 + 启用开关 + 词条编辑
 * ================================================================ */
let glossaryState = { list: [], selected: null, terms: {} };

VIEWS.glossary = async function renderGlossary() {
  const { items } = await getJSON("/api/glossaries");
  glossaryState.list = items;
  if (!glossaryState.selected && items.length) glossaryState.selected = items[0].name;

  const rows = items.map((g) => `
    <div class="gloss-row ${glossaryState.selected === g.name ? "active" : ""}" data-gloss="${escHtml(g.name)}">
      <span class="tree-label">${escHtml(g.name)}</span>
      <span class="muted" style="font-size:11px">${g.count} 条</span>
      <label class="switch" title="启用后翻译自动生效">
        <input type="checkbox" data-toggle="${escHtml(g.name)}" ${g.enabled ? "checked" : ""}/>
        <span class="slider"></span>
      </label>
    </div>`).join("");

  const left = `
    <div class="tree" id="paneLeft">
      <div class="tree-title">全局词库 <span class="muted" style="font-weight:400;font-size:11px">从上到下优先</span></div>
      ${rows || '<div class="muted" style="padding:12px 8px">还没有词库</div>'}
      <button class="btn" id="newGlossBtn" style="width:100%;margin-top:10px">+ 新建词库</button>
      <div class="muted" style="font-size:11px;padding:12px 4px;line-height:1.7">
        按剧集或领域建立多套词库，需要使用时打开启用开关。词库是全局资源，不需要在每个任务里重复选择。
      </div>
    </div>`;

  $("view").innerHTML = splitLayout(left, '<div class="muted" style="padding:20px">加载中…</div>');

  $("newGlossBtn").addEventListener("click", async () => {
    const name = window.prompt("词库名称（如：剧集名 / 领域名）:");
    if (!name || !name.trim()) return;
    try {
      await postJSON("/api/glossaries", { action: "create", name: name.trim() });
      glossaryState.selected = name.trim();
      VIEWS.glossary();
    } catch (e) { alert(String(e.message || e)); }
  });
  document.querySelectorAll("[data-gloss]").forEach((el) =>
    el.addEventListener("click", (e) => {
      if (e.target.closest(".switch")) return;
      glossaryState.selected = el.dataset.gloss;
      VIEWS.glossary();
    })
  );
  document.querySelectorAll("[data-toggle]").forEach((el) =>
    el.addEventListener("change", async () => {
      await postJSON("/api/glossaries", { action: "toggle", name: el.dataset.toggle, enabled: el.checked });
    })
  );
  document.querySelectorAll("[data-delgloss]").forEach((el) =>
    el.addEventListener("click", async () => {
      if (!window.confirm(`删除词库「${el.dataset.delgloss}」？`)) return;
      await postJSON("/api/glossaries", { action: "delete", name: el.dataset.delgloss });
      glossaryState.selected = null;
      VIEWS.glossary();
    })
  );

  renderGlossaryTerms();
};

async function renderGlossaryTerms() {
  const pane = $("paneRight");
  const name = glossaryState.selected;
  if (!name) {
    pane.innerHTML = `<div class="placeholder" style="height:60%">
      ${ICONS.book}
      <div class="ph-title">选择一个词库</div>
      <div class="muted">词库是全局资源。不需要在每个任务里重复选择。</div>
    </div>`;
    return;
  }
  const { items } = await getJSON(`/api/glossaries/${encodeURIComponent(name)}/terms`);
  glossaryState.terms = items;
  const entries = Object.entries(items);
  pane.innerHTML = `<div class="pane-body">
    <div class="pane-title">${escHtml(name)}
      <button class="btn" data-delgloss="${escHtml(name)}" style="margin-left:auto;font-size:12px;padding:4px 10px">删除词库</button>
    </div>
    <div class="pane-sub">术语固定译法，启用后翻译时自动生效</div>
    <div class="row" style="max-width:640px">
      <input type="text" id="termSrc" placeholder="源语，如 RAG" />
      <input type="text" id="termTgt" placeholder="译语，如 检索增强生成" />
      <button class="btn primary" id="addTermBtn">添加</button>
      <input type="file" id="glossCsv" accept=".csv" style="display:none" />
      <button class="btn" id="importCsvBtn">导入 CSV</button>
    </div>
    <div id="termList" style="max-width:640px">
      ${entries.length
        ? entries.map(([src, tgt]) => `
          <div class="term-row">
            <span>${escHtml(src)} → ${escHtml(tgt)}</span>
            <button class="btn term-del" data-src="${escHtml(src)}">删除</button>
          </div>`).join("")
        : '<p class="muted">暂无术语，添加或导入 CSV</p>'}
    </div>
  </div>`;

  $("addTermBtn").addEventListener("click", async () => {
    const src = $("termSrc").value.trim();
    const tgt = $("termTgt").value.trim();
    if (!src || !tgt) return;
    await postJSON(`/api/glossaries/${encodeURIComponent(name)}/terms`, { items: { [src]: tgt } });
    renderGlossaryTerms();
  });
  $("importCsvBtn").addEventListener("click", () => $("glossCsv").click());
  $("glossCsv").addEventListener("change", async (e) => {
    if (!e.target.files[0]) return;
    const fd = new FormData();
    fd.append("file", e.target.files[0]);
    await fetch(`/api/glossaries/${encodeURIComponent(name)}/import`, { method: "POST", body: fd });
    renderGlossaryTerms();
  });
  pane.querySelectorAll(".term-del").forEach((b) =>
    b.addEventListener("click", async () => {
      await postJSON(`/api/glossaries/${encodeURIComponent(name)}/terms`, { action: "delete", src: b.dataset.src });
      renderGlossaryTerms();
    })
  );
  pane.querySelector("[data-delgloss]")?.addEventListener("click", async (e) => {
    const n = e.target.dataset.delgloss;
    if (!window.confirm(`删除词库「${n}」？`)) return;
    await postJSON("/api/glossaries", { action: "delete", name: n });
    glossaryState.selected = null;
    VIEWS.glossary();
  });
}

/* ================================================================
 * 音色页：TTS 来源树 + 详情 + 我的音色库
 * ================================================================ */
const LOCAL_TTS_PLANNED = ["Kokoro 多语", "VITS 中文 AIShell3", "ZipVoice 声音克隆"];
const ONLINE_TTS_PLANNED = ["OpenAI", "SiliconFlow 硅基流动", "Azure", "豆包语音", "ElevenLabs"];

let voiceState = { selected: "overview", voices: [] };

VIEWS.voices = async function renderVoices() {
  const saved = currentSettings.tts || {};
  const { items: voices } = await getJSON("/api/voices").catch(() => ({ items: [] }));
  voiceState.voices = voices;

  const myVoiceItems = voices.map((v) =>
    treeItem(`voice-${v.id}`, v.name, { active: voiceState.selected === `voice-${v.id}` })
  ).join("");

  const left = `
    <div class="tree" id="paneLeft">
      <div class="tree-title">配音声音</div>
      ${treeItem("overview", "总览", { active: voiceState.selected === "overview" })}
      <div class="tree-section">本地模型</div>
      ${treeItem("gpt-sovits", "GPT-SoVITS 声音克隆", {
        badges: ["声音克隆"],
        active: voiceState.selected === "gpt-sovits",
      })}
      ${LOCAL_TTS_PLANNED.map((n) => treeItem(`planned-${n}`, n, { planned: true, disabled: true })).join("")}
      <div class="tree-section">在线服务</div>
      ${treeItem("edge-tts", "Edge TTS", { badges: ["免费"], active: voiceState.selected === "edge-tts" })}
      ${ONLINE_TTS_PLANNED.map((n) => treeItem(`planned-${n}`, n, { planned: true, disabled: true })).join("")}
      <div class="tree-section">我的音色</div>
      ${myVoiceItems}
      ${treeItem("add-voice", "+ 添加音色", {})}
    </div>`;

  $("view").innerHTML = splitLayout(left, '<div class="muted" style="padding:20px">加载中…</div>');
  bindTree((id) => { voiceState.selected = id; renderVoiceDetail(saved); });
  renderVoiceDetail(saved);

  function renderVoiceDetail(savedCfg) {
    const pane = $("paneRight");
    const sel = voiceState.selected;
    if (sel === "overview") pane.innerHTML = voiceOverview(savedCfg);
    else if (sel === "edge-tts") { pane.innerHTML = edgeTtsDetail(savedCfg); bindTtsDetail("edge-tts"); }
    else if (sel === "gpt-sovits") { pane.innerHTML = sovitsDetail(savedCfg); bindTtsDetail("gpt-sovits"); }
    else if (sel === "add-voice") { pane.innerHTML = addVoiceForm(); bindAddVoice(); }
    else if (sel.startsWith("voice-")) {
      const v = voices.find((x) => `voice-${x.id}` === sel);
      pane.innerHTML = v ? myVoiceDetail(v) : voiceOverview(savedCfg);
      if (v) bindMyVoice(v);
    } else pane.innerHTML = plannedDetail(sel.replace("planned-", ""), "该声音来源将在后续版本接入。");
  }
};

function voiceOverview(saved) {
  const provider = saved.provider || "edge-tts";
  return `<div class="pane-body">
    <div class="pane-title">配音声音总览</div>
    <div class="pane-sub">三类声音来源一览与推荐起步路径</div>
    <div class="rp-card" style="margin-bottom:12px">
      <div class="rp-card-title">当前配音引擎 <span class="badge ok">${escHtml(provider)}</span></div>
      <div class="muted" style="line-height:1.8">
        ${provider === "gpt-sovits"
          ? "正在使用本地音色克隆：配音听起来像原说话人。"
          : "正在使用 Edge TTS 在线合成（免费）。想要「原说话人音色」，可切换到 GPT-SoVITS 声音克隆。"}
      </div>
    </div>
    <div class="rp-card" style="margin-bottom:12px">
      <div class="rp-card-title">起步路径</div>
      <div class="muted" style="line-height:1.8">
        1. 快速出片：选「Edge TTS」，零配置免费合成<br>
        2. 音色克隆：选「GPT-SoVITS 声音克隆」，启动本地服务后克隆原声<br>
        3. 我的音色：保存常用参考音频，配音页随取随用
      </div>
    </div>
  </div>`;
}

function edgeTtsDetail(saved) {
  const isCurrent = (saved.provider || "edge-tts") === "edge-tts";
  return `<div class="pane-body">
    <div class="pane-title">Edge TTS ${isCurrent ? '<span class="badge ok" style="margin-left:8px">当前引擎</span>' : ""}</div>
    <div class="pane-sub">在线语音合成（微软，免费，逐条合成）</div>
    <div class="rp-card" style="max-width:560px">
      <label class="field"><span>音色（voice）</span>
        <input type="text" data-tcfg="voice" value="${escHtml(saved.voice || "zh-CN-YunxiNeural")}" />
        <small class="muted">如 zh-CN-YunxiNeural（男）/ zh-CN-XiaoxiaoNeural（女）/ zh-CN-YunjianNeural 等</small>
      </label>
      <label class="field"><span>语速（rate）</span>
        <input type="text" data-tcfg="rate" value="${escHtml(saved.rate || "+0%")}" />
      </label>
      <div class="row" style="margin-top:14px">
        <button class="btn primary" id="saveTtsBtn">保存并设为当前引擎</button>
        <button class="btn" id="testTtsBtn">试听</button>
        <span id="ttsStatus" class="status"></span>
      </div>
      <div id="ttsPreview"></div>
    </div>
  </div>`;
}

function sovitsDetail(saved) {
  const isCurrent = saved.provider === "gpt-sovits";
  return `<div class="pane-body">
    <div class="pane-title">GPT-SoVITS 声音克隆 ${isCurrent ? '<span class="badge ok" style="margin-left:8px">当前引擎</span>' : ""}</div>
    <div class="pane-sub">本地 few-shot 音色克隆：配音听起来像原说话人。需先启动 GPT-SoVITS 服务（127.0.0.1:9880）。</div>
    <div class="rp-card" style="max-width:560px">
      <label class="field"><span>API 地址</span>
        <input type="text" data-tcfg="api_url" value="${escHtml(saved.api_url || "http://127.0.0.1:9880")}" />
      </label>
      <label class="field"><span>参考音频路径（或在「我的音色」中选用）</span>
        <input type="text" data-tcfg="ref_audio" value="${escHtml(saved.ref_audio || "")}" />
      </label>
      <label class="field"><span>参考音频转写文本</span>
        <input type="text" data-tcfg="prompt_text" value="${escHtml(saved.prompt_text || "")}" />
      </label>
      <label class="field"><span>参考音频语言</span>
        <input type="text" data-tcfg="prompt_lang" value="${escHtml(saved.prompt_lang || "zh")}" />
      </label>
      <div class="row" style="margin-top:14px">
        <button class="btn primary" id="saveTtsBtn">保存并设为当前引擎</button>
        <button class="btn" id="testTtsBtn">试听</button>
        <span id="ttsStatus" class="status"></span>
      </div>
      <div id="ttsPreview"></div>
    </div>
  </div>`;
}

function bindTtsDetail(provider) {
  $("saveTtsBtn")?.addEventListener("click", async () => {
    const cfg = { provider };
    document.querySelectorAll("[data-tcfg]").forEach((el) => { cfg[el.dataset.tcfg] = el.value; });
    await postJSON("/api/settings", { tts: cfg });
    await loadSettings();
    const s = $("ttsStatus");
    if (s) { s.textContent = "✓ 已保存"; s.className = "status ok"; }
    refreshEnv();
  });
  $("testTtsBtn")?.addEventListener("click", async () => {
    const s = $("ttsStatus");
    if (s) { s.textContent = "合成中…"; s.className = "status active"; }
    const overrides = {};
    document.querySelectorAll("[data-tcfg]").forEach((el) => { overrides[el.dataset.tcfg] = el.value; });
    try {
      const r = await postJSON("/api/tts/synth", { text: "你好，这是配音引擎试听。", ...overrides });
      $("ttsPreview").innerHTML = `<audio controls autoplay src="${r.url}" style="width:100%;margin-top:10px"></audio>`;
      if (s) { s.textContent = ""; }
    } catch (e) {
      if (s) { s.textContent = `失败: ${e.message}`; s.className = "status"; }
    }
  });
}

function addVoiceForm() {
  return `<div class="pane-body">
    <div class="pane-title">添加音色</div>
    <div class="pane-sub">上传一段参考音频（3-10 秒清晰人声），配音时用 GPT-SoVITS 克隆该音色</div>
    <div class="rp-card" style="max-width:560px">
      <label class="field"><span>音色名称</span><input type="text" id="voiceName" placeholder="如：旁白君 / 角色A" /></label>
      <label class="field"><span>参考音频</span>
        <div class="row">
          <input type="text" id="voiceRefPath" placeholder="选择音频文件（WAV/MP3）" readonly />
          <button class="btn" id="pickRefBtn">选择文件</button>
        </div>
      </label>
      <label class="field"><span>参考音频转写文本</span><input type="text" id="voicePromptText" placeholder="这段音频里说了什么（提高克隆质量）" /></label>
      <label class="field"><span>语言</span>
        <select id="voiceLang"><option value="zh">中文</option><option value="en">英文</option><option value="ja">日文</option></select>
      </label>
      <div class="row" style="margin-top:14px">
        <button class="btn primary" id="addVoiceBtn">保存音色</button>
        <span id="voiceStatus" class="status"></span>
      </div>
    </div>
  </div>`;
}

function bindAddVoice() {
  let pickedFile = null; // 浏览器环境的 File 对象
  $("pickRefBtn").addEventListener("click", async () => {
    if (window.__TAURI__ && window.__TAURI__.dialog) {
      const p = await pickFile("audio");
      if (p) { $("voiceRefPath").value = p; pickedFile = null; }
    } else {
      const input = document.createElement("input");
      input.type = "file";
      input.accept = "audio/*";
      input.onchange = () => {
        if (input.files[0]) { pickedFile = input.files[0]; $("voiceRefPath").value = input.files[0].name; }
      };
      input.click();
    }
  });
  $("addVoiceBtn").addEventListener("click", async () => {
    const name = $("voiceName").value.trim();
    const promptText = $("voicePromptText").value.trim();
    const lang = $("voiceLang").value;
    const s = $("voiceStatus");
    if (s) { s.textContent = "保存中…"; s.className = "status active"; }
    try {
      if (pickedFile) {
        // 浏览器环境：multipart 上传文件内容
        const fd = new FormData();
        fd.append("file", pickedFile);
        const resp = await fetch(
          `/api/voices?name=${encodeURIComponent(name)}&prompt_text=${encodeURIComponent(promptText)}&prompt_lang=${lang}`,
          { method: "POST", body: fd }
        );
        if (!resp.ok) throw new Error((await resp.json().catch(() => ({}))).detail || "上传失败");
      } else {
        // Tauri 环境：路径直传，后端本地读取
        const path = $("voiceRefPath").value.trim();
        if (!path) { alert("请选择参考音频"); if (s) s.textContent = ""; return; }
        await postJSON("/api/voices/from_path", { path, name, prompt_text: promptText, prompt_lang: lang });
      }
      if (s) { s.textContent = "✓ 已保存"; s.className = "status ok"; }
      setTimeout(() => VIEWS.voices(), 400);
    } catch (e) {
      if (s) { s.textContent = `失败: ${e.message}`; s.className = "status"; }
    }
  });
}

function myVoiceDetail(v) {
  return `<div class="pane-body">
    <div class="pane-title">${escHtml(v.name)}</div>
    <div class="pane-sub">我的音色 · 克隆参考音频</div>
    <div class="rp-card" style="max-width:560px">
      <div class="kv-row"><span class="k">参考音频</span><span style="word-break:break-all">${escHtml(v.ref_audio)}</span></div>
      <div class="kv-row"><span class="k">语言</span><span>${escHtml(v.prompt_lang || "zh")}</span></div>
      <div class="kv-row"><span class="k">转写文本</span><span>${escHtml(v.prompt_text || "（未填写）")}</span></div>
      <div class="row" style="margin-top:14px">
        <button class="btn primary" id="auditionBtn">试听（GPT-SoVITS 克隆）</button>
        <button class="btn" id="delVoiceBtn">删除</button>
        <span id="auditionStatus" class="status"></span>
      </div>
      <div id="auditionPreview"></div>
    </div>
  </div>`;
}

function bindMyVoice(v) {
  $("auditionBtn").addEventListener("click", async () => {
    const s = $("auditionStatus");
    if (s) { s.textContent = "克隆合成中…"; s.className = "status active"; }
    try {
      const r = await postJSON("/api/tts/synth", { text: "你好，这是我的克隆音色试听。", voice_id: v.id });
      $("auditionPreview").innerHTML = `<audio controls autoplay src="${r.url}" style="width:100%;margin-top:10px"></audio>`;
      if (s) s.textContent = "";
    } catch (e) {
      if (s) { s.textContent = `失败: ${e.message}`; s.className = "status"; }
    }
  });
  $("delVoiceBtn").addEventListener("click", async () => {
    if (!window.confirm(`删除音色「${v.name}」？`)) return;
    await fetch(`/api/voices/${v.id}`, { method: "DELETE" });
    voiceState.selected = "overview";
    VIEWS.voices();
  });
}
