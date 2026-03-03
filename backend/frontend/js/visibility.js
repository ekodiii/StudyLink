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
    const [settingsResp, pendingResp, coursesResp] = await Promise.all([
        api("/visibility/settings"),
        api("/visibility/pending"),
        api("/users/me/courses"),
    ]);
    if (!settingsResp.ok) return;

    const settings = (await settingsResp.json()).settings;
    const pending = pendingResp.ok ? (await pendingResp.json()).pending : [];
    const courses = coursesResp.ok ? await coursesResp.json() : [];
    const el = document.getElementById("visibility-list");

    const courseHiddenMap = new Map();
    for (const c of courses) courseHiddenMap.set(c.id, c.hidden);

    const courseMap = new Map();
    for (const item of settings) {
        if (courseHiddenMap.get(item.course_id)) continue;
        if (!courseMap.has(item.course_id)) {
            courseMap.set(item.course_id, { name: item.course_name, groups: [] });
        }
        courseMap.get(item.course_id).groups.push(item);
    }

    for (const c of courses) {
        if (c.hidden) continue;
        if (!courseMap.has(c.id)) courseMap.set(c.id, { name: c.name, groups: [] });
    }

    for (const course of pending) {
        if (!courseMap.has(course.course_id)) {
            courseMap.set(course.course_id, { name: course.course_name, groups: [], pending: [] });
        }
        const entry = courseMap.get(course.course_id);
        if (!entry.pending) entry.pending = [];
        entry.pending.push(...course.groups);
    }

    window._visibilityData = courseMap;

    let html = "";
    if (!courseMap.size) {
        html = `<div class="empty">No courses synced yet. Use the browser extension to sync your Canvas assignments.</div>`;
        el.innerHTML = html;
        return;
    }

    const totalPending = pending.reduce((n, c) => n + c.groups.length, 0);
    if (totalPending > 0) {
        html += `<div class="pending-banner" style="margin-bottom:16px">
            <span>${totalPending} new course${totalPending > 1 ? 's need' : ' needs'} visibility decisions</span>
        </div>`;
    }

    for (const [courseId, data] of courseMap) {
        const sharedCount = data.groups.filter(g => g.visible).length;
        const totalGroups = data.groups.length + (data.pending ? data.pending.length : 0);
        const pendingCount = data.pending ? data.pending.length : 0;
        let meta = totalGroups > 0
            ? `Shared with ${sharedCount}/${totalGroups} group${totalGroups !== 1 ? 's' : ''}`
            : 'No groups yet';
        if (pendingCount > 0) meta += ` · <span style="color:var(--accent)">${pendingCount} pending</span>`;

        html += `<div class="vis-course-card" onclick="openVisOverlay('${courseId}')">
            <div class="vis-course-name">${esc(data.name)}</div>
            <div class="vis-course-meta">${meta}</div>
        </div>`;
    }

    el.innerHTML = html;
}

function openVisOverlay(courseId) {
    const data = window._visibilityData.get(courseId);
    if (!data) return;

    document.getElementById("vis-overlay")?.remove();

    let groupsHTML = "";
    for (const g of data.groups) {
        groupsHTML += `
            <div class="vis-group-row">
                <span class="vis-group-name">${esc(g.group_name)}</span>
                <label class="toggle">
                    <input type="checkbox" ${g.visible ? 'checked' : ''} onchange="toggleVisFromOverlay('${courseId}','${g.group_id}',this.checked)">
                    <span class="slider"></span>
                </label>
            </div>`;
    }

    if (data.pending) {
        for (const g of data.pending) {
            groupsHTML += `
                <div class="vis-group-row" id="vis-pending-${courseId}-${g.group_id}">
                    <div>
                        <span class="vis-group-name">${esc(g.group_name)}</span>
                        <div style="font-size:11px;color:var(--accent)">New</div>
                    </div>
                    <div style="display:flex;gap:6px">
                        <button class="btn btn-primary btn-small" onclick="decideCourseOverlay('${courseId}','${g.group_id}',true)">Share</button>
                        <button class="btn btn-secondary btn-small" onclick="decideCourseOverlay('${courseId}','${g.group_id}',false)">Hide</button>
                    </div>
                </div>`;
        }
    }

    const overlay = document.createElement("div");
    overlay.id = "vis-overlay";
    overlay.className = "vis-overlay";
    overlay.onclick = (e) => { if (e.target === overlay) overlay.remove(); };
    overlay.innerHTML = `
        <div class="vis-panel">
            <h3>${esc(data.name)}</h3>
            <div class="vis-course-code">Choose which groups can see this course</div>
            ${groupsHTML}
            <div style="margin-top:16px;text-align:right">
                <button class="btn btn-secondary btn-small" onclick="document.getElementById('vis-overlay').remove()">Done</button>
            </div>
        </div>`;
    document.body.appendChild(overlay);
}

async function toggleVisFromOverlay(courseId, groupId, visible) {
    await api("/visibility/settings", {
        method: "PATCH",
        body: JSON.stringify({ decisions: [{ course_id: courseId, group_id: groupId, visible }] }),
    });
    const data = window._visibilityData.get(courseId);
    if (data) {
        const g = data.groups.find(g => g.group_id === groupId);
        if (g) g.visible = visible;
    }
}

async function decideCourseOverlay(courseId, groupId, visible) {
    await api("/visibility/decide", {
        method: "POST",
        body: JSON.stringify({ decisions: [{ course_id: courseId, group_id: groupId, visible }] }),
    });
    document.getElementById("vis-overlay")?.remove();
    await loadVisibility();
    await loadPending();
}

async function loadCourses() {
    const el = document.getElementById("courses-list");
    el.innerHTML = '<div class="loading">Loading courses…</div>';
    const resp = await api("/users/me/courses");
    if (!resp.ok) { el.innerHTML = '<div class="empty">Could not load courses</div>'; return; }
    const courses = await resp.json();
    if (courses.length === 0) { el.innerHTML = '<div class="empty">No courses synced yet</div>'; return; }
    el.innerHTML = courses.map(c => `
        <div class="vis-row">
            <div style="min-width:0;flex:1;overflow:hidden">
                <div style="font-weight:600;font-size:14px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${esc(c.name)}</div>
                <div style="color:var(--text2);font-size:12px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${esc(c.course_code || '')}</div>
            </div>
            <label class="toggle" style="flex-shrink:0">
                <input type="checkbox" ${c.hidden ? '' : 'checked'} onchange="toggleCourseHiddenFromTab('${c.id}',this)">
                <span class="slider"></span>
            </label>
        </div>
    `).join("");
}

async function toggleCourseHiddenFromTab(courseId, checkbox) {
    const resp = await api(`/users/me/courses/${courseId}`, { method: "PATCH" });
    if (!resp.ok) { checkbox.checked = !checkbox.checked; return; }
}
