import Foundation
import Clerk

/// A service for fetching LiveKit authentication tokens from your backend
actor TokenService {
    struct ConnectionDetails: Codable {
        let serverUrl: String
        let roomName: String
        let participantName: String
        let participantToken: String
    }

    // Backend response structure
    private struct BackendResponse: Codable {
        let session_id: String
        let room_name: String
        let livekit_token: String
        let livekit_url: String
        let agent_type: String
        let user_id: String
    }

    enum TokenServiceError: LocalizedError {
        case authenticationFailed
        case backendError(String)
        case invalidResponse

        var errorDescription: String? {
            switch self {
            case .authenticationFailed:
                return "Failed to authenticate with Clerk"
            case .backendError(let message):
                return "Backend error: \(message)"
            case .invalidResponse:
                return "Invalid response from backend"
            }
        }
    }

    private let apiBaseUrl: String = {
        // Try to get from Info.plist first, fallback to config
        if let url = Bundle.main.object(forInfoDictionaryKey: "ApiBaseUrl") as? String {
            let cleanUrl = url.trimmingCharacters(in: CharacterSet(charactersIn: "\""))
            print("[TokenService] 🔧 Using API base URL from Info.plist: \(cleanUrl)")
            return cleanUrl
        }
        let fallbackUrl = "https://d95f3ba12854.ngrok-free.app/"
        print("[TokenService] 🔧 Using fallback API base URL: \(fallbackUrl)")
        return fallbackUrl
    }()

    func fetchConnectionDetails(roomName: String, participantName: String) async throws -> ConnectionDetails {
        // Get Clerk session token
        print("[TokenService] 🔐 Getting Clerk session token...")
        guard let clerkToken = await getClerkSessionToken() else {
            print("[TokenService] ❌ Failed to get Clerk token")
            throw TokenServiceError.authenticationFailed
        }

        print("[TokenService] ✅ Got Clerk token (length: \(clerkToken.count)), calling backend...")

        // Call backend API
        let backendDetails = try await fetchConnectionDetailsFromBackend(
            clerkToken: clerkToken
        )

        print("[TokenService] ✅ Got connection details from backend")
        return backendDetails
    }

    private func getClerkSessionToken() async -> String? {
        do {
            // Get the current session
            guard let session = await Clerk.shared.session else {
                print("[TokenService] ❌ No active Clerk session")
                return nil
            }

            // Clerk iOS SDK returns a TokenResource, we need to get the token string from it
            let tokenResource = try await session.getToken()

            // Extract the JWT token string from the TokenResource
            if let tokenString = tokenResource?.jwt {
                print("[TokenService] ✅ Got Clerk JWT token")
                return tokenString
            }

            // If jwt property doesn't exist, try other common properties
            if let tokenString = (tokenResource as AnyObject).value(forKey: "token") as? String {
                print("[TokenService] ✅ Got Clerk JWT token")
                return tokenString
            }

            print("[TokenService] ❌ Could not extract token string from TokenResource")
            return nil

        } catch {
            print("[TokenService] ❌ Failed to get Clerk token: \(error)")

            // Fallback: If getToken() doesn't work, try alternative methods
            // Uncomment the appropriate line based on your Clerk SDK version:

            // Alternative 1: If your SDK uses a different method
            // return try await Clerk.shared.getToken()

            // Alternative 2: If token is a property
            // if let session = await Clerk.shared.session,
            //    let token = (session as AnyObject).value(forKey: "token") as? String {
            //     return token
            // }

            print("[TokenService] 💡 If getToken() fails, check your Clerk iOS SDK documentation")
            print("[TokenService] 💡 Common alternatives: Clerk.shared.getToken(), session.token property")

            return nil
        }
    }

    private func fetchConnectionDetailsFromBackend(clerkToken: String) async throws -> ConnectionDetails {
        // Ensure we don't create double slashes
        let cleanBaseUrl = apiBaseUrl.hasSuffix("/") ? String(apiBaseUrl.dropLast()) : apiBaseUrl
        let url = URL(string: "\(cleanBaseUrl)/agent/session/create")!

        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.addValue("application/json", forHTTPHeaderField: "Content-Type")
        request.addValue("Bearer \(clerkToken)", forHTTPHeaderField: "Authorization")

        // iOS-specific session request
        let body: [String: Any] = [
            "agent_type": "main_zeno",
            "session_type": "ios",  // Use "ios" for iOS app
            "initial_context": [:]
        ]

        request.httpBody = try JSONSerialization.data(withJSONObject: body)

        print("[TokenService] 📡 Calling \(url.absoluteString)")
        print("[TokenService] 📡 Full URL: \(url)")
        print("[TokenService] 📡 Request headers: \(request.allHTTPHeaderFields ?? [:])")

        let (data, response) = try await URLSession.shared.data(for: request)

        print("[TokenService] 📡 Response status: \((response as? HTTPURLResponse)?.statusCode ?? -1)")
        if let responseString = String(data: data, encoding: .utf8) {
            print("[TokenService] 📡 Response body: \(responseString)")
        }

        guard let httpResponse = response as? HTTPURLResponse else {
            throw TokenServiceError.backendError("Invalid response")
        }

        guard (200...299).contains(httpResponse.statusCode) else {
            let errorMessage = String(data: data, encoding: .utf8) ?? "Unknown error"
            print("[TokenService] ❌ Backend error (\(httpResponse.statusCode)): \(errorMessage)")
            throw TokenServiceError.backendError("HTTP \(httpResponse.statusCode): \(errorMessage)")
        }

        let backendResponse = try JSONDecoder().decode(BackendResponse.self, from: data)

        return ConnectionDetails(
            serverUrl: backendResponse.livekit_url,
            roomName: backendResponse.room_name,
            participantName: "user", // Backend handles participant naming
            participantToken: backendResponse.livekit_token
        )
    }
}
