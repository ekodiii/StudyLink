const browserAPI = typeof browser !== "undefined" ? browser : chrome;
const API_BASE = "https://studylink-production.up.railway.app";

document.addEventListener("DOMContentLoaded", async () => {
    const { authToken, username, discriminator, lastSync } =
        await browserAPI.storage.local.get([
            "authToken",
            "username",
            "discriminator",
            "lastSync",
        ]);

    if (authToken) {
        showLoggedIn(username, discriminator, lastSync);
        await renderAccounts();
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

    const result = await browserAPI.runtime.sendMessage({ type: "MANUAL_SYNC" });

    if (result?.error) {
        btn.textContent = `Error: ${result.error}`;
    } else if (result?.skipped) {
        btn.textContent = "Recently synced";
    } else {
        btn.textContent = "Synced!";
        const { lastSync } = await browserAPI.storage.local.get("lastSync");
        document.getElementById("display-sync").textContent =
            `Last sync: ${new Date(lastSync).toLocaleString()}`;
    }

    setTimeout(() => {
        btn.textContent = "Sync Now";
        btn.disabled = false;
    }, 2000);
});

document.getElementById("btn-signout").addEventListener("click", async () => {
    await browserAPI.storage.local.clear();
    showLoggedOut();
});

// OAuth sign-in flows open a tab to the backend OAuth endpoint
document
    .getElementById("btn-google-signin")
    .addEventListener("click", () => {
        browserAPI.tabs.create({
            url: `${API_BASE}/auth/google/extension-flow`,
        });
    });

document
    .getElementById("btn-apple-signin")
    .addEventListener("click", () => {
        browserAPI.tabs.create({
            url: `${API_BASE}/auth/apple/extension-flow`,
        });
    });

async function renderAccounts() {
    const stored = await browserAPI.storage.local.get("knownAccounts");
    const accounts = stored.knownAccounts || [];
    const section = document.getElementById("accounts-section");
    const list = document.getElementById("accounts-list");

    if (accounts.length === 0) {
        section.classList.add("hidden");
        return;
    }

    section.classList.remove("hidden");
    list.innerHTML = "";

    accounts.forEach((acct, idx) => {
        const item = document.createElement("div");
        item.className = "account-item";

        const shortDomain = acct.domain.replace(".instructure.com", "");
        const statusClass = acct.status === "allowed" ? "allowed" : "denied";
        const statusLabel = acct.status === "allowed" ? "Allowed" : "Denied";
        const toggleLabel = acct.status === "allowed" ? "Deny" : "Allow";
        const toggleClass = acct.status === "allowed" ? "btn-danger btn-small" : "btn-primary btn-small";

        item.innerHTML = `
            <div class="account-info">
                <div class="account-domain">${shortDomain}</div>
                <div class="account-id">ID: ${acct.canvasUserId}</div>
            </div>
            <span class="account-status-badge ${statusClass}">${statusLabel}</span>
            <div class="account-actions">
                <button class="btn-toggle ${toggleClass}" data-idx="${idx}">${toggleLabel}</button>
                <button class="btn-remove btn-danger btn-small" data-idx="${idx}">Remove</button>
            </div>
        `;
        list.appendChild(item);
    });

    // Toggle allow/deny
    list.querySelectorAll(".btn-toggle").forEach((btn) => {
        btn.addEventListener("click", async () => {
            const idx = parseInt(btn.dataset.idx);
            const stored = await browserAPI.storage.local.get("knownAccounts");
            const accounts = stored.knownAccounts || [];
            if (accounts[idx]) {
                accounts[idx].status = accounts[idx].status === "allowed" ? "denied" : "allowed";
                await browserAPI.storage.local.set({ knownAccounts: accounts });
                renderAccounts();
            }
        });
    });

    // Remove account (from extension knowledge — backend data stays unless explicitly removed)
    list.querySelectorAll(".btn-remove").forEach((btn) => {
        btn.addEventListener("click", async () => {
            const idx = parseInt(btn.dataset.idx);
            const stored = await browserAPI.storage.local.get("knownAccounts");
            const accounts = stored.knownAccounts || [];
            const removed = accounts.splice(idx, 1)[0];
            await browserAPI.storage.local.set({ knownAccounts: accounts });

            // Optionally remove backend data for this account
            if (removed && confirm(`Also remove synced data for this account from StudyLink?`)) {
                const { authToken } = await browserAPI.storage.local.get("authToken");
                if (authToken) {
                    try {
                        await fetch(`${API_BASE}/sync/account/${removed.canvasUserId}`, {
                            method: "DELETE",
                            headers: { Authorization: `Bearer ${authToken}` },
                        });
                    } catch (e) {
                        console.error("Failed to remove account data:", e);
                    }
                }
            }
            renderAccounts();
        });
    });
}
