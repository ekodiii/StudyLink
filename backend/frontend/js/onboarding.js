// onboarding.js — Smart setup checklist

async function showOnboarding() {
    if (localStorage.getItem("onboardingDismissed")) return;

    const [coursesResp, groupsResp] = await Promise.all([
        api("/users/me/courses"),
        api("/groups"),
    ]);

    const courses = coursesResp.ok ? await coursesResp.json() : [];
    const groups = groupsResp.ok ? await groupsResp.json() : [];

    const steps = [
        {
            id: "signin",
            title: "Sign in with Google",
            done: true,
            help: ""
        },
        {
            id: "extension",
            title: "Install extension & sync courses",
            done: courses.length > 0,
            help: `<p>Install the <a href="https://chromewebstore.google.com/detail/StudyLink%20%E2%80%94%20Canvas%20Sync/cpcojnmmbkfgkoagljkopddbklohlkfk" target="_blank" rel="noopener">StudyLink Chrome Extension</a>, then visit any Canvas course page to sync.</p>
                   <p style="margin-top:8px;padding:8px 12px;background:var(--accent-soft);border-radius:8px;font-size:12px"><strong>Tip:</strong> After installing, reload your Canvas page for the extension to start syncing.</p>`
        },
        {
            id: "group",
            title: "Join or create a study group",
            done: groups.length > 0,
            help: `<p>Share an invite code with classmates or join an existing group.</p>
                   <div style="display:flex;gap:8px;margin-top:8px">
                       <button class="btn btn-secondary btn-small" onclick="document.getElementById('onboarding-panel').remove();showJoinModal()">Join Group</button>
                       <button class="btn btn-primary btn-small" onclick="document.getElementById('onboarding-panel').remove();showCreateModal()">Create Group</button>
                   </div>`
        }
    ];

    if (steps.every(s => s.done)) {
        localStorage.setItem("onboardingDismissed", "true");
        return;
    }

    renderOnboarding(steps);
}

function renderOnboarding(steps) {
    document.getElementById("onboarding-panel")?.remove();

    const doneCount = steps.filter(s => s.done).length;
    const panel = document.createElement("div");
    panel.id = "onboarding-panel";
    panel.className = "onboarding-panel";

    let stepsHTML = "";
    let foundFirstIncomplete = false;
    for (const step of steps) {
        const isFirstIncomplete = !step.done && !foundFirstIncomplete;
        if (isFirstIncomplete) foundFirstIncomplete = true;

        stepsHTML += `
            <div class="onboarding-step ${step.done ? 'done' : ''} ${isFirstIncomplete ? 'active' : ''}">
                <div class="onboarding-step-indicator">
                    ${step.done ? '<span class="check">\u2713</span>' : '<span class="circle"></span>'}
                </div>
                <div class="onboarding-step-content">
                    <div class="onboarding-step-title">${step.title}</div>
                    ${isFirstIncomplete && step.help ? `<div class="onboarding-step-help">${step.help}</div>` : ''}
                </div>
            </div>`;
    }

    panel.innerHTML = `
        <div class="onboarding-header">
            <h3>Getting Started</h3>
            <span class="onboarding-meta">${doneCount}/${steps.length}</span>
            <button class="btn-icon" onclick="dismissOnboarding()" title="Dismiss">&times;</button>
        </div>
        <div class="onboarding-progress">
            <div class="onboarding-progress-bar" style="width:${Math.round(doneCount / steps.length * 100)}%"></div>
        </div>
        <div class="onboarding-steps">${stepsHTML}</div>
    `;

    const pendingArea = document.getElementById("pending-area");
    pendingArea.parentNode.insertBefore(panel, pendingArea.nextSibling);
}

function dismissOnboarding() {
    localStorage.setItem("onboardingDismissed", "true");
    document.getElementById("onboarding-panel")?.remove();
}
