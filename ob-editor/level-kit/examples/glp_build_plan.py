"""The GLP full edit's plan (level kit, ~/ob-editor/level-kit). Writes everything except the pieces into plan.json, which
already holds pieces (recut + verified: the test's 12 pieces locked, then the rest of edl.json butt-joined, n2 split inside
its 0.32 s pause, p2's tail kept at the EDL's 2191.99). 0-17.31 s is the approved level test, cue for cue (its comp.py
constants); only the grid cells change for unisex. Run: python3 -I build_plan.py"""
import json, os
HERE = os.path.dirname(os.path.abspath(__file__)); PLAN = os.path.join(HERE, "plan.json")
p = json.load(open(PLAN))
SCR = "/private/tmp/claude-501/-Users-YOU/fc9372ce-cc7d-433e-8cbd-d868474efc17/scratchpad"
BR = "/Volumes/T7/b roll/"; ST = "/Volumes/T7/OB-EDITS/2026-11-05-scripts/GLP-shot/_work/stock/"
PEN, BLK1 = SCR + "/glp/pen", SCR + "/glp/blocks"          # the level test's Blender renders (pen.py, blocks.py), reused as-is
REGAIN = SCR + "/full/work/regain"                          # level-kit blender/blocks.py, mode fill (regain_spec.json)


def c(name, off=0.0): return {"cue": name, "off": off} if off else name
def w(word, line, off=0.0, n=1, at="s"): return {"word": word, "line": line, "off": off, "n": n, "at": at}


p["word_patches"] = [
    {"match": "GOPs", "cam_s": 2082.18, "w": "GLPs"},                       # Apple heard GLPs as GOPs
    {"match": "It", "cam_s": 2176.02, "s": 2176.30, "e": 2176.40},          # whisper + level: "It" starts at 2176.31
    {"match": "1st", "cam_s": 2198.34, "w": "first"},
    {"match": "and", "cam_s": 2198.64, "w": "in"},                          # whisper medium: "protein first in every meal"
    {"match": "1st", "cam_s": 2241.84, "w": "first"},
    {"match": "comment", "cam_s": 2313.18, "s": 2314.32}]                   # said once, after the pause the cut removes
OPEN = {  # the level test's cues (GLP-shot/_work/level/comp.py, tight clock), kept to the millisecond
    "T_PEN_LAND": 0.60, "T_GRID": 1.41, "T_DISC2": 2.58, "T_DISC0": 2.635, "T_THESE": 2.885, "T_NOTHING": 3.54, "T_DISC1": 4.19,
    "T_JOB": 4.24, "T_ONE": 4.49, "T_TURNS": 5.15, "T_HUNGER": 5.51, "T_DOWN": 5.87, "T_ELSE": 6.2, "T_PLATE": 7.345, "T_ZOOM0": 7.6,
    "T_N1": 7.7, "T_PROTECT": 8.601, "T_MUSCLE1": 8.901, "T_STAGE": 9.23, "T_FAST": 10.007, "T_SUB": 10.676, "T_FIX": 11.46,
    "T_LIFT": 12.239, "T_2": 12.479, "T_3": 12.779, "T_LOOK": 13.32, "T_TONED": 14.396, "T_STRONG": 14.996, "T_END": 15.656,
    "T_NOT": 16.11, "T_SAGGY": 16.306, "T_SOFT": 16.846,
    "C_TL": 1.496, "C_TR": 1.676, "C_BR": 1.856, "C_BL": 2.036, "S_TL": 13.324, "S_TR": 13.394, "S_BR": 13.464, "S_BL": 13.534}
