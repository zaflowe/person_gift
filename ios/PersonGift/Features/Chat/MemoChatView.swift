import SwiftUI

struct MemoChatView: View {
    @State private var inputText: String = ""
    @State private var memos: [String] = [] // Will be Model objects
    
    var body: some View {
        NavigationView {
            VStack {
                ScrollView {
                    LazyVStack(alignment: .leading, spacing: 12) {
                        ForEach(memos, id: \.self) { memo in
                            HStack {
                                Text(memo)
                                    .padding()
                                    .background(Color(.systemGray6))
                                    .cornerRadius(12)
                                Spacer()
                            }
                            .padding(.horizontal)
                        }
                    }
                }
                
                // Bottom Input Area
                HStack {
                    Button(action: {
                        // Open Camera/Photo picker action
                    }) {
                        Image(systemName: "camera.circle.fill")
                            .font(.system(size: 32))
                            .foregroundColor(.gray)
                    }
                    
                    TextField("Jot down a thought or task...", text: $inputText)
                        .padding(10)
                        .background(Color(.systemGray6))
                        .cornerRadius(20)
                        
                    Button(action: {
                        if !inputText.isEmpty {
                            memos.append(inputText)
                            // TODO: Send to AI / backend
                            inputText = ""
                        }
                    }) {
                        Image(systemName: "arrow.up.circle.fill")
                            .font(.system(size: 32))
                            .foregroundColor(inputText.isEmpty ? .gray : .blue)
                    }
                    .disabled(inputText.isEmpty)
                }
                .padding()
            }
            .navigationTitle("Memo")
        }
    }
}
