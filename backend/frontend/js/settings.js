function showHelp() {
    show("modal-help");
}

// Navigation — updates the URL hash
function showSettings() {
    navigate("settings");
}

// Rendering — called by the router
function renderSettings() {
    hide("screen-main");
    hide("screen-detail");
    hide("screen-auth");
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
