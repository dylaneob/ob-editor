import Foundation
import Vision
import CoreImage
import ImageIO
import UniformTypeIdentifiers
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
// usage: segment in.png out_mask.png  (Apple Vision person segmentation, on-device; writes an 8-bit mask at the input size)
let args = CommandLine.arguments
let url = URL(fileURLWithPath: args[1])
guard let src = CGImageSourceCreateWithURL(url as CFURL, nil), let cg = CGImageSourceCreateImageAtIndex(src, 0, nil) else { fatalError("read") }
let req = VNGeneratePersonSegmentationRequest()
req.qualityLevel = .accurate
req.outputPixelFormat = kCVPixelFormatType_OneComponent8
let h = VNImageRequestHandler(cgImage: cg, options: [:])
if !performSafely(h, [req], args[1]) { exit(3) }
guard let pb = req.results?.first?.pixelBuffer else { fatalError("no mask") }
var mask = CIImage(cvPixelBuffer: pb)
let sx = CGFloat(cg.width) / mask.extent.width, sy = CGFloat(cg.height) / mask.extent.height
mask = mask.transformed(by: CGAffineTransform(scaleX: sx, y: sy))
let ctx = CIContext()
guard let out = ctx.createCGImage(mask, from: CGRect(x: 0, y: 0, width: cg.width, height: cg.height)) else { fatalError("render") }
let dst = CGImageDestinationCreateWithURL(URL(fileURLWithPath: args[2]) as CFURL, UTType.png.identifier as CFString, 1, nil)!
CGImageDestinationAddImage(dst, out, nil); CGImageDestinationFinalize(dst)
print("mask \(cg.width)x\(cg.height)")
