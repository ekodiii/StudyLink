//
//  GroupsListView.swift
//  StudyLink
//
//  Groups list with create/join functionality
//

import SwiftUI

struct GroupsListView: View {
    @EnvironmentObject var appState: AppState
    @State private var showCreateModal = false
    @State private var showJoinModal = false

    var body: some View {
        VStack(spacing: 0) {
            // Header
            HStack {
                Text("Your Groups")
                    .font(.title3.bold())
                    .foregroundColor(.white)

                Spacer()

                Button {
                    showJoinModal = true
                } label: {
                    Text("Join Group")
                        .font(.caption.bold())
                        .foregroundColor(.white)
                        .padding(.horizontal, 12)
                        .padding(.vertical, 6)
                        .background(Color("Surface2"))
                        .cornerRadius(6)
                }

                Button {
                    showCreateModal = true
                } label: {
                    Text("Create Group")
                        .font(.caption.bold())
                        .foregroundColor(.white)
                        .padding(.horizontal, 12)
                        .padding(.vertical, 6)
                        .background(Color("Accent"))
                        .cornerRadius(6)
                }
            }
            .padding()

            // Groups List
            ScrollView {
                LazyVStack(spacing: 12) {
                    if appState.groups.isEmpty {
                        VStack(spacing: 12) {
                            Text("No groups yet")
                                .font(.body)
                                .foregroundColor(Color("Text2"))
                            Text("Create one or join with an invite code")
                                .font(.caption)
                                .foregroundColor(Color("Text2"))
                        }
                        .frame(maxWidth: .infinity)
                        .padding(.vertical, 60)
                    } else {
                        ForEach(appState.groups) { group in
                            NavigationLink(destination: GroupDetailView(groupId: group.id)) {
                                GroupCard(group: group)
                            }
                        }
                    }
                }
                .padding()
            }
        }
        .sheet(isPresented: $showCreateModal) {
            CreateGroupModal()
        }
        .sheet(isPresented: $showJoinModal) {
            JoinGroupModal()
        }
        .task {
            await appState.loadGroups()
        }
    }
}

struct GroupCard: View {
    let group: Group

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack {
                Text(group.name)
                    .font(.headline)
                    .foregroundColor(.white)

                Spacer()

                Text("\(group.memberCount) member\(group.memberCount != 1 ? "s" : "")")
                    .font(.caption)
                    .foregroundColor(Color("Text2"))
            }

            HStack {
                Text(group.isLeader ? "Leader" : "Member")
                    .font(.caption)
                    .foregroundColor(Color("Text2"))

                Text("•")
                    .foregroundColor(Color("Text2"))

                Text("Created \(group.createdAt.formatted(date: .abbreviated, time: .omitted))")
                    .font(.caption)
                    .foregroundColor(Color("Text2"))
            }
        }
        .padding()
        .background(Color("Surface"))
        .cornerRadius(12)
        .overlay(
            RoundedRectangle(cornerRadius: 12)
                .stroke(Color("Border"), lineWidth: 1)
        )
    }
}

struct CreateGroupModal: View {
    @EnvironmentObject var appState: AppState
    @Environment(\.dismiss) var dismiss
    @State private var groupName = ""
    @State private var isCreating = false
    @State private var errorMessage: String?

