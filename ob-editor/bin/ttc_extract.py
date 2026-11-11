"""Extract one face from a TrueType Collection into a standalone .ttf (no fontTools)."""
import struct, sys
src, idx, dst = sys.argv[1], int(sys.argv[2]), sys.argv[3]
b = open(src, "rb").read()
assert b[:4] == b"ttcf"
num = struct.unpack(">I", b[8:12])[0]
off = struct.unpack(">I", b[12 + 4 * idx:16 + 4 * idx])[0]
sfnt_ver, ntab = struct.unpack(">IH", b[off:off + 6])
recs = [struct.unpack(">4sIII", b[off + 12 + 16 * i: off + 28 + 16 * i]) for i in range(ntab)]
es = max(k for k in range(16) if 2 ** k <= ntab)
hdr = struct.pack(">IHHHH", sfnt_ver, ntab, 16 * 2 ** es, es, ntab * 16 - 16 * 2 ** es)
data, table_dir, pos = b"", b"", 12 + 16 * ntab
for tag, csum, toff, tlen in sorted(recs):
    t = b[toff:toff + tlen]
    table_dir += struct.pack(">4sIII", tag, csum, pos, tlen)
    pad = (4 - tlen % 4) % 4
    data += t + b"\0" * pad; pos += tlen + pad
open(dst, "wb").write(hdr + table_dir + data)
print(dst, len(hdr + table_dir + data), "bytes,", ntab, "tables")
