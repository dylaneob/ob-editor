// Has iCloud Drive finished uploading these files? (brctl names are obfuscated mid-upload, so ask macOS per file.)
//   swift icloud_uploaded.swift FILE [FILE ...]   ->  "uploaded" | "uploading" | "waiting" | "not in iCloud"  name
import Foundation

for p in CommandLine.arguments.dropFirst() {
    let u = URL(fileURLWithPath: p)
    guard let v = try? u.resourceValues(forKeys: [.isUbiquitousItemKey, .ubiquitousItemIsUploadedKey, .ubiquitousItemIsUploadingKey]),
          v.isUbiquitousItem == true else { print("not in iCloud  \(u.lastPathComponent)"); continue }
    let state = v.ubiquitousItemIsUploaded == true ? "uploaded" : (v.ubiquitousItemIsUploading == true ? "uploading" : "waiting")
    print("\(state)  \(u.lastPathComponent)")
}