    var body: some View {
        NavigationView {
            ZStack {
                Color("Background")
                    .ignoresSafeArea()

                VStack(spacing: 24) {
                    Text("Create Group")
                        .font(.title2.bold())
                        .foregroundColor(.white)

                    TextField("Group name", text: $groupName)
                        .textFieldStyle(CustomTextFieldStyle())
                        .submitLabel(.done)
                        .onSubmit {
                            Task { await createGroup() }
                        }

                    if let error = errorMessage {
                        Text(error)
                            .font(.caption)
                            .foregroundColor(.red)
                    }

                    HStack(spacing: 12) {
                        Button {
                            dismiss()
                        } label: {
                            Text("Cancel")
                                .font(.body.bold())
                                .foregroundColor(.white)
                                .frame(maxWidth: .infinity)
                                .padding()
                                .background(Color("Surface2"))
                                .cornerRadius(12)
                        }

                        Button {
                            Task { await createGroup() }
                        } label: {
                            Text("Create")
                                .font(.body.bold())
                                .foregroundColor(.white)
                                .frame(maxWidth: .infinity)
                                .padding()
                                .background(groupName.isEmpty ? Color.gray : Color("Accent"))
                                .cornerRadius(12)
                        }
                        .disabled(groupName.isEmpty || isCreating)
                    }

                    Spacer()
                }
                .padding()

                if isCreating {
                    Color.black.opacity(0.4)
                        .ignoresSafeArea()
                    ProgressView()
                        .progressViewStyle(CircularProgressViewStyle(tint: .white))
                        .scaleEffect(1.5)
                }
            }
            .navigationBarHidden(true)
        }
    }

    private func createGroup() async {
        guard !groupName.isEmpty else { return }

        isCreating = true
        errorMessage = nil

        do {
            _ = try await appState.createGroup(name: groupName)
            dismiss()
        } catch {
            errorMessage = error.localizedDescription
            isCreating = false
        }
    }
}

struct JoinGroupModal: View {
    @EnvironmentObject var appState: AppState
    @Environment(\.dismiss) var dismiss
    @State private var inviteCode = ""
    @State private var isJoining = false
    @State private var errorMessage: String?

    var body: some View {
        NavigationView {
            ZStack {
                Color("Background")
                    .ignoresSafeArea()

                VStack(spacing: 24) {
                    Text("Join Group")
                        .font(.title2.bold())
                        .foregroundColor(.white)

                    TextField("Invite code (e.g. ABC12XYZ)", text: $inviteCode)
                        .textFieldStyle(CustomTextFieldStyle())
                        .autocapitalization(.allCharacters)
                        .submitLabel(.done)
                        .onSubmit {
                            Task { await joinGroup() }
                        }
                        .onChange(of: inviteCode) {
                            inviteCode = inviteCode.uppercased()
                        }

                    if let error = errorMessage {
                        Text(error)
                            .font(.caption)
                            .foregroundColor(.red)
                    }

                    HStack(spacing: 12) {
                        Button {
                            dismiss()
                        } label: {
                            Text("Cancel")
                                .font(.body.bold())
                                .foregroundColor(.white)
                                .frame(maxWidth: .infinity)
                                .padding()
                                .background(Color("Surface2"))
                                .cornerRadius(12)
                        }

                        Button {
                            Task { await joinGroup() }
                        } label: {
                            Text("Join")
                                .font(.body.bold())
                                .foregroundColor(.white)
                                .frame(maxWidth: .infinity)
                                .padding()
                                .background(inviteCode.isEmpty ? Color.gray : Color("Accent"))
                                .cornerRadius(12)
                        }
                        .disabled(inviteCode.isEmpty || isJoining)
                    }

                    Spacer()
                }
                .padding()

                if isJoining {
                    Color.black.opacity(0.4)
                        .ignoresSafeArea()
                    ProgressView()
                        .progressViewStyle(CircularProgressViewStyle(tint: .white))
                        .scaleEffect(1.5)
                }
            }
            .navigationBarHidden(true)
        }
    }

    private func joinGroup() async {
        guard !inviteCode.isEmpty else { return }

        isJoining = true
        errorMessage = nil

        do {
            _ = try await appState.joinGroup(inviteCode: inviteCode)
            dismiss()
        } catch {
            errorMessage = error.localizedDescription
            isJoining = false
        }
    }
}

// Custom TextField Style
struct CustomTextFieldStyle: TextFieldStyle {
    func _body(configuration: TextField<Self._Label>) -> some View {
        configuration
            .padding()
            .background(Color("Surface2"))
            .cornerRadius(12)
            .overlay(
                RoundedRectangle(cornerRadius: 12)
                    .stroke(Color("Border"), lineWidth: 1)
            )
            .foregroundColor(.white)
    }
}

#Preview {
    GroupsListView()
        .environmentObject(AppState())
}
