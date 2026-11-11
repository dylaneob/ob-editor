"""Consent screen for client proof: flag candidate images that contain a photo of a client who must not be shown.

  ~/OpenMontage/.venv/bin/python -I proof_screen.py OUT.json --cands "GLOB" ["GLOB" ...] [--excl "Name" ...] [--raw IMG ...]

Reference photos = every image in the T7 photo folder of each --excl client (default: the standing exclusion list
below) plus any --raw images (e.g. album photos captioned "blur face"). SIFT features from all references go into
one FLANN index; each candidate votes for its nearest reference images, and the top 6 are verified with a Lowe ratio
test + RANSAC homography. 60+ inliers = the same photo (also inside collages and screenshots). 15-60: confirm by
eye (a chat photo of fries matched a before/after at 17). 8-14 is usually phone-UI chrome. Needs OpenCV (the editor venv, ~/ob-editor/.venv). It only finds the SAME photo: a different photo of an
excluded client still needs a visual check against their folder.
"""
import argparse, cv2, glob, json, os
import numpy as np

PH = os.path.expanduser("~/EditorWork/ARCHIVE/client-photos")   # one folder per client: PH/<Client Name>/...
EXCL = []   # folder names (under PH) of clients who did NOT consent to being shown
ap = argparse.ArgumentParser()
ap.add_argument("out"); ap.add_argument("--cands", nargs="+", required=True)
ap.add_argument("--excl", nargs="*", default=EXCL); ap.add_argument("--raw", nargs="*", default=[])
a = ap.parse_args()
img_ok = lambda p: p.lower().endswith((".jpg", ".jpeg", ".png")) and not os.path.basename(p).startswith("._")
CANDS = sorted({p for g in a.cands for p in glob.glob(g) if img_ok(p)})
sift, sift_c = cv2.SIFT_create(nfeatures=900), cv2.SIFT_create(nfeatures=5000)


def load(p, side):
    im = cv2.imread(p, cv2.IMREAD_GRAYSCALE)
    if im is None: return None
    s = side / max(im.shape)
    return cv2.resize(im, None, fx=s, fy=s, interpolation=cv2.INTER_AREA) if s < 1 else im


refs, ref_desc, ref_kp = [], [], []
srcs = [(n, p) for n in a.excl for p in glob.glob(f"{PH}/{n}/**/*", recursive=True) if img_ok(p)]
srcs += [("raw:" + os.path.basename(p), p) for p in a.raw]
for n, p in srcs:
    im = load(p, 700)
    if im is None: continue
    kp, d = sift.detectAndCompute(im, None)
    if d is None or len(kp) < 30: continue
    refs.append((n, p)); ref_desc.append(d); ref_kp.append(np.float32([k.pt for k in kp]))
print("refs", len(refs), "cands", len(CANDS), flush=True)
lab = np.concatenate([np.full(len(d), i) for i, d in enumerate(ref_desc)])
flann = cv2.FlannBasedMatcher(dict(algorithm=1, trees=4), dict(checks=64))
flann.add([np.vstack(ref_desc).astype(np.float32)]); flann.train()
bf = cv2.BFMatcher(cv2.NORM_L2)
out = []
for c in CANDS:
    im = load(c, 1400)
    kp, d = sift_c.detectAndCompute(im, None)
    if d is None: continue
    m = flann.knnMatch(d.astype(np.float32), k=1)
    votes = np.bincount([lab[x[0].trainIdx] for x in m if x and x[0].distance < 180], minlength=len(refs))
    best = None
    for ri in np.argsort(-votes)[:6]:
        if votes[ri] < 8: break
        mm = bf.knnMatch(ref_desc[ri], d, k=2)
        good = [p[0] for p in mm if len(p) == 2 and p[0].distance < 0.75 * p[1].distance]
        if len(good) < 12: continue
        src = ref_kp[ri][[g.queryIdx for g in good]]; dst = np.float32([kp[g.trainIdx].pt for g in good])
        H, mask = cv2.findHomography(src, dst, cv2.RANSAC, 6.0)
        inl = int(mask.sum()) if mask is not None else 0
        if best is None or inl > best[0]: best = (inl, refs[ri][0], refs[ri][1])
    out.append({"cand": c, "inliers": best[0] if best else 0, "person": best[1] if best else None, "ref": best[2] if best else None})
    if best and best[0] >= 15: print(f"FLAG {os.path.basename(c)} <- {best[1]} ({best[0]} inliers) {os.path.basename(best[2])}", flush=True)
json.dump(out, open(a.out, "w"), indent=1)
print("done", len(out), "| flagged", sum(1 for r in out if r["inliers"] >= 15), flush=True)
