//
//  StudyLinkApp.swift
//  StudyLink
//
//  Main app entry point
//

import SwiftUI

@main
struct StudyLinkApp: App {
    @StateObject private var appState = AppState()

    var body: some Scene {
        WindowGroup {
            ZStack {
                Color("Background")
                    .ignoresSafeArea()

                if appState.isAuthenticated {
                    MainView()
                        .environmentObject(appState)
                } else {
                    AuthView()
                        .environmentObject(appState)
                }
            }
            .preferredColorScheme(.dark)
        }
    }
}
