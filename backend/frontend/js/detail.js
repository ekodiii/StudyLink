let currentGroupId = null;
let currentGroup = null;
let currentProgress = null;
let currentView = "member";

// Navigation — called from onclick handlers and other code
async function showGroupDetail(groupId) {
    await navigate("group/" + groupId);
}

// Rendering — called by the router
async function renderGroupDetail(groupId) {
    currentGroupId = groupId;
    hide("screen-main");
    hide("screen-auth");
    hide("screen-settings");
    show("screen-detail");
    document.getElementById("user-tag-detail").textContent = `${currentUser.username}#${currentUser.discriminator}`;

    const resp = await api(`/groups/${groupId}`);
    if (!resp.ok) { await showMain(); return; }
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

    // Assignment view toggle
    const leaderToggleEl = document.getElementById("leader-assignment-toggle");
    const viewToggle = document.querySelector('.view-toggle');
    if (group.assignment_view_enabled) {
        viewToggle.classList.remove("hidden");
    } else {
        viewToggle.classList.add("hidden");
        if (currentView === "assignment") {
            currentView = "member";
            renderProgress();
        }
    }
    if (isLeader) {
        leaderToggleEl.classList.remove("hidden");
        leaderToggleEl.innerHTML = `
            <label class="leader-toggle-label">
                <span>Assignment view</span>
                <label class="toggle">
                    <input type="checkbox" ${group.assignment_view_enabled ? 'checked' : ''} onchange="toggleAssignmentView(this.checked)">
                    <span class="slider"></span>
                </label>
            </label>`;
    } else {
        leaderToggleEl.classList.add("hidden");
    }

    await loadProgress(groupId);
    await loadDashboard(groupId);
}

async function loadProgress(groupId) {
    const resp = await api(`/groups/${groupId}/progress`);
    if (!resp.ok) return;
    currentProgress = await resp.json();
    renderProgress();
}

async function loadDashboard(groupId) {
    const resp = await api(`/groups/${groupId}/dashboard`);
    if (!resp.ok) return;
    const data = await resp.json();
    renderDashboard(data);
}

