#!/usr/bin/env python3
"""Make the fonts the editor's graphics use, from this Mac's own system fonts (Apple's fonts can't be shipped).

  python3 font_setup.py ~/ob-editor/fonts

Writes AvenirNext-DemiBold.ttf, AvenirNext-Heavy.ttf, AvenirNext-Medium.ttf (pulled out of macOS's Avenir Next.ttc by
face name) and DINCondensed-Bold.ttf (copied from macOS). HyperFrames compositions load them from each project's
assets/fonts folder, so copy this folder into a project's hf/assets/fonts when you start one.
"""
import os, shutil, struct, sys

TTC = "/System/Library/Fonts/Avenir Next.ttc"
DIN = "/System/Library/Fonts/Supplemental/DIN Condensed Bold.ttf"
WANT = {"Avenir Next Demi Bold": "AvenirNext-DemiBold.ttf", "Avenir Next Heavy": "AvenirNext-Heavy.ttf",
        "Avenir Next Medium": "AvenirNext-Medium.ttf"}


def faces(b):
    n = struct.unpack(">I", b[8:12])[0]
    return [struct.unpack(">I", b[12 + 4 * i:16 + 4 * i])[0] for i in range(n)]


def tables(b, off):
    ntab = struct.unpack(">H", b[off + 4:off + 6])[0]
    return [struct.unpack(">4sIII", b[off + 12 + 16 * i:off + 28 + 16 * i]) for i in range(ntab)]


def full_name(b, off):
    for tag, _, toff, _ in tables(b, off):
        if tag != b"name": continue
        _, count, sto = struct.unpack(">HHH", b[toff:toff + 6])
        for i in range(count):
            pid, eid, lid, nid, ln, so = struct.unpack(">HHHHHH", b[toff + 6 + 12 * i:toff + 18 + 12 * i])
            if nid != 4: continue
            raw = b[toff + sto + so:toff + sto + so + ln]
            return raw.decode("utf-16-be") if pid in (0, 3) else raw.decode("mac_roman")
    return ""


def extract(b, off, dst):
    sfnt_ver = struct.unpack(">I", b[off:off + 4])[0]; recs = tables(b, off); ntab = len(recs)
    es = max(k for k in range(16) if 2 ** k <= ntab)
    hdr = struct.pack(">IHHHH", sfnt_ver, ntab, 16 * 2 ** es, es, ntab * 16 - 16 * 2 ** es)
    data, tdir, pos = b"", b"", 12 + 16 * ntab
    for tag, csum, toff, tlen in sorted(recs):
        t = b[toff:toff + tlen]; tdir += struct.pack(">4sIII", tag, csum, pos, tlen)
        pad = (4 - tlen % 4) % 4; data += t + b"\0" * pad; pos += tlen + pad
    open(dst, "wb").write(hdr + tdir + data)


def main():
    out = os.path.expanduser(sys.argv[1] if len(sys.argv) > 1 else "~/ob-editor/fonts"); os.makedirs(out, exist_ok=True)
    b = open(TTC, "rb").read(); found = set()
    for off in faces(b):
        name = full_name(b, off)
        if name in WANT and name not in found:
            extract(b, off, os.path.join(out, WANT[name])); found.add(name); print("  font", WANT[name])
    for name in set(WANT) - found: print("  missing in this macOS:", name)
    if os.path.exists(DIN): shutil.copyfile(DIN, os.path.join(out, "DINCondensed-Bold.ttf")); print("  font DINCondensed-Bold.ttf")
    else: print("  missing in this macOS: DIN Condensed Bold")


if __name__ == "__main__":
    main()
