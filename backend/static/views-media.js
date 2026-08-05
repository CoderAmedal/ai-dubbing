/* 媒体处理页面：下载 + 字幕 + 校对（按 design-pic/下载.png、字幕.png、校对.png）
 * 依赖 app.js 全局：$, VIEWS, ICONS, PROVIDERS, currentSettings, tasksCache,
 *   getJSON, postJSON, escHtml, pickFile, streamTask, fmtTime, refreshTasks, loadSettings
 */

/* ================================================================
 * 下载页：yt-dlp 引擎卡 + 链接框 + 选项行 + 任务进度
 * ================================================================ */
let dlState = { parsedUrls: [], running: false };

VIEWS.download = async function renderDownload() {
  const engine = await getJSON("/api/download/engine").catch(() => ({ installed: false }));

  $("view").innerHTML = `
    <div class="page" style="max-width:860px">
      <div class="engine-cards">
        <div class="engine-card">
          <div class="engine-card-icon blue">${ICONS.download}</div>
          <div style="flex:1">
            <div style="font-weight:600">yt-dlp <span class="muted" style="font-weight:400;font-size:12px">${escHtml(engine.sites || "")}</span></div>
            <div class="muted" style="font-size:12px;margin-top:3px">
              ${engine.installed ? `已安装 ${escHtml(engine.version)}` : "未安装"}
            </div>
          </div>
          <button class="btn" id="dlCheckUpdate">检查更新</button>
        </div>
      </div>

      <section class="card">
        <h2>视频下载</h2>
        <textarea id="dlText" class="dl-textarea" rows="5"
          placeholder="粘贴视频链接，一行一条&#10;支持从聊天记录等混杂文本中自动识别链接"></textarea>
        <div id="dlParsed"></div>
        <div class="dl-options">
          <label class="dl-opt"><span>保存到</span>
            <input type="text" id="dlDir" placeholder="默认：数据目录 downloads/" />
          </label>
          <label class="dl-opt"><span>清晰度</span>
            <select id="dlQuality">
              <option>最佳</option><option>1080p</option><option>720p</option><option>480p</option><option>仅音频</option>
            </select>
          </label>
          <label class="dl-opt"><span>引擎</span>
            <select id="dlEngine" disabled><option>自动 (按站点路由)</option></select>
          </label>
          <label class="dl-opt"><span>并发数</span>
            <select id="dlConcurrent"><option>1</option><option selected>2</option><option>3</option><option>4</option></select>
          </label>
          <label class="dl-opt check"><input type="checkbox" id="dlSubs" /> 同时下载官方字幕</label>
        </div>
        <div class="row" style="justify-content:flex-end;margin-top:6px">
          <button class="btn" id="dlParseBtn">解析链接</button>
          <button class="btn primary" id="dlStartBtn">直接下载</button>
        </div>
        <div id="dlProgress"></div>
      </section>

      <section class="card" id="dlTasksCard" style="display:none">
        <h2>下载记录</h2>
        <div id="dlTasks"></div>
      </section>
    </div>
  `;

  $("dlCheckUpdate").addEventListener("click", async (e) => {
    e.target.textContent = "检查中…";
    const eng = await getJSON("/api/download/engine").catch(() => null);
    e.target.textContent = eng && eng.installed ? `已是最新 ${eng.version}` : "检查失败";
    setTimeout(() => { e.target.textContent = "检查更新"; }, 2500);
  });

  $("dlParseBtn").addEventListener("click", async () => {
    const text = $("dlText").value;
    const { urls } = await postJSON("/api/downloads/parse", { text });
    dlState.parsedUrls = urls;
    $("dlParsed").innerHTML = urls.length
      ? `<div class="parsed-box">${urls.map((u, i) => `<div class="parsed-row"><span class="muted">${i + 1}.</span> ${escHtml(u)}</div>`).join("")}</div>`
      : '<div class="muted" style="padding:8px 0">未识别到链接</div>';
  });

  $("dlStartBtn").addEventListener("click", async () => {
    if (dlState.running) return;
    const text = $("dlText").value;
    try {
      const r = await postJSON("/api/downloads", {
        text,
        urls: dlState.parsedUrls.length ? dlState.parsedUrls : undefined,
        dir: $("dlDir").value.trim() || undefined,
        quality: $("dlQuality").value,
        subs: $("dlSubs").checked,
      });
      dlState.running = true;
      trackDownload(r.task_id);
    } catch (e) {
      $("dlProgress").innerHTML = `<div class="error">${escHtml(e.message)}</div>`;
    }
  });

  renderDownloadTasks();
};

