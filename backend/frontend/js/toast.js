// toast.js — Toast notification system
const _toastContainer = document.createElement("div");
_toastContainer.id = "toast-container";
document.body.appendChild(_toastContainer);

function showToast(message, type = "info", duration = 4000) {
    const toast = document.createElement("div");
    toast.className = `toast toast-${type}`;

    const icons = { success: "\u2713", error: "\u2717", info: "\u24D8" };
    toast.innerHTML = `
        <span class="toast-icon">${icons[type] || icons.info}</span>
        <span class="toast-message">${esc(message)}</span>
    `;

    _toastContainer.appendChild(toast);
    requestAnimationFrame(() => toast.classList.add("toast-visible"));

    setTimeout(() => {
        toast.classList.remove("toast-visible");
        toast.addEventListener("transitionend", () => toast.remove());
    }, duration);
}

function showConfirm(message) {
    return new Promise(resolve => {
        const overlay = document.createElement("div");
        overlay.className = "modal-overlay";
        overlay.style.zIndex = "150";
        overlay.innerHTML = `
            <div class="modal">
                <p style="margin-bottom:16px;font-size:14px;line-height:1.5">${esc(message)}</p>
                <div class="modal-actions">
                    <button class="btn btn-secondary btn-small" data-action="cancel">Cancel</button>
                    <button class="btn btn-danger btn-small" data-action="confirm">Confirm</button>
                </div>
            </div>
        `;
        overlay.querySelector('[data-action="cancel"]').onclick = () => { overlay.remove(); resolve(false); };
        overlay.querySelector('[data-action="confirm"]').onclick = () => { overlay.remove(); resolve(true); };
        overlay.onclick = (e) => { if (e.target === overlay) { overlay.remove(); resolve(false); } };
        document.body.appendChild(overlay);
    });
}
