//
//  GroupDetailViewModel.swift
//  StudyLink
//
//  View model for group details
//

import Foundation

@MainActor
class GroupDetailViewModel: ObservableObject {
    @Published var group: GroupDetail?
    @Published var progress: GroupProgress?
    @Published var dashboard: Dashboard?
    @Published var isLoading = false
    @Published var errorMessage: String?

    private let api = APIService.shared
    private var groupId: String?

    func loadGroup(groupId: String) async {
        self.groupId = groupId
        isLoading = true

        do {
            async let groupTask = api.getGroupDetail(groupId: groupId)
            async let progressTask = api.getGroupProgress(groupId: groupId)
            async let dashboardTask = api.getGroupDashboard(groupId: groupId)

            group = try await groupTask
            progress = try await progressTask
            dashboard = try await dashboardTask
        } catch {
            errorMessage = error.localizedDescription
        }

        isLoading = false
    }

    func regenerateInvite() async {
        guard let groupId = groupId else { return }

        do {
            group = try await api.regenerateInviteCode(groupId: groupId)
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    func toggleAssignmentView(_ enabled: Bool) async {
        guard let groupId = groupId else { return }

        do {
            group = try await api.updateGroup(groupId: groupId, assignmentViewEnabled: enabled)
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    func leaveGroup() async {
        guard let groupId = groupId else { return }

        do {
            try await api.leaveGroup(groupId: groupId)
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    func deleteGroup() async {
        guard let groupId = groupId else { return }

        do {
            try await api.deleteGroup(groupId: groupId)
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    func reloadProgress() async {
        guard let groupId = groupId else { return }

        do {
            progress = try await api.getGroupProgress(groupId: groupId)
        } catch {
            errorMessage = error.localizedDescription
        }
    }
}
