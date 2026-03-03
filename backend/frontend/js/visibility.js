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
    switchTab("courses");
}

async function loadCourses() {
    const el = document.getElementById("courses-list");
    el.innerHTML = '<div class="loading">Loading courses\u2026</div>';

    const [coursesResp, settingsResp, pendingResp] = await Promise.all([
        api("/users/me/courses"),
        api("/visibility/settings"),
        api("/visibility/pending"),
    ]);

    if (!coursesResp.ok) {
        el.innerHTML = '<div class="empty">Could not load courses</div>';
        return;
    }

    const courses = await coursesResp.json();
    const settings = settingsResp.ok ? (await settingsResp.json()).settings : [];
    const pending = pendingResp.ok ? (await pendingResp.json()).pending : [];

    if (!courses.length) {
        el.innerHTML = '<div class="empty">No courses synced yet. Use the Chrome extension to sync your Canvas assignments.</div>';
        return;
    }

    // Build per-course group data
    const courseGroupMap = new Map();
    for (const item of settings) {
        if (!courseGroupMap.has(item.course_id)) courseGroupMap.set(item.course_id, { groups: [], pending: [] });
        courseGroupMap.get(item.course_id).groups.push(item);
    }
    for (const course of pending) {
        if (!courseGroupMap.has(course.course_id)) courseGroupMap.set(course.course_id, { groups: [], pending: [] });
        courseGroupMap.get(course.course_id).pending.push(...course.groups);
    }

    el.innerHTML = courses.map(c => {
        const vis = courseGroupMap.get(c.id) || { groups: [], pending: [] };
        const sharedCount = vis.groups.filter(g => g.visible).length;
        const totalGroups = vis.groups.length + vis.pending.length;
        const pendingCount = vis.pending.length;

        let meta = '';
        if (!c.hidden && totalGroups > 0) {
            meta = `Shared with ${sharedCount}/${totalGroups} group${totalGroups !== 1 ? 's' : ''}`;
            if (pendingCount > 0) meta += ` &middot; <span style="color:var(--accent)">${pendingCount} pending</span>`;
        }
        if (c.hidden) {
            meta = '<span style="color:var(--text2)">Hidden</span>';
        }

        let groupsHTML = '';
        if (!c.hidden) {
            for (const g of vis.groups) {
                groupsHTML += `
                    <div class="vis-group-row">
                        <span class="vis-group-name">${esc(g.group_name)}</span>
                        <label class="toggle">
                            <input type="checkbox" ${g.visible ? 'checked' : ''} onchange="toggleGroupVis('${c.id}','${g.group_id}',this.checked)">
                            <span class="slider"></span>
                        </label>
                    </div>`;
            }
            for (const g of vis.pending) {
                groupsHTML += `
                    <div class="vis-group-row">
                        <div>
                            <span class="vis-group-name">${esc(g.group_name)}</span>
                            <div style="font-size:11px;color:var(--accent)">New &mdash; needs decision</div>
                        </div>
                        <div style="display:flex;gap:6px">
                            <button class="btn btn-primary btn-small" onclick="decideCourseGroup('${c.id}','${g.group_id}',true)">Share</button>
                            <button class="btn btn-secondary btn-small" onclick="decideCourseGroup('${c.id}','${g.group_id}',false)">Hide</button>
                        </div>
                    </div>`;
            }
        }

        const hasGroups = !c.hidden && totalGroups > 0;

        return `
            <div class="course-card">
                <div class="course-card-header ${hasGroups ? 'collapsible-header collapsed' : ''}" ${hasGroups ? 'onclick="toggleCollapsible(this)"' : ''}>
                    <div class="course-card-info">
                        <div class="course-card-name">${esc(c.name)}</div>
                        <div class="course-card-meta">${c.course_code ? esc(c.course_code) + (meta ? ' &middot; ' : '') : ''}${meta}</div>
                    </div>
                    <div class="course-card-controls">
                        <label class="toggle" onclick="event.stopPropagation()">
                            <input type="checkbox" ${c.hidden ? '' : 'checked'} onchange="toggleCourseHidden('${c.id}',this)">
                            <span class="slider"></span>
                        </label>
                        ${hasGroups ? '<span class="chevron" style="margin-left:8px;font-size:10px">&#9660;</span>' : ''}
                    </div>
                </div>
                ${hasGroups ? `<div class="collapsible-content collapsed" style="padding:8px 0 0 0">${groupsHTML}</div>` : ''}
            </div>
        `;
    }).join("");
}

async function toggleCourseHidden(courseId, checkbox) {
    const resp = await api(`/users/me/courses/${courseId}`, { method: "PATCH" });
    if (!resp.ok) {
        checkbox.checked = !checkbox.checked;
        showToast("Failed to update course", "error");
        return;
    }
    await loadCourses();
}

async function toggleGroupVis(courseId, groupId, visible) {
    const resp = await api("/visibility/settings", {
        method: "PATCH",
        body: JSON.stringify({ decisions: [{ course_id: courseId, group_id: groupId, visible }] }),
    });
    if (!resp.ok) {
        showToast("Failed to update visibility", "error");
    }
}

async function decideCourseGroup(courseId, groupId, visible) {
    const resp = await api("/visibility/decide", {
        method: "POST",
        body: JSON.stringify({ decisions: [{ course_id: courseId, group_id: groupId, visible }] }),
    });
    if (!resp.ok) {
        showToast("Failed to save decision", "error");
        return;
    }
    await loadCourses();
    await loadPending();
}
