import LiveKit
import SwiftUI
import Clerk

@main
struct VoiceAgentApp: App {
    // Create the root view model
    private let viewModel = AppViewModel()
    @State private var clerk = Clerk.shared
    
    var body: some Scene {
        WindowGroup {
            AppView()
                .environment(viewModel)
                .environment(\.clerk, clerk)
                .task {
                    // Use environment variable for Clerk publishable key
                    let publishableKey = Bundle.main.object(forInfoDictionaryKey: "ClerkPublishableKey") as? String
                        ?? "pk_test_c3RlYWR5LXRhcGlyLTMwLmNsZXJrLmFjY291bnRzLmRldiQ"
                    clerk.configure(publishableKey: publishableKey)
                    try? await clerk.load()
                  }
        }
        #if os(visionOS)
        .windowStyle(.plain)
        .windowResizability(.contentMinSize)
        .defaultSize(width: 1500, height: 500)
        #endif
    }
}

/// A set of flags that define the features supported by the agent.
/// Enable them based on your agent capabilities.
struct AgentFeatures: OptionSet {
    let rawValue: Int

    static let voice = Self(rawValue: 1 << 0)
    static let text = Self(rawValue: 1 << 1)
    static let video = Self(rawValue: 1 << 2)

    static let current: Self = [.voice, .text]
}
