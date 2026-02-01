//
//  VisibilityView.swift
//  StudyLink
//
//  Course visibility management per group
//

import SwiftUI

struct VisibilityView: View {
    @StateObject private var viewModel = VisibilityViewModel()
    @State private var selectedCourse: VisibilityCourseData?

    var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            // Header
            VStack(alignment: .leading, spacing: 8) {
                Text("Course Visibility")
                    .font(.title3.bold())
                    .foregroundColor(.white)

                Text("Control which courses each group can see. Click a course to manage per-group sharing.")
                    .font(.caption)
                    .foregroundColor(Color("Text2"))
            }
            .padding()

            // Pending banner
            if viewModel.pendingCount > 0 {
                HStack {
                    Text("\(viewModel.pendingCount) new course\(viewModel.pendingCount > 1 ? "s need" : " needs") visibility decisions")
                        .font(.body)
                        .foregroundColor(.white)

                    Spacer()
                }
                .padding()
                .background(Color("Surface2"))
                .cornerRadius(12)
                .overlay(
                    RoundedRectangle(cornerRadius: 12)
                        .stroke(Color("Accent"), lineWidth: 1)
                )
                .padding(.horizontal)
            }

            // Courses List
            ScrollView {
                LazyVStack(spacing: 12) {
                    if viewModel.isLoading {
                        ProgressView()
                            .frame(maxWidth: .infinity)
                            .padding(.top, 40)
                    } else if viewModel.visibilityCourses.isEmpty {
                        Text("No courses synced yet. Use the browser extension to sync your Canvas assignments.")
                            .font(.body)
                            .foregroundColor(Color("Text2"))
                            .frame(maxWidth: .infinity)
                            .padding(.vertical, 40)
                    } else {
                        ForEach(viewModel.visibilityCourses) { course in
                            VisibilityCourseCard(course: course) {
                                selectedCourse = course
                            }
                        }
                    }
                }
                .padding()
            }
        }
        .task {
            await viewModel.loadVisibility()
        }
        .sheet(item: $selectedCourse) { course in
            VisibilityCourseSheet(course: course, viewModel: viewModel)
        }
    }
}

struct VisibilityCourseCard: View {
    let course: VisibilityCourseData
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            VStack(alignment: .leading, spacing: 6) {
                Text(course.name)
                    .font(.headline)
                    .foregroundColor(.white)

                HStack(spacing: 4) {
                    Text(course.metaText)
                        .font(.caption)
                        .foregroundColor(Color("Text2"))

                    if course.pendingCount > 0 {
                        Text("•")
                            .font(.caption)
                            .foregroundColor(Color("Text2"))

                        Text("\(course.pendingCount) pending")
                            .font(.caption)
                            .foregroundColor(Color("Accent"))
                    }
                }
            }
            .frame(maxWidth: .infinity, alignment: .leading)
            .padding()
            .background(Color("Surface"))
            .cornerRadius(12)
            .overlay(
                RoundedRectangle(cornerRadius: 12)
                    .stroke(Color("Border"), lineWidth: 1)
            )
        }
    }
}

struct VisibilityCourseSheet: View {
    let course: VisibilityCourseData
    let viewModel: VisibilityViewModel
    @Environment(\.dismiss) var dismiss

    var body: some View {
        NavigationView {
            ZStack {
                Color("Background")
                    .ignoresSafeArea()

                VStack(alignment: .leading, spacing: 20) {
                    // Course title
                    VStack(alignment: .leading, spacing: 4) {
                        Text(course.name)
                            .font(.title3.bold())
                            .foregroundColor(.white)

                        Text("Choose which groups can see this course")
                            .font(.caption)
                            .foregroundColor(Color("Text2"))
                    }
                    .padding(.horizontal)
                    .padding(.top)

                    ScrollView {
                        VStack(spacing: 12) {
                            // Existing groups
                            ForEach(course.groups) { group in
                                HStack {
                                    Text(group.groupName)
                                        .font(.body)
                                        .foregroundColor(.white)

                                    Spacer()

                                    Toggle("", isOn: Binding(
                                        get: { group.visible },
                                        set: { newValue in
                                            Task {
                                                await viewModel.toggleVisibility(
                                                    courseId: course.id,
                                                    groupId: group.groupId,
                                                    visible: newValue
                                                )
                                            }
                                        }
                                    ))
                                    .labelsHidden()
                                    .toggleStyle(SwitchToggleStyle(tint: Color("Accent")))
                                }
                                .padding()
                                .overlay(
                                    Rectangle()
                                        .frame(height: 1)
                                        .foregroundColor(Color("Border")),
                                    alignment: .bottom
                                )
                            }

                            // Pending groups
                            ForEach(course.pendingGroups) { pending in
                                HStack {
                                    VStack(alignment: .leading, spacing: 2) {
                                        Text(pending.groupName)
                                            .font(.body)
                                            .foregroundColor(.white)

                                        Text("New")
                                            .font(.caption2.bold())
                                            .foregroundColor(Color("Accent"))
                                    }

                                    Spacer()

                                    HStack(spacing: 8) {
                                        Button {
                                            Task {
                                                await viewModel.decidePending(
                                                    courseId: course.id,
                                                    groupId: pending.groupId,
                                                    visible: true
                                                )
                                            }
                                        } label: {
                                            Text("Share")
                                                .font(.caption.bold())
                                                .foregroundColor(.white)
                                                .padding(.horizontal, 12)
                                                .padding(.vertical, 6)
                                                .background(Color("Accent"))
                                                .cornerRadius(6)
                                        }

                                        Button {
                                            Task {
                                                await viewModel.decidePending(
                                                    courseId: course.id,
                                                    groupId: pending.groupId,
                                                    visible: false
                                                )
                                            }
                                        } label: {
                                            Text("Hide")
                                                .font(.caption.bold())
                                                .foregroundColor(.white)
                                                .padding(.horizontal, 12)
                                                .padding(.vertical, 6)
                                                .background(Color("Surface2"))
                                                .cornerRadius(6)
                                        }
                                    }
                                }
                                .padding()
                                .overlay(
                                    Rectangle()
                                        .frame(height: 1)
                                        .foregroundColor(Color("Border")),
                                    alignment: .bottom
                                )
                            }
                        }
                        .padding(.horizontal)
                    }

                    HStack {
                        Spacer()
                        Button {
                            dismiss()
                        } label: {
                            Text("Done")
                                .font(.body.bold())
                                .foregroundColor(.white)
                                .padding(.horizontal, 24)
                                .padding(.vertical, 12)
                                .background(Color("Surface2"))
                                .cornerRadius(12)
                        }
                        Spacer()
                    }
                    .padding()
                }
            }
            .navigationBarHidden(true)
        }
    }
}

