//
//  Models.swift
//  StudyLink
//
//  Data models for StudyLink iOS app
//

import Foundation

// MARK: - User Models

struct User: Codable, Identifiable {
    let id: String
    var username: String
    let discriminator: String
    let isNewUser: Bool?

    enum CodingKeys: String, CodingKey {
        case id, username, discriminator
        case isNewUser = "is_new_user"
    }
}

struct AuthResponse: Codable {
    let accessToken: String
    let refreshToken: String
    let user: User

    enum CodingKeys: String, CodingKey {
        case accessToken = "access_token"
        case refreshToken = "refresh_token"
        case user
    }
}

struct GoogleAuthRequest: Codable {
    let idToken: String

    enum CodingKeys: String, CodingKey {
        case idToken = "id_token"
    }
}

struct RefreshRequest: Codable {
    let refreshToken: String

    enum CodingKeys: String, CodingKey {
        case refreshToken = "refresh_token"
    }
}

// MARK: - Group Models

struct Group: Codable, Identifiable {
    let id: String
    let name: String
    let inviteCode: String
    let memberCount: Int
    let isLeader: Bool
    let createdAt: Date

    enum CodingKeys: String, CodingKey {
        case id, name
        case inviteCode = "invite_code"
        case memberCount = "member_count"
        case isLeader = "is_leader"
        case createdAt = "created_at"
    }
}

struct GroupDetail: Codable, Identifiable {
    let id: String
    let name: String
    let inviteCode: String
    let leader: GroupMember
    let members: [GroupMember]
    var assignmentViewEnabled: Bool

    enum CodingKeys: String, CodingKey {
        case id, name
        case inviteCode = "invite_code"
        case leader, members
        case assignmentViewEnabled = "assignment_view_enabled"
    }
}

struct GroupMember: Codable, Identifiable {
    let id: String
    let username: String
    let discriminator: String
    let joinedAt: Date?
    let lastSyncedAt: Date?

    enum CodingKeys: String, CodingKey {
        case id, username, discriminator
        case joinedAt = "joined_at"
        case lastSyncedAt = "last_synced_at"
    }
}

struct CreateGroupRequest: Codable {
    let name: String
}

struct JoinGroupRequest: Codable {
    let inviteCode: String

    enum CodingKeys: String, CodingKey {
        case inviteCode = "invite_code"
    }
}

// MARK: - Assignment Models

enum AssignmentStatus: String, Codable {
    case submitted
    case graded
    case late
    case missing
    case unsubmitted
    case overdue
}

struct Assignment: Codable, Identifiable {
    var id: String { assignmentId }  // Use assignmentId as ID
    let assignmentId: String
    let name: String
    let dueAt: Date?
    var status: AssignmentStatus
    let submittedAt: Date?
    let verification: Verification?

    enum CodingKeys: String, CodingKey {
        case assignmentId = "assignment_id"
        case name
        case dueAt = "due_at"
        case status
        case submittedAt = "submitted_at"
        case verification
    }

    var effectiveStatus: AssignmentStatus {
        if let dueAt = dueAt, status == .unsubmitted, dueAt < Date() {
            return .overdue
        }
        return status
    }
}

struct Course: Codable, Identifiable {
    var id: String { courseId }  // Use courseId as ID
    let courseId: String
    let name: String
    let courseCode: String?
    let institution: String?
    let assignments: [Assignment]
    var hidden: Bool?

    enum CodingKeys: String, CodingKey {
        case courseId = "course_id"
        case name
        case courseCode = "course_code"
        case institution
        case assignments
        case hidden
    }
}

struct MemberProgress: Codable, Identifiable {
    var id: String { userId }  // Use userId as ID
    let userId: String
    let username: String
    let discriminator: String
    let lastSyncedAt: Date?
    let courses: [Course]

    enum CodingKeys: String, CodingKey {
        case userId = "user_id"
        case username, discriminator
        case lastSyncedAt = "last_synced_at"
        case courses
    }
}

struct GroupProgress: Codable {
    let members: [MemberProgress]
}

// MARK: - Dashboard Models

struct DashboardAssignment: Codable, Identifiable {
    var id: String { assignmentId }  // Use assignmentId as ID
    let assignmentId: String
    let name: String
    let dueAt: Date?
    let status: String  // Backend uses string
    let courseName: String
    let memberUsername: String
    let memberUserId: String

    enum CodingKeys: String, CodingKey {
        case assignmentId = "assignment_id"
        case name
        case dueAt = "due_at"
        case status
        case courseName = "course_name"
        case memberUsername = "member_username"
        case memberUserId = "member_user_id"
    }
}

struct Dashboard: Codable {
    let upcoming: [DashboardAssignment]
    let missing: [DashboardAssignment]
}

// MARK: - Verification Models

enum VerificationStatus: String, Codable {
    case pending
    case verified
}

struct Verification: Codable, Identifiable {
    let id: String
    let status: String  // Backend uses string, not enum
    let requesterId: String
    let requesterUsername: String
    let verifierId: String
    let verifierUsername: String
    let verificationWord: String

    enum CodingKeys: String, CodingKey {
        case id, status
        case requesterId = "requester_id"
        case requesterUsername = "requester_username"
        case verifierId = "verifier_id"
        case verifierUsername = "verifier_username"
        case verificationWord = "verification_word"
    }
}

struct VerificationRequest: Codable {
    let assignmentId: String
    let verifierId: String
    let groupId: String

    enum CodingKeys: String, CodingKey {
        case assignmentId = "assignment_id"
        case verifierId = "verifier_id"
        case groupId = "group_id"
    }
}

struct VerifyRequest: Codable {
    let verificationWord: String

    enum CodingKeys: String, CodingKey {
        case verificationWord = "verification_word"
    }
}

// MARK: - Visibility Models

struct VisibilitySetting: Codable, Identifiable {
    var id: String { "\(courseId)_\(groupId)" }  // Computed ID for SwiftUI
    let courseId: String
    let courseName: String
    let groupId: String
    let groupName: String
    var visible: Bool

    enum CodingKeys: String, CodingKey {
        case courseId = "course_id"
        case courseName = "course_name"
        case groupId = "group_id"
        case groupName = "group_name"
        case visible
    }
}

struct VisibilitySettings: Codable {
    let settings: [VisibilitySetting]
}

struct PendingGroup: Codable, Identifiable {
    var id: String { groupId }
    let groupId: String
    let groupName: String

    enum CodingKeys: String, CodingKey {
        case groupId = "group_id"
        case groupName = "group_name"
    }
}

struct PendingCourse: Codable, Identifiable {
    var id: String { courseId }
    let courseId: String
    let courseName: String
    let groups: [PendingGroup]

    enum CodingKeys: String, CodingKey {
        case courseId = "course_id"
        case courseName = "course_name"
        case groups
    }
}

struct PendingVisibility: Codable {
    let pending: [PendingCourse]
}

struct VisibilityDecision: Codable {
    let courseId: String
    let groupId: String
    let visible: Bool

    enum CodingKeys: String, CodingKey {
        case courseId = "course_id"
        case groupId = "group_id"
        case visible
    }
}

struct VisibilityDecisionRequest: Codable {
    let decisions: [VisibilityDecision]
}

struct UpdateGroupRequest: Codable {
    let assignmentViewEnabled: Bool?

    enum CodingKeys: String, CodingKey {
        case assignmentViewEnabled = "assignment_view_enabled"
    }
}

struct UpdateUsernameRequest: Codable {
    let username: String
}
