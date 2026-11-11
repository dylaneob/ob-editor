// Face scorer for thumbnail-frame hunting (Apple Vision, the older VN API, every revision pinned so scores do not drift with OS updates).
//   swiftc -O face_quality.swift -o face_quality
//   face_quality W H            raw RGB24 frames on stdin (W*H*3 bytes each), one JSON line out per frame  (used by thumb_frames.py)
//   face_quality IMAGE [...]    same analysis for image files, one "path<TAB>json" line each             (handy for spot checks)
// Only the largest face in the frame is reported. Fields:
//   nf              faces found (0 = no face, nothing else is printed)
//   x y w h         face box in pixels, top-left origin
//   q               VNDetectFaceCaptureQualityRequest score, 0..1 (revision 2)
//   yaw pitch roll  head pose in radians (VNDetectFaceRectanglesRequest revision 3)
//   py px open      pupil y / x inside the eye contour and eye height/width, mean of both eyes. Same numbers gaze.swift prints:
//                   py 0.30-0.36 = on the lens, py >= 0.45 = looking down, open < 0.13 = blink / closed. null if no pupils found.
//   omin            the smaller of the two eyes' openness (catches a wink or a half-blink)
//   mouth           inner-lip gap / mouth width (about 0.02 shut, 0.15+ clearly open)
//   brow            eyebrow-to-eye gap / face height (bigger = brows raised)
import Foundation
import Vision
import CoreGraphics
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

let QUALITY_REV = VNDetectFaceCaptureQualityRequestRevision2
let RECT_REV = VNDetectFaceRectanglesRequestRevision3        // pitch needs rev 3
let LANDMARK_REV = VNDetectFaceLandmarksRequestRevision3     // the revision gaze.swift gets by default (76 points, with pupils)

func num(_ v: Double?) -> String {
    guard let v = v, v.isFinite else { return "null" }
    return String(format: "%.4f", v)
}

func iou(_ a: CGRect, _ b: CGRect) -> CGFloat {
    let i = a.intersection(b)
    if i.isNull { return 0 }
    let ia = i.width * i.height
    return ia / (a.width * a.height + b.width * b.height - ia)
}

// The observation in `obs` that sits on the same face as `box` (several requests each return their own list).
func same(_ obs: [VNFaceObservation]?, as box: CGRect) -> VNFaceObservation? {
    guard let o = obs?.max(by: { iou($0.boundingBox, box) < iou($1.boundingBox, box) }), iou(o.boundingBox, box) > 0.3 else { return nil }
    return o
}

// Straight from gaze.swift: pupil x, pupil y (0 = top of the eye contour, 1 = bottom) and eye height / width.
func eyeStats(_ eye: VNFaceLandmarkRegion2D?, _ pupil: VNFaceLandmarkRegion2D?) -> (Double, Double, Double)? {
    guard let e = eye, let p = pupil, e.pointCount > 2, p.pointCount > 0 else { return nil }
    let pts = e.normalizedPoints
    let xs = pts.map { Double($0.x) }, ys = pts.map { Double($0.y) }
    let minX = xs.min()!, maxX = xs.max()!, minY = ys.min()!, maxY = ys.max()!
    let w = maxX - minX, h = maxY - minY
    guard w > 0, h > 0 else { return nil }
    let px = Double(p.normalizedPoints[0].x), py = Double(p.normalizedPoints[0].y)
    return ((px - minX) / w, 1 - (py - minY) / h, h / w)
}

func meanY(_ r: VNFaceLandmarkRegion2D?, _ size: CGSize) -> Double? {
    guard let r = r, r.pointCount > 0 else { return nil }
    let ys = r.pointsInImage(imageSize: size).map { Double($0.y) }
    return ys.reduce(0, +) / Double(ys.count)
}

