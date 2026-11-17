import Foundation
import Security

enum InstallationCredentialError: LocalizedError {
    case keychain(OSStatus)
    case missingToken
    case invalidResponse
    case serverError(Int)

    var errorDescription: String? {
        switch self {
        case .keychain(let status):
            return "Não foi possível guardar a credencial segura (Keychain: \(status))."
        case .missingToken:
            return "A credencial privada desta instalação não está disponível."
        case .invalidResponse:
            return "O servidor enviou uma resposta inválida para a memória."
        case .serverError(let status):
            return "O servidor de memória respondeu com erro (\(status))."
        }
    }
}

/// Stores only this installation's random credential in the iOS Keychain.
/// The shared server administration token is never embedded in the app.
enum InstallationCredentialStore {
    private static let service = "app.ultron.assistant.installation"
    private static let account = "private-memory-token"

    static func read() throws -> String? {
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
        guard status == errSecSuccess, let data = result as? Data,
              let token = String(data: data, encoding: .utf8) else {
            throw InstallationCredentialError.keychain(status)
        }
        return token
    }

    static func save(_ token: String) throws {
        let data = Data(token.utf8)
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
                throw InstallationCredentialError.keychain(addStatus)
            }
        } else if status != errSecSuccess {
            throw InstallationCredentialError.keychain(status)
        }
    }

    static func delete() throws {
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: account
        ]
        let status = SecItemDelete(query as CFDictionary)
        guard status == errSecSuccess || status == errSecItemNotFound else {
            throw InstallationCredentialError.keychain(status)
        }
    }
}
