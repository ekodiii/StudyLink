//
//  AuthView.swift
//  StudyLink
//
//  Authentication screen with Google Sign-In
//

import SwiftUI

struct AuthView: View {
    @EnvironmentObject var appState: AppState
    @State private var isLoading = false
    @State private var errorMessage: String?

    var body: some View {
        ZStack {
            Color("Background")
                .ignoresSafeArea()

            VStack(spacing: 32) {
                Spacer()

                // App Logo/Title
                VStack(spacing: 12) {
                    Text("Study")
                        .font(.system(size: 48, weight: .bold))
                        .foregroundColor(.white)
                    +
                    Text("Link")
                        .font(.system(size: 48, weight: .bold))
                        .foregroundColor(Color("Accent"))

                    Text("See at a glance whether your study group is keeping up with assignments.")
                        .font(.body)
                        .foregroundColor(Color("Text2"))
                        .multilineTextAlignment(.center)
                        .padding(.horizontal, 40)
                }

                Spacer()

                VStack(spacing: 16) {
                    // Google Sign In Button
                    Button {
                        Task {
                            await handleGoogleSignIn()
                        }
                    } label: {
                        HStack {
                            Image(systemName: "g.circle.fill")
                                .font(.title3)
                            Text("Sign in with Google")
                                .font(.body.bold())
                        }
                        .foregroundColor(.white)
                        .frame(maxWidth: .infinity)
                        .frame(height: 50)
                        .background(Color("Accent"))
                        .cornerRadius(12)
                    }
                    .padding(.horizontal, 40)
                    .disabled(isLoading)

                    if let error = errorMessage {
                        Text(error)
                            .font(.caption)
                            .foregroundColor(.red)
                            .padding(.horizontal, 40)
                    }
                }

                Spacer()
                    .frame(height: 80)
            }

            if isLoading {
                Color.black.opacity(0.4)
                    .ignoresSafeArea()
                ProgressView()
                    .progressViewStyle(CircularProgressViewStyle(tint: .white))
                    .scaleEffect(1.5)
            }
        }
    }

    private func handleGoogleSignIn() async {
        isLoading = true
        errorMessage = nil

        defer {
            isLoading = false  // Always reset loading state
        }

        do {
            // Get ID token from Google
            let idToken = try await GoogleSignInHelper.shared.signIn()

            // Authenticate with backend
            let user = try await APIService.shared.authenticateWithGoogle(idToken: idToken)

            // Update app state
            appState.currentUser = user
            appState.isAuthenticated = true
        } catch {
            errorMessage = error.localizedDescription
        }
    }
}

#Preview {
    AuthView()
        .environmentObject(AppState())
}
