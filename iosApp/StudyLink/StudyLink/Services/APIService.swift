//
//  APIService.swift
//  StudyLink
//
//  Networking layer with async/await
//

import Foundation

enum APIError: Error, LocalizedError {
    case invalidURL
    case unauthorized
    case serverError(String)
    case decodingError
    case networkError(Error)

    var errorDescription: String? {
        switch self {
        case .invalidURL:
            return "Invalid URL"
        case .unauthorized:
            return "Unauthorized. Please sign in again."
        case .serverError(let message):
            return message
        case .decodingError:
            return "Failed to decode response"
        case .networkError(let error):
            return error.localizedDescription
        }
    }
}

@MainActor
class APIService: ObservableObject {
    static let shared = APIService()

    private let baseURL: String
    private let decoder: JSONDecoder
    private let encoder: JSONEncoder

    @Published var accessToken: String? {
        didSet {
            if let token = accessToken {
                UserDefaults.standard.set(token, forKey: "accessToken")
            } else {
                UserDefaults.standard.removeObject(forKey: "accessToken")
            }
        }
    }

    @Published var refreshToken: String? {
        didSet {
            if let token = refreshToken {
                UserDefaults.standard.set(token, forKey: "refreshToken")
            } else {
                UserDefaults.standard.removeObject(forKey: "refreshToken")
            }
        }
    }

    private init() {
        // For development, use localhost. For production, use your deployed URL
        #if DEBUG
        self.baseURL = "https://studylink-production.up.railway.app"
        #else
        self.baseURL = "https://studylink-production.up.railway.app"
        #endif

        self.decoder = JSONDecoder()
        self.decoder.dateDecodingStrategy = .iso8601

        self.encoder = JSONEncoder()
        self.encoder.dateEncodingStrategy = .iso8601

        // Load saved tokens
        self.accessToken = UserDefaults.standard.string(forKey: "accessToken")
        self.refreshToken = UserDefaults.standard.string(forKey: "refreshToken")
    }

    func clearTokens() {
        accessToken = nil
        refreshToken = nil
    }

    // MARK: - Generic Request

    private func request<T: Decodable>(
        _ endpoint: String,
        method: String = "GET",
        body: Data? = nil,
        requiresAuth: Bool = true
    ) async throws -> T {
        guard let url = URL(string: "\(baseURL)\(endpoint)") else {
            throw APIError.invalidURL
        }

        var request = URLRequest(url: url)
        request.httpMethod = method
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")

        if requiresAuth, let token = accessToken {
            request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }

        if let body = body {
            request.httpBody = body
        }

        do {
            let (data, response) = try await URLSession.shared.data(for: request)

            guard let httpResponse = response as? HTTPURLResponse else {
                throw APIError.serverError("Invalid response")
            }

            // Handle 401 - try to refresh token
            if httpResponse.statusCode == 401 && requiresAuth {
                if try await refreshAccessToken() {
                    // Retry with new token
                    request.setValue("Bearer \(accessToken!)", forHTTPHeaderField: "Authorization")
                    let (retryData, retryResponse) = try await URLSession.shared.data(for: request)
                    guard let retryHTTP = retryResponse as? HTTPURLResponse else {
                        throw APIError.serverError("Invalid response")
                    }
                    if retryHTTP.statusCode >= 400 {
                        throw APIError.serverError("Request failed with status \(retryHTTP.statusCode)")
                    }
                    return try decoder.decode(T.self, from: retryData)
                } else {
                    throw APIError.unauthorized
                }
            }

            if httpResponse.statusCode >= 400 {
                throw APIError.serverError("Request failed with status \(httpResponse.statusCode)")
            }

            return try decoder.decode(T.self, from: data)
        } catch let error as APIError {
            throw error
        } catch {
            throw APIError.networkError(error)
        }
    }

    private func requestNoResponse(
        _ endpoint: String,
        method: String,
        body: Data? = nil,
        requiresAuth: Bool = true
    ) async throws {
        guard let url = URL(string: "\(baseURL)\(endpoint)") else {
            throw APIError.invalidURL
        }

        var request = URLRequest(url: url)
        request.httpMethod = method
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")

        if requiresAuth, let token = accessToken {
            request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }

        if let body = body {
            request.httpBody = body
        }

        do {
            let (_, response) = try await URLSession.shared.data(for: request)

            guard let httpResponse = response as? HTTPURLResponse else {
                throw APIError.serverError("Invalid response")
            }

            if httpResponse.statusCode == 401 && requiresAuth {
                if try await refreshAccessToken() {
                    request.setValue("Bearer \(accessToken!)", forHTTPHeaderField: "Authorization")
                    let (_, retryResponse) = try await URLSession.shared.data(for: request)
                    guard let retryHTTP = retryResponse as? HTTPURLResponse else {
                        throw APIError.serverError("Invalid response")
                    }
                    if retryHTTP.statusCode >= 400 {
                        throw APIError.serverError("Request failed")
                    }
                    return
                } else {
                    throw APIError.unauthorized
                }
            }

            if httpResponse.statusCode >= 400 {
                throw APIError.serverError("Request failed")
            }
        } catch let error as APIError {
            throw error
        } catch {
            throw APIError.networkError(error)
        }
    }