function trackDownload(taskId) {
  const box = $("dlProgress");
  box.innerHTML = `
    <div class="progress-wrap">
      <div class="progress-bar"><div id="dlFill" class="progress-fill"></div></div>
      <div class="progress-info"><span id="dlPct">0%</span><span id="dlMsg"></span></div>
    </div>`;
  streamTask(taskId, {
    onProgress: (d) => {
      const fill = $("dlFill");
      if (fill) fill.style.width = `${d.progress}%`;
      if ($("dlPct")) $("dlPct").textContent = `${d.progress}%`;
      if ($("dlMsg")) $("dlMsg").textContent = d.message || "";
      if (d.status === "failed") {
        box.innerHTML = `<div class="error">${escHtml(d.message || "下载失败")}</div>`;
        dlState.running = false;
      }
    },
    onEnd: async (d) => {
      dlState.running = false;
      if (d.status === "done") {
        const task = await getJSON(`/api/tasks/${taskId}`);
        box.innerHTML = `<div class="result"><p class="ok">✓ 下载完成</p>
          <p class="muted" style="word-break:break-all">${escHtml(task.result || "")}</p></div>`;
        refreshTasks();
        renderDownloadTasks();
      }
    },
  }).catch(() => { dlState.running = false; });
}

function renderDownloadTasks() {
  const downloads = tasksCache.filter((t) => t.kind === "download");
  if (!downloads.length) return;
  $("dlTasksCard").style.display = "";
  $("dlTasks").innerHTML = downloads.slice(0, 10).map((t) => `
    <div class="recent-row">
      <span class="r-status ${t.status}">${{ queued: "排队中", running: "运行中", done: "已完成", failed: "失败" }[t.status] || t.status}</span>
      <span class="r-msg">${escHtml(t.message || "")}${t.status === "running" ? ` · ${t.progress}%` : ""}</span>
      ${t.status === "done" && t.result ? `<span class="muted" style="font-size:11px;word-break:break-all">${escHtml(t.result)}</span>` : ""}
    </div>`).join("");
}

/* ================================================================
 * 字幕页：顶部配置条 + 导入区 + 运行日志（视频 → 字幕任务）
 * ================================================================ */
let subState = { file: null, running: false, logs: [] };

VIEWS.subtitles = function renderSubtitles() {
  const asr = currentSettings.asr || {};
  const tr = currentSettings.translate || {};
  const asrProviders = PROVIDERS.asr || [];
  const asrP = asrProviders.find((p) => p.name === (asr.provider || "faster-whisper")) || asrProviders[0];
  const modelOpts = ((asrP && asrP.models) || []).map((m) =>
    `<option value="${m.name}" ${m.name === (asr.model || "small") ? "selected" : ""}>${m.name}</option>`).join("");
  const langOpts = [["", "自动检测"], ["en", "英语"], ["zh", "中文"], ["ja", "日语"], ["ko", "韩语"]]
    .map(([v, l]) => `<option value="${v}" ${v === (asr.language || "") ? "selected" : ""}>${l}</option>`).join("");

  $("view").innerHTML = `
    <div class="page" style="max-width:860px">
      <div class="task-header">
        <div>
          <span class="task-title">视频 → 双语字幕</span>
          <span class="badge ok" style="margin-left:8px">新任务</span>
          <div class="muted" style="font-size:12px;margin-top:4px">导入文件后自动保存到最近任务</div>
        </div>
        <div class="row" style="margin:0">
          <button class="btn" id="subImportTop">导入</button>
          <button class="btn" id="subAdvanced">高级选项</button>
        </div>
      </div>

      <div class="config-bar">
        <label class="cfg-item"><span>语音模型</span>
          <select id="subAsrModel">${modelOpts || '<option value="small">small</option>'}</select>
        </label>
        <label class="cfg-item"><span>视频语言</span><select id="subLang">${langOpts}</select></label>
        <label class="cfg-item"><span>翻译成</span><select id="subTarget" disabled><option>简体中文</option></select></label>
        <label class="cfg-item"><span>翻译服务</span>
          <select id="subTrProvider" disabled><option>${escHtml(tr.provider === "deepseek" ? "深度求索" : (tr.provider || "深度求索"))}</option></select>
        </label>
        <label class="cfg-item"><span>输出内容</span>
          <select id="subOutput">
            <option value="bilingual-srt">仅输出翻译字幕</option>
            <option value="src-srt">仅输出原文字幕</option>
            <option value="video">配音成片（MP4）</option>
          </select>
        </label>
      </div>

      <div class="dropzone" id="subDrop">
        <div class="dz-icon">${ICONS.upload}</div>
        <div class="dz-title">${subState.file ? escHtml(subState.file.split("/").pop()) : "导入文件"}</div>
        <div class="muted">支持 MP4 / MKV / MOV / MP3 / WAV 等常见视频与音频格式</div>
        <div class="muted" style="font-size:12px;margin-top:10px">高级参数在右上角 · 点击右下角开始按钮，批量处理并实时查看进度</div>
        <button class="btn primary" id="subImportBtn" style="margin-top:16px">导入</button>
        <div class="muted" style="font-size:12px;margin-top:12px">也可以把媒体文件或文件夹直接拖进本页</div>
      </div>

      <div class="row" style="justify-content:flex-end">
        <button class="btn primary btn-lg" id="subStartBtn" ${subState.file ? "" : "disabled"}>开始任务</button>
      </div>

      <section class="card">
        <h2>运行日志（本任务）</h2>
        <div id="subLog" class="run-log"><span class="muted">暂无日志</span></div>
        <div id="subResult"></div>
      </section>
    </div>
  `;

  const pickMedia = async () => {
    const p = await pickFile("media");
    if (p) {
      subState.file = p;
      VIEWS.subtitles();
    }
  };
  $("subImportBtn").addEventListener("click", pickMedia);
  $("subImportTop").addEventListener("click", pickMedia);
  $("subAdvanced").addEventListener("click", () => { location.hash = "#/engines"; });

  // 页内拖拽（浏览器拖拽仅能拿到 File 名；Tauri 拿真实路径）
  const dz = $("subDrop");
  dz.addEventListener("dragover", (e) => { e.preventDefault(); dz.classList.add("dragover"); });
  dz.addEventListener("dragleave", () => dz.classList.remove("dragover"));
  dz.addEventListener("drop", (e) => { e.preventDefault(); dz.classList.remove("dragover"); });

  $("subStartBtn").addEventListener("click", startSubtitleTask);
};

