/* 配音与合成页面（按 design-pic/配音.png、合成.png）
 * 依赖 app.js 全局：$, VIEWS, ICONS, currentSettings,
 *   getJSON, postJSON, escHtml, pickFile, streamTask, fmtTime, refreshTasks
 * 依赖 views-config.js：splitLayout（仅本文件内聚使用自定义布局）
 */

/* ================================================================
 * 配音页：选字幕(+可选视频) → 左引擎音色 → 右逐行试听修正 → 导出成品
 * ================================================================ */
let dubState = { srt: null, video: null, rows: [], voices: [], rowAudio: {} };

VIEWS.voice = async function renderDub(params) {
  const { items: voices } = await getJSON("/api/voices").catch(() => ({ items: [] }));
  dubState.voices = voices;

  // 支持 #/voice?srt=路径 深链打开字幕
  if (params && params.get("srt") && !dubState.srt) {
    try {
      const r = await getJSON(`/api/subtitles/rows?path=${encodeURIComponent(params.get("srt"))}`);
      dubState.srt = r.path;
      dubState.rows = r.rows;
      renderDubWorkbench();
      return;
    } catch (e) { /* 忽略，回退空态 */ }
  }

  if (!dubState.srt) {
    $("view").innerHTML = `
      <div class="page" style="max-width:860px">
        <div class="task-header">
          <div class="row" style="margin:0">
            <button class="btn primary" id="dubPickSrt">选择字幕</button>
            <button class="btn" id="dubPickVideo">选择视频/音频 (可选)</button>
          </div>
        </div>
        <div class="placeholder" style="height:52%">
          ${ICONS.mic}
          <div class="muted" style="max-width:460px;line-height:2">
            支持 SRT / VTT / ASS 等格式；提供视频可替换或混合音轨并预览效果。<br>
            ① 在左侧挑选引擎与音色，可先试听 → ② 逐条合成语音<br>
            ③ 在右侧列表逐行试听与修正 → ④ 满意后一键导出成品
          </div>
          <button class="btn primary" id="dubPickSrt2">选择字幕</button>
          <div class="muted" style="font-size:12px">也可以把字幕/视频文件直接拖进本页</div>
        </div>
      </div>`;
    $("dubPickSrt").addEventListener("click", dubPickSrt);
    $("dubPickSrt2").addEventListener("click", dubPickSrt);
    $("dubPickVideo").addEventListener("click", dubPickVideo);
    return;
  }
  renderDubWorkbench();
};

async function dubPickSrt() {
  const p = await pickFile("srt");
  if (!p) return;
  try {
    const r = await getJSON(`/api/subtitles/rows?path=${encodeURIComponent(p)}`);
    dubState.srt = r.path;
    dubState.rows = r.rows;
    VIEWS.voice();
  } catch (e) { alert(e.message); }
}

async function dubPickVideo() {
  const p = await pickFile("media");
  if (p) {
    dubState.video = p;
    if (dubState.srt) renderDubWorkbench();
    else VIEWS.voice();
  }
}

