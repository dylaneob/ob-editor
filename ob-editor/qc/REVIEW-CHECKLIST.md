# Review checklist: what "right" means for an OB video (2026-11-10, extended in the editor rebuild the same day)

Used by the `video-reviewer` agent (`~/.claude/agents/video-reviewer.md`) on every render before OB sees it.
OB 11-10: "add this to all tasks" (the verification loop: make it, look at it, compare to what good looks like, fix).
The QC gate checks what code can measure. This list is the rest: what only eyes on the frames catch.
**Any note OB gives twice goes on this list (or into the gate) the same day.** Each line has an id (R01...) the ledger points to.

A render passes only if the gate has no FAIL and every line below is true. Each failure gets a timestamp, what is wrong, and the fix.
Numbers (caps, levels, bands) come from `~/ob-editor/qc/formats.json` for the job's route: `python3 -I ~/ob-editor/bin/ob_job.py rules ROUTE`.

## The gate (run it or read its report)
- With a WORK folder: `python3 -I ~/ob-editor/bin/ob_job.py gate WORK FILE` (every input, strict for the route). Zero FAIL; a check
  that did not run is a FAIL. Without one (older jobs): `python3 -I ~/ob-editor/bin/qc_gate.py FILE --script SCRIPT --work WORK`.
  Never a bare re-run with fewer inputs than the render had: it hides checks.
- Every WARN has an answer in `WORK/qc/warn_answers.json`. Read each answer: is it true for this file? An override must quote OB.

## Eyes on the frames
- R01 No text, caption, label or graphic over his face (M05), incl. his cap and chin.
- R02 Text sits outside the Instagram bands for the route (M12); ads and boosted posts use the stricter ad zone.
- R03 Captions say exactly what he said; spot-check 5 caption frames against the transcript (M25).
- R04 Hook text on frame 1, readable at phone size (scaled to 360 px wide), within the route's word limit (M10). Not on someone else's clip.
- R05 He is on screen every frame he talks; no full-screen overlay over his speech in a reel, ad or long-form video (M37, M87; OB 11-11 "you just put a bench, im not in the overlay"): every cover shows him, an empty bench or stock alone fails. Unless OB asked for a full-overlay format by name.
- R06 No black or near-black backgrounds, panels or bars; the frame is filled (M38).
- R07 **Someone else's clip plays whole and untouched**: first frame to last, no trims, text, stamps, music, grade, zoom or speed change. Only OB by green screen may sit over it (11-09).
- R08 A reaction shows the clip he reacts to while he watches it, and he is visibly watching (not scratching, not looking away) (M34, M47); a creator's voice never plays under his (M42).
- R09 Graphics land on his word (not before it).
- R10 **No text-only card.** Every overlay is footage, a real photo, a chart, a drawn object or 3D (M16, his most repeated note: "Again I hate boring just text slides").
- R11 Nothing looks AI-made or templated: no AI people, imagery, voice or music (M22, M28); no white bubble cards, flat gradient cards, pictogram people, flat stills pasted on a colour, placeholder cells. Compare with the slop table in `subjects/graphics.md` of the editor skill.
- R11b (OB 11-11, repeat note: "dont do the basic text bubbles you always do, dead give away you edited it", "be unique") UGC and ad text never sits in a plain rounded box, pill or bubble (captions, banners, labels). Text must look like the creator made it in-app (native IG/TikTok text styles) or like a deliberate, specific design for this ad. Same default caption look on every video = FAIL.
- R12 On-screen text: no em or en dashes, no "~", no "free", no "team" in text we wrote (M11). First person. Brand type (Big Shoulders Display, one yellow word), no boxes.
- R13 Client photos: consented only, first names only, never Client Y or Client P (M21, M56). When he says clients, coaching people, "over a decade" or a client's name, a client before/after is on screen within a second; the intro proof line and the CTA too.
- R14 His physique: never C1797 to C1802; the lean photo is DSC07329; no photo that makes him look worse than the line says (11-07).
- R15 No barbell squat or deadlift shown as his advice (RDLs fine) (M23).
- R16 No one-frame flashes, black frames, frozen frames, repeated-frame judder or half-second scraps between shots (M09, "glitchy").
- R17 Grade: highlights on his face not lifted (M18); skin has colour (not grey, not orange); inserts match his footage.
- R18 **No zooming**: no punch-ins, pushes or zoom kicks on him or on stills (UGC ads excepted) (11-07).
- R19 Motion is smooth: nothing bounces, kicks or fidgets; nothing slides around without a reason (11-07).
- R20 Cutouts are clean (hair, hands, no halo, no blur box beside him); the background behind a cutout is the picture of that sentence, not random stock; nothing he wrote on a board is erased or blurred (11-06, 11-09).
- R21 His face and body are framed whole: not cut by the frame edge or a box edge, no dead space around him (M50).
- R22 B-roll shows what the line says (he is lifting, not setting up; the food he names) (10-28).

## Ears (from the transcript, the levels and the sound plan)
- R23 No "cut that, Claude" or retake left in (M03); no word cut off at any edge (M02, M26); no line of his missing against the script or raw take unless he cut it.
- R24 No dead air: joins between his lines and voiceless stretches within the route's limits; no audible breaths left as pauses (M44, M48).
- R25 His voice is clearly over the music; master loudness and true peak within the route's numbers (M06).
- R26 Music: the record `WORK/audio/music_candidates.json` shows three or more scored tracks and the pick is its top one (or says why not); it is not a track used on a recent edit; teaching, reaction and FDOE edits sound upbeat and bright per the pick's tags, never moody (M57, M58); the bed sits at the route's level and fades out by the last frame.
- R27 Sound effects: from the bank, each tied in the plan to something that lands or moves on screen and described by what that thing does; no recording repeated past the route's cap; at the route's rate per minute; none in the first half second; none of the banned families (Kenney ticks, glitch) (M17, M59).

## Format and delivery
- R28 Short form is 1080x1920; one file per edit, no extra copies unless OB asked (M08, M45).
- R29 The creator's format is matched where the plan says it is: `WORK/qc/format_check.json` (ours against the creator's measured numbers) has no failed row.
- R30 **Against the bar.** Open `~/ob-editor/qc/gold.json`, find this format's approved exemplar and his words about it, and compare: pace, how much is on screen, type size, music level, sound-effect rate. Say where this render falls short of what he approved. No exemplar for the format: say so and compare with the creator reference.
