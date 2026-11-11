# YouTube thumbnails and A/B packaging (method as of 2026-11-01)

Used by the long-form YouTube preset and the /youtube skill. Built from OB's November repackaging round
(11 Title + thumbnail tests set 2026-11-01) and his notes on it.

## 1. Mirror a proven mega-outlier, then theme it

OB 11-01, after two rejected sets: "mirror really high winners and add our own stuff to the theme of it".

1. Pull the topic's biggest thumbnails (`yt_demand.py outliers --topic "<regex>"`) AND the biggest outliers
   overall, any niche (`yt_demand.py outliers --min-x 8 --min-views 1000000`).
2. Put them on one contact sheet next to his own top 12 long-form thumbnails (`yt_demand.py mine`,
   `maxresdefault.jpg`). His own winners first: body proof (shirt lift, before/after, calorie flip), huge white
   words with a red brush underline, the real product in frame, a dark room.
3. Pick 3 layouts that map onto props you really have (his frames, his photos, the real product, the person the
   video is about). Copy each layout closely: where the face sits, how many words, the arrow, the object.
4. Swap in his own stuff: his real frame from the take, his words, the product he talks about.
5. When you show the options, name the source video for each one with its views and its x (views over that
   channel's median), so he can judge the bet.

Rules that still hold:
- No AI imagery. Props are real photos (his own, Pexels, or Wikimedia Commons with the credit line in the
  description). Drawn labels, arrows and words are fine.
- 4 words max on the thumbnail, and none of them repeats a word in the title it is paired with. Check every
  pair word by word before building.
- Every claim on a thumbnail is something he says in the video. Note the source time for each.
- Frames come from the 4K camera file with his LUT, never from the YouTube export.
- Check every option at 168 px and 250 px wide (phone feed and sidebar) before it goes to him.

## 2. Clean his skin before anyone sees a thumbnail

OB 11-01: "get rid of acne in thumbnail ... if there is some on my face".

```
python3 -I ~/ob-editor/bin/clean_skin.py IN.png OUT.png X Y W H [compare.jpg]
```

- X Y W H is the face box: `~/ob-editor/bin/faces FRAME.png` prints x0 y0 x1 y1, so X = x0, Y = y0,
  W = x1 - x0, H = y1 - y0. Run it on the 4K frame, before any scaling or compositing.
- In a builder: `from clean_skin import clean; img, spots, px = clean(img, face_box)`.
- Spot removal only: small red spots are refilled from the skin around them, with a little grain. Eyes, lips
  and nose are never touched, and nothing bigger than a pimple is, so a flushed cheek stays.
- Always look at `compare.jpg`. Never "heal" whole forehead or cheek boxes: a broad heal smeared his face and
  washed out an eye on 11-01 (caught before sending).

## 3. A/B tests: keep the winner in slot 1

- YouTube Studio Test & compare picks the winner on watch-time share.
- When a test ends with "no clear winner", Studio keeps variant 1 live, even if another variant has the highest
  share. So "keep the winner" means: put the highest-share variant in slot 1 of the next test.
- Every new round = slot 1 (the winner, unchanged) + 2 new researched challengers.
- Save the old test's report before setting a new one, and log every round (date, slots, shares, CTR,
  impressions) next to the video's edit folder.
- Nothing goes to Studio before OB has seen the sheet and said yes.
- Read a test after 14 days. Packaging matters most in a video's first 2 to 3 weeks; old videos get few
  impressions and often end with no clear winner.

## 4. Up to 3 heavy builders at a time

Since 2026-11-03 the editing Mac is a Mac mini M5 Pro, 64 GB: up to 3 builders at once. History: the old 8 GB MacBook Air. On 2026-11-01 it hung and rebooted with three thumbnail builders
(4K frame grabs plus compositing) running beside a render, and every scratch file was lost.

- Run at most ONE heavy job at a time: 4K frame work, thumbnail builds, `thumb_frames` scans, renders.
  Never one beside another session's render. Queue batches and start the next when the last one reports.
- Keep working files and outputs on the edit drive (`<edit folder>/thumbs/...`), never only in /tmp, and save
  each finished thumbnail as it is done, so a crash costs one unit, not the batch.