NEW = {
    "T_N2": w("Number", "n2"), "T_ZOOM2": c("T_N2", -0.10), "T_FEED": w("feed", "n2"), "T_APPIN": w("shrinks", "n2", -0.12),
    "T_SHRINKS1": w("shrinks", "n2"), "T_APPETITE": w("appetite.", "n2"), "T_SO_P1": {"line": "p1"}, "T_PROTEIN1": w("protein", "p1"),
    "T_SHRINKS2": w("shrinks", "p1"), "T_WITH": w("with", "p1"), "T_FIRST": w("first.", "p2"), "T_P3": {"line": "p3"},
    "T_PROTEIN2": w("protein", "p3"), "T_1ST": w("first", "p3"), "T_EVERY": w("every", "p3"), "T_REST": w("rest.", "p3"),
    "T_N3A": {"line": "n3a"}, "T_NUM3": w("3", "n3a"), "T_NOBODY": w("nobody", "n3a"), "T_N3B": {"line": "n3b"}, "T_ZOOM3": c("T_N3B", -0.10),
    "T_HABITS": w("habits", "n3b"), "T_FOR": w("for", "n3b"), "T_LATER": w("later.", "n3b"),
    "T_REV": {"line": "rev"}, "T_REVIEW": w("review", "rev"), "T_AFTER": w("after", "rev"), "T_THEY": w("they", "rev"),
    "T_REGAIN_IN": c("T_THEY", -0.05), "T_60": w("60%", "rev"), "T_60LAND": c("T_REGAIN_IN", 1.15), "T_LOST": w("lost", "rev"),
    "T_1ST2": w("first", "rev"), "T_12": w("12", "rev"), "T_STAY": {"line": "stay"}, "T_STAYW": w("stay", "stay"), "T_OFF1": w("off", "stay"),
    "T_QUIET_L": {"line": "quiet"}, "T_QUIET": w("quiet", "quiet"), "T_BUILD": w("build", "quiet"), "T_ROUTINE": w("routine.", "quiet"),
    "T_HUNGER_L": {"line": "hunger"}, "T_HUNGER2": w("hunger", "hunger"), "T_COMES": w("comes", "hunger"), "T_BACK": w("back.", "hunger"),
    "T_MEAL_L": {"line": "meal"}, "T_MEALW": w("meal", "meal"), "T_STRUCT": w("structure,", "meal"), "T_DAILY": w("daily", "meal"),
    "T_WALK": w("walk.", "meal"), "T_WEEKLY": w("weekly", "walk"), "T_WEIGH": w("weigh", "walk"),
    "T_OFF_L": {"line": "off"}, "T_THESE2": w("these?", "off"), "T_NOT2": w("Not", "off"), "T_CTA": {"line": "cta"},
    "T_HIGH": w("high", "cta"), "T_LIST": w("list,", "cta"), "T_DIET": w("diet", "cta"), "T_TEMPLATES": w("templates", "cta"),
    "T_WORKOUT": w("workout", "cta"), "T_PLAN": w("plan,", "cta"), "T_COMMENT": w("comment", "cta"), "T_GLP": w("GLP,", "cta"),
    "T_SEND": w("send", "cta")}
p["cues"] = {**OPEN, **NEW}
p["cold_open_until"] = "T_GRID"
p["face"] = {"eye_x": 0.51, "eye_y": 0.305, "chin_y": 0.39, "box_bottom": 0.45}
p["layouts"] = {"COLD": [1.13, -93.0, 240.0], "GRID": [0.97, 33.0, 420.0], "STAGE": [0.85, 162.0, 603.0], "BIG": [1.10, -46.0, 360.0]}
p["layout_track"] = [[0, "COLD"], ["T_GRID", "GRID"], ["T_STAGE", "STAGE"], ["T_FIX", "GRID"],
                     ["T_REV", "STAGE"], ["T_STAY", "GRID"], ["T_CTA", "BIG"]]
