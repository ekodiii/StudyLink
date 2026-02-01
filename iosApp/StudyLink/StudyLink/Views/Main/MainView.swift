//
//  MainView.swift
//  StudyLink
//
//  Main tabbed interface
//

import SwiftUI

enum MainTab {
    case groups
    case courses
    case visibility
}

struct MainView: View {
    @EnvironmentObject var appState: AppState
    @State private var selectedTab: MainTab = .groups
    @State private var showSettings = false

    var body: some View {
        NavigationView {
            VStack(spacing: 0) {
                // Header
                HStack {
                    Text("Study")
                        .font(.title2.bold())
                        .foregroundColor(.white)
                    +
                    Text("Link")
                        .font(.title2.bold())
                        .foregroundColor(Color("Accent"))

                    Spacer()

                    if let user = appState.currentUser {
                        Text("\(user.username)#\(user.discriminator)")
                            .font(.caption)
                            .foregroundColor(Color("Text2"))
                    }

                    Button {
                        showSettings = true
                    } label: {
                        Image(systemName: "gearshape.fill")
                            .foregroundColor(Color("Text2"))
                    }

                    Button {
                        appState.logout()
                    } label: {
                        Text("Sign Out")
                            .font(.caption.bold())
                            .foregroundColor(.white)
                            .padding(.horizontal, 12)
                            .padding(.vertical, 6)
                            .background(Color("Surface2"))
                            .cornerRadius(6)
                    }
                }
                .padding()
                .background(Color("Background"))

                Divider()
                    .background(Color("Border"))

                // Pending visibility banner
                PendingVisibilityBanner()

                // Tab Bar
                HStack(spacing: 0) {
                    TabButton(title: "Groups", isSelected: selectedTab == .groups) {
                        selectedTab = .groups
                    }
                    TabButton(title: "Courses", isSelected: selectedTab == .courses) {
                        selectedTab = .courses
                    }
                    TabButton(title: "Visibility", isSelected: selectedTab == .visibility) {
                        selectedTab = .visibility
                    }
                }
                .background(Color("Background"))

                Divider()
                    .background(Color("Border"))

                // Content
                VStack {
                    switch selectedTab {
                    case .groups:
                        GroupsListView()
                    case .courses:
                        CoursesView()
                    case .visibility:
                        VisibilityView()
                    }
                }
            }
            .background(Color("Background"))
            .navigationBarHidden(true)
            .sheet(isPresented: $showSettings) {
                SettingsView()
            }
        }
        .navigationViewStyle(StackNavigationViewStyle())
    }
}

struct TabButton: View {
    let title: String
    let isSelected: Bool
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            VStack(spacing: 4) {
                Text(title)
                    .font(.subheadline)
                    .foregroundColor(isSelected ? Color("Accent") : Color("Text2"))
                    .padding(.vertical, 10)

                Rectangle()
                    .fill(isSelected ? Color("Accent") : Color.clear)
                    .frame(height: 2)
            }
        }
        .frame(maxWidth: .infinity)
    }
}

#Preview {
    MainView()
        .environmentObject(AppState())
}
