//
//  AppState.swift
//  StudyLink
//
//  Main app state and view model
//

import Foundation
import SwiftUI

@MainActor
class AppState: ObservableObject {
    @Published var isAuthenticated = false
    @Published var currentUser: User?
    @Published var groups: [Group] = []
    @Published var selectedGroup: GroupDetail?
    @Published var isLoading = false
    @Published var errorMessage: String?

    private let api = APIService.shared

    init() {
        // Check if we have saved tokens
        if api.accessToken != nil {
            Task {
                await loadCurrentUser()
            }
        }
    }

    func loadCurrentUser() async {
        do {
            currentUser = try await api.getCurrentUser()
            isAuthenticated = true
            await loadGroups()
        } catch {
            // Token expired or invalid
            logout()
        }
    }

    func logout() {
        api.clearTokens()
        isAuthenticated = false
        currentUser = nil
        groups = []
        selectedGroup = nil
    }

    func loadGroups() async {
        do {
            groups = try await api.getGroups()
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    func createGroup(name: String) async throws -> Group {
        let group = try await api.createGroup(name: name)
        await loadGroups()
        return group
    }

    func joinGroup(inviteCode: String) async throws -> Group {
        let group = try await api.joinGroup(inviteCode: inviteCode)
        await loadGroups()
        return group
    }

    func loadGroupDetail(groupId: String) async {
        do {
            selectedGroup = try await api.getGroupDetail(groupId: groupId)
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    func updateUsername(_ username: String) async throws {
        currentUser = try await api.updateUsername(username)
    }
}
