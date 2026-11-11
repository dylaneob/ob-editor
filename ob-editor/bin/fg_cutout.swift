// Cut the main object out of a photo (Apple Vision foreground instance mask, on-device): PNG with alpha, cropped to it.
//   fg_cutout IN.jpg OUT.png
import Foundation
import Vision
import CoreImage
import AppKit

let args = CommandLine.arguments
guard args.count == 3, let img = NSImage(contentsOfFile: args[1]),
      let cg = img.cgImage(forProposedRect: nil, context: nil, hints: nil) else { print("usage: fg_cutout IN OUT.png"); exit(1) }
let req = VNGenerateForegroundInstanceMaskRequest()
let h = VNImageRequestHandler(cgImage: cg, options: [:])
do { try h.perform([req]) } catch { print("vision failed: \(error)"); exit(2) }
guard let obs = req.results?.first else { print("no foreground found"); exit(3) }
do {
    let buf = try obs.generateMaskedImage(ofInstances: obs.allInstances, from: h, croppedToInstancesExtent: true)
    let ci = CIImage(cvPixelBuffer: buf)
    let ctx = CIContext()
    guard let out = ctx.createCGImage(ci, from: ci.extent) else { exit(4) }
    let rep = NSBitmapImageRep(cgImage: out)
    try rep.representation(using: .png, properties: [:])!.write(to: URL(fileURLWithPath: args[2]))
    print("\(args[2]) \(out.width)x\(out.height) instances=\(obs.allInstances.count)")
} catch { print("mask failed: \(error)"); exit(5) }