function renderDubWorkbench() {
  const tts = currentSettings.tts || {};
  const srtName = dubState.srt.split("/").pop();
  const videoName = dubState.video ? dubState.video.split("/").pop() : null;
  const voiceOpts = dubState.voices.map((v) =>
    `<option value="${v.id}">${escHtml(v.name)}（克隆）</option>`).join("");

  $("view").innerHTML = `
    <div class="page" style="max-width:1100px">
      <div class="task-header">
        <div class="row" style="margin:0;flex-wrap:wrap">
          <button class="btn" id="dubChangeSrt">${ICONS.doc} ${escHtml(srtName)}</button>
          <button class="btn" id="dubChangeVideo">${videoName ? escHtml(videoName) : "选择视频/音频 (可选)"}</button>
        </div>
        <div class="row" style="margin:0">
          <span id="dubStatus" class="status"></span>
          <button class="btn primary" id="dubExportBtn">一键导出成品</button>
        </div>
      </div>

      <div class="dub-layout">
        <aside class="dub-left">
          <div class="rp-card">
            <div class="rp-card-title">配音引擎与音色</div>
            <label class="field"><span>引擎</span>
              <select id="dubEngine">
                <option value="edge-tts" ${(tts.provider || "edge-tts") === "edge-tts" ? "selected" : ""}>Edge TTS（在线免费）</option>
                <option value="gpt-sovits" ${tts.provider === "gpt-sovits" ? "selected" : ""}>GPT-SoVITS（声音克隆）</option>
              </select>
            </label>
            <label class="field" id="dubVoiceWrap"><span>音色</span>
              <select id="dubVoice">
                <option value="">默认音色（${escHtml(tts.voice || "zh-CN-YunxiNeural")}）</option>
                ${voiceOpts}
              </select>
            </label>
            <button class="btn" id="dubTestBtn" style="width:100%">试听当前音色</button>
            <div id="dubTestPreview"></div>
            <div class="muted" style="font-size:12px;margin-top:10px;line-height:1.7">
              在右侧列表逐行试听与修正。满意后点右上角「一键导出成品」。
            </div>
          </div>
        </aside>

        <section class="dub-right">
          <div class="proof-table">
            ${dubState.rows.map((r) => `
              <div class="proof-row dub-row" data-id="${r.id}">
                <span class="p-idx">${r.id + 1}</span>
                <span class="p-time">${fmtTime(r.start)}</span>
                <div class="p-text" contenteditable="true" data-id="${r.id}">${escHtml(r.text)}</div>
                <button class="icon-btn dub-play" data-id="${r.id}" title="合成试听">${ICONS.play}</button>
              </div>`).join("")}
          </div>
        </section>
      </div>
      <div id="dubProgress"></div>
    </div>`;

  $("dubChangeSrt").addEventListener("click", dubPickSrt);
  $("dubChangeVideo").addEventListener("click", dubPickVideo);
  $("dubExportBtn").addEventListener("click", dubExport);

  // 文本编辑同步到 rows
  document.querySelectorAll(".p-text").forEach((el) =>
    el.addEventListener("input", () => {
      const row = dubState.rows.find((r) => r.id === parseInt(el.dataset.id, 10));
      if (row) row.text = el.textContent;
      delete dubState.rowAudio[el.dataset.id]; // 文本变了需重新合成
    })
  );

  // 逐行合成试听
  document.querySelectorAll(".dub-play").forEach((btn) =>
    btn.addEventListener("click", () => dubPlayRow(btn))
  );

  $("dubTestBtn").addEventListener("click", async () => {
    const s = $("dubStatus");
    if (s) { s.textContent = "合成中…"; s.className = "status active"; }
    try {
      const r = await postJSON("/api/tts/synth", { text: "你好，这是当前音色试听。", ...dubOverrides() });
      $("dubTestPreview").innerHTML = `<audio controls autoplay src="${r.url}" style="width:100%;margin-top:8px"></audio>`;
      if (s) s.textContent = "";
    } catch (e) {
      if (s) { s.textContent = `失败: ${e.message}`; s.className = "status"; }
    }
  });
}

function dubOverrides() {
  const engine = $("dubEngine") ? $("dubEngine").value : "edge-tts";
  const voiceId = $("dubVoice") ? $("dubVoice").value : "";
  const overrides = { provider: engine };
  if (voiceId) overrides.voice_id = voiceId;
  return overrides;
}

async function dubPlayRow(btn) {
  const id = parseInt(btn.dataset.id, 10);
  const row = dubState.rows.find((r) => r.id === id);
  if (!row || !row.text.trim()) return;
  btn.disabled = true;
  try {
    let url = dubState.rowAudio[id];
    if (!url) {
      const r = await postJSON("/api/tts/synth", { text: row.text.trim(), ...dubOverrides() });
      url = r.url;
      dubState.rowAudio[id] = url;
    }
    // 在行尾插入播放器
    const rowEl = btn.closest(".dub-row");
    let audio = rowEl.querySelector("audio");
    if (!audio) {
      audio = document.createElement("audio");
      audio.controls = true;
      audio.className = "dub-audio";
      audio.src = url;
      rowEl.appendChild(audio);
    }
    audio.play();
  } catch (e) {
    alert(`合成失败: ${e.message}`);
  } finally {
    btn.disabled = false;
  }
}

