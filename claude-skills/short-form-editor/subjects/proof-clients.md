# Subject: client proof and photos of people

Read it when the script or his voice mentions clients, coaching, results or a client's name, and whenever any photo of a person goes on screen (a client, or OB himself). The numbers (windows, banned files, excluded names) live in `~/ob-editor/qc/formats.json` and the gate reads them; this file is the method.

**The rule.** When he says clients, coaching people, "over a decade", "hundreds of people" or a client's name, a consented client before/after is on screen within a second. The intro proof line and the CTA carry client transformations too. OB 11-07: "when i say clients you are suppose to put clients on screen for proof"; earlier: "Show client transformations as well for CTA and intro saying who I am". Missed five times (ledger M56): 10-23, 10-26, 10-29, 11-03, 11-07 ("i remember you saying you will always put client transformations ... yet its not there"). The old "clients only on the thousands line" rule (M19) is dead; every mention counts.

## 1. Find the lines (step in the story pass)
1. From the word-level transcript of the cut, list every line that says clients, coaching people, "over a decade", "hundreds/thousands of people" or a client's name, with its time. Add the intro proof line and the CTA even when they use other words.
2. Another coach's clients do not count ("coaches are scared they won't get clients"). His own do. When a line is borderline, it counts.
3. → `WORK/plan/client_lines.json`: `[{"t", "line", "kind": "client|decade|name|intro|cta", "proof_asset"}]`. Every row needs a `proof_asset` before the build.

## 2. Pick the proof
Bank (read-only; copy what you use into WORK): `<OB's private archive>`
- `before-after-FINAL/`: 48 vetted composites, each row one person's before | after. Crop a row to get a clean single-person pair. Some rows repeat a person.
- `clean-final/` (charts and coaching chats with names removed), `web-ready/` (before-after, coaching-wins, data-proof, singles, testimonial videos), `lovable-upload/` (a few files already named by client).
- Source of new pulls: your client photo album, only the new tail, with `~/ob-editor/bin/icloud_album.py`. Never download the whole album again.

How to pick:
- Match the line: a named client gets only their own photos. If they are missing, the line shows an unnamed consented pair and the delivery note says the named client's photos are missing. Never put someone else under a name.
- A GLP line shows only clients who really were on a prescribed GLP-1.
- Mix men and women across the video. The same person under another filename counts once: dedupe by person before balancing, and never show one person twice in a cut.
- Prefer front, side or back views. No thong back views (YouTube age restriction). Drop any pair whose two halves cannot be confirmed as the same person.
- Names on screen: first names only, and only where the established convention allows (per your consent list; all others uncaptioned). Footnote "Individual results vary." where a result is stated. An unverified client runs unnamed, never guessed.
- Facts about a client (age, kids, job, weight, time frame, quote) come from their own file opened this session, or are left out. Never invent one (memory `feedback_no_fabricated_client_facts.md`; the 2026-05-27 invented backstories).
- A number is on screen only when he says it, with the figure he says. No number from a photo, a chart or your own sum.
- Placement: on screen at the start of the line or within one second of it, beside him or on his chest, never over his face and never instead of him (`subjects/graphics.md`). On a "thousands" line, flash several pairs fast, each long enough to read.
- The photo is a real client photo, never AI-made or stock standing in for a client.

## 3. The consent screen
Who may be shown: every client in the bank except the names in `consent_excluded` in `formats.json` (Client Y, Client P). No photo of Client Y. Client P never by name and never by face; the "OB HEALTH" 1080x1350 carousel (faces scribbled) is likely hers, skip it. Skip any photo with a red dot or white blob over the face and any weight card that shows a client's name. OB 10-21: "assume every one is a yes on consent unless they said no explicitly", so a client who has not said no is usable; the excluded list is the ones who did.

Screen every proof image before it goes in:
```bash
~/OpenMontage/.venv/bin/python -I ~/ob-editor/bin/proof_screen.py WORK/qc/proof_screen.json --cands "WORK/proof/*.jpg"
```
It matches each candidate against the excluded clients' photo folders (SIFT, so a face inside a collage is caught). A hit is out. Eye-check every hit and every new person against the excluded clients' folders: the screen scores a different view of the same session low. Known never-use items and look-alike traps are in memory `reference_ob_curated_proof_library.md`; read its "never use" lists before picking from the bank. Re-run the screen whenever new proof is pulled.

