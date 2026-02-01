//
//  ProgressSection.swift
//  StudyLink
//
//  Assignment progress views (by member or by assignment)
//

import SwiftUI

struct ProgressSection: View {
    let group: GroupDetail
    let progress: GroupProgress?
    @Binding var selectedView: ProgressViewType
    let currentUserId: String
    let viewModel: GroupDetailViewModel

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            // Header with view toggle
            HStack {
                Text("Assignment Progress")
                    .font(.headline)
                    .foregroundColor(.white)

                Spacer()

                // Leader toggle for assignment view
                if group.leader.userId == currentUserId {
                    HStack(spacing: 8) {
                        Text("Assignment view")
                            .font(.caption)
                            .foregroundColor(Color("Text2"))

                        Toggle("", isOn: Binding(
                            get: { group.assignmentViewEnabled },
                            set: { newValue in
                                Task {
                                    await viewModel.toggleAssignmentView(newValue)
                                }
                            }
                        ))
                        .labelsHidden()
                        .toggleStyle(SwitchToggleStyle(tint: Color("Accent")))
                    }
                }
            }

            // View toggle buttons
            if group.assignmentViewEnabled {
                HStack(spacing: 0) {
                    ViewToggleButton(
                        title: ProgressViewType.member.rawValue,
                        isSelected: selectedView == .member
                    ) {
                        selectedView = .member
                    }

                    ViewToggleButton(
                        title: ProgressViewType.assignment.rawValue,
                        isSelected: selectedView == .assignment
                    ) {
                        selectedView = .assignment
                    }
                }
            }

            // Content
            if let progress = progress {
                if progress.members.isEmpty {
                    Text("No progress data yet. Members need to sync via the browser extension.")
                        .font(.body)
                        .foregroundColor(Color("Text2"))
                        .frame(maxWidth: .infinity)
                        .padding(.vertical, 40)
                } else {
                    if selectedView == .member || !group.assignmentViewEnabled {
                        ByMemberView(progress: progress, currentUserId: currentUserId, groupMembers: group.members, viewModel: viewModel)
                    } else {
                        ByAssignmentView(progress: progress)
                    }
                }
            }
        }
    }
}

struct ViewToggleButton: View {
    let title: String
    let isSelected: Bool
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            Text(title)
                .font(.caption)
                .foregroundColor(isSelected ? .white : Color("Text2"))
                .padding(.vertical, 8)
                .padding(.horizontal, 16)
                .background(isSelected ? Color("Accent") : Color("Surface2"))
                .overlay(
                    Rectangle()
                        .stroke(Color("Border"), lineWidth: 1)
                )
        }
        .frame(maxWidth: .infinity)
    }
}

struct ByMemberView: View {
    let progress: GroupProgress
    let currentUserId: String
    let groupMembers: [GroupMember]
    let viewModel: GroupDetailViewModel

    var body: some View {
        VStack(spacing: 12) {
            ForEach(progress.members) { member in
                MemberProgressCard(
                    member: member,
                    isCurrentUser: member.userId == currentUserId,
                    groupMembers: groupMembers,
                    viewModel: viewModel
                )
            }
        }
    }
}

struct MemberProgressCard: View {
    let member: MemberProgress
    let isCurrentUser: Bool
    let groupMembers: [GroupMember]
    let viewModel: GroupDetailViewModel

    @State private var isExpanded = false

    var allAssignments: [Assignment] {
        member.courses.flatMap { $0.assignments }
    }