async function dubExport() {
  // 先把编辑后的行保存回字幕文件，保证导出与界面一致
  const s = $("dubStatus");
  if (s) { s.textContent = "保存字幕…"; s.className = "status active"; }
  try {
    await postJSON("/api/subtitles/save", { path: dubState.srt, rows: dubState.rows });
  } catch (e) { /* 不阻塞 */ }

  const payload = { srt_path: dubState.srt, ...dubOverrides() };
  if (dubState.video) payload.video_path = dubState.video;

  if (s) { s.textContent = "批量合成中…"; }
  $("dubExportBtn").disabled = true;
  $("dubProgress").innerHTML = `
    <div class="progress-wrap">
      <div class="progress-bar"><div id="dubFill" class="progress-fill"></div></div>
      <div class="progress-info"><span id="dubPct">0%</span><span id="dubMsg"></span></div>
    </div>`;
  try {
    const { task_id } = await postJSON("/api/dub/export", payload);
    await streamTask(task_id, {
      onProgress: (d) => {
        if ($("dubFill")) $("dubFill").style.width = `${d.progress}%`;
        if ($("dubPct")) $("dubPct").textContent = `${d.progress}%`;
        if ($("dubMsg")) $("dubMsg").textContent = d.message || "";
        if (d.status === "failed" && s) { s.textContent = d.message; s.className = "status"; }
      },
      onEnd: async (d) => {
        $("dubExportBtn").disabled = false;
        if (d.status === "done") {
          const task = await getJSON(`/api/tasks/${task_id}`);
          const file = task.result ? task.result.split("/").pop() : "";
          if (s) { s.textContent = "✓ 完成"; s.className = "status ok"; }
          $("dubProgress").innerHTML = `<div class="result"><p class="ok">✓ 成品已导出</p>
            <div class="row"><a class="btn primary" href="/api/output/${file}" target="_blank">打开成品</a>
            <a class="btn" href="#/home">返回启动台</a></div></div>`;
          refreshTasks();
        }
      },
    });
  } catch (e) {
    $("dubExportBtn").disabled = false;
    if (s) { s.textContent = `失败: ${e.message}`; s.className = "status"; }
  }
}

/* ================================================================
 * 合成页：字幕样式编辑器 + 烧录/软封装
 * ================================================================ */
const MUX_PRESETS = {
  "经典白字黑边": { font: "Noto Sans CJK SC", size: 24, color: "#FFFFFF", back_mode: "outline", outline_color: "#000000", outline_width: 2, shadow_color: "#000000", shadow_opacity: 50 },
  "电影字幕": { font: "Noto Serif CJK SC", size: 22, color: "#FFFFFF", back_mode: "outline", outline_color: "#101010", outline_width: 2, shadow_color: "#000000", shadow_opacity: 60 },
  "YouTube风格": { font: "Noto Sans CJK SC", size: 24, color: "#FFFFFF", back_mode: "box", box_color: "#000000", box_opacity: 70, outline_width: 0, shadow_opacity: 0 },
  "黑底白字": { font: "Noto Sans CJK SC", size: 24, color: "#FFFFFF", back_mode: "box", box_color: "#000000", box_opacity: 100, outline_width: 0, shadow_opacity: 0 },
  "清新简约": { font: "Noto Sans CJK SC", size: 22, color: "#F5F5F5", back_mode: "outline", outline_color: "#333333", outline_width: 1, shadow_color: "#000000", shadow_opacity: 30 },
  "醒目加粗": { font: "Noto Sans CJK SC", size: 30, color: "#FFE04B", back_mode: "outline", outline_color: "#000000", outline_width: 3, shadow_color: "#000000", shadow_opacity: 60, bold: true },
};

let muxState = {
  video: null, srt: null, audio: null,
  mode: "burn",
  style: { ...MUX_PRESETS["经典白字黑边"] },
  myStyles: JSON.parse(localStorage.getItem("muxMyStyles") || "[]"),
  running: false,
};

