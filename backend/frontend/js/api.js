const API = window.location.origin;
let token = localStorage.getItem("token");
let refreshToken = localStorage.getItem("refreshToken");
let currentUser = null;

async function api(path, opts = {}) {
    const headers = { "Content-Type": "application/json", ...opts.headers };
    if (token) headers["Authorization"] = `Bearer ${token}`;
    const resp = await fetch(`${API}${path}`, { ...opts, headers });
    if (resp.status === 401 && refreshToken) {
        const ok = await doRefresh();
        if (ok) {
            headers["Authorization"] = `Bearer ${token}`;
            const retry = await fetch(`${API}${path}`, { ...opts, headers });
            return retry;
        }
    }
    return resp;
}

async function doRefresh() {
    try {
        const resp = await fetch(`${API}/auth/refresh`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ refresh_token: refreshToken }),
        });
        if (!resp.ok) return false;
        const data = await resp.json();
        token = data.access_token;
        localStorage.setItem("token", token);
        return true;
    } catch {
        return false;
    }
}
