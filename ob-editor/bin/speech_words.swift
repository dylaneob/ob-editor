// Word timings from Apple's on-device transcriber (macOS 26 SpeechAnalyzer / SpeechTranscriber), to test against whisper.cpp.
//   swiftc -O speech_words.swift -o speech_words
//   ./speech_words check                 -> is the en-US model supported / installed (never downloads)
//   ./speech_words words AUDIO.wav       -> JSON [{"w": word, "s": start, "e": end}, ...] on stdout (seconds)
import AVFoundation
import Foundation
import Speech

let args = CommandLine.arguments
let locale = Locale(identifier: "en-US")

func makeTranscriber() -> SpeechTranscriber {
    SpeechTranscriber(locale: locale, transcriptionOptions: [], reportingOptions: [], attributeOptions: [.audioTimeRange])
}

func check() async {
    let supported = await SpeechTranscriber.supportedLocales.map { $0.identifier(.bcp47) }
    let installed = await SpeechTranscriber.installedLocales.map { $0.identifier(.bcp47) }
    let status = await AssetInventory.status(forModules: [makeTranscriber()])
    print("supported en-US:", supported.contains("en-US"), "| installed:", installed, "| asset status:", status)
}

func words(_ path: String) async throws {
    let transcriber = makeTranscriber()
    var status = await AssetInventory.status(forModules: [transcriber])
    if status != .installed {
        // Each new binary has to ask for the module. When the model is already on the Mac (en-US was, 10-20: 0 bytes to fetch), asking
        // registers it at once. downloadAndInstall() is never called here, so this never downloads anything.
        _ = try await AssetInventory.assetInstallationRequest(supporting: [transcriber])
        status = await AssetInventory.status(forModules: [transcriber])
    }
    guard status == .installed else { FileHandle.standardError.write("model not installed (status \(status)); a download would be needed, so stopping\n".data(using: .utf8)!); exit(2) }
    let analyzer = SpeechAnalyzer(modules: [transcriber])
    let file = try AVAudioFile(forReading: URL(fileURLWithPath: path))
    var out: [[String: Any]] = []
    let collect = Task {
        for try await result in transcriber.results {
            for run in result.text.runs {
                guard let r = run.audioTimeRange else { continue }
                let w = String(result.text[run.range].characters).trimmingCharacters(in: .whitespacesAndNewlines)
                if w.isEmpty { continue }
                out.append(["w": w, "s": r.start.seconds, "e": r.end.seconds])
            }
        }
    }
    let t0 = Date()
    if let last = try await analyzer.analyzeSequence(from: file) { try await analyzer.finalizeAndFinish(through: last) } else { await analyzer.cancelAndFinishNow() }
    try await collect.value
    FileHandle.standardError.write(String(format: "%.2f s to transcribe\n", Date().timeIntervalSince(t0)).data(using: .utf8)!)
    print(String(data: try JSONSerialization.data(withJSONObject: out), encoding: .utf8)!)
}

if args.count >= 2 && args[1] == "check" { await check() }
else if args.count >= 3 && args[1] == "words" { try await words(args[2]) }
else { print("usage: speech_words check | words AUDIO.wav"); exit(1) }