VIEWS.mux = function renderMux(params) {
  // 支持从其他页带参跳转（?srt=xxx&video=xxx）
  if (params) {
    if (params.get("srt")) muxState.srt = params.get("srt");
    if (params.get("video")) muxState.video = params.get("video");
  }
  const s = muxState.style;

  const presetCards = Object.entries(MUX_PRESETS).map(([name, st]) => `
    <div class="preset-card ${presetEqual(s, st) ? "active" : ""}" data-preset="${escHtml(name)}">
      <div class="preset-sample" style="${sampleCss(st)}">字幕 Aa</div>
      <div class="preset-name">${escHtml(name)}</div>
    </div>`).join("");

  const myStyleCards = muxState.myStyles.map((st, i) => `
    <div class="preset-card" data-my="${i}">
      <div class="preset-sample" style="${sampleCss(st)}">字幕 Aa</div>
      <div class="preset-name">${escHtml(st.name || `我的样式 ${i + 1}`)}</div>
    </div>`).join("");

  $("view").innerHTML = `
    <div class="mux-topbar">
      <button class="btn" id="muxPickVideo">${muxState.video ? escHtml(muxState.video.split("/").pop()) : "点击选择视频文件"}</button>
      <button class="btn" id="muxPickSrt">${muxState.srt ? escHtml(muxState.srt.split("/").pop()) : "点击选择字幕文件"}</button>
      <button class="btn" id="muxPickAudio">${muxState.audio ? escHtml(muxState.audio.split("/").pop()) : "配音音轨 (可选)"}</button>
    </div>

    <div class="mux-layout">
      <aside class="mux-left">
        <div class="mux-section">
          <div class="mux-sec-title">字幕样式</div>
          <div class="mux-sec-sub">预设样式</div>
          <div class="preset-grid">${presetCards}</div>
        </div>
        <div class="mux-section">
          <div class="mux-sec-sub">我的样式 (${muxState.myStyles.length})</div>
          ${myStyleCards ? `<div class="preset-grid">${myStyleCards}</div>` : ""}
          <div class="muted" style="font-size:11px;line-height:1.6">微调样式后点「存为我的样式」保存。</div>
          <button class="btn" id="muxSaveStyle" style="width:100%;margin-top:6px;font-size:12px">存为我的样式</button>
        </div>

        <div class="mux-section">
          <div class="mux-sec-sub">基础设置</div>
          <label class="field"><span>字体</span>
            <select id="stFont">
              ${["Noto Sans CJK SC", "Noto Serif CJK SC", "Microsoft YaHei", "PingFang SC"].map((f) => `<option ${s.font === f ? "selected" : ""}>${f}</option>`).join("")}
            </select>
          </label>
          <label class="field"><span>字号</span>
            <input type="number" id="stSize" value="${s.size}" min="12" max="72" />
          </label>
          <label class="field"><span>字体颜色</span>
            <input type="color" id="stColor" value="${s.color}" />
          </label>
        </div>

        <div class="mux-section">
          <div class="mux-sec-sub">样式效果</div>
          <label class="radio-row"><input type="radio" name="backMode" value="outline" ${s.back_mode !== "box" ? "checked" : ""}/> 文字带描边和阴影 <span class="muted">适合大多数视频</span></label>
          <label class="radio-row"><input type="radio" name="backMode" value="box" ${s.back_mode === "box" ? "checked" : ""}/> 文字带底色色块 <span class="muted">画面杂乱时更清晰</span></label>
          <div id="outlineOpts" ${s.back_mode === "box" ? 'style="display:none"' : ""}>
            <label class="field"><span>描边粗细</span><input type="number" id="stOutlineW" value="${s.outline_width}" min="0" max="6" /></label>
            <label class="field"><span>描边颜色</span><input type="color" id="stOutlineC" value="${s.outline_color || "#000000"}" /></label>
            <label class="field"><span>阴影透明度 ${s.shadow_opacity}%</span><input type="range" id="stShadowO" value="${s.shadow_opacity}" min="0" max="100" /></label>
          </div>
          <div id="boxOpts" ${s.back_mode === "box" ? "" : 'style="display:none"'}>
            <label class="field"><span>底色颜色</span><input type="color" id="stBoxC" value="${s.box_color || "#000000"}" /></label>
            <label class="field"><span>底色不透明度 ${s.box_opacity ?? 70}%</span><input type="range" id="stBoxO" value="${s.box_opacity ?? 70}" min="0" max="100" /></label>
          </div>
        </div>
      </aside>

      <section class="mux-right">
        <div class="mux-steps">
          <div class="mux-step ${muxState.video && muxState.srt ? "done" : "active"}"><b>1 选择视频与字幕</b><span class="muted">在上方文件条选择视频和字幕文件，选中后即刻预览</span></div>
          <div class="mux-step active"><b>2 调整字幕样式</b><span class="muted">左侧挑选预设或微调</span></div>
          <div class="mux-step"><b>3 生成视频</b><span class="muted">选择烧录或软封装，确认输出路径后一键生成</span></div>
        </div>

        <div class="mux-preview" id="muxPreview">
          <div class="mux-preview-inner">
            <div class="preset-sample" id="muxSample" style="${sampleCss(s)}">示例字幕文字 Example</div>
          </div>
          <div class="muted" style="font-size:12px;margin-top:8px">样式实时预览</div>
        </div>

        <div class="mux-bottombar">
          <label class="radio-row"><input type="radio" name="muxMode" value="burn" ${muxState.mode === "burn" ? "checked" : ""}/> 烧录硬字幕</label>
          <label class="radio-row"><input type="radio" name="muxMode" value="soft" ${muxState.mode === "soft" ? "checked" : ""}/> 封装软字幕 (MKV)</label>
          <label class="dl-opt"><span>导出画质</span><select id="muxQuality"><option>原画质</option></select></label>
          <label class="dl-opt" style="flex:1"><span>输出路径</span>
            <input type="text" id="muxOut" placeholder="默认：输出目录" />
          </label>
          <button class="btn primary btn-lg" id="muxStartBtn" ${muxState.video && muxState.srt ? "" : "disabled"}>生成视频</button>
        </div>
        <div id="muxProgress"></div>
      </section>
    </div>`;

  bindMux();
};

