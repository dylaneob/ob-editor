// Face boxes via Apple Vision (no OpenCV cascades needed).
//   swiftc -O faces.swift -o faces && ./faces IMG [IMG ...]
// One line per image: path, then x0 y0 x1 y1 per face in pixels, top-left origin (largest face first). "none" if no face.
import Foundation
import Vision
import AppKit
import CoreML

// 2026-11-03 (Mac mini): with another job's model on the Neural Engine (the FDOE cutouts' person segmentation), Vision can
// refuse to load the next one ("Could not build inference plan - ANECF error"), and `try?` turned that into "no face".
// performSafely retries once, then runs the same requests on the CPU; only if that fails too does the image count as an
// error (stderr, exit 3), so a caller can tell a failure from an empty frame.
var visionFailures = 0
func onCPU(_ reqs: [VNRequest]) {
    for r in reqs {
        guard let stages = try? r.supportedComputeStageDevices else { continue }
        for (stage, devs) in stages {
            if let cpu = devs.first(where: { if case .cpu = $0 { return true } else { return false } }) { r.setComputeDevice(cpu, for: stage) }
        }
    }
}
func performSafely(_ h: VNImageRequestHandler, _ reqs: [VNRequest], _ path: String) -> Bool {
    for attempt in 0..<3 {
        do { try h.perform(reqs); return true } catch {
            if attempt == 0 { usleep(400_000) } else { onCPU(reqs) }
            if attempt == 2 { FileHandle.standardError.write("vision failed on \(path): \(error.localizedDescription)\n".data(using: .utf8)!) }
        }
    }
    visionFailures += 1; return false
}

for path in CommandLine.arguments.dropFirst() {
    guard let img = NSImage(contentsOfFile: path),
          let cg = img.cgImage(forProposedRect: nil, context: nil, hints: nil) else { print("\(path) error"); continue }
    let W = Double(cg.width), H = Double(cg.height)
    let req = VNDetectFaceRectanglesRequest()
    if !performSafely(VNImageRequestHandler(cgImage: cg, options: [:]), [req], path) { print("\(path) error"); continue }
    let faces = (req.results ?? []).map { $0.boundingBox }.sorted { $0.width * $0.height > $1.width * $1.height }
    if faces.isEmpty { print("\(path) none"); continue }
    let s = faces.map { b in String(format: "%.0f %.0f %.0f %.0f", b.minX * W, (1 - b.maxY) * H, b.maxX * W, (1 - b.minY) * H) }
    print("\(path) " + s.joined(separator: " | "))
}
if visionFailures > 0 { exit(3) }
