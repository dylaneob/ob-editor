import Foundation
import Vision
import ImageIO
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
// usage: frame_obstacles in.png  -> JSON {"w":W,"h":H,"faces":[[x,y,w,h]...],"texts":[[x,y,w,h,"str"]...]} (pixels, top-left origin)
// Apple Vision on-device: face rectangles + recognized text boxes. Used to place hook text clear of faces and burned-in text.
let url = URL(fileURLWithPath: CommandLine.arguments[1])
guard let src = CGImageSourceCreateWithURL(url as CFURL, nil), let cg = CGImageSourceCreateImageAtIndex(src, 0, nil) else { fatalError("read") }
let W = CGFloat(cg.width), H = CGFloat(cg.height)
let fr = VNDetectFaceRectanglesRequest()
let tr = VNRecognizeTextRequest(); tr.recognitionLevel = .fast; tr.usesLanguageCorrection = false
if !performSafely(VNImageRequestHandler(cgImage: cg, options: [:]), [fr, tr], CommandLine.arguments[1]) { exit(3) }   // no JSON: the gate retries the frame
func px(_ b: CGRect) -> [Int] { [Int(b.minX * W), Int((1 - b.maxY) * H), Int(b.width * W), Int(b.height * H)] }
var faces: [[Int]] = []
for o in fr.results ?? [] { faces.append(px(o.boundingBox)) }
var texts: [[Any]] = []
for o in tr.results ?? [] { let b = px(o.boundingBox); texts.append(b + [o.topCandidates(1).first?.string ?? ""]) }
let out: [String: Any] = ["w": Int(W), "h": Int(H), "faces": faces, "texts": texts]
print(String(data: try JSONSerialization.data(withJSONObject: out), encoding: .utf8)!)
