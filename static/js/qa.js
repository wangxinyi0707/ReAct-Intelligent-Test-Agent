// ============ JWT 认证 ============
let accessToken = localStorage.getItem("qa_access") || "";
let refreshToken = localStorage.getItem("qa_refresh") || "";

function setTokens(data) {
    accessToken = data.access || "";
    refreshToken = data.refresh || "";
    localStorage.setItem("qa_access", accessToken);
    localStorage.setItem("qa_refresh", refreshToken);
}

async function api(path, options = {}, retried = false) {
    const headers = { "Content-Type": "application/json", ...(options.headers || {}) };
    if (accessToken) headers["Authorization"] = `Bearer ${accessToken}`;
    const res = await fetch(path, { ...options, headers });
    if (res.status === 401 && !retried && refreshToken) {
        const ok = await refreshAccess();
        if (ok) return api(path, options, true);
    }
    return res;
}

async function refreshAccess() {
    try {
        const res = await fetch("/api/accounts/login/refresh/", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ refresh: refreshToken }),
        });
        if (!res.ok) throw new Error("refresh failed");
        const data = await res.json();
        setTokens(data);
        return true;
    } catch (e) {
        showLogin();
        return false;
    }
}

function showLogin() {
    document.getElementById("loginMask").classList.remove("hidden");
    document.getElementById("loginMask").classList.add("flex");
}

function logout() {
    localStorage.removeItem("qa_access");
    localStorage.removeItem("qa_refresh");
    accessToken = "";
    location.reload();
}

async function doLogin() {
    const username = document.getElementById("loginUsername").value;
    const password = document.getElementById("loginPassword").value;
    const res = await fetch("/api/accounts/login/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password }),
    });
    const data = await res.json();
    if (!res.ok) {
        const err = document.getElementById("loginError");
        err.textContent = data.detail || "登录失败";
        err.classList.remove("hidden");
        return;
    }
    setTokens(data);
    document.getElementById("loginMask").classList.add("hidden");
    init();
}

// ============ 统计看板 ============
async function loadStats() {
    const res = await api("/api/qa/executions/stats/");
    if (!res.ok) { if (res.status === 401) showLogin(); return; }
    const data = await res.json();
    const cards = document.getElementById("statsCards");
    const latest = data.latest;
    const passRate = latest ? latest.pass_rate : 0;
    cards.innerHTML = `
        <div class="bg-white rounded-lg p-4 shadow text-center">
            <div class="text-3xl font-bold text-blue-600">${data.total_executions}</div>
            <div class="text-gray-500 mt-1">累计执行</div>
        </div>
        <div class="bg-white rounded-lg p-4 shadow text-center">
            <div class="text-3xl font-bold text-green-600">${data.total_cases}</div>
            <div class="text-gray-500 mt-1">启用用例</div>
        </div>
        <div class="bg-white rounded-lg p-4 shadow text-center">
            <div class="text-3xl font-bold text-teal-600">${passRate}%</div>
            <div class="text-gray-500 mt-1">最近通过率</div>
        </div>
        <div class="bg-white rounded-lg p-4 shadow text-center">
            <div class="text-3xl font-bold ${latest && latest.failed > 0 ? "text-red-600" : "text-gray-800"}">
                ${latest ? latest.failed : 0}</div>
            <div class="text-gray-500 mt-1">最近失败数</div>
        </div>`;

    const chart = echarts.init(document.getElementById("trendChart"));
    chart.setOption({
        tooltip: { trigger: "axis" },
        grid: { left: 40, right: 20, top: 20, bottom: 30 },
        xAxis: { type: "category", data: data.trend.map(e => `#${e.id}`).reverse() },
        yAxis: { type: "value", max: 100, axisLabel: { formatter: "{value}%" } },
        series: [{
            name: "通过率",
            type: "line",
            smooth: true,
            data: data.trend.map(e => e.pass_rate).reverse(),
            areaStyle: { opacity: 0.2 },
        }],
    });
}

// ============ 套件 ============
async function loadSuites() {
    const res = await api("/api/qa/suites/");
    if (!res.ok) return;
    const data = await res.json();
    const select = document.getElementById("suiteSelect");
    select.innerHTML = '<option value="">全部用例</option>' +
        data.results.map(s => `<option value="${s.id}">${s.name} (${s.case_count})</option>`).join("");
}

async function createSuite() {
    const name = document.getElementById("newSuiteName").value.trim();
    if (!name) return alert("请输入套件名");
    await api("/api/qa/suites/", {
        method: "POST",
        body: JSON.stringify({ name, description: "" }),
    });
    document.getElementById("newSuiteName").value = "";
    loadSuites();
}