async function startSubtitleTask() {
  if (subState.running || !subState.file) return;
  // 保存配置条到 settings（真实生效）
  await postJSON("/api/settings", {
    asr: { model: $("subAsrModel").value, language: $("subLang").value },
  }).catch(() => {});
  await loadSettings();

  subState.running = true;
  subState.logs = [];
  const logEl = $("subLog");
  logEl.innerHTML = "";
  $("subStartBtn").disabled = true;

  const appendLog = (msg) => {
    subState.logs.push(msg);
    logEl.innerHTML = subState.logs.map((l) => `<div class="log-line">${escHtml(l)}</div>`).join("");
    logEl.scrollTop = logEl.scrollHeight;
  };

  try {
    const { task_id } = await postJSON("/api/tasks", {
      video_path: subState.file,
      output_mode: $("subOutput").value,
    });
    appendLog("任务已提交");
    await streamTask(task_id, {
      onProgress: (d) => {
        appendLog(`[${d.progress}%] ${d.message || ""}`);
        if (d.status === "failed") {
          appendLog(`失败: ${d.message}`);
          subState.running = false;
          $("subStartBtn").disabled = false;
        }
      },
      onEnd: async (d) => {
        subState.running = false;
        $("subStartBtn").disabled = false;
        if (d.status === "done") {
          const task = await getJSON(`/api/tasks/${task_id}`);
          const file = task.result ? task.result.split("/").pop() : "";
          appendLog("✓ 完成");
          $("subResult").innerHTML = `
            <div class="row" style="margin-top:10px">
              <a class="btn primary" href="/api/output/${file}" target="_blank" download>下载字幕</a>
              <a class="btn" href="#/proofread">去校对</a>
              <a class="btn" href="#/mux">去合成</a>
            </div>`;
          refreshTasks();
        }
      },
    });
  } catch (e) {
    appendLog(`错误: ${e.message}`);
    subState.running = false;
    $("subStartBtn").disabled = false;
  }
}

/* ================================================================
 * 校对页：导入视频/字幕 → 逐行编辑（自动保存）
 * ================================================================ */
let proofState = { path: null, rows: [], dirty: false };

