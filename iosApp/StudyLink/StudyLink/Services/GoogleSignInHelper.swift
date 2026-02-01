//
//  GoogleSignInHelper.swift
//  StudyLink
//
//  Google Sign-In using official GoogleSignIn SDK
//

import Foundation
import GoogleSignIn

@MainActor
class GoogleSignInHelper: ObservableObject {
    static let shared = GoogleSignInHelper()

    private let clientID = "374855005519-b4vrdccg2ts9i5po31r3inotu6ij8i7k.apps.googleusercontent.com"

    private init() {
        // Configure GoogleSignIn
        let config = GIDConfiguration(clientID: clientID)
        GIDSignIn.sharedInstance.configuration = config
    }

    func signIn() async throws -> String {
        guard let windowScene = UIApplication.shared.connectedScenes.first as? UIWindowScene,
              let rootViewController = windowScene.windows.first?.rootViewController else {
            throw GoogleSignInError.noViewController
        }

        do {
            let result = try await GIDSignIn.sharedInstance.signIn(withPresenting: rootViewController)

            guard let idToken = result.user.idToken?.tokenString else {
                throw GoogleSignInError.noIDToken
            }

            return idToken
        } catch {
            if (error as NSError).code == GIDSignInError.canceled.rawValue {
                throw GoogleSignInError.userCancelled
            }
            throw error
        }
    }
}

enum GoogleSignInError: LocalizedError {
    case noViewController
    case noIDToken
    case userCancelled

    var errorDescription: String? {
        switch self {
        case .noViewController:
            return "Could not find view controller"
        case .noIDToken:
            return "No ID token received from Google"
        case .userCancelled:
            return "Sign-in was cancelled"
        }
    }
}