p["camera"] = {
    "shots": [[0, 1.0, 1.035, "face"], ["T_GRID", 1.0, 1.012], ["T_DISC2", 1.0, 1.01], ["T_NOTHING", 1.08, 1.09, "face"], ["T_JOB", 1.0, 1.015],
              ["T_HUNGER", 1.06, 1.07, "face"], ["T_ELSE", 1.0, 1.01], ["T_PLATE", 1.08, 1.085, "face"], ["T_N1", 1.0, 1.0, "land"],
              ["T_PROTECT", 1.08, 1.09, "face"], ["T_STAGE", 1.0, 1.03], ["T_FIX", 1.0, 1.01], ["T_LIFT", 1.08, 1.085, "face"], ["T_3", 1.15, 1.16, "face"],
              ["T_LOOK", 1.0, 1.01], ["T_TONED", 1.08, 1.085, "face"], ["T_STRONG", 1.0, 1.03], ["T_NOT", 1.08, 1.09, "face"], ["T_SOFT", 1.0, 1.02],
              # item 2
              ["T_N2", 1.0, 1.0, "land"], ["T_FEED", 1.08, 1.09, "face"], ["T_APPIN", 1.0, 1.015], ["T_PROTEIN1", 1.06, 1.07, "face"],
              ["T_SHRINKS2", 1.0, 1.012], ["T_FIRST", 1.15, 1.16, "face"], ["T_P3", 1.0, 1.01], ["T_1ST", 1.08, 1.085, "face"],
              ["T_EVERY", 1.0, 1.012], ["T_REST", 1.06, 1.065, "face"],
              # item 3
              ["T_N3A", 1.0, 1.012], ["T_NOBODY", 1.08, 1.09, "face"], ["T_N3B", 1.0, 1.0, "land"], ["T_LATER", 1.06, 1.065, "face"],
              ["T_REV", 1.0, 1.03], ["T_REGAIN_IN", 1.0, 1.035], ["T_LOST", 1.06, 1.065, "face"], [c("T_1ST2", -0.05), 1.0, 1.01], ["T_12", 1.05, 1.06], ["T_STAY", 1.0, 1.01], ["T_OFF1", 1.06, 1.065, "face"],
              ["T_QUIET_L", 1.0, 1.012], ["T_ROUTINE", 1.08, 1.085, "face"], ["T_HUNGER_L", 1.0, 1.01], ["T_COMES", 1.1, 1.11, "face"],
              ["T_MEAL_L", 1.0, 1.01], ["T_WALK", 1.06, 1.065, "face"], ["T_WEEKLY", 1.0, 1.01], ["T_WEIGH", 1.08, 1.085, "face"],
              # close
              ["T_OFF_L", 1.0, 1.012], ["T_NOT2", 1.12, 1.13, "face"], ["T_CTA", 1.0, 1.02], ["T_HIGH", 1.06, 1.065, "face"],
              ["T_DIET", 1.0, 1.01], ["T_WORKOUT", 1.06, 1.065, "face"], ["T_COMMENT", 1.0, 1.01], ["T_GLP", 1.1, 1.11, "face"], ["T_SEND", 1.0, 1.025]],
    "zoom_through": [["T_ZOOM0", "T_N1", 1.085, 1.34], ["T_ZOOM2", "T_N2", 1.085, 1.34], ["T_ZOOM3", "T_N3B", 1.085, 1.34]],
    "kicks": [["T_PEN_LAND", 5.0, 9.0, 0.32], ["T_SUB", 7.0, 8.0, 0.30, 0.012], ["T_60LAND", 7.0, 8.0, 0.30, 0.012], [c("T_GLP", 0.05), 5.0, 9.0, 0.32]],
    "top_guard": [["T_GRID", c("T_JOB", 0.3), 256], [c("T_JOB", 0.3), c("T_ELSE", 0.2), 276], ["T_N1", "T_STAGE", 292], ["T_STAGE", "T_N2", 230],
                  ["T_N2", "T_APPIN", 292], ["T_APPIN", "T_N3A", 230], ["T_N3A", "T_REV", 292], ["T_REV", "T_OFF_L", 230],
                  ["T_OFF_L", "T_CTA", 390], ["T_CTA", None, 262]]}


def cascade(cue):
    return {q: c(cue, d) for q, d in (("TL", 0.004), ("TR", 0.074), ("BR", 0.144), ("BL", 0.214))}


p["cells"] = {
    "B_TL": {"src": BR + "C1424.MP4", "in": 27.0, "dur": 7.4},                         # OB: seated dumbbell curl
    "B_TR": {"src": ST + "pexels/8090811.mp4", "in": 0.3, "dur": 7.4, "cx": 0.55},      # a woman pouring her shake
    "B_BR": {"src": BR + "C4010.MP4", "in": 4.6, "dur": 7.4},                          # OB: stepping onto his scale
    "B_BL": {"src": ST + "mixkit/4823.mp4", "in": 2.0, "dur": 7.4},                    # a woman on her walk
    "M_TL": {"src": BR + "C3445.MP4", "in": 18.0, "dur": 6.6},                         # OB: overhead press machine
    "M_TR": {"src": ST + "mixkit/52111.mp4", "in": 4.0, "dur": 6.6, "cx": 0.45},       # a woman: dumbbell press
    "M_BR": {"src": BR + "C3400.MP4", "in": 30.0, "dur": 6.6},                         # OB: leg press
    "M_BL": {"src": ST + "pexels/5983521.mp4", "in": 1.0, "dur": 6.6},                 # a woman: lat pulldown
    "P_TL": {"src": BR + "copy_9A8A5639-0929-4282-B59A-A491F060796F.mov", "in": 6.0, "dur": 4.8},  # OB: tank, back double biceps
    "P_TR": {"src": ST + "mixkit/52102.mp4", "in": 2.0, "dur": 4.8},                   # a strong woman, hands on hips
    "P_BR": {"src": BR + "C3448.MP4", "in": 92.0, "dur": 4.8},                         # OB: gym, front
    "P_BL": {"src": ST + "mixkit/40246.mp4", "in": 0.5, "dur": 4.8},                   # a woman: box jump (vertical)
    "PR_TL": {"src": ST + "mixkit/42909.mp4", "in": 0.0, "dur": 9.8, "speed": 0.85},   # eggs into the pan (her hands)
    "PR_TR": {"src": BR + "C3085.MP4", "in": 30.0, "dur": 9.8},                        # OB: his protein shake
    "PR_BR": {"src": ST + "pexels/4399560.mp4", "in": 0.0, "dur": 9.8},                # chicken on the grill
    "PR_BL": {"src": ST + "mixkit/26095.mp4", "in": 0.0, "dur": 9.8, "speed": 0.64},   # a woman eating a protein plate (vertical)
    "B2_TL": {"src": BR + "C1424.MP4", "in": 20.0, "dur": 2.7}, "B2_TR": {"src": ST + "pexels/8090811.mp4", "in": 5.5, "dur": 2.7, "cx": 0.55},
    "B2_BR": {"src": BR + "C4010.MP4", "in": 8.0, "dur": 2.7}, "B2_BL": {"src": ST + "mixkit/4823.mp4", "in": 7.2, "dur": 2.7},
    "H_TL": {"src": ST + "pexels/6894121.mp4", "in": 0.0, "dur": 10.2, "speed": 0.75},  # meal-prep boxes
    "H_TR": {"src": "/Volumes/T7/C2988.MP4", "in": 1.0, "dur": 10.2},                  # OB: walking Tokyo
    "H_BR": {"src": ST + "pexels/4540695.mp4", "in": 0.0, "dur": 10.2},                # a weigh-in, feet on the scale
    "H_BL": {"src": ST + "pexels/3048200.mp4", "in": 0.0, "dur": 10.2, "cx": 0.55},    # a woman checking her tracker
    "H2_TL": {"src": ST + "pexels/6894121.mp4", "in": 0.0, "dur": 9.4, "speed": 0.83},  # meal-prep boxes (855922 read as a blur)
    "H2_TR": {"src": "/Volumes/T7/C2988.MP4", "in": 13.0, "dur": 9.4},
    "H2_BR": {"src": ST + "pexels/4540695.mp4", "in": 7.9, "dur": 9.4},
    "H2_BL": {"src": ST + "pexels/3048200.mp4", "in": 3.6, "dur": 9.4, "cx": 0.55},
    "B3_TL": {"src": BR + "C1424.MP4", "in": 36.0, "dur": 9.2}, "B3_TR": {"src": ST + "pexels/8090811.mp4", "in": 0.0, "dur": 9.2, "speed": 0.9, "cx": 0.55},
    "B3_BR": {"src": BR + "C4010.MP4", "in": 4.6, "dur": 9.2}, "B3_BL": {"src": ST + "mixkit/4823.mp4", "in": 0.5, "dur": 9.2}}