    var statusCounts: [AssignmentStatus: Int] {
        var counts: [AssignmentStatus: Int] = [:]
        for assignment in allAssignments {
            let status = assignment.effectiveStatus
            counts[status, default: 0] += 1
        }
        return counts
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            Button {
                withAnimation {
                    isExpanded.toggle()
                }
            } label: {
                HStack {
                    Text(member.username)
                        .font(.headline)
                        .foregroundColor(.white)

                    Spacer()

                    StatusSummary(counts: statusCounts)

                    Text("synced \(timeAgo(member.lastSyncedAt))")
                        .font(.caption)
                        .foregroundColor(Color("Text2"))

                    Image(systemName: "chevron.down")
                        .font(.caption)
                        .foregroundColor(Color("Text2"))
                        .rotationEffect(.degrees(isExpanded ? 0 : -90))
                }
                .padding()
            }

            if isExpanded {
                VStack(spacing: 12) {
                    if member.courses.isEmpty {
                        Text("No visible courses")
                            .font(.caption)
                            .foregroundColor(Color("Text2"))
                            .padding(.vertical, 8)
                    } else {
                        ForEach(member.courses) { course in
                            CourseBlock(
                                course: course,
                                member: member,
                                isCurrentUser: isCurrentUser,
                                groupMembers: groupMembers,
                                viewModel: viewModel
                            )
                        }
                    }
                }
                .padding(.horizontal, 12)
                .padding(.bottom, 12)
            }
        }
        .background(Color("Surface"))
        .cornerRadius(12)
        .overlay(
            RoundedRectangle(cornerRadius: 12)
                .stroke(Color("Border"), lineWidth: 1)
        )
    }
}

struct CourseBlock: View {
    let course: Course
    let member: MemberProgress
    let isCurrentUser: Bool
    let groupMembers: [GroupMember]
    let viewModel: GroupDetailViewModel

    @State private var isExpanded = false

    var statusCounts: [AssignmentStatus: Int] {
        var counts: [AssignmentStatus: Int] = [:]
        for assignment in course.assignments {
            let status = assignment.effectiveStatus
            counts[status, default: 0] += 1
        }
        return counts
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            Button {
                withAnimation {
                    isExpanded.toggle()
                }
            } label: {
                HStack {
                    Text(course.courseCode ?? course.name)
                        .font(.subheadline.bold())
                        .foregroundColor(Color("Accent"))

                    StatusSummary(counts: statusCounts)

                    Spacer()

                    Image(systemName: "chevron.down")
                        .font(.caption2)
                        .foregroundColor(Color("Text2"))
                        .rotationEffect(.degrees(isExpanded ? 0 : -90))
                }
                .padding(.vertical, 6)
                .padding(.horizontal, 4)
            }

            if isExpanded {
                VStack(spacing: 6) {
                    if course.assignments.isEmpty {
                        Text("No assignments")
                            .font(.caption)
                            .foregroundColor(Color("Text2"))
                            .padding(.vertical, 6)
                    } else {
                        ForEach(course.assignments) { assignment in
                            ProgressAssignmentRow(
                                assignment: assignment,
                                member: member,
                                isCurrentUser: isCurrentUser,
                                groupMembers: groupMembers,
                                viewModel: viewModel
                            )
                        }
                    }
                }
            }
        }
    }
}

struct ProgressAssignmentRow: View {
    let assignment: Assignment
    let member: MemberProgress
    let isCurrentUser: Bool
    let groupMembers: [GroupMember]
    let viewModel: GroupDetailViewModel

    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            HStack(spacing: 8) {
                Text(assignment.name)
                    .font(.caption)
                    .foregroundColor(.white)
                    .lineLimit(1)

                Spacer()

                if let dueAt = assignment.dueAt {
                    Text(formatDue(dueAt))
                        .font(.caption2)
                        .foregroundColor(Color("Text2"))
                }

                StatusBadge(status: assignment.effectiveStatus)
            }

            // Verification UI would go here
            // Simplified for now
        }
        .padding(8)
        .background(Color("Surface2"))
        .cornerRadius(6)
    }
}

struct ByAssignmentView: View {
    let progress: GroupProgress

    var courseMap: [String: [(assignment: Assignment, member: String)]] {
        var map: [String: [(assignment: Assignment, member: String)]] = [:]

        for member in progress.members {
            for course in member.courses {
                let key = course.courseCode ?? course.name
                for assignment in course.assignments {
                    map[key, default: []].append((assignment, member.username))
                }
            }
        }

        return map
    }

    var body: some View {
        VStack(spacing: 12) {
            if courseMap.isEmpty {
                Text("No visible assignments")
                    .font(.body)
                    .foregroundColor(Color("Text2"))
                    .padding(.vertical, 40)
            } else {
                ForEach(Array(courseMap.keys.sorted()), id: \.self) { courseName in
                    CourseAssignmentCard(
                        courseName: courseName,
                        assignments: courseMap[courseName] ?? []
                    )
                }
            }
        }
    }
}