func analyze(_ cg: CGImage) -> String {
    let size = CGSize(width: cg.width, height: cg.height)
    let rects = VNDetectFaceRectanglesRequest(); rects.revision = RECT_REV
    let quality = VNDetectFaceCaptureQualityRequest(); quality.revision = QUALITY_REV
    let marks = VNDetectFaceLandmarksRequest(); marks.revision = LANDMARK_REV
    let handler = VNImageRequestHandler(cgImage: cg, options: [:])
    if !performSafely(handler, [rects, quality, marks], "frame") { return "{\"nf\":0,\"err\":1}" }
    let faces = rects.results ?? []
    guard let face = faces.max(by: { $0.boundingBox.width * $0.boundingBox.height < $1.boundingBox.width * $1.boundingBox.height }) else {
        return "{\"nf\":0}"
    }
    let box = face.boundingBox
    let q = same(quality.results, as: box)?.faceCaptureQuality.map { Double($0) }
    var py: Double?, px: Double?, open: Double?, omin: Double?, mouth: Double?, brow: Double?
    if let lm = same(marks.results, as: box)?.landmarks {
        let eyes = [eyeStats(lm.leftEye, lm.leftPupil), eyeStats(lm.rightEye, lm.rightPupil)].compactMap { $0 }
        if !eyes.isEmpty {
            px = eyes.map { $0.0 }.reduce(0, +) / Double(eyes.count)
            py = eyes.map { $0.1 }.reduce(0, +) / Double(eyes.count)
            open = eyes.map { $0.2 }.reduce(0, +) / Double(eyes.count)
            omin = eyes.map { $0.2 }.min()
        }
        if let inner = lm.innerLips, let outer = lm.outerLips, inner.pointCount > 2, outer.pointCount > 2 {
            let iy = inner.pointsInImage(imageSize: size).map { Double($0.y) }
            let ox = outer.pointsInImage(imageSize: size).map { Double($0.x) }
            if let w = ox.max().flatMap({ a in ox.min().map { a - $0 } }), w > 0 { mouth = (iy.max()! - iy.min()!) / w }
        }
        let faceH = Double(box.height) * Double(size.height)
        var gaps: [Double] = []
        if let b = meanY(lm.leftEyebrow, size), let e = meanY(lm.leftEye, size) { gaps.append((b - e) / faceH) }
        if let b = meanY(lm.rightEyebrow, size), let e = meanY(lm.rightEye, size) { gaps.append((b - e) / faceH) }
        if !gaps.isEmpty { brow = gaps.reduce(0, +) / Double(gaps.count) }
    }
    let W = Double(size.width), H = Double(size.height)
    let fields = [
        "\"nf\":\(faces.count)",
        "\"x\":\(num(Double(box.minX) * W))", "\"y\":\(num((1 - Double(box.maxY)) * H))",
        "\"w\":\(num(Double(box.width) * W))", "\"h\":\(num(Double(box.height) * H))",
        "\"q\":\(num(q))",
        "\"yaw\":\(num(face.yaw?.doubleValue))", "\"pitch\":\(num(face.pitch?.doubleValue))", "\"roll\":\(num(face.roll?.doubleValue))",
        "\"py\":\(num(py))", "\"px\":\(num(px))", "\"open\":\(num(open))", "\"omin\":\(num(omin))",
        "\"mouth\":\(num(mouth))", "\"brow\":\(num(brow))",
    ]
    return "{" + fields.joined(separator: ",") + "}"
}

func readExactly(_ n: Int, into buf: UnsafeMutableRawPointer) -> Bool {
    var got = 0
    while got < n {
        let r = read(0, buf + got, n - got)
        if r < 0 && errno == EINTR { continue }
        if r <= 0 { return false }
        got += r
    }
    return true
}

func rgbImage(_ bytes: UnsafeRawPointer, w: Int, h: Int) -> CGImage? {
    let data = Data(bytes: bytes, count: w * h * 3)
    guard let provider = CGDataProvider(data: data as CFData), let space = CGColorSpace(name: CGColorSpace.sRGB) else { return nil }
    return CGImage(width: w, height: h, bitsPerComponent: 8, bitsPerPixel: 24, bytesPerRow: w * 3, space: space,
                   bitmapInfo: CGBitmapInfo(rawValue: CGImageAlphaInfo.none.rawValue), provider: provider, decode: nil,
                   shouldInterpolate: false, intent: .defaultIntent)
}

setvbuf(stdout, nil, _IOLBF, 0)
let args = Array(CommandLine.arguments.dropFirst())
if args.count == 2, let w = Int(args[0]), let h = Int(args[1]), w > 0, h > 0 {
    let n = w * h * 3
    let buf = UnsafeMutableRawPointer.allocate(byteCount: n, alignment: 16)
    while readExactly(n, into: buf) {
        autoreleasepool {
            if let img = rgbImage(buf, w: w, h: h) { print(analyze(img)) } else { print("{\"nf\":0,\"err\":2}") }
        }
    }
} else if args.isEmpty {
    FileHandle.standardError.write("usage: face_quality W H < rgb24 frames    |    face_quality IMAGE [IMAGE ...]\n".data(using: .utf8)!)
    exit(2)
} else {
    for path in args {
        autoreleasepool {
            if let src = CGImageSourceCreateWithURL(URL(fileURLWithPath: path) as CFURL, nil), let img = CGImageSourceCreateImageAtIndex(src, 0, nil) {
                print("\(path)\t\(analyze(img))")
            } else {
                print("\(path)\t{\"nf\":0,\"err\":3}")
            }
        }
    }
}
