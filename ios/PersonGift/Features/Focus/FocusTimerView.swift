import SwiftUI

struct FocusTimerView: View {
    @State private var isRunning = false
    @State private var timeElapsed: Int = 0 // in seconds
    
    // Timer publisher
    let timer = Timer.publish(every: 1, on: .main, in: .common).autoconnect()
    
    var body: some View {
        NavigationView {
            VStack(spacing: 0) {
                
                // Top Header Card
                HStack {
                    ZStack {
                        Circle()
                            .fill(Color.blue.opacity(0.1))
                            .frame(width: 48, height: 48)
                        Image(systemName: "clock")
                            .foregroundColor(.blue)
                            .font(.system(size: 24))
                    }
                    
                    VStack(alignment: .leading, spacing: 4) {
                        Text("专注学习")
                            .font(.subheadline)
                            .foregroundColor(.secondary)
                        Text("\(timeElapsed)s")
                            .font(.system(size: 28, weight: .bold))
                            .foregroundColor(.primary)
                    }
                    
                    Spacer()
                    
                    // Toggle switch placeholder
                    HStack(spacing: 0) {
                        Text("本周")
                            .font(.footnote)
                            .padding(.horizontal, 12)
                            .padding(.vertical, 6)
                            .background(Color(.systemBackground))
                            .cornerRadius(16)
                            .shadow(color: Color.black.opacity(0.05), radius: 2, y: 1)
                        
                        Text("统计")
                            .font(.footnote)
                            .padding(.horizontal, 12)
                            .padding(.vertical, 6)
                            .foregroundColor(.secondary)
                    }
                    .background(Color(.systemGray6))
                    .cornerRadius(18)
                }
                .padding()
                .background(Color(.secondarySystemGroupedBackground))
                
                Divider()
                
                Spacer()
                
                // Main Play/Pause Area
                VStack(spacing: 24) {
                    
                    Button(action: {
                        isRunning.toggle()
                    }) {
                        ZStack {
                            Circle()
                                .fill(Color(.systemGray6))
                                .frame(width: 100, height: 100)
                            
                            Image(systemName: isRunning ? "pause.fill" : "play.fill")
                                .font(.system(size: 40))
                                .foregroundColor(isRunning ? .red : .blue)
                                .offset(x: isRunning ? 0 : 4) // visual alignment for play button
                        }
                    }
                    
                    VStack(spacing: 8) {
                        Text("本周还没开始专注")
                            .font(.headline)
                        Text("积跬步以至千里")
                            .font(.subheadline)
                            .foregroundColor(.secondary)
                    }
                    
                    Button(action: {
                        isRunning.toggle()
                    }) {
                        Text(isRunning ? "暂停专注" : "开始专注")
                            .font(.headline)
                            .foregroundColor(.white)
                            .frame(width: 160, height: 50)
                            .background(isRunning ? Color.red : Color.blue)
                            .cornerRadius(25)
                    }
                }
                
                Spacer()
                Spacer()
            }
            .navigationTitle("Focus")
            .navigationBarHidden(true)
            .background(Color(.systemGroupedBackground).edgesIgnoringSafeArea(.all))
            .onReceive(timer) { _ in
                if isRunning {
                    timeElapsed += 1
                }
            }
        }
    }
}
