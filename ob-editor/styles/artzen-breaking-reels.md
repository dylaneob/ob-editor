# Style card: Artzen "Breaking Reels" (@artzenmedia, reel DfE7jMLTLSx, 2026-10-29) -> OB FDOE / LEGIT series
Source study: T7 artzen-box-flash-effect-study-2026-10-29.pdf. Watched by frames 2026-10-29 (download is 360x640, 51 s).

## Anatomy (observed)
- 0-8 s DEMO FIRST: source clip as a rounded inset, LEFT ~55% width, y ~38-90%; eye icon + view count ("163K") bottom-left of inset = proof badge.
  Handwritten label above inset ("HOW TO MAKE THIS..."). Host seated RIGHT, leaning in.
  DEPTH LAYER: host's cap/head sits IN FRONT of the inset's top-right corner; hands/arms stay BEHIND it.
- Captions: one word at a time, white handwritten font, centre-low (y ~68-72%). No box except in the demo effect.
- 8-12 s SERIES FRAME: spoken "This is <series>, the series where I ..." + chalkboard title card: logo (white bold word in an outline box + red script sub-word),
  eye-icon view counter that climbs (719K -> 985K -> 1M) and a hand-drawn zigzag line that rises.
- 12 s+: host talking head (handwritten one-word captions), one keyword overlay per step (white serif / red-on-white box),
  then screen recording on top with host in a ROUNDED PiP frame below.
- Close: about 4 s, one CTA line, "Peace." Total ~51 s.

## Box flash caption (the effect taught)
Each word: 2 frames as a solid white box (text background on, white, opacity 100), then plain white text until the next word. Single-word timing from transcription.

## OB transfer (FDOE reviews = LEGIT series)
- Inset = the FDOE creator's clip with HER real view count; label e.g. "HOW MANY CALORIES IS THIS?"; OB's hat + face in front, arms behind (person mask ∩ head region, composited above the inset).
- Series frame = LEGIT (his existing series name, never "Breaking reels"); chalkboard card, climbing counter of his real numbers only.
- Middle = Cronometer screen on top, OB in rounded PiP below; one keyword overlay per meal.
- Close = locked closer. No keyword-asset funnel. Captions: test box flash vs current style on skip rate, one variable.

## Measured details (1080x1920 download, 2026-10-29) - match these
- Cut map (scene detect 0.08): opening inset 0-7.3 s (inset cuts are the SOURCE's own cuts: 1.4, 1.8, 2.3, 2.7, 3.7, 5.4, 6.3);
  7.3-7.9 burst of 1-3 frame flash cuts into the title card; title card 7.9-10.0 (2.1 s); full-screen host 10.0-13.5 with keyword overlays;
  screen + PiP section 13.6-46.9 (alternating with full-screen host for spoken beats); close 46.9-51 (follow card).
- OPENING inset: x ~3-55% of width, y ~39-91%; corner radius ~2% width; eye icon + count bottom-left inside inset (white, small bold).
  Label above inset, left-aligned, handwritten caps, 2 staggered lines, white, ~3.5% height.
  Depth: cap brim AND face (nose, cheek) overlap the inset's top-right corner; shoulder/arm continue BEHIND the inset edge.
- TITLE CARD: chalkboard texture (dark grey, chalk dust), logo enters oversized and settles (scale-down slam), eye counter climbs, chalk zigzag line draws up-right.
  Captions continue over it (same handwritten word style).
- SCREEN + PiP: background near-black. Screen recording top ~0-48% (UI panels, rounded). PiP box x 104-973 px (9.6% side margins, 80.5% wide),
  top edge at y 1138 (59.3%), runs off the bottom; corner radius ~40 px; ~4 px glowing border, colour sampled from the footage (cyan/blue on top, gold on the left edge).
  HEAD POP-OUT: cap top at y ~958, so head + cap break ~180 px (9.4% of height) above the box top; the head is in front of the border too.
  Needs headroom in the shot: hat fully in frame with space above.
- Captions: single word, white handwritten, ~70 px cap height, centred x 50%, y ~72%; on full-screen host they sit on the chest.
- Keyword overlays: red italic serif word on a white rectangle above the head (y ~25%); plain white sans phrase typed on (top-left, y ~19%) for the explained line.
- Close: comment CTA graphic (red handwritten small word + big white bold word in quotes + hand cursor tap); end card = avatar circle + name + Follow button clicked by a cursor.
- Grade: warm daylight, teal window highlights; host lit soft from the window side.

- 2026-11-04: OB sent the box-flash tutorial again (instagram.com/reel/DfUmDI2Py8Z, Breaking Reels, "Yo, this text effect is so clean"). Already built: `~/ob-editor/bin/box_flash.py` (10-29). Re-measured: 2 frames per word, cream-white box at the word's own size, words stack line by line; Artzen mixes an italic serif with a bold sans.
- 2026-11-04 upgrade: `box_flash.py` now stacks words in blocks (default `--layout stack`: 10 characters a line, 3 lines, centred at y 0.62, clear of the IG bottom band), one baseline per line, brand font and shadow. Demo on C4413 121.5-129.2 s passed the gate.
