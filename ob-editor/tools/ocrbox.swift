// OCR one image with Apple's Vision framework and print each text line with its box in PIXELS (top-left origin):
//   ocrbox IMAGE  ->  x0 y0 x1 y1 \t text
import Foundation
import Vision
import AppKit
let path = CommandLine.arguments[1]
guard let img = NSImage(contentsOfFile: path), let cg = img.cgImage(forProposedRect: nil, context: nil, hints: nil) else { exit(1) }
let W = CGFloat(cg.width), H = CGFloat(cg.height)
let req = VNRecognizeTextRequest(); req.recognitionLevel = .accurate; req.usesLanguageCorrection = true
try? VNImageRequestHandler(cgImage: cg, options: [:]).perform([req])
for o in req.results ?? [] {
    guard let c = o.topCandidates(1).first else { continue }
    let b = o.boundingBox
    let x0 = Int(b.minX * W), x1 = Int(b.maxX * W), y0 = Int((1 - b.maxY) * H), y1 = Int((1 - b.minY) * H)
    print("\(x0) \(y0) \(x1) \(y1)\t\(c.string)")
}