SETS = ["B", "M", "P", "PR", "B2", "H", "H2", "B3"]
p["grid"] = {
    "sets": {s: {q: f"{s}_{q}" for q in ("TL", "TR", "BR", "BL")} for s in SETS},
    "wall_at": "T_GRID",
    "frame_base": {"B": 1.39, "M": 7.56, "P": 13.23, "PR": c("T_N2", -0.14), "B2": c("T_N3A", -0.09), "H": c("T_N3B", -0.14),
                   "H2": c("T_STAY", -0.09), "B3": c("T_OFF_L", -0.09)},
    "schedule": [{"set": "B", "at": {"TL": "C_TL", "TR": "C_TR", "BR": "C_BR", "BL": "C_BL"}},
                 {"set": "M", "at": {q: "T_N1" for q in ("TL", "TR", "BR", "BL")}, "style": "land"},
                 {"set": "P", "at": {"TL": "S_TL", "TR": "S_TR", "BR": "S_BR", "BL": "S_BL"}},
                 {"set": "PR", "at": {q: "T_N2" for q in ("TL", "TR", "BR", "BL")}, "style": "land"},
                 {"set": "B2", "at": cascade("T_N3A")},
                 {"set": "H", "at": {q: "T_N3B" for q in ("TL", "TR", "BR", "BL")}, "style": "land"},
                 {"set": "H2", "at": cascade("T_STAY")},
                 {"set": "B3", "at": cascade("T_OFF_L")}],
    "seams_from": "C_BL",
    "pops": [{"q": "ALL", "cue": c("T_ELSE", 0.04), "amp": 0.045, "stagger": 0.08}, {"q": "ALL", "cue": "T_LIFT", "amp": 0.04, "stagger": 0.05},
             {"q": "ALL", "cue": "T_THESE", "amp": 0.03, "stagger": 0.06}, {"q": "TR", "cue": c("T_PLATE", -0.02), "amp": 0.07},
             {"q": "TL", "cue": c("T_PROTEIN2", -0.02), "amp": 0.07}, {"q": "TR", "cue": c("T_1ST", -0.02), "amp": 0.07},
             {"q": "BR", "cue": c("T_EVERY", -0.02), "amp": 0.07}, {"q": "BL", "cue": c("T_REST", -0.02), "amp": 0.07},
             {"q": "ALL", "cue": w("then", "p3"), "amp": 0.03, "stagger": 0.05},
             {"q": "ALL", "cue": "T_BUILD", "amp": 0.035, "stagger": 0.06},
             {"q": "TL", "cue": c("T_MEALW", -0.02), "amp": 0.07}, {"q": "TR", "cue": c("T_DAILY", -0.02), "amp": 0.07},
             {"q": "BL", "cue": c("T_WALK", -0.02), "amp": 0.05}, {"q": "BR", "cue": c("T_WEIGH", -0.02), "amp": 0.07},
             {"q": "ALL", "cue": c("T_COMMENT", 0.1), "amp": 0.04, "stagger": 0.05}],
    "outlines": [{"q": "TR", "set": "B", "on": c("T_PLATE", -0.05), "off_from": c("T_N1", -0.25), "off_to": c("T_N1", -0.05)},
                 {"q": "TL", "set": "PR", "on": c("T_PROTEIN2", -0.05), "off_from": c("T_N3A", -0.25), "off_to": c("T_N3A", -0.05)},
                 {"q": "TL", "set": "H2", "on": c("T_MEALW", -0.05), "off_from": c("T_OFF_L", -0.25), "off_to": c("T_OFF_L", -0.05)},
                 {"q": "TR", "set": "H2", "on": c("T_DAILY", -0.05), "off_from": c("T_OFF_L", -0.25), "off_to": c("T_OFF_L", -0.05)},
                 {"q": "BR", "set": "H2", "on": c("T_WEIGH", -0.05), "off_from": c("T_OFF_L", -0.25), "off_to": c("T_OFF_L", -0.05)}],
    # rack focus: the two test beats, then 'not saggy and soft' over a blur (unisex rule: the melt never sits on a real
    # person's body), the bars, the receipts + 3D beat, the hunger callback
    "rack": [{"in": "T_JOB", "out": "T_ELSE", "blur": 15, "dim": 0.42}, {"in": "T_STAGE", "out": "T_FIX", "blur": 11, "dim": 0.26},
             {"in": "T_NOT", "out": "T_N2", "blur": 14, "dim": 0.46, "spring_in": [3.6, 0.8]},
             {"in": "T_APPIN", "out": "T_P3", "blur": 13, "dim": 0.40}, {"in": "T_REV", "out": "T_STAY", "blur": 11, "dim": 0.30},
             {"in": "T_QUIET_L", "out": "T_MEAL_L", "blur": 10, "dim": 0.32}],
    "top_grade": [["T_GRID", c("T_JOB", 0.29), 700, 0.55], ["T_N3A", "T_REV", 660, 0.45], ["T_STAY", "T_QUIET_L", 660, 0.45],
                  ["T_MEAL_L", "T_OFF_L", 700, 0.5], ["T_OFF_L", 99, 760, 0.5]]}
