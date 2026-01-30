(async function () {
    const browserAPI = typeof browser !== "undefined" ? browser : chrome;

    console.log("[StudyLink] Content script loaded on:", window.location.hostname);

    // Only run on Canvas pages
    if (!window.location.hostname.includes("instructure.com")) {
        console.log("[StudyLink] Not a Canvas page, exiting");
        return;
    }

    console.log("[StudyLink] Canvas page detected");

    // Prevent double-execution
    if (window.__studylinkLoaded) {
        console.log("[StudyLink] Already loaded, skipping");
        return;
    }
    window.__studylinkLoaded = true;

    // Check auth
    let authToken;
    try {
        const result = await browserAPI.storage.local.get("authToken");
        authToken = result.authToken;
    } catch (e) {
        console.error("[StudyLink] Failed to read storage:", e);
        return;
    }

    if (!authToken) {
        console.log("[StudyLink] No auth token, exiting");
        return;
    }
    console.log("[StudyLink] Authenticated");

    // Get Canvas user ID from API instead of ENV (content scripts can't access page JS)
    let canvasUserId;
    try {
        const resp = await fetch("/api/v1/users/self", { credentials: "same-origin" });
        if (!resp.ok) {
            console.log("[StudyLink] Not logged into Canvas (API returned", resp.status, ")");
            return;
        }
        const user = await resp.json();
        canvasUserId = String(user.id);
        console.log("[StudyLink] Canvas user ID:", canvasUserId);
    } catch (e) {
        console.error("[StudyLink] Failed to get Canvas user:", e);
        return;
    }

    // Listen for manual sync requests from popup
    browserAPI.runtime.onMessage.addListener((message, sender, sendResponse) => {
        if (message.type === "DO_SYNC") {
            syncAssignments().then(sendResponse);
            return true;
        }
    });

    // Auto-sync on page load
    await syncAssignments();

    async function syncAssignments() {
        const domain = window.location.hostname;

        try {
            // Step 1: Get all active courses
            console.log("[StudyLink] Fetching active courses...");
            const courses = await canvasFetch(
                "/api/v1/courses?enrollment_state=active&per_page=100"
            );

            if (!Array.isArray(courses) || courses.length === 0) {
                console.log("[StudyLink] No active courses found");
                return { error: "No active courses" };
            }

            console.log(`[StudyLink] Found ${courses.length} active courses`);

            const syncData = {
                institution_domain: domain,
                canvas_user_id: canvasUserId,
                courses: [],
            };

            // Step 2: For each course, fetch its assignments
            for (const course of courses) {
                if (!course.id || !course.name) continue;

                console.log(`[StudyLink] Fetching assignments for: ${course.name}`);

                let assignments = [];
                try {
                    assignments = await canvasFetch(
                        `/api/v1/courses/${course.id}/assignments?include[]=submission&per_page=100`
                    );
                } catch (err) {
                    console.warn(`[StudyLink] Skipping course ${course.name}: ${err.message}`);
                    continue;
                }

                if (!Array.isArray(assignments)) {
                    console.warn(`[StudyLink] Unexpected response for course ${course.name}`);
                    continue;
                }

                // Step 3: Map each assignment with its status
                syncData.courses.push({
                    canvas_course_id: String(course.id),
                    name: course.name,
                    course_code: course.course_code || "",
                    assignments: assignments.map((a) => ({
                        canvas_assignment_id: String(a.id),
                        name: a.name,
                        due_at: a.due_at || null,
                        points_possible: a.points_possible || 0,
                        submission: mapSubmission(a.submission),
                    })),
                });
            }

            console.log(
                `[StudyLink] Sync payload: ${syncData.courses.length} courses, ` +
                `${syncData.courses.reduce((n, c) => n + c.assignments.length, 0)} assignments`
            );

            // Step 4: Send the complete package to background for API call
            const result = await browserAPI.runtime.sendMessage({
                type: "TRIGGER_SYNC",
                data: syncData,
            });

            console.log("[StudyLink] Sync result:", JSON.stringify(result));
            return result;
        } catch (err) {
            console.error("[StudyLink] Sync error:", err);
            return { error: err.message };
        }
    }

    function mapSubmission(sub) {
        if (!sub) return { status: "unsubmitted" };

        let status = "unsubmitted";
        if (sub.missing) status = "missing";
        else if (sub.late) status = "late";
        else if (sub.workflow_state === "graded") status = "graded";
        else if (sub.workflow_state === "submitted") status = "submitted";

        return {
            status,
            submitted_at: sub.submitted_at || null,
        };
    }

    async function canvasFetch(path) {
        let allResults = [];
        let url = path;
        const seen = new Set();
        const MAX_PAGES = 20;
        let page = 0;

        while (url) {
            if (seen.has(url) || page >= MAX_PAGES) break;
            seen.add(url);
            page++;

            const response = await fetch(url, { credentials: "same-origin" });
            if (!response.ok) {
                throw new Error(`Canvas API ${response.status} for ${url}`);
            }

            const data = await response.json();

            if (!Array.isArray(data)) break;

            allResults = allResults.concat(data);

            const linkHeader = response.headers.get("Link");
            url = parseLinkNext(linkHeader);
        }

        return allResults;
    }

    function parseLinkNext(header) {
        if (!header) return null;
        const parts = header.split(",");
        for (const part of parts) {
            const match = part.match(/<([^>]+)>;\s*rel="next"/);
            if (match) return match[1];
        }
        return null;
    }
})();
