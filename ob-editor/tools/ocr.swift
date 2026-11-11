// OCR images with Apple's Vision framework (accurate mode). Paths on stdin, one per line.
// Prints: PATH \t recognized text (lines joined with " | ").
import Foundation
import Vision
import AppKit
while let line = readLine() {
    let path = line.trimmingCharacters(in: .whitespacesAndNewlines)
    if path.isEmpty { continue }
    guard let img = NSImage(contentsOfFile: path), let cg = img.cgImage(forProposedRect: nil, context: nil, hints: nil) else {
        print("\(path)\t<unreadable>"); continue
    }
    let req = VNRecognizeTextRequest()
    req.recognitionLevel = .accurate
    req.usesLanguageCorrection = true
    let handler = VNImageRequestHandler(cgImage: cg, options: [:])
    try? handler.perform([req])
    let text = (req.results ?? []).compactMap { $0.topCandidates(1).first?.string }.joined(separator: " | ")
    print("\(path)\t\(text)")
    fflush(stdout)
}