    // MARK: - Auth

    func authenticateWithGoogle(idToken: String) async throws -> User {
        let request = GoogleAuthRequest(idToken: idToken)
        let body = try encoder.encode(request)
        let response: AuthResponse = try await self.request("/auth/google", method: "POST", body: body, requiresAuth: false)
        accessToken = response.accessToken
        refreshToken = response.refreshToken
        return response.user
    }

    private func refreshAccessToken() async throws -> Bool {
        guard let refresh = refreshToken else {
            return false
        }

        let request = RefreshRequest(refreshToken: refresh)
        let body = try encoder.encode(request)

        do {
            let response: AuthResponse = try await self.request("/auth/refresh", method: "POST", body: body, requiresAuth: false)
            accessToken = response.accessToken
            return true
        } catch {
            clearTokens()
            return false
        }
    }

    // MARK: - User

    func getCurrentUser() async throws -> User {
        return try await request("/users/me")
    }

    func updateUsername(_ username: String) async throws -> User {
        let request = UpdateUsernameRequest(username: username)
        let body = try encoder.encode(request)
        return try await self.request("/users/me", method: "PATCH", body: body)
    }

    func getUserCourses() async throws -> [Course] {
        return try await request("/users/me/courses")
    }

    func toggleCourseHidden(courseId: String) async throws {
        try await requestNoResponse("/users/me/courses/\(courseId)", method: "PATCH")
    }

    // MARK: - Groups

    func getGroups() async throws -> [Group] {
        return try await request("/groups")
    }

    func createGroup(name: String) async throws -> Group {
        let request = CreateGroupRequest(name: name)
        let body = try encoder.encode(request)
        return try await self.request("/groups", method: "POST", body: body)
    }

    func joinGroup(inviteCode: String) async throws -> Group {
        let request = JoinGroupRequest(inviteCode: inviteCode)
        let body = try encoder.encode(request)
        return try await self.request("/groups/join", method: "POST", body: body)
    }

    func getGroupDetail(groupId: String) async throws -> GroupDetail {
        return try await request("/groups/\(groupId)")
    }

    func updateGroup(groupId: String, assignmentViewEnabled: Bool) async throws -> GroupDetail {
        let request = UpdateGroupRequest(assignmentViewEnabled: assignmentViewEnabled)
        let body = try encoder.encode(request)
        return try await self.request("/groups/\(groupId)", method: "PATCH", body: body)
    }

    func regenerateInviteCode(groupId: String) async throws -> GroupDetail {
        return try await request("/groups/\(groupId)/regenerate-invite", method: "POST")
    }

    func leaveGroup(groupId: String) async throws {
        try await requestNoResponse("/groups/\(groupId)/leave", method: "DELETE")
    }

    func deleteGroup(groupId: String) async throws {
        try await requestNoResponse("/groups/\(groupId)", method: "DELETE")
    }

    func getGroupProgress(groupId: String) async throws -> GroupProgress {
        return try await request("/groups/\(groupId)/progress")
    }

    func getGroupDashboard(groupId: String) async throws -> Dashboard {
        return try await request("/groups/\(groupId)/dashboard")
    }

    // MARK: - Verification

    func requestVerification(assignmentId: String, verifierId: String, groupId: String) async throws {
        let request = VerificationRequest(assignmentId: assignmentId, verifierId: verifierId, groupId: groupId)
        let body = try encoder.encode(request)
        try await requestNoResponse("/verification/request", method: "POST", body: body)
    }

    func confirmVerification(requestId: String, word: String) async throws {
        let request = VerifyRequest(verificationWord: word)
        let body = try encoder.encode(request)
        try await requestNoResponse("/verification/\(requestId)/verify", method: "POST", body: body)
    }

    func cancelVerification(requestId: String) async throws {
        try await requestNoResponse("/verification/\(requestId)/cancel", method: "POST")
    }

    func revokeVerification(requestId: String) async throws {
        try await requestNoResponse("/verification/\(requestId)/revoke", method: "POST")
    }

    // MARK: - Visibility

    func getVisibilitySettings() async throws -> VisibilitySettings {
        return try await request("/visibility/settings")
    }

    func updateVisibilitySettings(decisions: [VisibilityDecision]) async throws {
        let request = VisibilityDecisionRequest(decisions: decisions)
        let body = try encoder.encode(request)
        try await requestNoResponse("/visibility/settings", method: "PATCH", body: body)
    }

    func getPendingVisibility() async throws -> PendingVisibility {
        return try await request("/visibility/pending")
    }

    func decideVisibility(decisions: [VisibilityDecision]) async throws {
        let request = VisibilityDecisionRequest(decisions: decisions)
        let body = try encoder.encode(request)
        try await requestNoResponse("/visibility/decide", method: "POST", body: body)
    }
}
