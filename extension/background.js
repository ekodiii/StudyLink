const API_BASE = "https://api.studylink.app";
const SYNC_DEBOUNCE_MS = 5 * 60 * 1000; // 5 minutes

let lastSyncTime = 0;

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    if (message.type === "TRIGGER_SYNC") {
        handleSync(message.data).then(sendResponse);
        return true; // async response
    }
    if (message.type === "MANUAL_SYNC") {
        lastSyncTime = 0; // reset debounce
        chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
            if (tabs[0]?.url?.includes(".instructure.com")) {
                chrome.tabs.sendMessage(tabs[0].id, { type: "DO_SYNC" }, sendResponse);
            } else {
                sendResponse({ error: "No Canvas tab active" });
            }
        });
        return true;
    }
});

async function handleSync(syncData) {
    const now = Date.now();
    if (now - lastSyncTime < SYNC_DEBOUNCE_MS) {
        return { skipped: true, reason: "debounced" };
    }

    const { authToken } = await chrome.storage.local.get("authToken");
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

        await chrome.storage.local.set({
            lastSync: new Date().toISOString(),
            lastSyncResult: result,
        });

        return result;
    } catch (err) {
        return { error: err.message };
    }
}