function presetEqual(a, b) {
  return a.font === b.font && a.size === b.size && a.color === b.color && a.back_mode === b.back_mode;
}

/* 样式 dict → 预览 CSS（HTML 近似模拟烧录效果） */
function sampleCss(st) {
  let css = `font-size:${Math.max(13, st.size * 0.7)}px;color:${st.color};font-weight:${st.bold ? "700" : "500"};`;
  if (st.back_mode === "box") {
    const op = (st.box_opacity ?? 70) / 100;
    css += `background:${hexWithAlpha(st.box_color || "#000000", op)};padding:2px 10px;border-radius:3px;`;
  } else {
    const w = st.outline_width || 0;
    const oc = st.outline_color || "#000000";
    if (w > 0) {
      css += `text-shadow:-${w}px 0 ${oc},${w}px 0 ${oc},0 -${w}px ${oc},0 ${w}px ${oc},-${w}px -${w}px ${oc},${w}px ${w}px ${oc},-${w}px ${w}px ${oc},${w}px -${w}px ${oc};`;
    }
    if ((st.shadow_opacity || 0) > 0) css += `filter:drop-shadow(1px 2px 2px rgba(0,0,0,${st.shadow_opacity / 100}));`;
  }
  return css;
}

function hexWithAlpha(hex, alpha) {
  const h = hex.replace("#", "");
  const r = parseInt(h.slice(0, 2), 16), g = parseInt(h.slice(2, 4), 16), b = parseInt(h.slice(4, 6), 16);
  return `rgba(${r},${g},${b},${alpha})`;
}

