import SwiftUI

struct TasksStreamView: View {
    // Mock task data structure for scaffold
    struct DemoTask: Identifiable {
        let id = UUID()
        let title: String
        let pressureLevel: Int // 0: Safe(White/Gray), 1: <6h(Yellow), 2: <2h(Orange), 3: Overdue(Red)
        var isDone: Bool = false
    }
    
    @State private var tasks: [DemoTask] = [
        DemoTask(title: "Read research paper (1 hr)", pressureLevel: 3),
        DemoTask(title: "Gym workflow", pressureLevel: 2),
        DemoTask(title: "Update iOS roadmap", pressureLevel: 1),
        DemoTask(title: "Evening stretch", pressureLevel: 0)
    ]
    
    var body: some View {
        NavigationView {
            List {
                ForEach(tasks.filter { !$0.isDone }) { task in
                    TaskCardRow(task: task)
                        // Slide to complete action
                        .swipeActions(edge: .trailing, allowsFullSwipe: true) {
                            Button {
                                withAnimation {
                                    completeTask(task)
                                }
                            } label: {
                                Label("Complete", systemImage: "checkmark.circle.fill")
                            }
                            .tint(.green)
                        }
                }
            }
            .listStyle(.inset)
            .navigationTitle("Today's Rules")
        }
    }
    
    private func completeTask(_ task: DemoTask) {
        if let index = tasks.firstIndex(where: { $0.id == task.id }) {
            tasks[index].isDone = true
            // TODO: Trigger API to backend or show evidence sheet
        }
    }
}

// Minimal Card with left-edge pressure indicator
struct TaskCardRow: View {
    let task: TasksStreamView.DemoTask
    
    var pressureColor: Color {
        switch task.pressureLevel {
        case 3: return .red
        case 2: return .orange
        case 1: return .yellow
        default: return .gray // Safe
        }
    }
    
    var body: some View {
        HStack {
            // Pressure Bar
            Rectangle()
                .fill(pressureColor)
                .frame(width: 4)
                .cornerRadius(2)
            
            VStack(alignment: .leading, spacing: 4) {
                Text(task.title)
                    .font(.headline)
                    .foregroundColor(.primary)
                
                Text(task.pressureLevel == 3 ? "OVERDUE" : "Active")
                    .font(.caption)
                    .foregroundColor(.secondary)
            }
            .padding(.vertical, 8)
            .padding(.leading, 8)
            
            Spacer()
            
            Image(systemName: "chevron.right")
                .foregroundColor(.gray)
                .font(.footnote)
        }
        .padding(.vertical, 4)
    }
}