Then the clearance ledger: `WORK/qc/clearance.csv`, one row per client image, with a screen score and an eye-check note. A row without both is unverified. Ship at zero unverified rows.

## 4. His own photos and clips
- Banned in every video, as lean, toned, shredded, "after" or dream-body: C1797, C1798, C1800, C1801, C1802 (the shirtless clips from 17 June 2025; C1799, feet on a scale, is fine for weigh-in beats). OB 10-29: "you showed me looking like actual shit wtf"; 11-07: "y do you always show me fat asf as toned and shredded so odd". The catalogue once labelled C1797 "lean year round"; ignore any such label.
- His lean photo is DSC07329 (`/Volumes/T7/OB-EDITS/C4415-fdoe-women/rev2/ob/DSC07329.jpg`, read only; copy it into WORK). Hold it static, no push. A newer photo only when he names it in chat. Otherwise a lean shot of someone else (licensed, native resolution) or no physique shot. Clothed b-roll of him (gym, kitchen) is fine for story beats.
- Look at every photo before it goes in. Build one contact sheet of every person-photo in the cut, save it as `WORK/qc/contact_proof.jpg`, and view it. In `WORK/BREAKDOWN.md` list each image: file, who, source, "viewed". Check the sheet for repeats across events and for flagged people, not only per file. Memory `feedback_photo_view_first.md` has the history.
- Helper briefs carry this rule (it comes with `ob_job.py brief WORK`). A hand-written brief never bans client photos: that brief made a helper override the check on 10-23 and again on C4465 (11-10).

## 5. No barbell squats or deadlifts
No client visual (photo, clip, b-roll, stock) shows a barbell back squat or a deadlift, least of all as his recommendation. The gate's `assets` terms are `barbell_terms` in `formats.json`. His clients' plans use other lifts; RDLs are fine. When a pick is unclear from the thumbnail, open the clip and look.

## 6. How the gate checks it, and what overrides it
Tag every client overlay in the events file (`WORK/events_resolved.json`) with `"client_proof": true` and its `edit_in` / `edit_out` (a Progress Photos or Client & Testimonial file path also counts). Reels and ads have no engine events file: write it yourself, one event per client overlay, times in the finished file: `{"events": [{"id": "c1", "type": "photo_overlay", "edit_in": 4.2, "edit_out": 6.5, "client_proof": true, "folder": DIR, "items": [[FILE]]}]}` (`qc_assets.py build` reads the same file). Then:
```bash
python3 -I ~/ob-editor/bin/ob_job.py gate WORK FILE
```
The `clients` check hears every client line in the finished cut and FAILs each one with no client overlay running from one second before the line to three seconds after its start. It needs the events file: without it the check cannot run, and a check that cannot run is a FAIL here. Aim for the one-second rule, not the gate's edge. The reviewer checklist (`~/ob-editor/qc/REVIEW-CHECKLIST.md`, ids R01 to R30) repeats it from the picture side.

Overrides: OB's own words quoted with the date, or for a false positive the transcript time as `proof`, written in `WORK/qc/gate_overrides.json`. The editor's own brief, a missing photo, or "the check is wrong" is not OB's word. A missing photo is fixed with an unnamed consented pair (section 2). A line that is not about his clients but trips the check is a false positive: prove it with the transcript time and fix the check with a fixture (`subjects/qc.md`).

## Traps
- A brief banning "client photos" (10-23, 11-10): the brief is wrong, the rule stands.
- Proof only in the middle: the intro and the CTA were skipped at 11-07 ("yet its not there"). The gate sees them only if the lines are heard; check the list in step 1 by hand.
- A named client with no photos of their own: unnamed pair, noted at delivery.
- A collage that holds an excluded person: screen every collage, not only the singles.
- The same woman twice under two filenames: dedupe.
- A reviewer's or helper's statement about what a client eats or looks like is a lead; open the client's own file first.
