// subject_instances: Apple Vision foreground instance masks (on-device subject lifting; segmentation of a real photo,
// no generated pixels). Built 2026-10-18 for the Halloween candy flat lay: one mask per separate object.
// usage: subject_instances <image> <out_dir>   -> out_dir/mask_NN.png (8-bit, full image size, EXIF-oriented)
import Foundation
import Vision
import CoreImage
import ImageIO
import UniformTypeIdentifiers

let args = CommandLine.arguments
guard args.count >= 3 else { print("usage: subject_instances <image> <out_dir>"); exit(1) }
let outDir = URL(fileURLWithPath: args[2])
try? FileManager.default.createDirectory(at: outDir, withIntermediateDirectories: true)
guard let ci = CIImage(contentsOf: URL(fileURLWithPath: args[1]), options: [.applyOrientationProperty: true]) else {
    print("cannot read \(args[1])"); exit(1)
}
let handler = VNImageRequestHandler(ciImage: ci, options: [:])
let req = VNGenerateForegroundInstanceMaskRequest()
do { try handler.perform([req]) } catch { print("vision failed: \(error)"); exit(1) }
guard let obs = req.results?.first else { print("instances 0"); exit(0) }
let ctx = CIContext()
let gray = CGColorSpaceCreateDeviceGray()
var n = 0
for idx in obs.allInstances.sorted() {
    guard let pb = try? obs.generateScaledMaskForImage(forInstances: IndexSet(integer: idx), from: handler) else { continue }
    let m = CIImage(cvPixelBuffer: pb)
    guard let cg = ctx.createCGImage(m, from: m.extent, format: .L8, colorSpace: gray) else { continue }
    n += 1
    let url = outDir.appendingPathComponent(String(format: "mask_%02d.png", n))
    guard let dest = CGImageDestinationCreateWithURL(url as CFURL, UTType.png.identifier as CFString, 1, nil) else { continue }
    CGImageDestinationAddImage(dest, cg, nil)
    CGImageDestinationFinalize(dest)
}
print("instances \(n)")