// ============ 用例 ============
async function loadCases() {
    const suite = document.getElementById("suiteSelect").value;
    const url = "/api/qa/cases/" + (suite ? `?suite=${suite}` : "");
    const res = await api(url);
    if (!res.ok) return;
    const data = await res.json();
    const box = document.getElementById("caseTable");
    if (!data.results.length) { box.innerHTML = '<p class="text-gray-400">暂无用例，可在左侧用 AI 生成或手动创建</p>'; return; }
    box.innerHTML = `<table class="w-full">
        <thead><tr class="text-left text-gray-500 border-b">
            <th class="py-2">标题</th><th>类型</th><th>优先级</th><th>来源</th><th>接口</th><th>操作</th>
        </tr></thead><tbody>
        ${data.results.map(c => `<tr class="border-b hover:bg-gray-50">
            <td class="py-2">${c.title}</td>
            <td>${c.case_type === "api" ? "接口" : "手动"}</td>
            <td><span class="px-2 py-0.5 rounded text-xs ${
                c.priority === "P0" ? "bg-red-100 text-red-600" :
                c.priority === "P1" ? "bg-orange-100 text-orange-600" : "bg-gray-100 text-gray-600"}">${c.priority}</span></td>
            <td>${c.source}</td>
            <td class="text-blue-500 text-xs">${c.method} ${c.endpoint}</td>
            <td><button onclick="toggleCase(${c.id}, '${c.status}')" class="text-xs text-indigo-600">${c.status === "active" ? "停用" : "启用"}</button></td>
        </tr>`).join("")}
        </tbody></table>`;
}

async function toggleCase(id, status) {
    await api(`/api/qa/cases/${id}/`, {
        method: "PATCH",
        body: JSON.stringify({ status: status === "active" ? "disabled" : "active" }),
    });
    loadCases();
}

// ============ AI 生成与接口扫描 ============
async function generateCases() {
    const requirement = document.getElementById("requirement").value.trim();
    if (!requirement) return alert("请输入需求描述");
    const count = document.getElementById("generateCount").value;
    const suite = document.getElementById("suiteSelect").value;
    const btn = event.target;
    btn.disabled = true; btn.textContent = "生成中...";
    try {
        const res = await api("/api/qa/cases/generate/", {
            method: "POST",
            body: JSON.stringify({ requirement, count: parseInt(count), suite: suite || null }),
        });
        const data = await res.json();
        if (!res.ok) { alert(data.error || "生成失败"); return; }
        alert(`AI 已生成 ${data.created} 条用例`);
        loadCases();
    } finally {
        btn.disabled = false; btn.textContent = "AI 生成";
    }
}

async function scanApis() {
    const res = await api("/api/qa/cases/scan/");
    if (!res.ok) return;
    const data = await res.json();
    const box = document.getElementById("apiList");
    box.innerHTML = data.apis.map(a => `
        <div class="flex justify-between items-center py-1 border-b">
            <div>
                <span class="text-xs text-teal-600 font-mono">${a.methods.join("/")}</span>
                <span class="font-mono ml-1">${a.path}</span>
                <div class="text-gray-400 text-xs">${a.fields.join(", ") || "无参数定义"}</div>
            </div>
            <button onclick="generateFromApi(${JSON.stringify(a).replace(/"/g, "&quot;")})"
                    class="text-xs bg-teal-100 text-teal-700 px-2 py-1 rounded">AI 生成</button>
        </div>`).join("") || '<p class="text-gray-400">未发现 API</p>';
}

async function generateFromApi(apiObj) {
    const suite = document.getElementById("suiteSelect").value;
    const res = await api("/api/qa/cases/generate-from-api/", {
        method: "POST",
        body: JSON.stringify({ api: apiObj, suite: suite || null }),
    });
    const data = await res.json();
    if (!res.ok) { alert(data.error || "生成失败"); return; }
    alert(`已生成 ${data.created} 条接口用例`);
    loadCases();
}

// ============ 执行 ============
async function loadExecutions() {
    const res = await api("/api/qa/executions/");
    if (!res.ok) return;
    const data = await res.json();
    const box = document.getElementById("executionTable");
    if (!data.results.length) { box.innerHTML = '<p class="text-gray-400">暂无执行记录</p>'; return; }
    box.innerHTML = `<table class="w-full"><thead><tr class="text-left text-gray-500 border-b">
        <th class="py-2">ID</th><th>名称</th><th>状态</th><th>通过/失败/跳过</th><th>通过率</th><th>耗时</th><th>操作</th>
    </tr></thead><tbody>
    ${data.results.map(e => {
        const color = e.status === "passed" ? "text-green-600" : e.status === "failed" ? "text-red-600" : "text-yellow-600";
        return `<tr class="border-b hover:bg-gray-50">
            <td class="py-2">#${e.id}</td>
            <td>${e.name}</td>
            <td class="${color}">${e.status}</td>
            <td>${e.passed} / ${e.failed} / ${e.skipped}</td>
            <td>${e.pass_rate}%</td>
            <td>${e.duration}s</td>
            <td>
                <button onclick="runExecution(${e.id})" class="text-xs bg-blue-100 text-blue-700 px-2 py-1 rounded">执行</button>
                <button onclick="showDetail(${e.id})" class="text-xs bg-gray-100 text-gray-700 px-2 py-1 rounded">详情</button>
            </td>
        </tr>`;
    }).join("")}</tbody></table>`;
}

