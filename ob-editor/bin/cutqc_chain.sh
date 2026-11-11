#!/bin/zsh
# Word-loss + join QC for a long-form cut (2026-10-31, the 10-30 night takes). react_qc.py wants whisper -ml 1 JSON for the raw mic
# (mic_words.json) and the edit (qc/edit_words.json); both are made here from whisper medium DTW word times (dtw_words.py), which hold
# within ~0.1 s where -ml 1 drifts up to 3 s. Then cut_audit.py (60 ms lead/tail, 140-650 ms joins).
#   cutqc_chain.sh WORK HOOK
W=$1; H=$2; B=~/ob-editor/bin; cd $W
cp cutlist_$H.json cutlist.json && cp react_cutlist_$H.json react_cutlist.json && cp qc/master16k.wav mic16.wav
conv() { python3 -I - "$1" "$2" <<'PY'
import json, sys
w = json.load(open(sys.argv[1]))["words"]
json.dump({"transcription": [{"offsets": {"from": int(a * 1000), "to": int(b * 1000)}, "text": " " + t} for a, b, t in w]}, open(sys.argv[2], "w"))
PY
}
conv qc/words.json mic_words.json
python3 -I $B/react_qc.py $W build
nice -n 5 whisper-cli -m ~/.whisper-models/ggml-medium.en.bin -f qc/edit_mic16.wav -nfa -dtw medium.en -ojf -of qc/edit_dtw -t 6 > qc/edit_whisper.log 2>&1
python3 -I $B/dtw_words.py qc/edit_dtw.json qc/edit_dtwwords.json > /dev/null && conv qc/edit_dtwwords.json qc/edit_words.json
python3 -I $B/react_qc.py $W compare > qc/react_qc.out 2>&1; echo "react_qc exit $?" >> qc/react_qc.out
python3 -I $B/cut_audit.py $W > qc/cut_audit.out 2>&1; echo "cut_audit exit $?" >> qc/cut_audit.out
echo "CUTQC DONE $(date +%H:%M:%S)" >> qc/react_qc.out