function bindMux() {
  const s = muxState.style;
  const refresh = () => {
    const sample = $("muxSample");
    if (sample) sample.style.cssText = sampleCss(s);
    $("muxStartBtn").disabled = !(muxState.video && muxState.srt) || muxState.running;
  };

  $("muxPickVideo").addEventListener("click", async () => {
    const p = await pickFile("video");
    if (p) { muxState.video = p; VIEWS.mux(); }
  });
  $("muxPickSrt").addEventListener("click", async () => {
    const p = await pickFile("srt");
    if (p) { muxState.srt = p; VIEWS.mux(); }
  });
  $("muxPickAudio").addEventListener("click", async () => {
    const p = await pickFile("audio");
    if (p) { muxState.audio = p; VIEWS.mux(); }
  });

  document.querySelectorAll("[data-preset]").forEach((el) =>
    el.addEventListener("click", () => {
      muxState.style = { ...MUX_PRESETS[el.dataset.preset] };
      VIEWS.mux();
    })
  );
  document.querySelectorAll("[data-my]").forEach((el) =>
    el.addEventListener("click", () => {
      muxState.style = { ...muxState.myStyles[parseInt(el.dataset.my, 10)] };
      VIEWS.mux();
    })
  );

  $("muxSaveStyle").addEventListener("click", () => {
    const name = window.prompt("样式名称:", "我的样式");
    if (!name) return;
    muxState.myStyles.push({ ...s, name });
    localStorage.setItem("muxMyStyles", JSON.stringify(muxState.myStyles));
    VIEWS.mux();
  });

  $("stFont").addEventListener("change", (e) => { s.font = e.target.value; refresh(); });
  $("stSize").addEventListener("input", (e) => { s.size = parseInt(e.target.value, 10) || 24; refresh(); });
  $("stColor").addEventListener("input", (e) => { s.color = e.target.value; refresh(); });
  document.querySelectorAll('[name="backMode"]').forEach((r) =>
    r.addEventListener("change", () => {
      s.back_mode = r.value;
      $("outlineOpts").style.display = r.value === "box" ? "none" : "";
      $("boxOpts").style.display = r.value === "box" ? "" : "none";
      refresh();
    })
  );
  $("stOutlineW")?.addEventListener("input", (e) => { s.outline_width = parseInt(e.target.value, 10) || 0; refresh(); });
  $("stOutlineC")?.addEventListener("input", (e) => { s.outline_color = e.target.value; refresh(); });
  $("stShadowO")?.addEventListener("input", (e) => { s.shadow_opacity = parseInt(e.target.value, 10); refresh(); });
  $("stBoxC")?.addEventListener("input", (e) => { s.box_color = e.target.value; refresh(); });
  $("stBoxO")?.addEventListener("input", (e) => { s.box_opacity = parseInt(e.target.value, 10); refresh(); });
  document.querySelectorAll('[name="muxMode"]').forEach((r) =>
    r.addEventListener("change", () => { muxState.mode = r.value; })
  );

  $("muxStartBtn").addEventListener("click", muxStart);
  refresh();
}

async function muxStart() {
  if (muxState.running || !muxState.video || !muxState.srt) return;
  muxState.running = true;
  $("muxStartBtn").disabled = true;
  $("muxProgress").innerHTML = `
    <div class="progress-wrap">
      <div class="progress-bar"><div id="muxFill" class="progress-fill"></div></div>
      <div class="progress-info"><span id="muxPct">0%</span><span id="muxMsg"></span></div>
    </div>`;
  try {
    const payload = {
      video: muxState.video,
      srt: muxState.srt,
      mode: muxState.mode,
      style: muxState.style,
    };
    if (muxState.audio) payload.audio = muxState.audio;
    const out = $("muxOut").value.trim();
    if (out) payload.out = out;
    const { task_id } = await postJSON("/api/mux", payload);
    await streamTask(task_id, {
      onProgress: (d) => {
        if ($("muxFill")) $("muxFill").style.width = `${d.progress}%`;
        if ($("muxPct")) $("muxPct").textContent = `${d.progress}%`;
        if ($("muxMsg")) $("muxMsg").textContent = d.message || "";
      },
      onEnd: async (d) => {
        muxState.running = false;
        $("muxStartBtn").disabled = false;
        if (d.status === "done") {
          const task = await getJSON(`/api/tasks/${task_id}`);
          const file = task.result ? task.result.split("/").pop() : "";
          $("muxProgress").innerHTML = `<div class="result"><p class="ok">✓ 视频已生成</p>
            <div class="row"><a class="btn primary" href="/api/output/${file}" target="_blank">打开视频</a>
            <a class="btn" href="#/home">返回启动台</a></div></div>`;
          refreshTasks();
        } else {
          $("muxProgress").innerHTML = `<div class="error">合成失败</div>`;
        }
      },
    });
  } catch (e) {
    muxState.running = false;
    $("muxStartBtn").disabled = false;
    $("muxProgress").innerHTML = `<div class="error">${escHtml(e.message)}</div>`;
  }
}
