const API = window.location.origin;
let token = localStorage.getItem("token");
let refreshToken = localStorage.getItem("refreshToken");
let currentUser = null;
let currentGroupId = null;
let currentGroup = null;
let currentProgress = null;
let currentView = "member";

// ── Helpers ─────────────────────────────────────────────────────────────────

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

function show(id) { document.getElementById(id).classList.remove("hidden"); }
function hide(id) { document.getElementById(id).classList.add("hidden"); }

function closeModal(e, id) {
    if (e.target.classList.contains("modal-overlay")) hide(id);
}

function timeAgo(iso) {
    if (!iso) return "never";
    const diff = Date.now() - new Date(iso).getTime();
    const mins = Math.floor(diff / 60000);
    if (mins < 1) return "just now";
    if (mins < 60) return `${mins}m ago`;
    const hrs = Math.floor(mins / 60);
    if (hrs < 24) return `${hrs}h ago`;
    return `${Math.floor(hrs / 24)}d ago`;
}

function statusHTML(s) {
    const labels = {
        submitted: "Submitted",
        graded: "Graded",
        late: "Late",
        missing: "Missing",
        unsubmitted: "Not yet",
    };
    return `<span class="status status-${s}">${labels[s] || s}</span>`;
}

function formatDue(iso) {
    if (!iso) return "";
    return new Date(iso).toLocaleDateString("en-US", { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" });
}

// ── Auth ────────────────────────────────────────────────────────────────────

function initGoogleSignIn() {
    if (!window.google) {
        // Retry after script loads
        setTimeout(initGoogleSignIn, 500);
        return;
    }
    google.accounts.id.initialize({
        client_id: window.__GOOGLE_CLIENT_ID || "",
        callback: handleGoogleAuth,
        auto_select: true,
    });
    google.accounts.id.renderButton(
        document.getElementById("google-signin-btn"),
        { theme: "outline", size: "large", text: "signin_with", shape: "pill", width: 280 }
    );
}

async function handleGoogleAuth(response) {
    const resp = await fetch(`${API}/auth/google`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ id_token: response.credential }),
    });
    if (!resp.ok) {
        alert("Sign-in failed. Please try again.");
        return;
    }
    const data = await resp.json();
    token = data.access_token;
    refreshToken = data.refresh_token;
    localStorage.setItem("token", token);
    localStorage.setItem("refreshToken", refreshToken);
    currentUser = data.user;
    showMain();
}

function doLogout() {
    token = null;
    refreshToken = null;
    currentUser = null;
    localStorage.removeItem("token");
    localStorage.removeItem("refreshToken");
    hide("screen-main");
    hide("screen-detail");
    hide("screen-settings");
    show("screen-auth");
    if (window.google) {
        google.accounts.id.disableAutoSelect();
    }
}

// ── Screens ─────────────────────────────────────────────────────────────────

async function showMain() {
    hide("screen-auth");
    hide("screen-detail");
    hide("screen-settings");
    show("screen-main");

    if (!currentUser) {
        const resp = await api("/users/me");
        if (!resp.ok) { doLogout(); return; }
        currentUser = await resp.json();
    }

    document.getElementById("user-tag").textContent = `${currentUser.username}#${currentUser.discriminator}`;
    await loadGroups();
    await loadPending();
}

function switchTab(tab) {
    document.querySelectorAll(".tab").forEach(t => t.classList.toggle("active", t.dataset.tab === tab));
    document.getElementById("tab-groups").classList.toggle("hidden", tab !== "groups");
    document.getElementById("tab-visibility").classList.toggle("hidden", tab !== "visibility");
    if (tab === "visibility") loadVisibility();
}

// ── Groups ──────────────────────────────────────────────────────────────────

