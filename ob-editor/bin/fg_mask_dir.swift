import Foundation
import Vision
import CoreImage
import ImageIO
import UniformTypeIdentifiers
// usage: fg_mask_dir IN_DIR OUT_DIR -> one 8-bit mask PNG per input PNG, full frame (not cropped): Apple Vision's foreground
// instance mask (on-device), which keeps what he holds (the mic, a scale, a plate). tmpl.py unions it with the person matte near his
// body (2026-11-04: over her footage the mic went see-through, because the person matte leaves held objects out).
let a = CommandLine.arguments
guard a.count == 3 else { print("usage: fg_mask_dir IN_DIR OUT_DIR"); exit(1) }
let fm = FileManager.default
let files = try fm.contentsOfDirectory(atPath: a[1]).filter { $0.hasSuffix(".png") && !$0.hasPrefix("._") }.sorted()
try? fm.createDirectory(atPath: a[2], withIntermediateDirectories: true)
let ctx = CIContext()
let gray = CGColorSpaceCreateDeviceGray()
var done = 0
for f in files {
    let url = URL(fileURLWithPath: a[1]).appendingPathComponent(f)
    guard let src = CGImageSourceCreateWithURL(url as CFURL, nil), let cg = CGImageSourceCreateImageAtIndex(src, 0, nil) else { continue }
    let req = VNGenerateForegroundInstanceMaskRequest()
    let h = VNImageRequestHandler(cgImage: cg, options: [:])
    var ci = CIImage(color: CIColor(red: 0, green: 0, blue: 0)).cropped(to: CGRect(x: 0, y: 0, width: cg.width, height: cg.height))
    do {
        try h.perform([req])
        if let obs = req.results?.first {
            let buf = try obs.generateScaledMaskForImage(forInstances: obs.allInstances, from: h)
            ci = CIImage(cvPixelBuffer: buf)
        }
    } catch { }
    guard let out = ctx.createCGImage(ci, from: CGRect(x: 0, y: 0, width: cg.width, height: cg.height), format: .L8, colorSpace: gray) else { continue }
    let dst = URL(fileURLWithPath: a[2]).appendingPathComponent(f)
    guard let d = CGImageDestinationCreateWithURL(dst as CFURL, UTType.png.identifier as CFString, 1, nil) else { continue }
    CGImageDestinationAddImage(d, out, nil); CGImageDestinationFinalize(d); done += 1
}
print("fg masks: \(done) of \(files.count)")
