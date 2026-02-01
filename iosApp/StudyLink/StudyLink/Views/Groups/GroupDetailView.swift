//
//  GroupDetailView.swift
//  StudyLink
//
//  Detailed group view with members, dashboard, and progress
//

import SwiftUI

enum ProgressViewType: String {
    case member = "By Member"
    case assignment = "By Assignment"
}

struct GroupDetailView: View {
    let groupId: String

    @EnvironmentObject var appState: AppState
    @StateObject private var viewModel = GroupDetailViewModel()
    @State private var selectedView: ProgressViewType = .member
    @State private var showDeleteConfirm = false
    @State private var showLeaveConfirm = false

    var body: some View {
        ZStack {
            Color("Background")
                .ignoresSafeArea()

            ScrollView {
                VStack(alignment: .leading, spacing: 20) {
                    if let group = viewModel.group {
                        // Group Header
                        GroupHeaderSection(group: group, viewModel: viewModel, showDeleteConfirm: $showDeleteConfirm, showLeaveConfirm: $showLeaveConfirm)

                        // Invite Code
                        InviteCodeSection(group: group, viewModel: viewModel)

                        // Members
                        MembersSection(group: group)

                        // Dashboard
                        if let dashboard = viewModel.dashboard {
                            DashboardSection(dashboard: dashboard, progress: viewModel.progress)
                        }

                        // Progress
                        ProgressSection(
                            group: group,
                            progress: viewModel.progress,
                            selectedView: $selectedView,
                            currentUserId: appState.currentUser?.id ?? "",
                            viewModel: viewModel
                        )
                    } else if viewModel.isLoading {
                        ProgressView()
                            .frame(maxWidth: .infinity)
                            .padding(.top, 100)
                    }
                }
                .padding()
            }
        }
        .navigationTitle(viewModel.group?.name ?? "Group")
        .navigationBarTitleDisplayMode(.inline)
        .task {
            await viewModel.loadGroup(groupId: groupId)
        }
        .alert("Delete Group", isPresented: $showDeleteConfirm) {
            Button("Cancel", role: .cancel) { }
            Button("Delete", role: .destructive) {
                Task {
                    await viewModel.deleteGroup()
                    appState.selectedGroup = nil
                }
            }
        } message: {
            Text("This cannot be undone.")
        }
        .alert("Leave Group", isPresented: $showLeaveConfirm) {
            Button("Cancel", role: .cancel) { }
            Button("Leave", role: .destructive) {
                Task {
                    await viewModel.leaveGroup()
                    appState.selectedGroup = nil
                }
            }
        } message: {
            Text("Are you sure you want to leave this group?")
        }
    }
}

struct GroupHeaderSection: View {
    let group: GroupDetail
    let viewModel: GroupDetailViewModel
    @Binding var showDeleteConfirm: Bool
    @Binding var showLeaveConfirm: Bool
    @EnvironmentObject var appState: AppState

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack {
                Text(group.name)
                    .font(.title2.bold())
                    .foregroundColor(.white)

                Spacer()

                Menu {
                    if group.leader.id == appState.currentUser?.id {
                        Button {
                            Task { await viewModel.regenerateInvite() }
                        } label: {
                            Label("New Invite Code", systemImage: "arrow.clockwise")
                        }

                        Button(role: .destructive) {
                            showDeleteConfirm = true
                        } label: {
                            Label("Delete Group", systemImage: "trash")
                        }
                    }

                    Button(role: .destructive) {
                        showLeaveConfirm = true
                    } label: {
                        Label("Leave Group", systemImage: "rectangle.portrait.and.arrow.right")
                    }
                } label: {
                    Image(systemName: "ellipsis.circle")
                        .foregroundColor(Color("Text2"))
                        .font(.title3)
                }
            }
        }
    }
}

struct InviteCodeSection: View {
    let group: GroupDetail
    let viewModel: GroupDetailViewModel
    @State private var copied = false

    var body: some View {
        HStack {
            VStack(alignment: .leading, spacing: 4) {
                Text("Invite Code")
                    .font(.caption)
                    .foregroundColor(Color("Text2"))

                Text(group.inviteCode)
                    .font(.system(.title3, design: .monospaced).bold())
                    .foregroundColor(.white)
                    .tracking(2)
            }

            Spacer()

            Button {
                UIPasteboard.general.string = group.inviteCode
                copied = true
                DispatchQueue.main.asyncAfter(deadline: .now() + 1.5) {
                    copied = false
                }
            } label: {
                Text(copied ? "Copied!" : "Copy")
                    .font(.caption.bold())
                    .foregroundColor(.white)
                    .padding(.horizontal, 12)
                    .padding(.vertical, 6)
                    .background(Color("Surface2"))
                    .cornerRadius(6)
            }
        }
        .padding()
        .background(Color("Surface2"))
        .cornerRadius(12)
        .overlay(
            RoundedRectangle(cornerRadius: 12)
                .stroke(Color("Border"), lineWidth: 1)
        )
    }
}

struct MembersSection: View {
    let group: GroupDetail

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("Members")
                .font(.headline)
                .foregroundColor(.white)

            VStack(spacing: 0) {
                ForEach(group.members) { member in
                    MemberRow(member: member, isLeader: member.id == group.leader.id)
                }
            }
        }
    }
}

struct MemberRow: View {
    let member: GroupMember
    let isLeader: Bool

    var body: some View {
        HStack {
            HStack(spacing: 8) {
                Text(member.username)
                    .font(.body)
                    .foregroundColor(.white)

                if isLeader {
                    Text("Leader")
                        .font(.caption.bold())
                        .foregroundColor(.white)
                        .padding(.horizontal, 6)
                        .padding(.vertical, 2)
                        .background(Color("Accent"))
                        .cornerRadius(4)
                }
            }

            Spacer()

            Text("synced \(timeAgo(member.lastSyncedAt))")
                .font(.caption)
                .foregroundColor(Color("Text2"))
        }
        .padding(.vertical, 10)
        .padding(.horizontal, 12)
        .background(Color("Surface"))
        .overlay(
            Rectangle()
                .frame(height: 1)
                .foregroundColor(Color("Border")),
            alignment: .bottom
        )
    }
}

#Preview {
    NavigationView {
        GroupDetailView(groupId: "test")
            .environmentObject(AppState())
    }
}
