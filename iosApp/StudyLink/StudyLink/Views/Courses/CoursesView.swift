//
//  CoursesView.swift
//  StudyLink
//
//  Courses management view
//

import SwiftUI

struct CoursesView: View {
    @StateObject private var viewModel = CoursesViewModel()

    var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            // Header
            VStack(alignment: .leading, spacing: 8) {
                Text("Your Courses")
                    .font(.title3.bold())
                    .foregroundColor(.white)

                Text("Toggle courses on or off site-wide. Hidden courses stop syncing and won't appear in any group.")
                    .font(.caption)
                    .foregroundColor(Color("Text2"))
            }
            .padding()

            // Courses List
            ScrollView {
                LazyVStack(spacing: 0) {
                    if viewModel.isLoading {
                        ProgressView()
                            .frame(maxWidth: .infinity)
                            .padding(.top, 40)
                    } else if viewModel.courses.isEmpty {
                        Text("No courses synced yet. Use the browser extension to sync your Canvas assignments.")
                            .font(.body)
                            .foregroundColor(Color("Text2"))
                            .frame(maxWidth: .infinity)
                            .padding(.vertical, 40)
                    } else {
                        ForEach(viewModel.courses) { course in
                            CourseRow(course: course, viewModel: viewModel)
                        }
                    }
                }
                .padding(.horizontal)
            }
        }
        .task {
            await viewModel.loadCourses()
        }
    }
}

struct CourseRow: View {
    let course: Course
    let viewModel: CoursesViewModel

    var body: some View {
        HStack(spacing: 12) {
            VStack(alignment: .leading, spacing: 4) {
                Text(course.name)
                    .font(.body)
                    .foregroundColor(.white)
                    .lineLimit(1)

                if let code = course.courseCode {
                    Text(code)
                        .font(.caption)
                        .foregroundColor(Color("Text2"))
                        .lineLimit(1)
                }
            }
            .frame(maxWidth: .infinity, alignment: .leading)

            Toggle("", isOn: Binding(
                get: { !(course.hidden ?? false) },
                set: { _ in
                    Task {
                        await viewModel.toggleCourse(courseId: course.id)
                    }
                }
            ))
            .labelsHidden()
            .toggleStyle(SwitchToggleStyle(tint: Color("Accent")))
        }
        .padding(.vertical, 10)
        .padding(.horizontal, 12)
        .overlay(
            Rectangle()
                .frame(height: 1)
                .foregroundColor(Color("Border")),
            alignment: .bottom
        )
    }
}

@MainActor
class CoursesViewModel: ObservableObject {
    @Published var courses: [Course] = []
    @Published var isLoading = false
    @Published var errorMessage: String?

    private let api = APIService.shared

    func loadCourses() async {
        isLoading = true

        do {
            courses = try await api.getUserCourses()
        } catch {
            errorMessage = error.localizedDescription
        }

        isLoading = false
    }

    func toggleCourse(courseId: String) async {
        do {
            try await api.toggleCourseHidden(courseId: courseId)
            // Update local state
            if let index = courses.firstIndex(where: { $0.id == courseId }) {
                courses[index].hidden?.toggle()
            }
        } catch {
            errorMessage = error.localizedDescription
        }
    }
}

#Preview {
    CoursesView()
}
