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

async function loadPlans() {
    const res = await api("/api/travel/list/");
    if (!res) return;
    const data = await res.json();
    let html = "";

    data.plans.forEach(plan => {
        html += `
        <div class="bg-white p-5 mb-3 rounded">
            <h2 class="text-xl font-bold">${plan.title}</h2>
            <p>${plan.destination}</p>
            <p>${plan.start_date} - ${plan.end_date}</p>
        </div>
        `;
    });
    document.getElementById("plans").innerHTML = html;
}

async function createPlan() {
    const submitData = {
        title: document.getElementById("title").value,
        destination: document.getElementById("destination").value,
        start_date: document.getElementById("start").value,
        end_date: document.getElementById("end").value,
        budget: 5000
    };

    const res = await api("/api/travel/create/", {
        method: "POST",
        body: JSON.stringify(submitData)
    });
    if (!res) return;
    loadPlans();
}

loadPlans();