async function loadGroups() {
    const resp = await api("/groups");
    if (!resp.ok) return;
    const groups = await resp.json();
    const el = document.getElementById("groups-list");

    if (!groups.length) {
        el.innerHTML = `<div class="empty">No groups yet. Create one or join with an invite code.</div>`;
        return;
    }

    el.innerHTML = groups.map(g => `
        <div class="card" onclick="showGroupDetail('${g.id}')">
            <div class="card-header">
                <span class="card-title">${esc(g.name)}</span>
                <span class="card-meta">${g.member_count} member${g.member_count !== 1 ? 's' : ''}</span>
            </div>
            <div class="card-meta">${g.is_leader ? 'Leader' : 'Member'} &middot; Created ${new Date(g.created_at).toLocaleDateString()}</div>
        </div>
    `).join("");
}

function showCreateModal() { show("modal-create"); document.getElementById("create-name").value = ""; document.getElementById("create-name").focus(); }
function showJoinModal() { show("modal-join"); document.getElementById("join-code").value = ""; document.getElementById("join-code").focus(); }

async function createGroup() {
    const name = document.getElementById("create-name").value.trim();
    if (!name) return;
    const resp = await api("/groups", { method: "POST", body: JSON.stringify({ name }) });
    if (!resp.ok) { alert("Failed to create group"); return; }
    hide("modal-create");
    const group = await resp.json();
    showGroupDetail(group.id);
}

async function joinGroup() {
    const code = document.getElementById("join-code").value.trim().toUpperCase();
    if (!code) return;
    const resp = await api("/groups/join", { method: "POST", body: JSON.stringify({ invite_code: code }) });
    if (resp.status === 404) { alert("Invalid invite code"); return; }
    if (resp.status === 409) { alert("Already a member"); return; }
    if (!resp.ok) { alert("Failed to join group"); return; }
    hide("modal-join");
    const group = await resp.json();
    showGroupDetail(group.id);
}

// ── Group Detail ────────────────────────────────────────────────────────────

async function showGroupDetail(groupId) {
    currentGroupId = groupId;
    hide("screen-main");
    hide("screen-auth");
    show("screen-detail");
    document.getElementById("user-tag-detail").textContent = `${currentUser.username}#${currentUser.discriminator}`;

    const resp = await api(`/groups/${groupId}`);
    if (!resp.ok) { showMain(); return; }
    const group = await resp.json();
    currentGroup = group;

    document.getElementById("detail-name").textContent = group.name;
    document.getElementById("detail-invite").textContent = group.invite_code;

    // Actions (leader-only)
    const isLeader = group.leader.id === currentUser.id;
    const actionsEl = document.getElementById("detail-actions");
    actionsEl.innerHTML = "";
    if (isLeader) {
        actionsEl.innerHTML += `<button class="btn btn-secondary btn-small" onclick="regenerateInvite()">New Code</button>`;
        actionsEl.innerHTML += `<button class="btn btn-danger btn-small" onclick="deleteGroup()">Delete</button>`;
    }
    actionsEl.innerHTML += `<button class="btn btn-secondary btn-small" onclick="leaveGroup()">Leave</button>`;

    // Members
    const membersEl = document.getElementById("detail-members");
    membersEl.innerHTML = group.members.map(m => `
        <div class="member-row">
            <div>
                <span class="member-name">
                    ${esc(m.username)}
                    ${m.id === group.leader.id ? '<span class="leader-badge">Leader</span>' : ''}
                </span>
            </div>
            <span class="member-sync">synced ${timeAgo(m.last_synced_at)}</span>
        </div>
    `).join("");

    // Assignment view toggle (visibility + leader control)
    const assignBtn = document.querySelector('.view-toggle button:last-child');
    const leaderToggleEl = document.getElementById("leader-assignment-toggle");
    if (group.assignment_view_enabled) {
        assignBtn.classList.remove("hidden");
    } else {
        assignBtn.classList.add("hidden");
        if (currentView === "assignment") {
            currentView = "member";
            document.querySelectorAll(".view-toggle button").forEach(b => b.classList.remove("active"));
            document.querySelector(".view-toggle button:first-child").classList.add("active");
        }
    }
    if (isLeader) {
        leaderToggleEl.classList.remove("hidden");
        leaderToggleEl.innerHTML = `
            <label class="toggle" style="display:flex;align-items:center;gap:8px;font-size:13px;color:var(--text2)">
                <span>Assignment view</span>
                <input type="checkbox" ${group.assignment_view_enabled ? 'checked' : ''} onchange="toggleAssignmentView(this.checked)">
                <span class="slider"></span>
            </label>`;
    } else {
        leaderToggleEl.classList.add("hidden");
    }

    // Load progress
    await loadProgress(groupId);
}

