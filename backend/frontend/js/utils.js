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

function isOverdue(a) {
    return a.due_at && a.status === "unsubmitted" && new Date(a.due_at) < new Date();
}

function effectiveStatus(a) {
    return isOverdue(a) ? "overdue" : a.status;
}

function statusHTML(s) {
    const labels = {
        submitted: "Submitted",
        graded: "Graded",
        late: "Late",
        missing: "Missing",
        unsubmitted: "Not yet",
        overdue: "Overdue",
        no_submission: "No submission",
    };
    return `<span class="status status-${s}">${labels[s] || s}</span>`;
}

function formatDue(iso) {
    if (!iso) return "";
    return new Date(iso).toLocaleDateString("en-US", { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" });
}

function toggleCollapsible(el) {
    const content = el.nextElementSibling;
    const isOpen = !content.classList.contains("collapsed");
    content.classList.toggle("collapsed", isOpen);
    el.classList.toggle("collapsed", isOpen);
}

function countStatuses(assignments) {
    const c = {};
    for (const a of assignments) {
        const s = effectiveStatus(a);
        c[s] = (c[s] || 0) + 1;
    }
    return c;
}

function summaryHTML(counts) {
    const parts = [];
    if (counts.submitted) parts.push(`<span class="status status-submitted">${counts.submitted} submitted</span>`);
    if (counts.graded) parts.push(`<span class="status status-graded">${counts.graded} graded</span>`);
    if (counts.late) parts.push(`<span class="status status-late">${counts.late} late</span>`);
    if (counts.missing) parts.push(`<span class="status status-missing">${counts.missing} missing</span>`);
    if (counts.overdue) parts.push(`<span class="status status-overdue">${counts.overdue} overdue</span>`);
    if (counts.unsubmitted) parts.push(`<span class="status status-unsubmitted">${counts.unsubmitted} pending</span>`);
    if (counts.no_submission) parts.push(`<span class="status status-no_submission">${counts.no_submission} no submission</span>`);
    return parts.length ? `<span class="summary-counts">${parts.join(' ')}</span>` : '';
}

function esc(s) {
    const d = document.createElement("div");
    d.textContent = s || "";
    return d.innerHTML;
}