function renderDashboard(data) {
    const area = document.getElementById("dashboard-area");

    const overdue = [];
    if (currentProgress) {
        for (const member of currentProgress.members) {
            for (const course of member.courses) {
                for (const a of course.assignments) {
                    if (isOverdue(a)) {
                        overdue.push({
                            name: a.name,
                            due_at: a.due_at,
                            course_name: course.course_code || course.name,
                            member_username: member.username,
                        });
                    }
                }
            }
        }
    }
    overdue.sort((a, b) => new Date(a.due_at) - new Date(b.due_at));

    if (!data.upcoming.length && !data.missing.length && !overdue.length) {
        area.innerHTML = "";
        return;
    }
    let html = `<div class="dashboard">`;
    if (data.upcoming.length) {
        html += `<div class="dashboard-section">`;
        html += `<div class="dashboard-header collapsible-header" onclick="toggleCollapsible(this)">
            <span class="dashboard-title">&#9200; Upcoming (7 days) &mdash; ${data.upcoming.length} assignment${data.upcoming.length !== 1 ? 's' : ''}</span>
            <span class="chevron">&#9660;</span>
        </div>`;
        html += `<div class="collapsible-content">`;
        for (const a of data.upcoming) {
            html += `<div class="assignment-row">
                <span class="assignment-name">${esc(a.member_username)} &middot; ${esc(a.course_name)} &mdash; ${esc(a.name)}</span>
                <span class="assignment-due">${formatDue(a.due_at)}</span>
                ${statusHTML(effectiveStatus(a))}
            </div>`;
        }
        html += `</div></div>`;
    }
    if (overdue.length) {
        html += `<div class="dashboard-section">`;
        html += `<div class="dashboard-header collapsible-header" onclick="toggleCollapsible(this)">
            <span class="dashboard-title">&#9203; Overdue &mdash; ${overdue.length} assignment${overdue.length !== 1 ? 's' : ''}</span>
            <span class="chevron">&#9660;</span>
        </div>`;
        html += `<div class="collapsible-content">`;
        for (const a of overdue) {
            html += `<div class="assignment-row">
                <span class="assignment-name">${esc(a.member_username)} &middot; ${esc(a.course_name)} &mdash; ${esc(a.name)}</span>
                <span class="assignment-due">${formatDue(a.due_at)}</span>
                ${statusHTML("overdue")}
            </div>`;
        }
        html += `</div></div>`;
    }
    if (data.missing.length) {
        html += `<div class="dashboard-section">`;
        html += `<div class="dashboard-header collapsible-header" onclick="toggleCollapsible(this)">
            <span class="dashboard-title">&#9888; Missing &mdash; ${data.missing.length} assignment${data.missing.length !== 1 ? 's' : ''}</span>
            <span class="chevron">&#9660;</span>
        </div>`;
        html += `<div class="collapsible-content">`;
        for (const a of data.missing) {
            html += `<div class="assignment-row">
                <span class="assignment-name">${esc(a.member_username)} &middot; ${esc(a.course_name)} &mdash; ${esc(a.name)}</span>
                <span class="assignment-due">${formatDue(a.due_at)}</span>
                ${statusHTML(a.status)}
            </div>`;
        }
        html += `</div></div>`;
    }
    html += `</div>`;
    area.innerHTML = html;
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
    const viewToggle = document.querySelector('.view-toggle');
    if (enabled) {
        viewToggle.classList.remove("hidden");
    } else {
        viewToggle.classList.add("hidden");
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

function verificationHTML(a, member) {
    const v = a.verification;
    const isMe = member.user_id === currentUser.id;
    const iAmVerifier = v && v.verifier_id === currentUser.id;
    const iAmRequester = v && v.requester_id === currentUser.id;

    if (!v) {
        if (isMe) {
            return `<div class="verify-actions">
                <select class="verify-select" id="vsel-${a.assignment_id}">
                    <option value="">Ask friend...</option>
                    ${currentGroup.members.filter(m => m.id !== currentUser.id).map(m =>
                        `<option value="${m.id}">${esc(m.username)}</option>`
                    ).join('')}
                </select>
                <button class="btn btn-secondary btn-small" onclick="requestVerification('${a.assignment_id}', document.getElementById('vsel-${a.assignment_id}').value)">Request</button>
            </div>`;
        }
        return '';
    }

    if (v.status === 'pending') {
        if (iAmRequester) {
            return `<span class="verify-badge verify-pending">Pending verify by ${esc(v.verifier_username)} &middot; word: <strong>${esc(v.verification_word)}</strong>
                <button class="btn btn-secondary btn-small" onclick="cancelVerification('${v.id}')">Cancel</button></span>`;
        }
        if (iAmVerifier) {
            return `<span class="verify-badge verify-pending">
                ${esc(v.requester_username)} asks you to verify &middot; type: <strong>${esc(v.verification_word)}</strong>
                <input class="verify-input" id="vword-${v.id}" placeholder="Type word...">
                <button class="btn btn-primary btn-small" onclick="confirmVerification('${v.id}')">Verify</button>
            </span>`;
        }
        return `<span class="verify-badge verify-pending">Pending verification</span>`;
    }

    if (v.status === 'verified') {
        let actions = '';
        if (iAmRequester) actions = `<button class="btn btn-secondary btn-small" onclick="cancelVerification('${v.id}')">Undo</button>`;
        if (iAmVerifier) actions = `<button class="btn btn-secondary btn-small" onclick="revokeVerification('${v.id}')">Revoke</button>`;
        return `<span class="verify-badge verify-confirmed">&#10003; Verified by ${esc(v.verifier_username)} ${actions}</span>`;
    }

    return '';
}

function renderByMember(area) {
    let html = "";
    for (const member of currentProgress.members) {
        const allAssignments = member.courses.flatMap(c => c.assignments);
        const memberCounts = countStatuses(allAssignments);

        html += `<div class="card" style="cursor:default">`;
        html += `<div class="card-header collapsible-header collapsed" onclick="toggleCollapsible(this)">
            <span class="card-title">${esc(member.username)}</span>
            <span class="card-meta">${summaryHTML(memberCounts)} synced ${timeAgo(member.last_synced_at)} <span class="chevron">&#9660;</span></span>
        </div>`;
        html += `<div class="collapsible-content collapsed">`;
        if (!member.courses.length) {
            html += `<div class="card-meta" style="padding:8px 0">No visible courses</div>`;
        }
        for (const course of member.courses) {
            const courseCounts = countStatuses(course.assignments);
            html += `<div class="course-block">`;
            html += `<div class="course-label collapsible-header collapsed" onclick="toggleCollapsible(this)">${esc(course.course_code || course.name)} ${summaryHTML(courseCounts)} <span class="chevron">&#9660;</span></div>`;
            html += `<div class="collapsible-content collapsed">`;
            for (const a of course.assignments) {
                html += `<div class="assignment-row">
                    <span class="assignment-name">${esc(a.name)}</span>
                    <span class="assignment-due">${formatDue(a.due_at)}</span>
                    ${statusHTML(effectiveStatus(a))}
                    ${verificationHTML(a, member)}
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
    const courseMap = new Map();
    for (const member of currentProgress.members) {
        for (const course of member.courses) {
            const courseKey = course.course_code || course.name;
            if (!courseMap.has(courseKey)) {
                courseMap.set(courseKey, { assignments: new Map(), statuses: [] });
            }
            const entry = courseMap.get(courseKey);
            for (const a of course.assignments) {
                const aKey = `${a.name}||${a.due_at}`;
                if (!entry.assignments.has(aKey)) {
                    entry.assignments.set(aKey, { name: a.name, due_at: a.due_at, members: [] });
                }
                const es = effectiveStatus(a);
                entry.assignments.get(aKey).members.push({ username: member.username, status: es });
                entry.statuses.push({ status: es });
            }
        }
    }

    if (!courseMap.size) {
        area.innerHTML = `<div class="empty">No visible assignments</div>`;
        return;
    }

    let html = "";
    for (const [courseName, entry] of courseMap) {
        const courseCounts = countStatuses(entry.statuses);
        html += `<div class="card" style="cursor:default">`;
        html += `<div class="card-header collapsible-header collapsed" onclick="toggleCollapsible(this)">
            <span class="card-title">${esc(courseName)}</span>
            <span class="card-meta">${summaryHTML(courseCounts)} <span class="chevron">&#9660;</span></span>
        </div>`;
        html += `<div class="collapsible-content collapsed">`;
        for (const [, info] of entry.assignments) {
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

// ── Group Actions ────────────────────────────────────────────────────────────

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
    if (!await showConfirm("Leave this group?")) return;
    await api(`/groups/${currentGroupId}/leave`, { method: "DELETE" });
    showMain();
}

async function deleteGroup() {
    if (!await showConfirm("Delete this group? This cannot be undone.")) return;
    await api(`/groups/${currentGroupId}`, { method: "DELETE" });
    showMain();
}
