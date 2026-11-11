"""Split-screen geometry for reaction edits at 4K (3840x2160): one source of truth for the stills,
the mockups and the render.

Doctor Mike's layout, mirrored for OB (2026-10-16): the clip sits on the RIGHT. OB watches his screen
down and to frame-right, so with the clip on that side he looks at it.
"""
W, H = 3840, 2160
OB_X, OB_W = 0, 2505            # OB panel on the canvas, flush left
OB_SRC_X = 668                  # left edge of the OB crop in the camera frame (crop width = OB_W)
CLIP_X, CLIP_W = 2565, 1215     # clip panel: 60 px gap after OB, 60 px right margin

# Dr. Mike Israetel's (RP) frame, OB 2026-11-03 (C4407): OB full frame; the clip in a white-bordered box in the top corner
# on the side he looks to (top right at the desk set). 16:9 clips: PIP_W wide; 9:16 clips: PIP_VH tall; never cropped.
PIP_W, PIP_VH, PIP_B, PIP_M = 2000, 1960, 26, 60     # box width (16:9), box height (9:16), white border, margin from the edges (OB 11-03: "still bigger")
# OB 11-03: "Make them bigger, don't cover me": under the box his frame is punched in from the left (crop from x=PIP_D, top
# anchored, scaled back to 4K: x1.185), which moves him left. Measured with Apple Vision person masks on every C4407 clip shot
# (bin/person_extent): the 1720 box clears his body by 101 px or more in all of them.
PIP_D = 950   # x1.329 (11-03 "still bigger": 2000 box, clears him by 71 px or more in every C4407 clip shot)
PIP_FONT = "~/ob-editor/fonts/BigShoulders/BigShouldersDisplay[wght].ttf"
