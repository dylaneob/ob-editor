import Foundation
import Vision
import CoreML
import CoreImage
import ImageIO
import UniformTypeIdentifiers
// usage: person_mask_dir IN_DIR OUT_DIR  -> one 8-bit mask PNG per input PNG (Apple Vision person segmentation, on-device,
// accurate quality, model loaded once). Real footage only; used to cut OB out of his own takes.
let a = CommandLine.arguments
let fm = FileManager.default
let files = try fm.contentsOfDirectory(atPath: a[1]).filter { $0.hasSuffix(".png") && !$0.hasPrefix("._") }.sorted()
try? fm.createDirectory(atPath: a[2], withIntermediateDirectories: true)
let req = VNGeneratePersonSegmentationRequest(); req.qualityLevel = .accurate; req.outputPixelFormat = kCVPixelFormatType_OneComponent8
let ctx = CIContext()
// 11-03 (the Mac mini, macOS 27): the Neural Engine can refuse the matting model ("no ANE resources (transient; retry)") and the
// tool died with SIGTRAP mid-render. Retry on the default device, then run the same model on the GPU, then the CPU: same masks.
var devices: [MLComputeDevice?] = [nil]
if #available(macOS 14.0, *) { devices += MLComputeDevice.allComputeDevices.filter { if case .gpu = $0 { return true }; return false }.map { Optional($0) }
                               devices += MLComputeDevice.allComputeDevices.filter { if case .cpu = $0 { return true }; return false }.map { Optional($0) } }
var dev = 0
func perform(_ cg: CGImage) throws {
    var last: Error? = nil
    for attempt in 0..<(2 + devices.count) {
        do { try VNImageRequestHandler(cgImage: cg, options: [:]).perform([req]); return }
        catch {
            last = error
            if attempt == 0 { usleep(400_000); continue }   // "transient; retry"
            dev += 1; if dev >= devices.count { break }
            if #available(macOS 14.0, *), let d = devices[dev] {
                for stage in (try? req.supportedComputeStageDevices.keys.map { $0 }) ?? [] { req.setComputeDevice(d, for: stage) }
                FileHandle.standardError.write("person_mask_dir: Neural Engine refused the model, using \(d)\n".data(using: .utf8)!)
            }
        }
    }
    throw last!
}
for f in files {
    let url = URL(fileURLWithPath: a[1] + "/" + f)
    guard let src = CGImageSourceCreateWithURL(url as CFURL, nil), let cg = CGImageSourceCreateImageAtIndex(src, 0, nil) else { continue }
    try perform(cg)
    guard let pb = req.results?.first?.pixelBuffer else { continue }
    var m = CIImage(cvPixelBuffer: pb)
    m = m.transformed(by: CGAffineTransform(scaleX: CGFloat(cg.width) / m.extent.width, y: CGFloat(cg.height) / m.extent.height))
    guard let out = ctx.createCGImage(m, from: CGRect(x: 0, y: 0, width: cg.width, height: cg.height)) else { continue }
    let d = CGImageDestinationCreateWithURL(URL(fileURLWithPath: a[2] + "/" + f) as CFURL, UTType.png.identifier as CFString, 1, nil)!
    CGImageDestinationAddImage(d, out, nil); CGImageDestinationFinalize(d)
}
print("masks: \(files.count)")