struct VisibilityCourseData: Identifiable {
    let id: String
    let name: String
    var groups: [VisibilityGroupData]
    var pendingGroups: [PendingGroup]

    var sharedCount: Int {
        groups.filter { $0.visible }.count
    }

    var totalGroups: Int {
        groups.count + pendingGroups.count
    }

    var pendingCount: Int {
        pendingGroups.count
    }

    var metaText: String {
        if totalGroups > 0 {
            return "Shared with \(sharedCount)/\(totalGroups) group\(totalGroups != 1 ? "s" : "")"
        } else {
            return "No groups yet"
        }
    }
}

struct VisibilityGroupData: Identifiable {
    let id: String
    let groupId: String
    let groupName: String
    var visible: Bool
}

@MainActor
class VisibilityViewModel: ObservableObject {
    @Published var visibilityCourses: [VisibilityCourseData] = []
    @Published var pendingCount = 0
    @Published var isLoading = false
    @Published var errorMessage: String?

    private let api = APIService.shared

    func loadVisibility() async {
        isLoading = true

        do {
            async let settingsTask = api.getVisibilitySettings()
            async let pendingTask = api.getPendingVisibility()
            async let coursesTask = api.getUserCourses()

            let settings = try await settingsTask
            let pending = try await pendingTask
            let courses = try await coursesTask

            // Build course map
            var courseMap: [String: VisibilityCourseData] = [:]

            // Add settings
            for setting in settings.settings {
                if courseMap[setting.courseId] == nil {
                    courseMap[setting.courseId] = VisibilityCourseData(
                        id: setting.courseId,
                        name: setting.courseName,
                        groups: [],
                        pendingGroups: []
                    )
                }
                courseMap[setting.courseId]?.groups.append(VisibilityGroupData(
                    id: setting.id,
                    groupId: setting.groupId,
                    groupName: setting.groupName,
                    visible: setting.visible
                ))
            }

            // Add courses without settings yet (non-hidden only)
            for course in courses where !(course.hidden ?? false) {
                if courseMap[course.id] == nil {
                    courseMap[course.id] = VisibilityCourseData(
                        id: course.id,
                        name: course.name,
                        groups: [],
                        pendingGroups: []
                    )
                }
            }

            // Add pending
            for pendingCourse in pending.pending {
                if courseMap[pendingCourse.courseId] != nil {
                    courseMap[pendingCourse.courseId]?.pendingGroups = pendingCourse.groups
                }
            }

            visibilityCourses = Array(courseMap.values).sorted { $0.name < $1.name }
            pendingCount = pending.pending.reduce(0) { $0 + $1.groups.count }
        } catch {
            errorMessage = error.localizedDescription
        }

        isLoading = false
    }

    func toggleVisibility(courseId: String, groupId: String, visible: Bool) async {
        do {
            let decision = VisibilityDecision(courseId: courseId, groupId: groupId, visible: visible)
            try await api.updateVisibilitySettings(decisions: [decision])

            // Update local state
            if let courseIndex = visibilityCourses.firstIndex(where: { $0.id == courseId }) {
                if let groupIndex = visibilityCourses[courseIndex].groups.firstIndex(where: { $0.groupId == groupId }) {
                    visibilityCourses[courseIndex].groups[groupIndex].visible = visible
                }
            }
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    func decidePending(courseId: String, groupId: String, visible: Bool) async {
        do {
            let decision = VisibilityDecision(courseId: courseId, groupId: groupId, visible: visible)
            try await api.decideVisibility(decisions: [decision])

            // Reload to get fresh data
            await loadVisibility()
        } catch {
            errorMessage = error.localizedDescription
        }
    }
}

#Preview {
    VisibilityView()
}