p["elements"] = [
    # ---- depth (behind his matte) ----
    {"type": "title", "id": "title", "layer": "depth",
     "lines": [{"words": ["WHAT", "THE", "SHOT"], "size": 140, "colors": ["white"] * 3, "top": 252, "t0": -0.20, "stagger": 0.06, "rise": 46, "spring": [3.0, 0.55], "grow": 0.08, "fade": 0.07},
               {"words": ["DOESN'T", "DO"], "size": 236, "colors": ["white", "yel"], "top": 478, "t0": 0.15, "stagger": 0.12, "rise": 210, "spring": [2.5, 0.58]}],
     "dock": {"cue": "T_GRID", "scale": 0.62, "top": 264}, "lift": {"cue": "T_JOB", "dy": 760}, "gone": c("T_JOB", 0.6), "drift": 8,
     "sub": {"text": "I SELL NONE OF THESE. NOT MEDICAL ADVICE.", "size": 34, "in": "T_DISC0", "out": "T_DISC1", "y": 728.8}},
    {"type": "object3d", "id": "pen", "layer": "depth", "stage_from": "T_JOB", "frames": PEN, "len_px": 1300.0,
     "drop": {"t": 0.36, "from": [540, -240, 640], "to": [540, 420, 640], "spring": [2.4, 0.70], "rot0": -16, "rot_spring": [2.0, 0.5]},
     "dock_title": "title", "hero": {"cue": "T_JOB", "to": [540, 405, 880], "spring": [2.0, 0.62], "kick": -9, "wobble": 2.6},
     "exit": {"cue": "T_ELSE", "d": [760, -980], "rot": -38, "spring": [2.4, 0.9]}, "until": c("T_ELSE", 0.45),
     "play": {"t0": 0.36, "after": 2.0, "rate_after": 0.6}},
    {"type": "depth_word", "layer": "depth", "text": "STRONG", "size": 300, "color": "yel", "top": 548, "rise": "T_STRONG", "stagger": 0.035,
     "sweep": "T_END", "sag": "T_SAGGY", "soft": "T_SOFT", "out": c("T_ZOOM2", -0.05)},
    # ---- stage (in front of him, above his head): item 1 as the test ----
    {"type": "text_pop", "text": "ONE JOB", "size": 76, "weight": "Black", "track": 10, "y": 284, "in": c("T_ONE", -0.15), "rise": 30, "spring": [3.0, 0.62], "out": {"cue": "T_ELSE", "dy": -700}},
    {"type": "bar", "label": "HUNGER", "in": c("T_TURNS", -0.1), "yc": 588, "levels": [["T_HUNGER", 0.2, 1.55, 0.72]], "arrow": {"from": "T_HUNGER", "bounce": "T_DOWN"}, "out": {"cue": "T_ELSE", "dy": -700}},
    {"type": "item_label", "num": "1.", "name": "MUSCLE", "in": "T_N1", "pulse": "T_MUSCLE1", "dock": "T_STAGE", "out": {"cue": c("T_ZOOM2", -0.06), "dy": 700}},
    {"type": "blocks3d", "frames": BLK1, "in": "T_STAGE", "out": "T_FIX", "y": 206, "scale": 1.10, "header": {"text": "OF THE WEIGHT LOST", "y": 254},
     "sources": {"after": c("T_FAST", 0.25), "x": 40, "y": 884, "lines": ["STEP 1 (N=83): LEAN 5.8 KG, FAT 9.3 KG LOST", "CLINICALTRIALS.GOV NCT03548935",
                                                                        "SURMOUNT-1 (N=160): ABOUT 25% OF LOSS LEAN", "LOOK ET AL., DIABETES OBES METAB 2025"]}},
    {"type": "chips", "items": list("MTWTFSS"), "tw": 92, "gap": 14, "yc": 628, "in": "T_2", "lit": {"0": c("T_2", 0.02), "3": c("T_2", 0.14)},
     "outlined": {"5": c("T_3", 0.02)}, "out": {"cue": "T_LOOK", "dy": -600}},
    # ---- item 2: protein ----
    {"type": "item_label", "num": "2.", "name": "PROTEIN", "in": "T_N2", "pulse": "T_FEED", "dock": "T_APPIN", "out": {"cue": c("T_N3A", -0.1), "dy": 700}},
    {"type": "bar", "label": "APPETITE", "in": "T_APPIN", "yc": 430, "levels": [["T_SHRINKS1", 0.25, 1.55, 0.72]], "arrow": {"from": "T_SHRINKS1", "bounce": "T_APPETITE"},
     "moves": [["T_FIRST", 580]], "out": {"cue": "T_P3", "dy": -700}},
    {"type": "bar", "label": "PROTEIN", "in": "T_SO_P1", "yc": 580, "levels": [["T_SHRINKS2", 0.25, 1.55, 0.72], ["T_FIRST", 1.0, 2.0, 0.5]],
     "arrow": {"from": "T_SHRINKS2", "bounce": "T_WITH", "until": "T_FIRST"}, "moves": [["T_FIRST", 430]], "label_color": [["T_FIRST", "yel"]], "out": {"cue": "T_P3", "dy": -700}},
    {"type": "chips", "items": ["1. PROTEIN", "2. THE REST"], "tw": 340, "th": 96, "gap": 30, "yc": 548, "in": "T_PROTEIN2",
     "item_in": {"0": "T_PROTEIN2", "1": c("T_REST", -0.25)}, "lit": {"0": "T_1ST"}, "outlined": {"1": "T_REST"}, "text_size": 52, "track": 3, "fade_out": True, "out": {"cue": "T_N3A", "dy": -600}},
    # ---- item 3: habits for later ----
    {"type": "text_pop", "text": "3.", "size": 230, "color": "yel", "y": 300, "in": c("T_NUM3", -0.04), "spring": [3.2, 0.5], "stamp": 0.35,
     "pulse": "T_NOBODY", "box_after": {"w": 470}, "fade_out": True, "out": {"cue": c("T_ZOOM3", -0.04), "dy": -600}},
    {"type": "item_label", "num": "3.", "reveal": [["T_HABITS", "HABITS"], ["T_FOR", "FOR"], ["T_LATER", "LATER"]], "slot": "T_N3B", "tag": [46.0, 238.0, 0.22],
     "in": "T_N3B", "dock": "T_REV", "out": {"cue": c("T_OFF_L", -0.1), "dy": 700}},
    {"type": "card", "box": [90, 300, 990, 690], "in": c("T_REVIEW", -0.12), "kicker": ["SYSTEMATIC REVIEW + META-REGRESSION"],
     "title": ["TRAJECTORY OF WEIGHT REGAIN AFTER", "CESSATION OF GLP-1 RECEPTOR AGONISTS"], "title_size": 46,
     "foot": ["BUDINI ET AL., ECLINICALMEDICINE 2026", "48 STUDIES REVIEWED, 6 RCTS MODELLED (3,236 PEOPLE)"],
     "track": {"y": 318, "from_label": "STOPPED", "to_label": "1 YEAR LATER", "go": "T_AFTER", "f": 0.9, "d": 0.85}, "out": {"cue": c("T_THEY", -0.12), "dy": -900}},
    {"type": "blocks3d", "frames": REGAIN, "fix_white": False, "in": "T_REGAIN_IN", "out": "T_STAY", "y": 290, "scale": 1.22, "pulse": ["T_LOST"], "sweep": w("weight", "rev"),
     "header": {"text": "1 YEAR AFTER STOPPING", "y": 300},
     "sources": {"after": c("T_60", 0.3), "x": 60, "y": 962, "lines": ["BUDINI ET AL., ECLINICALMEDICINE 2026 (PMID 41938838)",
                                                                       "6 RCTS, 3,236 PEOPLE: 60% OF WEIGHT LOST REGAINED AT 1 YEAR"]}},
    {"type": "chips", "items": [str(i) for i in range(1, 13)], "cols": 3, "tw": 74, "th": 52,
     "gap": 10, "row_gap": 12, "x": 915, "yc": 440, "in": c("T_1ST2", -0.12), "stagger": 0.03,
     "lit": {str(i): c("T_1ST2", 0.06 * i) for i in range(12)}, "text_size": 32, "fade_out": True, "out": {"cue": "T_STAY", "dy": -600}},
    {"type": "object3d", "id": "pen2", "layer": "stage", "frames": PEN, "len_px": 1300.0,
     "drop": {"t": "T_STAY", "from": [540, -260, 600], "to": [540, 395, 600], "spring": [2.4, 0.70], "rot0": -16, "rot_spring": [2.0, 0.5]},
     "hero": {"cue": c("T_STAY", 0.6), "to": [540, 395, 600], "spring": [2.0, 0.62], "kick": -6, "wobble": 2.6},
     "exit": {"cue": "T_QUIET_L", "d": [-760, -980], "rot": 38, "spring": [2.4, 0.9]}, "until": c("T_QUIET_L", 0.45),
     "play": {"t0": "T_STAY", "offset": 2.2, "rate_after": 1.0}},
    {"type": "chips", "items": ["STAY ON IT", "GET OFF IT"], "tw": 360, "th": 96, "gap": 70, "yc": 560, "in": "T_STAYW",
     "item_in": {"0": "T_STAYW", "1": "T_OFF1"}, "outlined": {"0": "T_STAYW", "1": "T_OFF1"}, "text_size": 50, "track": 3, "fade_out": True, "out": {"cue": "T_QUIET_L", "dy": -600}},
    {"type": "text_pop", "text": "THE QUIET MONTHS", "size": 72, "weight": "Black", "track": 6, "y": 395, "in": c("T_QUIET", -0.1), "rise": 30,
     "spring": [3.0, 0.62], "pulse": "T_ROUTINE", "out": {"cue": "T_MEAL_L", "dy": -700}},
    {"type": "bar", "label": "HUNGER", "in": c("T_QUIET", -0.08), "yc": 560, "level0": 0.2, "levels": [[w("still", "hunger"), 0.32, 3.0, 0.35], ["T_COMES", 1.0, 1.9, 0.5]],
     "arrow": {"from": "T_COMES", "bounce": "T_BACK", "dir": "up"}, "out": {"cue": "T_MEAL_L", "dy": -700}},
    {"type": "checklist", "x": 150, "y": 330, "lh": 106, "size": 64, "out": {"cue": "T_OFF_L", "dy": -700},
     "rows": [{"text": "MEAL STRUCTURE", "in": c("T_MEALW", -0.1), "tick": "T_STRUCT"}, {"text": "DAILY WALK", "in": c("T_DAILY", -0.1), "tick": "T_WALK"},
              {"text": "WEEKLY WEIGH IN", "in": c("T_WEEKLY", -0.1), "tick": "T_WEIGH"}]},
    # ---- close ----
    {"type": "text_pop", "text": "NOT MY CALL", "size": 124, "y": 400, "in": "T_NOT2", "spring": [3.2, 0.5], "stamp": 0.45, "rot": -3, "underline": True,
     "fade_out": True, "out": {"cue": "T_CTA", "dy": -700}},
    {"type": "checklist", "x": 150, "y": 300, "lh": 100, "size": 60, "out": {"cue": c("T_COMMENT", -0.05), "dy": -700},
     "rows": [{"text": "HIGH PROTEIN LIST", "in": c("T_HIGH", -0.1), "tick": "T_LIST"}, {"text": "DIET TEMPLATES", "in": c("T_DIET", -0.1), "tick": "T_TEMPLATES"},
              {"text": "FULL WORKOUT PLAN", "in": c("T_WORKOUT", -0.15), "tick": "T_PLAN"}]},
    {"type": "keyword", "text": "GLP", "size": 300, "x": 540, "y": 460, "in": "T_GLP", "per": 0.09, "kicker": {"text": "COMMENT", "in": "T_COMMENT", "y": 272, "size": 64},
     "pulse": ["T_SEND"]}]
