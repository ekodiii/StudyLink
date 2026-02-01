//
//  SettingsView.swift
//  StudyLink
//
//  User profile settings
//

import SwiftUI

struct SettingsView: View {
    @EnvironmentObject var appState: AppState
    @Environment(\.dismiss) var dismiss
    @State private var username = ""
    @State private var isSaving = false
    @State private var saveMessage: String?

    var body: some View {
        NavigationView {
            ZStack {
                Color("Background")
                    .ignoresSafeArea()

                VStack(alignment: .leading, spacing: 24) {
                    // Profile Settings Card
                    VStack(alignment: .leading, spacing: 16) {
                        Text("Profile Settings")
                            .font(.title3.bold())
                            .foregroundColor(.white)

                        VStack(alignment: .leading, spacing: 8) {
                            Text("Username")
                                .font(.caption)
                                .foregroundColor(Color("Text2"))

                            HStack(spacing: 12) {
                                TextField("Username", text: $username)
                                    .textFieldStyle(CustomTextFieldStyle())

                                Button {
                                    Task { await saveUsername() }
                                } label: {
                                    Text("Save")
                                        .font(.body.bold())
                                        .foregroundColor(.white)
                                        .padding(.horizontal, 16)
                                        .padding(.vertical, 12)
                                        .background(username.isEmpty ? Color.gray : Color("Accent"))
                                        .cornerRadius(12)
                                }
                                .disabled(username.isEmpty || isSaving)
                            }

                            if let user = appState.currentUser {
                                Text("Discriminator: #\(user.discriminator)")
                                    .font(.caption)
                                    .foregroundColor(Color("Text2"))
                            }

                            if let message = saveMessage {
                                Text(message)
                                    .font(.caption)
                                    .foregroundColor(Color("Accent"))
                            }
                        }
                    }
                    .padding()
                    .background(Color("Surface"))
                    .cornerRadius(12)
                    .overlay(
                        RoundedRectangle(cornerRadius: 12)
                            .stroke(Color("Border"), lineWidth: 1)
                    )

                    Spacer()
                }
                .padding()

                if isSaving {
                    Color.black.opacity(0.4)
                        .ignoresSafeArea()
                    ProgressView()
                        .progressViewStyle(CircularProgressViewStyle(tint: .white))
                        .scaleEffect(1.5)
                }
            }
            .navigationTitle("Settings")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .navigationBarLeading) {
                    Button {
                        dismiss()
                    } label: {
                        Image(systemName: "chevron.left")
                            .foregroundColor(.white)
                        Text("Back")
                            .foregroundColor(.white)
                    }
                }
            }
        }
        .onAppear {
            username = appState.currentUser?.username ?? ""
        }
    }

    private func saveUsername() async {
        guard !username.isEmpty else { return }

        isSaving = true
        saveMessage = nil

        do {
            let oldDisc = appState.currentUser?.discriminator
            try await appState.updateUsername(username)
            let newDisc = appState.currentUser?.discriminator

            if oldDisc != newDisc {
                saveMessage = "Username updated! Discriminator changed to #\(newDisc ?? "")"
            } else {
                saveMessage = "Username updated!"
            }

            DispatchQueue.main.asyncAfter(deadline: .now() + 3) {
                saveMessage = nil
            }
        } catch {
            saveMessage = "Failed to update: \(error.localizedDescription)"
        }

        isSaving = false
    }
}

#Preview {
    SettingsView()
        .environmentObject(AppState())
}
