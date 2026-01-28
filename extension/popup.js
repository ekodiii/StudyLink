const API_BASE = "https://api.studylink.app";

document.addEventListener("DOMContentLoaded", async () => {
    const { authToken, username, discriminator, lastSync } =
        await chrome.storage.local.get([
            "authToken",
            "username",
            "discriminator",
            "lastSync",
        ]);

    if (authToken) {
        showLoggedIn(username, discriminator, lastSync);
    } else {
        showLoggedOut();
    }
});

function showLoggedIn(username, discriminator, lastSync) {
    document.getElementById("logged-out").classList.add("hidden");
    document.getElementById("logged-in").classList.remove("hidden");
    document.getElementById("display-user").textContent =
        `${username || "user"}#${discriminator || "0000"}`;
    document.getElementById("display-sync").textContent = lastSync
        ? `Last sync: ${new Date(lastSync).toLocaleString()}`
        : "Not synced yet";
}

function showLoggedOut() {
    document.getElementById("logged-in").classList.add("hidden");
    document.getElementById("logged-out").classList.remove("hidden");
}

document.getElementById("btn-sync").addEventListener("click", async () => {
    const btn = document.getElementById("btn-sync");
    btn.textContent = "Syncing...";
    btn.disabled = true;

    const result = await chrome.runtime.sendMessage({ type: "MANUAL_SYNC" });

    if (result?.error) {
        btn.textContent = `Error: ${result.error}`;
    } else if (result?.skipped) {
        btn.textContent = "Recently synced";
    } else {
        btn.textContent = "Synced!";
        const { lastSync } = await chrome.storage.local.get("lastSync");
        document.getElementById("display-sync").textContent =
            `Last sync: ${new Date(lastSync).toLocaleString()}`;
    }

    setTimeout(() => {
        btn.textContent = "Sync Now";
        btn.disabled = false;
    }, 2000);
});

document.getElementById("btn-signout").addEventListener("click", async () => {
    await chrome.storage.local.clear();
    showLoggedOut();
});

// OAuth sign-in flows open a tab to the backend OAuth endpoint
document
    .getElementById("btn-google-signin")
    .addEventListener("click", () => {
        chrome.tabs.create({
            url: `${API_BASE}/auth/google/extension-flow`,
        });
    });

document
    .getElementById("btn-apple-signin")
    .addEventListener("click", () => {
        chrome.tabs.create({
            url: `${API_BASE}/auth/apple/extension-flow`,
        });
    });