p["captions"] = {"below_box": 16, "y_min": 760, "y_max": 1436}
# OB 11-06 (on A/E): "needs background music, change up sound effects, I also hated that sound effect you used". The Kenney
# ticks were 9-11 of A's and E's 20-26 hits, so they are gone; no file more than 3 times, families mixed; CC0 (Kenney), his
# Drive kit and the code-made kit only (the TAI pack is organic-only, so it would block an ad cut of this one).
p["music"] = {"track": "/Volumes/T7/funkavenue-feel-good-funk-anthem-572932.mp3", "start": 0.0, "rel_db": -16.0, "duck_db": 5.0,
              "cuts": [["T_NOT", "T_N2"]],   # dead under the punch line "Not saggy and soft.", back on "Number two"
              "licence": "Pixabay Content License, https://pixabay.com/music/funk-feel-good-funk-anthem-572932/ (OB saved it to the T7 root; "
                         "page checked 2026-11-06: no AI-generated label). Four other Pixabay tracks in music/pixabay/ carry 'AI generated' labels."}
p["sfx"] = [  # each aligned on its own peak; db = its loudest 100 ms vs his speech level
    {"file": "sfx_real/click_3.wav", "cue": "T_PEN_LAND", "db": -22, "why": "pen lands (the test's click: its peak sits at its start, clear of the first 0.5 s)"},
    {"file": "sfx_real/swipe_1.wav", "cue": c("T_GRID", 0.016), "db": -23, "why": "pull back into the grid"},
    {"file": "sfx_real/pop_1.wav", "cue": "C_TL", "db": -26, "why": "cascade TL"}, {"file": "sfx_real/pop_2.wav", "cue": "C_TR", "db": -26, "why": "cascade TR"},
    {"file": "sfx_real/pop_3.wav", "cue": "C_BR", "db": -26, "why": "cascade BR"}, {"file": "sfx/pop_1.wav", "cue": "C_BL", "db": -26, "why": "cascade BL"},
    {"file": "sfx_ob_drive/whoosh.mp3", "cue": c("T_N1", 0.031), "db": -22, "why": "zoom into 1. MUSCLE"},
    {"file": "sfx_ob_drive/sub_drop_boom.mp3", "cue": "T_SUB", "db": -20, "why": "the lean numbers land"},
    {"file": "sfx_ob_drive/whoosh.mp3", "cue": c("T_N2", 0.031), "db": -22, "why": "zoom into 2. PROTEIN (music back)"},
    {"file": "sfx_ob_drive/flick.mp3", "cue": "T_FIRST", "db": -24, "why": "protein jumps to first"},
    {"file": "sfx_real/swipe_2.wav", "cue": c("T_N3A", 0.016), "db": -23, "why": "cascade back: the number 3 open loop"},
    {"file": "sfx_ob_drive/whoosh.mp3", "cue": c("T_N3B", 0.031), "db": -22, "why": "zoom into 3. HABITS FOR LATER"},
    {"file": "sfx_ob_drive/sub_drop_boom.mp3", "cue": "T_60LAND", "db": -20, "why": "60% lands"},
    {"file": "sfx_real/paper_1.wav", "cue": "T_STRUCT", "db": -26, "why": "meal structure ticked"},
    {"file": "sfx_real/paper_2.wav", "cue": "T_WALK", "db": -26, "why": "daily walk ticked"},
    {"file": "sfx_real/paper_3.wav", "cue": "T_WEIGH", "db": -26, "why": "weekly weigh in ticked"},
    {"file": "sfx_real/swipe_3.wav", "cue": c("T_OFF_L", 0.016), "db": -23, "why": "cascade back to the home grid"},
    {"file": "sfx_ob_drive/mouse-click.mp3", "cue": "T_LIST", "db": -26, "why": "protein list ticked"},
    {"file": "sfx_ob_drive/camera-click.mp3", "cue": "T_TEMPLATES", "db": -26, "why": "diet templates ticked"},
    {"file": "sfx_real/click_1.wav", "cue": "T_PLAN", "db": -26, "why": "workout plan ticked"},
    {"file": "sfx_ob_drive/flash.mp3", "cue": c("T_GLP", 0.05), "db": -24, "why": "the GLP keyword lands"}]
json.dump(p, open(PLAN, "w"), indent=1)
print("plan written:", len(p["elements"]), "elements,", len(p["cells"]), "cells,", len(p["sfx"]), "sfx")