struct CourseAssignmentCard: View {
    let courseName: String
    let assignments: [(assignment: Assignment, member: String)]

    @State private var isExpanded = false

    // Group assignments by name+due date
    var groupedAssignments: [(name: String, dueAt: Date?, members: [(member: String, status: AssignmentStatus)])] {
        var groups: [String: (dueAt: Date?, members: [(String, AssignmentStatus)])] = [:]

        for item in assignments {
            let key = "\(item.assignment.name)||\(item.assignment.dueAt?.ISO8601Format() ?? "")"
            if groups[key] == nil {
                groups[key] = (item.assignment.dueAt, [])
            }
            groups[key]?.members.append((item.member, item.assignment.effectiveStatus))
        }

        return groups.map { key, value in
            let name = key.components(separatedBy: "||")[0]
            return (name, value.dueAt, value.members)
        }
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            Button {
                withAnimation {
                    isExpanded.toggle()
                }
            } label: {
                HStack {
                    Text(courseName)
                        .font(.headline)
                        .foregroundColor(.white)

                    Spacer()

                    Image(systemName: "chevron.down")
                        .font(.caption)
                        .foregroundColor(Color("Text2"))
                        .rotationEffect(.degrees(isExpanded ? 0 : -90))
                }
                .padding()
            }

            if isExpanded {
                VStack(spacing: 12) {
                    ForEach(groupedAssignments, id: \.name) { assignment in
                        VStack(alignment: .leading, spacing: 6) {
                            HStack {
                                Text(assignment.name)
                                    .font(.subheadline.bold())
                                    .foregroundColor(Color("Accent"))

                                Spacer()

                                if let dueAt = assignment.dueAt {
                                    Text(formatDue(dueAt))
                                        .font(.caption2)
                                        .foregroundColor(Color("Text2"))
                                }
                            }

                            ForEach(assignment.members, id: \.member) { memberStatus in
                                HStack {
                                    Text(memberStatus.member)
                                        .font(.caption)
                                        .foregroundColor(.white)

                                    Spacer()

                                    StatusBadge(status: memberStatus.status)
                                }
                                .padding(8)
                                .background(Color("Surface2"))
                                .cornerRadius(6)
                            }
                        }
                    }
                }
                .padding(.horizontal, 12)
                .padding(.bottom, 12)
            }
        }
        .background(Color("Surface"))
        .cornerRadius(12)
        .overlay(
            RoundedRectangle(cornerRadius: 12)
                .stroke(Color("Border"), lineWidth: 1)
        )
    }
}

struct StatusSummary: View {
    let counts: [AssignmentStatus: Int]

    var body: some View {
        HStack(spacing: 4) {
            ForEach([AssignmentStatus.submitted, .graded, .late, .missing, .overdue, .unsubmitted], id: \.self) { status in
                if let count = counts[status], count > 0 {
                    StatusBadge(status: status, count: count)
                }
            }
        }
    }
}

struct StatusBadge: View {
    let status: AssignmentStatus
    var count: Int?

    var statusColor: Color {
        switch status {
        case .submitted, .graded:
            return Color.green
        case .late:
            return Color.orange
        case .missing, .overdue:
            return Color.red
        case .unsubmitted:
            return Color("Text2")
        }
    }

    var statusLabel: String {
        switch status {
        case .submitted:
            return count != nil ? "\(count!) submitted" : "Submitted"
        case .graded:
            return count != nil ? "\(count!) graded" : "Graded"
        case .late:
            return count != nil ? "\(count!) late" : "Late"
        case .missing:
            return count != nil ? "\(count!) missing" : "Missing"
        case .overdue:
            return count != nil ? "\(count!) overdue" : "Overdue"
        case .unsubmitted:
            return count != nil ? "\(count!) pending" : "Not yet"
        }
    }

    var body: some View {
        Text(statusLabel)
            .font(.caption2.bold())
            .foregroundColor(statusColor)
            .padding(.horizontal, 6)
            .padding(.vertical, 2)
            .background(statusColor.opacity(0.15))
            .cornerRadius(4)
    }
}