VIEWS.proofread = async function renderProofread(params) {
  // 支持 #/proofread?srt=路径 深链打开字幕
  if (params && params.get("srt") && !proofState.path) {
    try {
      const r = await getJSON(`/api/subtitles/rows?path=${encodeURIComponent(params.get("srt"))}`);
      proofState = { path: r.path, rows: r.rows, dirty: false };
      renderProofEditor();
      return;
    } catch (e) { /* 忽略，回退空态 */ }
  }
  if (!proofState.path) {
    $("view").innerHTML = `
      <div class="placeholder" style="height:62%">
        ${ICONS.docCheck}
        <div class="ph-title">导入视频或字幕</div>
        <div class="muted" style="max-width:420px;line-height:1.9">
          选视频会自动检测关联字幕。也可直接导入字幕或整个文件夹。<br>
          修改自动保存。完成后导出字幕或衔接合成、配音。
        </div>
        <div class="row" style="justify-content:center;margin-top:14px">
          <button class="btn primary" id="proofImportVideo">导入视频</button>
          <button class="btn" id="proofImportSrt">导入字幕</button>
        </div>
        <div class="muted" style="font-size:12px;margin-top:10px">导入视频或字幕文件开始批量校对</div>
        <div id="proofMsg" style="margin-top:12px"></div>
      </div>`;
    $("proofImportVideo").addEventListener("click", () => proofPickVideo());
    $("proofImportSrt").addEventListener("click", () => proofPickSrt());
    return;
  }
  renderProofEditor();
}

async function proofPickVideo() {
  const p = await pickFile("video");
  if (!p) return;
  // 自动检测关联字幕：同 stem .srt 或产物目录 {stem}_zh.srt / {stem}_src.srt
  const stem = p.replace(/\.[^.]+$/, "");
  const candidates = [`${stem}.srt`, `${stem}_zh.srt`, `${stem}_src.srt`];
  for (const c of candidates) {
    try {
      const r = await getJSON(`/api/subtitles/rows?path=${encodeURIComponent(c)}`);
      proofState = { path: r.path, rows: r.rows, dirty: false };
      VIEWS.proofread();
      return;
    } catch (e) { /* 尝试下一个 */ }
  }
  $("proofMsg").innerHTML = `<div class="error">未找到「${escHtml(p.split("/").pop())}」的关联字幕。可先到「字幕」页转写，或直接导入字幕。</div>`;
}

async function proofPickSrt() {
  const p = await pickFile("srt");
  if (!p) return;
  try {
    const r = await getJSON(`/api/subtitles/rows?path=${encodeURIComponent(p)}`);
    proofState = { path: r.path, rows: r.rows, dirty: false };
    VIEWS.proofread();
  } catch (e) {
    $("proofMsg").innerHTML = `<div class="error">${escHtml(e.message)}</div>`;
  }
}

function renderProofEditor() {
  const name = proofState.path.split("/").pop();
  $("view").innerHTML = `
    <div class="page" style="max-width:960px">
      <div class="task-header">
        <div>
          <span class="task-title">${escHtml(name)}</span>
          <div class="muted" style="font-size:12px;margin-top:4px">${proofState.rows.length} 行 · 修改自动保存</div>
        </div>
        <div class="row" style="margin:0">
          <span id="proofSaveStatus" class="status"></span>
          <button class="btn" id="proofClose">关闭</button>
          <a class="btn" href="/api/output/${encodeURIComponent(name)}" target="_blank" download>导出字幕</a>
          <a class="btn" href="#/voice">去配音</a>
          <a class="btn primary" href="#/mux">去合成</a>
        </div>
      </div>
      <div class="proof-table">
        <div class="proof-head"><span>#</span><span>开始</span><span>结束</span><span>文本</span></div>
        ${proofState.rows.map((r) => `
          <div class="proof-row" data-id="${r.id}">
            <span class="p-idx">${r.id + 1}</span>
            <span class="p-time">${fmtTime(r.start)}</span>
            <span class="p-time">${fmtTime(r.end)}</span>
            <div class="p-text" contenteditable="true" data-id="${r.id}">${escHtml(r.text)}</div>
          </div>`).join("")}
      </div>
    </div>`;

  $("proofClose").addEventListener("click", () => {
    proofState = { path: null, rows: [], dirty: false };
    VIEWS.proofread();
  });

  let saveTimer = null;
  document.querySelectorAll(".p-text").forEach((el) =>
    el.addEventListener("input", () => {
      const id = parseInt(el.dataset.id, 10);
      const row = proofState.rows.find((r) => r.id === id);
      if (row) row.text = el.textContent;
      proofState.dirty = true;
      const s = $("proofSaveStatus");
      if (s) { s.textContent = "编辑中…"; s.className = "status active"; }
      clearTimeout(saveTimer);
      saveTimer = setTimeout(proofSave, 800);
    })
  );
}

async function proofSave() {
  if (!proofState.dirty || !proofState.path) return;
  try {
    await postJSON("/api/subtitles/save", { path: proofState.path, rows: proofState.rows });
    proofState.dirty = false;
    const s = $("proofSaveStatus");
    if (s) { s.textContent = "✓ 已自动保存"; s.className = "status ok"; }
  } catch (e) {
    const s = $("proofSaveStatus");
    if (s) { s.textContent = `保存失败: ${e.message}`; s.className = "status"; }
  }
}