async function createExecution() {
    const suite = document.getElementById("suiteSelect").value;
    const name = prompt("执行名称：", `执行-${new Date().toLocaleString()}`);
    if (!name) return;
    const res = await api("/api/qa/executions/", {
        method: "POST",
        body: JSON.stringify({ name, suite: suite || null }),
    });
    if (res.ok) loadExecutions();
}

async function runExecution(id) {
    if (!confirm("确认执行？")) return;
    await api(`/api/qa/executions/${id}/run/`, { method: "POST" });
    await Promise.all([loadExecutions(), loadStats()]);
    showDetail(id);
}

async function showDetail(id) {
    const res = await api(`/api/qa/executions/${id}/`);
    if (!res.ok) return;
    const e = await res.json();
    document.getElementById("executionDetail").classList.remove("hidden");
    document.getElementById("executionDetail").classList.add("block");
    document.getElementById("executionDetail").scrollIntoView({ behavior: "smooth" });
    document.getElementById("detailContent").innerHTML = `
        <div class="grid grid-cols-5 gap-2 text-center mb-4">
            <div class="bg-gray-50 rounded p-2">状态<br><b>${e.status}</b></div>
            <div class="bg-gray-50 rounded p-2">通过率<br><b>${e.pass_rate}%</b></div>
            <div class="bg-green-50 rounded p-2">通过<br><b>${e.passed}</b></div>
            <div class="bg-red-50 rounded p-2">失败<br><b>${e.failed}</b></div>
            <div class="bg-yellow-50 rounded p-2">耗时<br><b>${e.duration}s</b></div>
        </div>
        <pre class="bg-gray-900 text-green-300 text-xs p-3 rounded overflow-x-auto max-h-40 mb-4">${escapeHtml(e.summary || "")}</pre>
        <table class="w-full text-sm"><thead><tr class="text-left text-gray-500 border-b">
            <th class="py-2">用例</th><th>结果</th><th>耗时</th><th>日志</th><th>AI 分析</th>
        </tr></thead><tbody>
        ${e.results.map(r => {
            const color = r.status === "passed" ? "text-green-600" : r.status === "failed" ? "text-red-600" : "text-gray-400";
            return `<tr class="border-b align-top">
                <td class="py-2 w-56">${escapeHtml(r.case_title)}</td>
                <td class="${color}">${r.status}</td>
                <td>${r.duration}s</td>
                <td class="text-xs max-w-xs">${escapeHtml(r.log.slice(0, 200))}</td>
                <td class="text-xs max-w-xs">${r.analysis ? `<pre class="bg-indigo-50 p-2 rounded whitespace-pre-wrap">${escapeHtml(r.analysis)}</pre>` : "—"}</td>
            </tr>`;
        }).join("")}</tbody></table>`;
}

function closeDetail() {
    document.getElementById("executionDetail").classList.add("hidden");
    document.getElementById("executionDetail").classList.remove("block");
}

// ============ AI Agent 执行 ============
async function runAgent() {
    const goal = document.getElementById("agentGoal").value.trim();
    if (!goal) return alert("请输入测试目标");
    const btn = event.target;
    btn.disabled = true; btn.textContent = "Agent 执行中...";
    try {
        const res = await api("/api/qa/agent/run/", {
            method: "POST",
            body: JSON.stringify({ goal }),
        });
        const data = await res.json();
        if (!res.ok) { alert(data.error || "启动失败"); return; }
        await Promise.all([loadExecutions(), loadStats()]);
        showDetail(data.execution.id);
    } finally {
        btn.disabled = false; btn.textContent = "Agent 执行";
    }
}

function escapeHtml(s) {
    return (s || "").replace(/[&<>"']/g, c => ({
        "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
    }[c]));
}

// ============ 初始化 ============
async function init() {
    await Promise.all([loadStats(), loadSuites(), loadCases(), loadExecutions()]);
}

if (accessToken) {
    init().catch(() => showLogin());
} else {
    showLogin();
}
