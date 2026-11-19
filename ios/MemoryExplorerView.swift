import SwiftUI
import SceneKit
import UIKit

struct MemoryExplorerView: View {
    let serverURL: String
    private let client = ChatClient()

    @State private var graph: MemoryGraphResponse?
    @State private var insights: MemoryInsightsResponse?
    @State private var selectedID: Int?
    @State private var searchText = ""
    @State private var selectedKind = "all"
    @State private var isLoading = false
    @State private var errorMessage: String?

    private let kinds = ["all", "episodic", "semantic", "procedural"]

    private var visibleNodes: [MemoryGraphNode] {
        guard let nodes = graph?.nodes else { return [] }
        return nodes.filter { node in
            let kindMatches = selectedKind == "all" || node.category == selectedKind
            let query = searchText.trimmingCharacters(in: .whitespacesAndNewlines)
            let textMatches = query.isEmpty ||
                node.title.localizedCaseInsensitiveContains(query) ||
                node.content.localizedCaseInsensitiveContains(query) ||
                node.source.localizedCaseInsensitiveContains(query)
            return kindMatches && textMatches
        }
    }

    private var selectedNode: MemoryGraphNode? {
        graph?.nodes.first { $0.id == selectedID }
    }

    private var selectedEdges: [MemoryGraphEdge] {
        guard let selectedID else { return [] }
        return graph?.edge_details.filter {
            $0.source_id == selectedID || $0.target_id == selectedID
        } ?? []
    }

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 16) {
                header
                searchAndFilters
                if let errorMessage {
                    Label(errorMessage, systemImage: "exclamationmark.triangle.fill")
                        .font(.footnote)
                        .foregroundStyle(.orange)
                        .padding(12)
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .background(.orange.opacity(0.10), in: RoundedRectangle(cornerRadius: 12))
                }
                graphPanel
                if let selectedNode { selectedMemoryPanel(selectedNode) }
                if let insights { diagnosticsPanel(insights) }
                if isLoading && graph == nil {
                    ProgressView("Carregando memória privada…")
                        .frame(maxWidth: .infinity)
                        .padding(30)
                }
                if graph?.truncated == true {
                    Text("Exibindo até 300 registros. O conjunto completo pode conter mais memórias.")
                        .font(.caption2)
                        .foregroundStyle(.secondary)
                }
            }
            .padding()
        }
        .background(Color(red: 0.025, green: 0.04, blue: 0.075).ignoresSafeArea())
        .navigationTitle("Universo neural")
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
            ToolbarItem(placement: .topBarTrailing) {
                Button { Task { await reload() } } label: {
                    Image(systemName: "arrow.clockwise")
                }
                .disabled(isLoading)
                .accessibilityLabel("Atualizar universo neural")
            }
        }
        .task { await reload() }
    }

    private var header: some View {
        VStack(alignment: .leading, spacing: 6) {
            HStack(spacing: 8) {
                Image(systemName: "brain.head.profile")
                    .foregroundStyle(.cyan)
                Text("ULTRON / MEMÓRIA")
                    .font(.caption.weight(.bold))
                    .tracking(1.5)
                    .foregroundStyle(.cyan)
                Spacer()
                Text("SOMENTE LEITURA")
                    .font(.system(size: 9, weight: .bold, design: .monospaced))
                    .foregroundStyle(.green)
                    .padding(.horizontal, 8)
                    .padding(.vertical, 5)
                    .background(.green.opacity(0.12), in: Capsule())
            }
            Text("Explore o que o ULTRON lembra.")
                .font(.title2.weight(.bold))
                .foregroundStyle(.white)
            Text("Cada esfera é uma memória real. As linhas representam relações de origem registradas.")
                .font(.subheadline)
                .foregroundStyle(.white.opacity(0.65))
        }
    }

    private var searchAndFilters: some View {
        VStack(spacing: 10) {
            HStack(spacing: 8) {
                Image(systemName: "magnifyingglass").foregroundStyle(.secondary)
                TextField("Buscar conteúdo, origem ou título", text: $searchText)
                    .font(.subheadline)
                    .foregroundStyle(.white)
                    .textInputAutocapitalization(.never)
                    .autocorrectionDisabled()
            }
            .padding(12)
            .background(Color.white.opacity(0.08), in: RoundedRectangle(cornerRadius: 12))

            Picker("Tipo de memória", selection: $selectedKind) {
                Text("Todas").tag("all")
                Text("Episódicas").tag("episodic")
                Text("Semânticas").tag("semantic")
                Text("Procedurais").tag("procedural")
            }
            .pickerStyle(.segmented)
            .tint(.cyan)
        }
    }

    private var graphPanel: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack {
                Text("MAPA 3D")
                    .font(.caption.weight(.bold))
                    .tracking(1.2)
                    .foregroundStyle(.white.opacity(0.8))
                Spacer()
                Text("\(visibleNodes.count) nós")
                    .font(.caption.monospacedDigit())
                    .foregroundStyle(.cyan)
            }
            MemorySceneView(
                nodes: visibleNodes,
                edges: graph?.edge_details ?? [],
                selectedID: selectedID
            ) { id in
                selectedID = id
            }
            .frame(height: 330)
            .clipShape(RoundedRectangle(cornerRadius: 18))
            .overlay(RoundedRectangle(cornerRadius: 18).stroke(.cyan.opacity(0.25), lineWidth: 1))
            HStack(spacing: 14) {
                legendDot(.cyan, "Semântica")
                legendDot(.purple, "Episódica")
                legendDot(.orange, "Procedural")
                Spacer(minLength: 0)
            }
            .font(.caption2)
            .foregroundStyle(.white.opacity(0.7))
            Text("Arraste para girar · pinça para aproximar · toque em um nó para investigar")
                .font(.caption2)
                .foregroundStyle(.white.opacity(0.5))
        }
        .padding(12)
        .background(Color.white.opacity(0.045), in: RoundedRectangle(cornerRadius: 18))
    }

    private func legendDot(_ color: Color, _ title: String) -> some View {
        HStack(spacing: 5) {
            Circle().fill(color).frame(width: 7, height: 7)
            Text(title)
        }
    }

    private func selectedMemoryPanel(_ node: MemoryGraphNode) -> some View {
        VStack(alignment: .leading, spacing: 10) {
            sectionTitle("LEMBRANÇA SELECIONADA", symbol: "point.3.connected.trianglepath.dotted")
            Text(node.title)
                .font(.headline)
                .foregroundStyle(.white)
            Text(node.content)
                .font(.subheadline)
                .foregroundStyle(.white.opacity(0.78))
                .textSelection(.enabled)
            Divider().overlay(.white.opacity(0.12))
            metadataRow("Tipo", value: node.category)
            metadataRow("Origem", value: node.source)
            metadataRow("Criada", value: node.modified)
            metadataRow("Último acesso", value: node.last_accessed_at)
            metadataRow("Confiança", value: node.confidence.formatted(.percent.precision(.fractionLength(0))))
            metadataRow("Acessos", value: "\(node.access_count)")
            metadataRow("Conexões explícitas", value: "\(selectedEdges.count)")
            if !selectedEdges.isEmpty {
                Text("NAVEGAR PELAS RELAÇÕES")
                    .font(.caption.weight(.bold))
                    .tracking(1)
                    .foregroundStyle(.cyan)
                    .padding(.top, 4)
                ForEach(selectedEdges) { edge in
                    let neighborID = edge.source_id == node.id ? edge.target_id : edge.source_id
                    let neighbor = graph?.nodes.first { $0.id == neighborID }
                    Button {
                        selectedID = neighborID
                    } label: {
                        HStack {
                            Image(systemName: "arrow.triangle.branch")
                            VStack(alignment: .leading, spacing: 2) {
                                Text(neighbor?.title ?? "Memória \(neighborID)")
                                    .lineLimit(2)
                                Text(edge.relation)
                                    .font(.caption2)
                                    .foregroundStyle(.secondary)
                            }
                            Spacer()
                            Image(systemName: "chevron.right").font(.caption)
                        }
                        .foregroundStyle(.white)
                        .padding(10)
                        .background(Color.white.opacity(0.06), in: RoundedRectangle(cornerRadius: 10))
                    }
                    .buttonStyle(.plain)
                }
            } else {
                Text("Nenhuma relação de origem explícita registrada para esta lembrança.")
                    .font(.caption)
                    .foregroundStyle(.white.opacity(0.55))
            }
        }
        .padding(14)
        .background(Color.white.opacity(0.055), in: RoundedRectangle(cornerRadius: 18))
    }

    private func diagnosticsPanel(_ data: MemoryInsightsResponse) -> some View {
        VStack(alignment: .leading, spacing: 12) {
            sectionTitle("DIAGNÓSTICO DO CONHECIMENTO", symbol: "waveform.path.ecg")
            Text(data.summary)
                .font(.subheadline)
                .foregroundStyle(.white.opacity(0.75))
            HStack(spacing: 8) {
                metricCard("Memórias", value: "\(data.analyzed_memories)")
                metricCard("Repetições", value: "\(data.duplicate_candidates.count)")
                metricCard("Lacunas", value: "\(data.knowledge_gaps.count)")
            }
            if !data.duplicate_candidates.isEmpty {
                Text("POSSÍVEIS REPETIÇÕES · REVISÃO NECESSÁRIA")
                    .font(.caption.weight(.bold))
                    .foregroundStyle(.orange)
                ForEach(data.duplicate_candidates) { item in
                    Text("IDs \(item.memory_ids.map(String.init).joined(separator: " ↔ ")) · \(Int(item.similarity * 100))% · \(item.method)")
                        .font(.caption)
                        .foregroundStyle(.white.opacity(0.75))
                }
            }
            if !data.knowledge_gaps.isEmpty {
                Text("SINAIS DE LACUNAS")
                    .font(.caption.weight(.bold))
                    .foregroundStyle(.orange)
                ForEach(data.knowledge_gaps) { gap in
                    VStack(alignment: .leading, spacing: 3) {
                        Text(gap.kind ?? gap.type)
                            .font(.subheadline.weight(.medium))
                            .foregroundStyle(.white)
                        Text(gap.evidence ?? "Sinal para investigação; não é uma conclusão.")
                            .font(.caption)
                            .foregroundStyle(.white.opacity(0.6))
                    }
                }
            }
            Divider().overlay(.white.opacity(0.12))
            sectionTitle("SEIS ESPECIALISTAS", symbol: "person.3.sequence")
            ForEach(data.specialist_cycle) { specialist in
                HStack(alignment: .top, spacing: 9) {
                    Image(systemName: specialist.status == "completed" ? "checkmark.circle.fill" : "circle.dashed")
                        .foregroundStyle(specialist.status == "completed" ? .green : .orange)
                    VStack(alignment: .leading, spacing: 3) {
                        Text(specialist.role.replacingOccurrences(of: "_", with: " ").uppercased())
                            .font(.caption.weight(.bold))
                            .foregroundStyle(.white)
                        Text(specialist.task)
                            .font(.caption)
                            .foregroundStyle(.white.opacity(0.6))
                    }
                    Spacer()
                    Text(specialist.status == "proposal_only" ? "PROPOSTA" : specialist.status.uppercased())
                        .font(.system(size: 9, weight: .bold))
                        .foregroundStyle(.cyan)
                }
            }
            Text("Escritas realizadas: \(data.writes_performed). Repetições e lacunas são hipóteses para revisão, não alterações automáticas.")
                .font(.caption2)
                .foregroundStyle(.green.opacity(0.85))
            ForEach(data.analysis_limits, id: \.self) { limit in
                Text("• \(limit)")
                    .font(.caption2)
                    .foregroundStyle(.white.opacity(0.45))
            }
        }
        .padding(14)
        .background(Color.white.opacity(0.055), in: RoundedRectangle(cornerRadius: 18))
    }

    private func sectionTitle(_ title: String, symbol: String) -> some View {
        Label(title, systemImage: symbol)
            .font(.caption.weight(.bold))
            .tracking(0.9)
            .foregroundStyle(.cyan)
    }

    private func metadataRow(_ title: String, value: String) -> some View {
        HStack(alignment: .top) {
            Text(title).foregroundStyle(.white.opacity(0.5))
            Spacer()
            Text(value.isEmpty ? "Não informado" : value)
                .foregroundStyle(.white.opacity(0.85))
                .multilineTextAlignment(.trailing)
        }
        .font(.caption)
    }

    private func metricCard(_ title: String, value: String) -> some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(value).font(.title3.bold()).foregroundStyle(.white)
            Text(title).font(.caption2).foregroundStyle(.white.opacity(0.55))
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(10)
        .background(Color.white.opacity(0.06), in: RoundedRectangle(cornerRadius: 12))
    }

    @MainActor
    private func reload() async {
        guard !isLoading else { return }
        isLoading = true
        errorMessage = nil
        do {
            async let graphRequest = client.fetchMemoryGraph(serverURL: serverURL)
            async let insightsRequest = client.fetchMemoryInsights(serverURL: serverURL)
            let (newGraph, newInsights) = try await (graphRequest, insightsRequest)
            graph = newGraph
            insights = newInsights
            if let selectedID, !newGraph.nodes.contains(where: { $0.id == selectedID }) {
                self.selectedID = nil
            }
            if self.selectedID == nil { self.selectedID = newGraph.nodes.first?.id }
        } catch {
            errorMessage = error.localizedDescription
        }
        isLoading = false
    }
}