async function loadProgress(groupId) {
    const resp = await api(`/groups/${groupId}/progress`);
    if (!resp.ok) return;
    currentProgress = await resp.json();
    renderProgress();
}

function setView(view, btn) {
    currentView = view;
    document.querySelectorAll(".view-toggle button").forEach(b => b.classList.remove("active"));
    btn.classList.add("active");
    renderProgress();
}

async function toggleAssignmentView(enabled) {
    const resp = await api(`/groups/${currentGroupId}`, {
        method: "PATCH",
        body: JSON.stringify({ assignment_view_enabled: enabled }),
    });
    if (!resp.ok) return;
    currentGroup.assignment_view_enabled = enabled;
    const assignBtn = document.querySelector('.view-toggle button:last-child');
    if (enabled) {
        assignBtn.classList.remove("hidden");
    } else {
        assignBtn.classList.add("hidden");
        if (currentView === "assignment") {
            currentView = "member";
            document.querySelectorAll(".view-toggle button").forEach(b => b.classList.remove("active"));
            document.querySelector(".view-toggle button:first-child").classList.add("active");
            renderProgress();
        }
    }
}

function renderProgress() {
    const area = document.getElementById("progress-area");
    if (!currentProgress || !currentProgress.members.length) {
        area.innerHTML = `<div class="empty">No progress data yet. Members need to sync via the browser extension.</div>`;
        return;
    }

    if (currentView === "member") {
        renderByMember(area);
    } else {
        renderByAssignment(area);
    }
}

function toggleCollapsible(el) {
    const content = el.nextElementSibling;
    const isOpen = !content.classList.contains("collapsed");
    content.classList.toggle("collapsed", isOpen);
    el.classList.toggle("collapsed", isOpen);
}

function renderByMember(area) {
    let html = "";
    for (const member of currentProgress.members) {
        html += `<div class="card" style="cursor:default">`;
        html += `<div class="card-header collapsible-header" onclick="toggleCollapsible(this)">
            <span class="card-title">${esc(member.username)}</span>
            <span class="card-meta">synced ${timeAgo(member.last_synced_at)} <span class="chevron">&#9660;</span></span>
        </div>`;
        html += `<div class="collapsible-content">`;
        if (!member.courses.length) {
            html += `<div class="card-meta" style="padding:8px 0">No visible courses</div>`;
        }
        for (const course of member.courses) {
            html += `<div class="course-block">`;
            html += `<div class="course-label collapsible-header" onclick="toggleCollapsible(this)">${esc(course.course_code || course.name)} <span class="chevron">&#9660;</span></div>`;
            html += `<div class="collapsible-content">`;
            for (const a of course.assignments) {
                html += `<div class="assignment-row">
                    <span class="assignment-name">${esc(a.name)}</span>
                    <span class="assignment-due">${formatDue(a.due_at)}</span>
                    ${statusHTML(a.status)}
                </div>`;
            }
            if (!course.assignments.length) {
                html += `<div class="assignment-row"><span class="card-meta">No assignments</span></div>`;
            }
            html += `</div>`;
            html += `</div>`;
        }
        html += `</div>`;
        html += `</div>`;
    }
    area.innerHTML = html;
}

