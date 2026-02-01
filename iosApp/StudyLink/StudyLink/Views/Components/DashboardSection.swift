//
//  DashboardSection.swift
//  StudyLink
//
//  Dashboard with upcoming, overdue, and missing assignments
//

import SwiftUI

struct DashboardSection: View {
    let dashboard: Dashboard
    let progress: GroupProgress?

    @State private var upcomingExpanded = false
    @State private var overdueExpanded = false
    @State private var missingExpanded = false

    var overdueAssignments: [DashboardAssignment] {
        guard let progress = progress else { return [] }

        var overdue: [DashboardAssignment] = []

        for member in progress.members {
            for course in member.courses {
                for assignment in course.assignments {
                    if assignment.effectiveStatus == .overdue {
                        overdue.append(DashboardAssignment(
                            name: assignment.name,
                            dueAt: assignment.dueAt,
                            status: .overdue,
                            courseName: course.courseCode ?? course.name,
                            memberUsername: member.username
                        ))
                    }
                }
            }
        }

        return overdue.sorted { ($0.dueAt ?? Date.distantPast) < ($1.dueAt ?? Date.distantPast) }
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            if !dashboard.upcoming.isEmpty || !overdueAssignments.isEmpty || !dashboard.missing.isEmpty {
                // Upcoming
                if !dashboard.upcoming.isEmpty {
                    DashboardCard(
                        title: "⏰ Upcoming (7 days)",
                        count: dashboard.upcoming.count,
                        isExpanded: $upcomingExpanded
                    ) {
                        ForEach(dashboard.upcoming, id: \.name) { assignment in
                            AssignmentRow(assignment: assignment)
                        }
                    }
                }

                // Overdue
                if !overdueAssignments.isEmpty {
                    DashboardCard(
                        title: "⏳ Overdue",
                        count: overdueAssignments.count,
                        isExpanded: $overdueExpanded
                    ) {
                        ForEach(overdueAssignments, id: \.name) { assignment in
                            AssignmentRow(assignment: assignment)
                        }
                    }
                }

                // Missing
                if !dashboard.missing.isEmpty {
                    DashboardCard(
                        title: "⚠️ Missing",
                        count: dashboard.missing.count,
                        isExpanded: $missingExpanded
                    ) {
                        ForEach(dashboard.missing, id: \.name) { assignment in
                            AssignmentRow(assignment: assignment)
                        }
                    }
                }
            }
        }
    }
}

struct DashboardCard<Content: View>: View {
    let title: String
    let count: Int
    @Binding var isExpanded: Bool
    @ViewBuilder let content: () -> Content

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            Button {
                withAnimation {
                    isExpanded.toggle()
                }
            } label: {
                HStack {
                    Text(title)
                        .font(.subheadline.bold())
                        .foregroundColor(.white)

                    Text("—")
                        .foregroundColor(Color("Text2"))

                    Text("\(count) assignment\(count != 1 ? "s" : "")")
                        .font(.caption)
                        .foregroundColor(Color("Text2"))

                    Spacer()

                    Image(systemName: "chevron.down")
                        .font(.caption)
                        .foregroundColor(Color("Text2"))
                        .rotationEffect(.degrees(isExpanded ? 0 : -90))
                }
                .padding()
            }

            if isExpanded {
                VStack(spacing: 6) {
                    content()
                }
                .padding(.horizontal, 12)
                .padding(.bottom, 12)
            }
        }
        .background(Color("Surface"))
        .cornerRadius(12)
    }
}

struct AssignmentRow: View {
    let assignment: DashboardAssignment

    var body: some View {
        HStack(alignment: .top, spacing: 8) {
            VStack(alignment: .leading, spacing: 2) {
                HStack {
                    Text(assignment.memberUsername)
                        .font(.caption)
                        .foregroundColor(Color("Text2"))

                    Text("•")
                        .font(.caption)
                        .foregroundColor(Color("Text2"))

                    Text(assignment.courseName)
                        .font(.caption)
                        .foregroundColor(Color("Text2"))

                    Text("—")
                        .font(.caption)
                        .foregroundColor(Color("Text2"))

                    Text(assignment.name)
                        .font(.caption)
                        .foregroundColor(.white)
                        .lineLimit(1)
                }

                if let dueAt = assignment.dueAt {
                    Text(formatDue(dueAt))
                        .font(.caption2)
                        .foregroundColor(Color("Text2"))
                }
            }

            Spacer()

            StatusBadge(status: assignment.status)
        }
        .padding(8)
        .background(Color("Surface2"))
        .cornerRadius(6)
    }
}
