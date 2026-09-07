// JWT 认证辅助
function getToken() {
    return localStorage.getItem("qa_access") || "";
}

async function api(path, options = {}) {
    const headers = { "Content-Type": "application/json", ...(options.headers || {}) };
    const token = getToken();
    if (token) headers["Authorization"] = `Bearer ${token}`;
    const res = await fetch(path, { ...options, headers });
    if (res.status === 401) {
        alert("请先登录（可用 /api/accounts/login/ 获取 token）");
        return null;
    }
    return res;
}

async function askAI() {
    const question = document.getElementById("question").value;
    const res = await api("/api/ai/ask/", {
        method: "POST",
        body: JSON.stringify({ question })
    });
    if (!res) return;
    const data = await res.json();
    document.getElementById("answer").innerHTML = data.answer;
}

async function recommend() {
    const destination = document.getElementById("destination").value;
    const days = document.getElementById("days").value;
    const res = await api("/api/ai/recommend/", {
        method: "POST",
        body: JSON.stringify({
            destination,
            days,
            budget: "5000",
            preference: "自由行"
        })
    });
    if (!res) return;
    const data = await res.json();
    document.getElementById("plan").innerHTML = data.plan;
}