function renderByAssignment(area) {
    // Collect all assignments across members, grouped by course then assignment
    const courseMap = new Map();
    for (const member of currentProgress.members) {
        for (const course of member.courses) {
            const courseKey = course.course_code || course.name;
            if (!courseMap.has(courseKey)) {
                courseMap.set(courseKey, new Map());
            }
            const assignMap = courseMap.get(courseKey);
            for (const a of course.assignments) {
                const aKey = `${a.name}||${a.due_at}`;
                if (!assignMap.has(aKey)) {
                    assignMap.set(aKey, {
                        name: a.name,
                        due_at: a.due_at,
                        members: [],
                    });
                }
                assignMap.get(aKey).members.push({
                    username: member.username,
                    status: a.status,
                });
            }
        }
    }

    if (!courseMap.size) {
        area.innerHTML = `<div class="empty">No visible assignments</div>`;
        return;
    }

    let html = "";
    for (const [courseName, assignments] of courseMap) {
        html += `<div class="card" style="cursor:default">`;
        html += `<div class="card-header collapsible-header" onclick="toggleCollapsible(this)">
            <span class="card-title">${esc(courseName)}</span>
            <span class="chevron">&#9660;</span>
        </div>`;
        html += `<div class="collapsible-content">`;
        for (const [, info] of assignments) {
            html += `<div class="course-block">`;
            html += `<div class="course-label">${esc(info.name)} <span class="card-meta">${formatDue(info.due_at)}</span></div>`;
            for (const m of info.members) {
                html += `<div class="assignment-row">
                    <span class="assignment-name">${esc(m.username)}</span>
                    ${statusHTML(m.status)}
                </div>`;
            }
            html += `</div>`;
        }
        html += `</div>`;
        html += `</div>`;
    }
    area.innerHTML = html;
}

async function copyInvite() {
    const code = document.getElementById("detail-invite").textContent;
    await navigator.clipboard.writeText(code);
    document.querySelector(".invite-box .btn").textContent = "Copied!";
    setTimeout(() => document.querySelector(".invite-box .btn").textContent = "Copy", 1500);
}

async function regenerateInvite() {
    const resp = await api(`/groups/${currentGroupId}/regenerate-invite`, { method: "POST" });
    if (!resp.ok) return;
    const data = await resp.json();
    document.getElementById("detail-invite").textContent = data.invite_code;
}

async function leaveGroup() {
    if (!confirm("Leave this group?")) return;
    await api(`/groups/${currentGroupId}/leave`, { method: "DELETE" });
    showMain();
}

async function deleteGroup() {
    if (!confirm("Delete this group? This cannot be undone.")) return;
    await api(`/groups/${currentGroupId}`, { method: "DELETE" });
    showMain();
}

// ── Visibility ──────────────────────────────────────────────────────────────

async function loadPending() {
    const resp = await api("/visibility/pending");
    if (!resp.ok) return;
    const data = await resp.json();
    const el = document.getElementById("pending-area");

    if (!data.pending.length) {
        el.innerHTML = "";
        return;
    }

    const count = data.pending.reduce((n, c) => n + c.groups.length, 0);
    el.innerHTML = `
        <div class="pending-banner">
            <span>${count} course${count > 1 ? 's' : ''} need${count === 1 ? 's' : ''} visibility decisions</span>
            <button class="btn btn-primary btn-small" onclick="showPendingDecisions()">Decide</button>
        </div>
    `;
}

async function showPendingDecisions() {
    switchTab("visibility");
    await loadVisibility();
}

