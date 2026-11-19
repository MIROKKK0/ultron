import Foundation

extension ChatClient {
    func fetchMemoryGraph(serverURL: String, limit: Int = 300) async throws -> MemoryGraphResponse {
        let bounded = min(max(limit, 1), 500)
        let data = try await authenticatedData(path: "/v2/memory/graph?limit=\(bounded)", method: "GET", serverURL: serverURL)
        return try JSONDecoder().decode(MemoryGraphResponse.self, from: data)
    }

    func fetchMemoryInsights(serverURL: String) async throws -> MemoryInsightsResponse {
        let data = try await authenticatedData(path: "/v2/memory/insights", method: "GET", serverURL: serverURL)
        return try JSONDecoder().decode(MemoryInsightsResponse.self, from: data)
    }
}

struct MemoryGraphResponse: Decodable {
    let nodes: [MemoryGraphNode]
    let edges: [[Int]]
    let edge_details: [MemoryGraphEdge]
    let truncated: Bool?
}

struct MemoryGraphNode: Decodable, Identifiable {
    let id: Int
    let title: String
    let category: String
    let region: String
    let content: String
    let source: String
    let confidence: Double
    let updated: String
    let modified: String
    let last_accessed_at: String
    let access_count: Int
    let position: [Double]
    let degree: Int
}

struct MemoryGraphEdge: Decodable, Identifiable {
    var id: String { "\(source_id)-\(target_id)-\(relation)" }
    let source_id: Int
    let target_id: Int
    let relation: String
}

struct MemoryInsightsResponse: Decodable {
    let analyzed_memories: Int
    let summary: String
    let counts_by_kind: [String: Int]
    let duplicate_candidates: [DuplicateMemoryCandidate]
    let knowledge_gaps: [MemoryKnowledgeGap]
    let low_confidence_memories: [LowConfidenceMemory]
    let specialist_cycle: [MemorySpecialistActivity]
    let analysis_limits: [String]
    let writes_performed: Int
}

struct DuplicateMemoryCandidate: Decodable, Identifiable {
    var id: String { memory_ids.map(String.init).joined(separator: "-") }
    let memory_ids: [Int]
    let similarity: Double
    let method: String
    let status: String
}

struct MemoryKnowledgeGap: Decodable, Identifiable {
    var id: String { "\(type)-\(kind ?? "all")" }
    let type: String
    let kind: String?
    let evidence: String?
    let memory_ids: [Int]?
}

struct LowConfidenceMemory: Decodable, Identifiable {
    var id: Int { memory_id }
    let memory_id: Int
    let confidence: Double
}

struct MemorySpecialistActivity: Decodable, Identifiable {
    var id: String { role }
    let role: String
    let status: String
    let task: String
}

extension ChatClient {
    func fetchMemoryGraph(serverURL: String, limit: Int = 300) async throws -> MemoryGraphResponse {
        let bounded = min(max(limit, 1), 500)
        let data = try await authenticatedData(
            path: "/v2/memory/graph?limit=\(bounded)",
            method: "GET",
            serverURL: serverURL
        )
        return try JSONDecoder().decode(MemoryGraphResponse.self, from: data)
    }

    func fetchMemoryInsights(serverURL: String) async throws -> MemoryInsightsResponse {
        let data = try await authenticatedData(
            path: "/v2/memory/insights",
            method: "GET",
            serverURL: serverURL
        )
        return try JSONDecoder().decode(MemoryInsightsResponse.self, from: data)
    }
}
