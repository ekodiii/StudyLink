async function requestVerification(assignmentId, verifierId) {
    if (!verifierId) { alert("Select a friend to verify"); return; }
    const resp = await api("/verification/request", {
        method: "POST",
        body: JSON.stringify({ assignment_id: assignmentId, verifier_id: verifierId, group_id: currentGroupId }),
    });
    if (resp.status === 409) { alert("Active verification already exists"); return; }
    if (!resp.ok) { alert("Failed to create request"); return; }
    await loadProgress(currentGroupId);
}

async function confirmVerification(requestId) {
    const input = document.getElementById(`vword-${requestId}`);
    const word = input ? input.value.trim() : "";
    if (!word) { alert("Type the verification word"); return; }
    const resp = await api(`/verification/${requestId}/verify`, {
        method: "POST",
        body: JSON.stringify({ verification_word: word }),
    });
    if (resp.status === 400) { alert("Incorrect word. Try again."); return; }
    if (!resp.ok) { alert("Failed to verify"); return; }
    await loadProgress(currentGroupId);
}

async function cancelVerification(requestId) {
    if (!confirm("Cancel this verification request?")) return;
    const resp = await api(`/verification/${requestId}/cancel`, { method: "POST" });
    if (!resp.ok) { alert("Failed to cancel"); return; }
    await loadProgress(currentGroupId);
}

async function revokeVerification(requestId) {
    if (!confirm("Revoke this verification?")) return;
    const resp = await api(`/verification/${requestId}/revoke`, { method: "POST" });
    if (!resp.ok) { alert("Failed to revoke"); return; }
    await loadProgress(currentGroupId);
}
