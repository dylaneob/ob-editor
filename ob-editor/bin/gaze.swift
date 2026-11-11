// Eye-line check for talking-head frames (Apple Vision). For each image: head pitch/yaw and where each pupil sits
// inside its eye (0 = top/left edge of the eye contour, 1 = bottom/right), plus eye openness (height / width).
// Looking down at a script reads as pitch down and/or pupils low with lids lowered.
//   gaze IMAGE [IMAGE ...]      ->  path  pitch  yaw  pupil_y  pupil_x  open      (one line each; "-" if no face)
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

func eyeStats(_ eye: VNFaceLandmarkRegion2D?, _ pupil: VNFaceLandmarkRegion2D?) -> (Double, Double, Double)? {
    guard let e = eye, let p = pupil, e.pointCount > 2, p.pointCount > 0 else { return nil }
    let pts = e.normalizedPoints
    let xs = pts.map { Double($0.x) }, ys = pts.map { Double($0.y) }
    let minX = xs.min()!, maxX = xs.max()!, minY = ys.min()!, maxY = ys.max()!
    let w = maxX - minX, h = maxY - minY
    guard w > 0, h > 0 else { return nil }
    let px = Double(p.normalizedPoints[0].x), py = Double(p.normalizedPoints[0].y)
    // Vision's y axis points up: 1 - (py - minY)/h puts 0 at the top of the eye, 1 at the bottom
    return ((px - minX) / w, 1 - (py - minY) / h, h / w)
}

for path in CommandLine.arguments.dropFirst() {
    guard let img = NSImage(contentsOfFile: path), let cg = img.cgImage(forProposedRect: nil, context: nil, hints: nil) else {
        print("\(path) -"); continue
    }
    let req = VNDetectFaceLandmarksRequest()
    let rect = VNDetectFaceRectanglesRequest(); rect.revision = VNDetectFaceRectanglesRequestRevision3   // pitch needs rev 3
    let h = VNImageRequestHandler(cgImage: cg, options: [:])
    if !performSafely(h, [req, rect], path) { print("\(path) -"); continue }
    guard let faces = req.results, let f = faces.max(by: { $0.boundingBox.width < $1.boundingBox.width }) else { print("\(path) -"); continue }
    let fr = rect.results?.max(by: { $0.boundingBox.width < $1.boundingBox.width })
    let pitch = fr?.pitch?.doubleValue ?? .nan, yaw = fr?.yaw?.doubleValue ?? .nan
    let l = eyeStats(f.landmarks?.leftEye, f.landmarks?.leftPupil), r = eyeStats(f.landmarks?.rightEye, f.landmarks?.rightPupil)
    let both = [l, r].compactMap { $0 }
    if both.isEmpty { print(String(format: "%@ %.3f %.3f nan nan nan", path, pitch, yaw)); continue }
    let px = both.map { $0.0 }.reduce(0, +) / Double(both.count)
    let py = both.map { $0.1 }.reduce(0, +) / Double(both.count)
    let op = both.map { $0.2 }.reduce(0, +) / Double(both.count)
    print(String(format: "%@ %.3f %.3f %.3f %.3f %.3f", path, pitch, yaw, py, px, op))
}
if visionFailures > 0 { exit(3) }
