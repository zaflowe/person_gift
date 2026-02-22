import SwiftUI

@main
struct PersonGiftApp: App {
    var body: some Scene {
        WindowGroup {
            ContentView()
        }
    }
}

struct ContentView: View {
    @State private var selection = 0
    
    var body: some Scene {
        TabView(selection: $selection) {
            MemoChatView()
                .tabItem {
                    Image(systemName: "note.text")
                    Text("Memo")
                }
                .tag(0)
            
            TasksStreamView()
                .tabItem {
                    Image(systemName: "checklist")
                    Text("Tasks")
                }
                .tag(1)
                
            FocusTimerView()
                .tabItem {
                    Image(systemName: "clock")
                    Text("Focus")
                }
                .tag(2)
        }
        .preferredColorScheme(.dark)
        .tint(.white)
    }
}
