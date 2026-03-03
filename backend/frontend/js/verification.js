async function requestVerification(assignmentId, verifierId) {
    if (!verifierId) { showToast("Select a friend to verify", "info"); return; }
    const resp = await api("/verification/request", {
        method: "POST",
        body: JSON.stringify({ assignment_id: assignmentId, verifier_id: verifierId, group_id: currentGroupId }),
    });
    if (resp.status === 409) { showToast("Active verification already exists", "info"); return; }
    if (!resp.ok) { showToast("Failed to create request", "error"); return; }
    await loadProgress(currentGroupId);
}

async function confirmVerification(requestId) {
    const input = document.getElementById(`vword-${requestId}`);
    const word = input ? input.value.trim() : "";
    if (!word) { showToast("Type the verification word", "info"); return; }
    const resp = await api(`/verification/${requestId}/verify`, {
        method: "POST",
        body: JSON.stringify({ verification_word: word }),
    });
    if (resp.status === 400) { showToast("Incorrect word. Try again.", "error"); return; }
    if (!resp.ok) { showToast("Failed to verify", "error"); return; }
    await loadProgress(currentGroupId);
}

async function cancelVerification(requestId) {
    if (!await showConfirm("Cancel this verification request?")) return;
    const resp = await api(`/verification/${requestId}/cancel`, { method: "POST" });
    if (!resp.ok) { showToast("Failed to cancel", "error"); return; }
    await loadProgress(currentGroupId);
}

async function revokeVerification(requestId) {
    if (!await showConfirm("Revoke this verification?")) return;
    const resp = await api(`/verification/${requestId}/revoke`, { method: "POST" });
    if (!resp.ok) { showToast("Failed to revoke", "error"); return; }
    await loadProgress(currentGroupId);
}
