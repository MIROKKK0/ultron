import Foundation
import CryptoKit

struct OfflineMemoryEntry: Codable, Identifiable {
    let id: UUID
    let kind: String
    let content: String
    let source: String
    let confidence: Double
    let queuedAt: Date

    init(kind: String, content: String, source: String, confidence: Double) {
        self.id = UUID()
        self.kind = kind
        self.content = content
        self.source = source
        self.confidence = confidence
        self.queuedAt = Date()
    }
}

/// Installation-local queue. Payloads are encrypted at rest with a key derived
/// from the installation credential stored in the iOS Keychain.
actor OfflineMemoryQueue {
    static let shared = OfflineMemoryQueue()
    private let filename = "ultron-memory-queue.enc"

    private func fileURL() throws -> URL {
        guard let root = FileManager.default.urls(for: .applicationSupportDirectory,
                                                   in: .userDomainMask).first else {
            throw CocoaError(.fileNoSuchFile)
        }
        let directory = root.appendingPathComponent("ULTRON", isDirectory: true)
        try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
        return directory.appendingPathComponent(filename)
    }

    private func encryptionKey() throws -> SymmetricKey {
        let credentials = try InstallationCredentialStore.loadOrCreate()
        let digest = SHA256.hash(data: Data(credentials.token.utf8))
        return SymmetricKey(data: Data(digest))
    }

    private func readEntries() throws -> [OfflineMemoryEntry] {
        let url = try fileURL()
        guard FileManager.default.fileExists(atPath: url.path) else { return [] }
        let sealedData = try Data(contentsOf: url)
        let box = try AES.GCM.SealedBox(combined: sealedData)
        let plaintext = try AES.GCM.open(box, using: encryptionKey())
        return try JSONDecoder().decode([OfflineMemoryEntry].self, from: plaintext)
    }

    private func writeEntries(_ entries: [OfflineMemoryEntry]) throws {
        let plaintext = try JSONEncoder().encode(entries)
        let box = try AES.GCM.seal(plaintext, using: encryptionKey())
        guard let combined = box.combined else { throw CocoaError(.fileWriteUnknown) }
        try combined.write(to: fileURL(), options: [.atomic, .completeFileProtection])
    }

    func enqueue(kind: String, content: String, source: String = "offline_user_explicit",
                 confidence: Double = 1.0) throws -> UUID {
        let normalized = content.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !normalized.isEmpty, normalized.count <= 4000 else {
            throw CocoaError(.validationMissingMandatoryProperty)
        }
        var entries = try readEntries()
        let entry = OfflineMemoryEntry(kind: kind, content: normalized,
                                       source: source, confidence: confidence)
        entries.append(entry)
        try writeEntries(entries)
        return entry.id
    }

    func pending() throws -> [OfflineMemoryEntry] {
        try readEntries()
    }

    func remove(_ ids: Set<UUID>) throws {
        let remaining = try readEntries().filter { !ids.contains($0.id) }
        try writeEntries(remaining)
    }

    func count() throws -> Int {
        try readEntries().count
    }
}