private struct MemorySceneView: UIViewRepresentable {
    let nodes: [MemoryGraphNode]
    let edges: [MemoryGraphEdge]
    let selectedID: Int?
    let onSelect: (Int) -> Void

    func makeCoordinator() -> Coordinator { Coordinator(onSelect: onSelect) }

    func makeUIView(context: Context) -> SCNView {
        let view = SCNView()
        view.backgroundColor = UIColor(red: 0.015, green: 0.025, blue: 0.055, alpha: 1)
        view.allowsCameraControl = true
        view.autoenablesDefaultLighting = true
        view.antialiasingMode = .multisampling4X
        view.scene = SCNScene()
        let tap = UITapGestureRecognizer(target: context.coordinator, action: #selector(Coordinator.handleTap(_:)))
        view.addGestureRecognizer(tap)
        context.coordinator.view = view
        configure(view, coordinator: context.coordinator)
        return view
    }

    func updateUIView(_ view: SCNView, context: Context) {
        context.coordinator.onSelect = onSelect
        let signature = nodes.map { "\($0.id):\($0.position)" }.joined(separator: "|") +
            edges.map { "\($0.source_id)-\($0.target_id)-\($0.relation)" }.joined(separator: "|")
        if signature != context.coordinator.signature {
            context.coordinator.signature = signature
            configure(view, coordinator: context.coordinator)
        }
        context.coordinator.highlight(selectedID)
    }

    private func configure(_ view: SCNView, coordinator: Coordinator) {
        let scene = SCNScene()
        coordinator.nodeByID.removeAll()
        let cameraNode = SCNNode()
        cameraNode.camera = SCNCamera()
        cameraNode.position = SCNVector3(0, 1.5, 15)
        scene.rootNode.addChildNode(cameraNode)
        scene.rootNode.addChildNode(makeLight(position: SCNVector3(0, 8, 12), intensity: 900))
        scene.rootNode.addChildNode(makeLight(position: SCNVector3(-8, -3, 4), intensity: 500))

        for edge in edges {
            guard let source = nodes.first(where: { $0.id == edge.source_id }),
                  let target = nodes.first(where: { $0.id == edge.target_id }) else { continue }
            let start = vector(source.position)
            let end = vector(target.position)
            let line = connection(from: start, to: end)
            line.opacity = 0.55
            scene.rootNode.addChildNode(line)
        }

        for memory in nodes {
            let sphere = SCNSphere(radius: 0.12)
            sphere.segmentCount = 12
            let material = SCNMaterial()
            material.diffuse.contents = color(for: memory.category)
            material.emission.contents = color(for: memory.category).withAlphaComponent(0.25)
            material.lightingModel = .physicallyBased
            sphere.materials = [material]
            let node = SCNNode(geometry: sphere)
            node.name = "memory-\(memory.id)"
            node.position = vector(memory.position)
            node.scale = SCNVector3(1, 1, 1)
            scene.rootNode.addChildNode(node)
            coordinator.nodeByID[memory.id] = node
        }

        let center = SCNNode(geometry: SCNSphere(radius: 0.42))
        let coreMaterial = SCNMaterial()
        coreMaterial.diffuse.contents = UIColor.black
        coreMaterial.emission.contents = UIColor.cyan.withAlphaComponent(0.5)
        center.geometry?.materials = [coreMaterial]
        center.position = SCNVector3(0, 0, 0)
        scene.rootNode.addChildNode(center)

        view.scene = scene
        view.pointOfView = cameraNode
        coordinator.highlight(selectedID)
    }

    private func makeLight(position: SCNVector3, intensity: CGFloat) -> SCNNode {
        let node = SCNNode()
        let light = SCNLight()
        light.type = .omni
        light.intensity = intensity
        node.light = light
        node.position = position
        return node
    }

    private func vector(_ values: [Double]) -> SCNVector3 {
        guard values.count >= 3 else { return SCNVector3Zero }
        return SCNVector3(Float(values[0]), Float(values[1]), Float(values[2]))
    }

    private func connection(from start: SCNVector3, to end: SCNVector3) -> SCNNode {
        let dx = end.x - start.x
        let dy = end.y - start.y
        let dz = end.z - start.z
        let length = sqrt(dx * dx + dy * dy + dz * dz)
        let cylinder = SCNCylinder(radius: 0.012, height: CGFloat(max(length, 0.001)))
        cylinder.radialSegmentCount = 5
        let material = SCNMaterial()
        material.diffuse.contents = UIColor.cyan.withAlphaComponent(0.45)
        material.emission.contents = UIColor.cyan.withAlphaComponent(0.18)
        cylinder.materials = [material]
        let node = SCNNode(geometry: cylinder)
        node.position = SCNVector3((start.x + end.x) / 2, (start.y + end.y) / 2, (start.z + end.z) / 2)

        // SCNCylinder's long axis is +Y. Rotate that axis onto the full 3D
        // source-to-target vector, including its Z component.
        let axisX = dz
        let axisZ = -dx
        let axisLength = sqrt(axisX * axisX + axisZ * axisZ)
        let angle = acos(max(-1, min(1, dy / max(length, 0.0001))))
        if axisLength < 0.0001 {
            node.rotation = SCNVector4(1, 0, 0, dy < 0 ? Float.pi : 0)
        } else {
            node.rotation = SCNVector4(axisX / axisLength, 0, axisZ / axisLength, angle)
        }
        return node
    }

    private func color(for kind: String) -> UIColor {
        switch kind {
        case "episodic": return UIColor.systemPurple
        case "procedural": return UIColor.systemOrange
        default: return UIColor.systemCyan
        }
    }

    final class Coordinator: NSObject {
        weak var view: SCNView?
        var onSelect: (Int) -> Void
        var nodeByID: [Int: SCNNode] = [:]
        var signature = ""

        init(onSelect: @escaping (Int) -> Void) { self.onSelect = onSelect }

        func highlight(_ selectedID: Int?) {
            for (id, node) in nodeByID {
                guard let material = node.geometry?.firstMaterial else { continue }
                let selected = id == selectedID
                node.scale = selected ? SCNVector3(1.9, 1.9, 1.9) : SCNVector3(1, 1, 1)
                material.emission.contents = selected
                    ? UIColor.white.withAlphaComponent(0.95)
                    : (material.diffuse.contents as? UIColor)?.withAlphaComponent(0.25)
            }
        }

        @objc func handleTap(_ gesture: UITapGestureRecognizer) {
            guard let view, gesture.state == .ended else { return }
            let point = gesture.location(in: view)
            guard let hit = view.hitTest(point, options: nil).first else { return }
            var candidate: SCNNode? = hit.node
            while let node = candidate {
                if let name = node.name, name.hasPrefix("memory-"),
                   let id = Int(name.replacingOccurrences(of: "memory-", with: "")) {
                    onSelect(id)
                    return
                }
                candidate = node.parent
            }
        }
    }
}
