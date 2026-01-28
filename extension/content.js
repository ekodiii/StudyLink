(async function () {
    // Only run on Canvas pages
    if (!window.location.hostname.endsWith(".instructure.com")) return;

    // Wait for Canvas ENV to be available
    if (typeof ENV === "undefined" || !ENV.current_user_id) return;

    // Check auth
    const { authToken } = await chrome.storage.local.get("authToken");
    if (!authToken) return;

    // Listen for manual sync requests from popup
    chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
        if (message.type === "DO_SYNC") {
            syncAssignments().then(sendResponse);
            return true;
        }
    });

    // Auto-sync on page load
    await syncAssignments();

    async function syncAssignments() {
        const domain = window.location.hostname;
        const canvasUserId = String(ENV.current_user_id);

        try {
            const courses = await canvasFetch(
                "/api/v1/courses?enrollment_state=active&per_page=100"
            );

            const syncData = {
                institution_domain: domain,
                canvas_user_id: canvasUserId,
                courses: [],
            };

            for (const course of courses) {
                const assignments = await canvasFetch(
                    `/api/v1/courses/${course.id}/assignments?include[]=submission&per_page=100`
                );

                syncData.courses.push({
                    canvas_course_id: String(course.id),
                    name: course.name,
                    course_code: course.course_code,
                    assignments: assignments.map((a) => ({
                        canvas_assignment_id: String(a.id),
                        name: a.name,
                        due_at: a.due_at,
                        points_possible: a.points_possible,
                        submission: mapSubmission(a.submission),
                    })),
                });
            }

            // Send to background script for debounced API call
            const result = await chrome.runtime.sendMessage({
                type: "TRIGGER_SYNC",
                data: syncData,
            });

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
            submitted_at: sub.submitted_at,
        };
    }

    async function canvasFetch(path) {
        let allResults = [];
        let url = path;

        while (url) {
            const response = await fetch(url, { credentials: "same-origin" });
            if (!response.ok)
                throw new Error(`Canvas API error: ${response.status}`);

            const data = await response.json();
            allResults = allResults.concat(data);

            const linkHeader = response.headers.get("Link");
            url = parseLinkHeader(linkHeader)?.next || null;
        }

        return allResults;
    }

    function parseLinkHeader(header) {
        if (!header) return null;
        const links = {};
        header.split(",").forEach((part) => {
            const match = part.match(/<([^>]+)>;\s*rel="([^"]+)"/);
            if (match) links[match[2]] = match[1];
        });
        return links;
    }
})();
