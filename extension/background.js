const browserAPI = typeof browser !== "undefined" ? browser : chrome;
const API_BASE = "https://studylink-production.up.railway.app";
const SYNC_DEBOUNCE_MS = 5 * 60 * 1000; // 5 minutes

let lastSyncTime = 0;

browserAPI.runtime.onMessage.addListener((message, sender, sendResponse) => {
    if (message.type === "TRIGGER_SYNC") {
        handleSync(message.data).then(sendResponse);
        return true; // async response
    }
    if (message.type === "MANUAL_SYNC") {
        lastSyncTime = 0; // reset debounce
        browserAPI.tabs.query({ active: true, currentWindow: true }, (tabs) => {
            if (tabs[0]?.url?.includes(".instructure.com")) {
                browserAPI.tabs.sendMessage(tabs[0].id, { type: "DO_SYNC" }, sendResponse);
            } else {
                sendResponse({ error: "No Canvas tab active" });
            }
        });
        return true;
    }
});

// ---------------------------------------------------------------------------
// Listen for OAuth callback tabs and extract auth data from the URL hash
// ---------------------------------------------------------------------------
browserAPI.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
    if (!changeInfo.url) return;
    const url = changeInfo.url;
    if (!url.includes("/auth/google/extension-callback") &&
        !url.includes("/auth/apple/extension-callback")) return;

    const hashIdx = url.indexOf("#studylink-auth:");
    if (hashIdx === -1) return;

    try {
        const json = decodeURIComponent(url.substring(hashIdx + "#studylink-auth:".length));
        const data = JSON.parse(json);
        if (data.authToken) {
            browserAPI.storage.local.set({
                authToken: data.authToken,
                username: data.username,
                discriminator: data.discriminator,
            });
            // Close the callback tab after a short delay
            setTimeout(() => browserAPI.tabs.remove(tabId), 1000);
        }
    } catch (e) {
        console.error("StudyLink: failed to parse auth callback", e);
    }
});

async function handleSync(syncData) {
    const now = Date.now();
    if (now - lastSyncTime < SYNC_DEBOUNCE_MS) {
        return { skipped: true, reason: "debounced" };
    }

    const { authToken } = await browserAPI.storage.local.get("authToken");
    if (!authToken) {
        return { error: "Not authenticated" };
    }

    try {
        const response = await fetch(`${API_BASE}/sync`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                Authorization: `Bearer ${authToken}`,
            },
            body: JSON.stringify(syncData),
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }

        const result = await response.json();
        lastSyncTime = now;

        await browserAPI.storage.local.set({
            lastSync: new Date().toISOString(),
            lastSyncResult: result,
        });

        return result;
    } catch (err) {
        return { error: err.message };
    }
}
