//
//  Helpers.swift
//  StudyLink
//
//  Utility functions and extensions
//

import Foundation
import SwiftUI

// MARK: - Time Formatting

func timeAgo(_ date: Date?) -> String {
    guard let date = date else { return "never" }

    let diff = Date().timeIntervalSince(date)
    let mins = Int(diff / 60)

    if mins < 1 { return "just now" }
    if mins < 60 { return "\(mins)m ago" }

    let hrs = mins / 60
    if hrs < 24 { return "\(hrs)h ago" }

    let days = hrs / 24
    return "\(days)d ago"
}

func formatDue(_ date: Date) -> String {
    let formatter = DateFormatter()
    formatter.dateFormat = "MMM d, h:mm a"
    return formatter.string(from: date)
}

// MARK: - Extensions

extension Color {
    init(hex: String) {
        let hex = hex.trimmingCharacters(in: CharacterSet.alphanumerics.inverted)
        var int: UInt64 = 0
        Scanner(string: hex).scanHexInt64(&int)
        let a, r, g, b: UInt64
        switch hex.count {
        case 3: // RGB (12-bit)
            (a, r, g, b) = (255, (int >> 8) * 17, (int >> 4 & 0xF) * 17, (int & 0xF) * 17)
        case 6: // RGB (24-bit)
            (a, r, g, b) = (255, int >> 16, int >> 8 & 0xFF, int & 0xFF)
        case 8: // ARGB (32-bit)
            (a, r, g, b) = (int >> 24, int >> 16 & 0xFF, int >> 8 & 0xFF, int & 0xFF)
        default:
            (a, r, g, b) = (1, 1, 1, 0)
        }

        self.init(
            .sRGB,
            red: Double(r) / 255,
            green: Double(g) / 255,
            blue:  Double(b) / 255,
            opacity: Double(a) / 255
        )
    }
}