async function loadVisibility() {
    // Load both settings and pending
    const [settingsResp, pendingResp] = await Promise.all([
        api("/visibility/settings"),
        api("/visibility/pending"),
    ]);
    if (!settingsResp.ok) return;

    const settings = (await settingsResp.json()).settings;
    const pending = pendingResp.ok ? (await pendingResp.json()).pending : [];
    const el = document.getElementById("visibility-list");

    // Build combined list: pending (undecided) + existing settings
    let html = "";

    if (pending.length) {
        html += `<h3 style="margin-bottom:12px;color:var(--accent)">New Courses</h3>`;
        for (const course of pending) {
            for (const group of course.groups) {
                html += `
                    <div class="vis-row">
                        <div>
                            <div style="font-weight:500">${esc(course.course_name)}</div>
                            <div style="font-size:12px;color:var(--text2)">Share with ${esc(group.group_name)}</div>
                        </div>
                        <div style="display:flex;gap:6px">
                            <button class="btn btn-primary btn-small" onclick="decideCourse('${course.course_id}','${group.group_id}',true)">Share</button>
                            <button class="btn btn-secondary btn-small" onclick="decideCourse('${course.course_id}','${group.group_id}',false)">Hide</button>
                        </div>
                    </div>`;
            }
        }
    }

    if (settings.length) {
        html += `<h3 style="margin:16px 0 12px">All Settings</h3>`;
        for (const item of settings) {
            html += `
                <div class="vis-row">
                    <div>
                        <div style="font-weight:500">${esc(item.course_name)}</div>
                        <div style="font-size:12px;color:var(--text2)">${esc(item.group_name)}</div>
                    </div>
                    <label class="toggle">
                        <input type="checkbox" ${item.visible ? 'checked' : ''} onchange="toggleVis('${item.course_id}','${item.group_id}',this.checked)">
                        <span class="slider"></span>
                    </label>
                </div>`;
        }
    }

    if (!html) {
        html = `<div class="empty">No courses synced yet. Use the browser extension to sync your Canvas assignments.</div>`;
    }

    el.innerHTML = html;
}

async function decideCourse(courseId, groupId, visible) {
    await api("/visibility/decide", {
        method: "POST",
        body: JSON.stringify({ decisions: [{ course_id: courseId, group_id: groupId, visible }] }),
    });
    await loadVisibility();
    await loadPending();
}

async function toggleVis(courseId, groupId, visible) {
    await api("/visibility/settings", {
        method: "PATCH",
        body: JSON.stringify({ decisions: [{ course_id: courseId, group_id: groupId, visible }] }),
    });
}

// ── Settings ────────────────────────────────────────────────────────────────

function showSettings() {
    hide("screen-main");
    show("screen-settings");
    document.getElementById("settings-username").value = currentUser.username;
    document.getElementById("settings-disc").textContent = `Discriminator: #${currentUser.discriminator}`;
}

async function saveUsername() {
    const name = document.getElementById("settings-username").value.trim();
    if (!name) return;
    const oldDisc = currentUser.discriminator;
    const resp = await api("/users/me", { method: "PATCH", body: JSON.stringify({ username: name }) });
    if (!resp.ok) { alert("Failed to update username"); return; }
    currentUser = await resp.json();
    document.getElementById("settings-disc").textContent = `Discriminator: #${currentUser.discriminator}`;
    if (currentUser.discriminator !== oldDisc) {
        alert(`Username updated! Your discriminator changed to #${currentUser.discriminator} because someone already has that username with your old discriminator.`);
    } else {
        alert("Username updated!");
    }
}

// ── Util ────────────────────────────────────────────────────────────────────

function esc(s) {
    const d = document.createElement("div");
    d.textContent = s || "";
    return d.innerHTML;
}

// ── Init ────────────────────────────────────────────────────────────────────

(async function init() {
    // Fetch Google client ID from backend config endpoint
    try {
        const resp = await fetch(`${API}/auth/config`);
        if (resp.ok) {
            const cfg = await resp.json();
            window.__GOOGLE_CLIENT_ID = cfg.google_client_id;
        }
    } catch {}

    if (token) {
        await showMain();
    } else {
        show("screen-auth");
        initGoogleSignIn();
    }
})();
