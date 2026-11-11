// ocrfind: Apple Vision text recognition on a page image; boxes in image px, top-left origin.
//   ocrfind IMAGE "phrase" ...   one line per phrase: phrase<TAB>x y w h | x y w h ...   (a phrase inside ONE recognised line,
//                                case-insensitive; same output as the C4367 tools/ocrfind this grew from)
//   ocrfind --words IMAGE        JSON on stdout, for callers that match phrases themselves (also across line wraps):
//                                {"w":W,"h":H,"lines":[{"text":..,"box":[x,y,w,h],"words":[{"t":..,"box":[x,y,w,h]}]}]}
//                                boxes are floats (2 decimals); round once at the end, per line, not per word.
// The image is read as data only (NSImage -> CGImage -> VNRecognizeTextRequest); nothing in it is executed.
// Build: swiftc -O -o ocrfind ocrfind.swift   (bin/ocrfind is the compiled copy; doc_page.py rebuilds it when it is missing)
import Foundation
import Vision
import AppKit

func fail(_ m: String) -> Never { FileHandle.standardError.write((m + "\n").data(using: .utf8)!); exit(1) }
var args = Array(CommandLine.arguments.dropFirst())
let dump = args.first == "--words"
if dump { args.removeFirst() }
guard args.count >= (dump ? 1 : 2) else { fail("usage: ocrfind IMAGE \"phrase\" ...   |   ocrfind --words IMAGE") }
guard let img = NSImage(contentsOfFile: args[0]), let cg = img.cgImage(forProposedRect: nil, context: nil, hints: nil) else { fail("cannot read image: \(args[0])") }
let W = Double(cg.width), H = Double(cg.height)
let req = VNRecognizeTextRequest(); req.recognitionLevel = .accurate; req.usesLanguageCorrection = false
do { try VNImageRequestHandler(cgImage: cg, options: [:]).perform([req]) } catch { fail("vision failed: \(error)") }
let obs = req.results ?? []

func box(_ c: VNRecognizedText, _ r: Range<String.Index>) -> [Double]? {
  guard let bb = try? c.boundingBox(for: r)?.boundingBox else { return nil }
  return [bb.minX * W, (1 - bb.maxY) * H, bb.width * W, bb.height * H]
}
func r2(_ v: Double) -> Double { (v * 100).rounded() / 100 }

if dump {
  var lines: [[String: Any]] = []
  for o in obs {
    guard let c = o.topCandidates(1).first else { continue }
    let s = c.string
    var words: [[String: Any]] = []
    var i = s.startIndex
    while i < s.endIndex {
      if s[i] == " " { i = s.index(after: i); continue }
      var j = i
      while j < s.endIndex && s[j] != " " { j = s.index(after: j) }
      if let b = box(c, i..<j) { words.append(["t": String(s[i..<j]), "box": b.map(r2)]) }
      i = j
    }
    if let lb = box(c, s.startIndex..<s.endIndex) { lines.append(["text": s, "box": lb.map(r2), "words": words]) }
  }
  lines.sort { (($0["box"] as! [Double])[1]) < (($1["box"] as! [Double])[1]) }
  let out: [String: Any] = ["w": Int(W), "h": Int(H), "lines": lines]
  let d = try JSONSerialization.data(withJSONObject: out, options: [])
  print(String(data: d, encoding: .utf8)!)
} else {
  for ph in args[1...] {
    var hits: [String] = []
    for o in obs {
      guard let c = o.topCandidates(1).first else { continue }
      let s = c.string
      if let r = s.range(of: ph, options: [.caseInsensitive]), let b = box(c, r) { hits.append(String(format: "%.0f %.0f %.0f %.0f", b[0], b[1], b[2], b[3])) }
    }
    print("\(ph)\t\(hits.joined(separator: " | "))")
  }
}
