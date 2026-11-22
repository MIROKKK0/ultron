import Foundation
import Security

struct InstallationCredentials: Codable {
    let id: String
    let token: String
    var registered: Bool
}

enum InstallationCredentialStore {
    private static let service = "app.ultron.assistant.installation"
    private static let account = "installation-credentials"

    static func loadOrCreate() throws -> InstallationCredentials {
        if let stored = try read() { return stored }
        let credentials = InstallationCredentials(
            id: UUID().uuidString.lowercased(),
            token: UUID().uuidString.replacingOccurrences(of: "-", with: "") +
                   UUID().uuidString.replacingOccurrences(of: "-", with: ""),
            registered: false
        )
        try save(credentials)
        return credentials
    }

    static func read() throws -> InstallationCredentials? {
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: account,
            kSecReturnData as String: true,
            kSecMatchLimit as String: kSecMatchLimitOne
        ]
        var result: CFTypeRef?
        let status = SecItemCopyMatching(query as CFDictionary, &result)
        if status == errSecItemNotFound { return nil }
        guard status == errSecSuccess,
              let data = result as? Data,
              let credentials = try? JSONDecoder().decode(InstallationCredentials.self, from: data) else {
            throw NSError(domain: NSOSStatusErrorDomain, code: Int(status))
        }
        return credentials
    }

    static func save(_ credentials: InstallationCredentials) throws {
        let data = try JSONEncoder().encode(credentials)
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: account
        ]
        let attributes: [String: Any] = [
            kSecValueData as String: data,
            kSecAttrAccessible as String: kSecAttrAccessibleAfterFirstUnlockThisDeviceOnly
        ]
        let status = SecItemUpdate(query as CFDictionary, attributes as CFDictionary)
        if status == errSecItemNotFound {
            var insertion = query
            attributes.forEach { insertion[$0.key] = $0.value }
            let addStatus = SecItemAdd(insertion as CFDictionary, nil)
            guard addStatus == errSecSuccess else {
                throw NSError(domain: NSOSStatusErrorDomain, code: Int(addStatus))
            }
        } else if status != errSecSuccess {
            throw NSError(domain: NSOSStatusErrorDomain, code: Int(status))
        }
    }

    static func setRegistered(_ registered: Bool) throws {
        var credentials = try loadOrCreate()
        credentials.registered = registered
        try save(credentials)
    }

    static func delete() throws {
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: account
        ]
        let status = SecItemDelete(query as CFDictionary)
        guard status == errSecSuccess || status == errSecItemNotFound else {
            throw NSError(domain: NSOSStatusErrorDomain, code: Int(status))
        }
    }
}
