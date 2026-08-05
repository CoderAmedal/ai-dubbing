/* AI 配音工作台前端逻辑 */
const $ = (id) => document.getElementById(id);

let currentTask = null;
let eventsClosed = false;

/* ---------- 事件绑定 ---------- */
$("startBtn").addEventListener("click", startTask);
$("saveKeyBtn").addEventListener("click", saveApiKey);

/* ---------- API Key 设置 ---------- */
async function saveApiKey() {
  const key = $("apiKey").value.trim();
  if (!key) {
    setKeyStatus("请输入 API Key", "");
    return;
  }
  setKeyStatus("保存中…", "active");
  try {
    const resp = await fetch("/api/settings", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ deepseek_api_key: key }),
    });
    if (!resp.ok) throw new Error("保存失败");
    setKeyStatus("✓ 已保存", "ok");
    $("apiKey").value = "";
  } catch (e) {
    setKeyStatus(String(e.message || e), "");
  }
}

function setKeyStatus(msg, cls) {
  const el = $("keyStatus");
  el.textContent = msg;
  el.className = "status" + (cls ? " " + cls : "");
}

window.addEventListener("load", async () => {
  try {
    const resp = await fetch("/api/settings");
    if (resp.ok) {
      const s = await resp.json();
      if (s.deepseek_api_key) setKeyStatus("✓ API Key 已配置", "ok");
    }
  } catch (e) {
    /* 忽略 */
  }
});

document.querySelectorAll(".chip").forEach((btn) => {
  btn.addEventListener("click", () => {
    $("videoPath").value = btn.dataset.path;
  });
});

$("ttsBackend").addEventListener("change", () => {
  const isSovits = $("ttsBackend").value === "gpt-sovits";
  $("sovitsOpts").classList.toggle("hidden", !isSovits);
});

$("browseBtn").addEventListener("click", async () => {
  // Tauri 桌面环境：使用系统文件对话框
  if (window.__TAURI__ && window.__TAURI__.dialog) {
    try {
      const selected = await window.__TAURI__.dialog.open({
        multiple: false,
        filters: [{ name: "视频", extensions: ["mp4", "webm", "mov", "mkv"] }],
      });
      if (typeof selected === "string") $("videoPath").value = selected;
      return;
    } catch (e) {
      console.warn("Tauri 文件对话框失败，退回手动输入", e);
    }
  }
  // 浏览器环境：提示手动输入完整路径
  alert("请在输入框中填入视频的完整路径（浏览器环境无文件系统访问）。");
});

/* ---------- 任务流程 ---------- */
function setStatus(msg, cls) {
  const el = $("status");
  el.textContent = msg;
  el.className = "status" + (cls ? " " + cls : "");
}

function showProgress(show) {
  $("progressWrap").classList.toggle("hidden", !show);
  if (show) {
    $("result").classList.add("hidden");
    $("error").classList.add("hidden");
  }
}

function setProgress(pct, msg) {
  $("progressFill").style.width = pct + "%";
  $("progressPct").textContent = pct + "%";
  $("progressMsg").textContent = msg || "";
}

async function startTask() {
  const videoPath = $("videoPath").value.trim();
  if (!videoPath) {
    showError("请先输入视频路径");
    return;
  }

  const payload = {
    video_path: videoPath,
    tts_backend: $("ttsBackend").value,
    multi_speaker: $("multiSpeaker").value === "true",
    elastic_timeline: $("elasticTimeline").value === "true",
  };
  if (payload.tts_backend === "gpt-sovits" && !payload.multi_speaker) {
    payload.ref_audio = $("refAudio").value.trim() || undefined;
    payload.prompt_text = $("promptText").value.trim() || "";
  }
  const numSpeakers = parseInt($("numSpeakers").value, 10);
  if (Number.isInteger(numSpeakers) && numSpeakers > 0) payload.num_speakers = numSpeakers;

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
    if (data.status === "failed") {
      showError(data.message || "任务失败");
      return;
    }
    setProgress(data.progress || 0, data.message || "");
  } else if (type === "end") {
    eventsClosed = true;
    if (data.status === "done") {
      fetchResult();
    }
  }
}

async function fetchResult() {
  const resp = await fetch(`/api/tasks/${currentTask}`);
  if (!resp.ok) return;
  const task = await resp.json();
  if (task.status === "done" && task.result) {
    const filename = task.result.split("/").pop();
    const url = `/api/output/${filename}`;
    $("resultVideo").src = url;
    $("openResult").href = url;
    $("result").classList.remove("hidden");
    setProgress(100, "完成");
    setStatus("完成", "");
  }
}

function showError(msg) {
  showProgress(false);
  const el = $("error");
  el.textContent = msg;
  el.classList.remove("hidden");
  setStatus("失败", "");
}
