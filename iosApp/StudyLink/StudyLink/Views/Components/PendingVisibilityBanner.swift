//
//  PendingVisibilityBanner.swift
//  StudyLink
//
//  Banner for pending visibility decisions
//

import SwiftUI

struct PendingVisibilityBanner: View {
    @StateObject private var viewModel = PendingViewModel()

    var body: some View {
        if viewModel.pendingCount > 0 {
            HStack {
                Text("\(viewModel.pendingCount) course\(viewModel.pendingCount > 1 ? "s" : "") need\(viewModel.pendingCount == 1 ? "s" : "") visibility decisions")
                    .font(.body)
                    .foregroundColor(.white)

                Spacer()

                Button {
                    // Switch to visibility tab
                    // This would need to be wired up through the parent
                } label: {
                    Text("Decide")
                        .font(.caption.bold())
                        .foregroundColor(.white)
                        .padding(.horizontal, 12)
                        .padding(.vertical, 6)
                        .background(Color("Accent"))
                        .cornerRadius(6)
                }
            }
            .padding()
            .background(Color("Surface2"))
            .cornerRadius(12)
            .overlay(
                RoundedRectangle(cornerRadius: 12)
                    .stroke(Color("Accent"), lineWidth: 1)
            )
            .padding(.horizontal)
            .padding(.vertical, 8)
            .task {
                await viewModel.loadPending()
            }
        }
    }
}

@MainActor
class PendingViewModel: ObservableObject {
    @Published var pendingCount = 0

    private let api = APIService.shared

    func loadPending() async {
        do {
            let pending = try await api.getPendingVisibility()
            pendingCount = pending.pending.reduce(0) { $0 + $1.groups.count }
        } catch {
            // Silently fail for banner
        }
    }
}

#Preview {
    PendingVisibilityBanner()
}
