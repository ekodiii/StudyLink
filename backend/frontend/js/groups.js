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

function showCreateModal() {
    show("modal-create");
    document.getElementById("create-name").value = "";
    document.getElementById("create-name").focus();
}

function showJoinModal() {
    show("modal-join");
    document.getElementById("join-code").value = "";
    document.getElementById("join-code").focus();
}

async function createGroup() {
    const name = document.getElementById("create-name").value.trim();
    if (!name) return;
    const resp = await api("/groups", { method: "POST", body: JSON.stringify({ name }) });
    if (!resp.ok) { showToast("Failed to create group", "error"); return; }
    hide("modal-create");
    const group = await resp.json();
    showGroupDetail(group.id);
}

async function joinGroup() {
    const code = document.getElementById("join-code").value.trim().toUpperCase();
    if (!code) return;
    const resp = await api("/groups/join", { method: "POST", body: JSON.stringify({ invite_code: code }) });
    if (resp.status === 404) { showToast("Invalid invite code", "error"); return; }
    if (resp.status === 409) { showToast("You're already a member of this group", "info"); return; }
    if (!resp.ok) { showToast("Failed to join group", "error"); return; }
    hide("modal-join");
    const group = await resp.json();
    showGroupDetail(group.id);
}
