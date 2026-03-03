function initGoogleSignIn() {
    if (!window.google) {
        setTimeout(initGoogleSignIn, 500);
        return;
    }
    google.accounts.id.initialize({
        client_id: window.__GOOGLE_CLIENT_ID || "",
        callback: handleGoogleAuth,
        auto_select: true,
    });
    google.accounts.id.renderButton(
        document.getElementById("google-signin-btn"),
        { theme: "outline", size: "large", text: "signin_with", shape: "pill", width: 280 }
    );
}

async function handleGoogleAuth(response) {
    const resp = await fetch(`${API}/auth/google`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ id_token: response.credential }),
    });
    if (!resp.ok) {
        alert("Sign-in failed. Please try again.");
        return;
    }
    const data = await resp.json();
    token = data.access_token;
    refreshToken = data.refresh_token;
    localStorage.setItem("token", token);
    localStorage.setItem("refreshToken", refreshToken);
    currentUser = data.user;

    await showMain();

    if (data.user.is_new_user) {
        localStorage.setItem("hasSeenHelp", "true");
        showHelp();
    }
}

function doLogout() {
    token = null;
    refreshToken = null;
    currentUser = null;
    localStorage.removeItem("token");
    localStorage.removeItem("refreshToken");
    // Suppress the hashchange that follows so handleRoute doesn't try to auth-check
    _routeHandled = true;
    location.hash = "";
    hide("screen-main");
    hide("screen-detail");
    hide("screen-settings");
    show("screen-auth");
    if (window.google) {
        google.accounts.id.disableAutoSelect();
    }
    initGoogleSignIn();
}
