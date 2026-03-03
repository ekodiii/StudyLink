// ── Router ───────────────────────────────────────────────────────────────────

let _routeHandled = false;

async function navigate(path) {
    _routeHandled = true;
    if (location.hash.slice(1) !== path) location.hash = path;
    await handleRoute(path);
}

window.addEventListener("hashchange", async () => {
    if (_routeHandled) { _routeHandled = false; return; }
    await handleRoute(location.hash.slice(1));
});

async function handleRoute(path) {
    path = path || "groups";

    if (!token) {
        hide("screen-main");
        hide("screen-detail");
        hide("screen-settings");
        show("screen-auth");
        initGoogleSignIn();
        return;
    }

    // Ensure currentUser is loaded before rendering any authenticated screen
    if (!currentUser) {
        const resp = await api("/users/me");
        if (!resp.ok) { doLogout(); return; }
        currentUser = await resp.json();
    }

    if (path === "settings") {
        renderSettings();
    } else if (path.startsWith("group/")) {
        await renderGroupDetail(path.slice(6));
    } else {
        await renderMain();
    }
}

// ── Main Screen ──────────────────────────────────────────────────────────────

async function renderMain() {
    hide("screen-auth");
    hide("screen-detail");
    hide("screen-settings");
    show("screen-main");
    document.getElementById("user-tag").textContent = `${currentUser.username}#${currentUser.discriminator}`;
    await loadGroups();
    await loadPending();
}

async function showMain() {
    await navigate("groups");
}

// ── Tabs ─────────────────────────────────────────────────────────────────────

function switchTab(tab) {
    document.querySelectorAll(".tab").forEach(t => t.classList.toggle("active", t.dataset.tab === tab));
    ["tab-groups", "tab-courses", "tab-visibility"].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.classList.toggle("hidden", id !== "tab-" + tab);
    });
    if (tab === "courses") loadCourses();
    if (tab === "visibility") loadVisibility();
}

// ── Init ─────────────────────────────────────────────────────────────────────

(async function init() {
    try {
        const resp = await fetch(`${API}/auth/config`);
        if (resp.ok) {
            const cfg = await resp.json();
            window.__GOOGLE_CLIENT_ID = cfg.google_client_id;
        }
    } catch {}

    await handleRoute(location.hash.slice(1));
})();
