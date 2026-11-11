# Third-party pieces

Included in this kit:
- `ob-clipper/models/face_detection_yunet_2023mar.onnx`: the YuNet face detector from OpenCV Zoo (https://github.com/opencv/opencv_zoo), MIT licence.
- `ob-clipper/fonts/Anton-Regular.ttf`: Anton by Vernon Adams, SIL Open Font License 1.1 (Google Fonts).

Installed by INSTALL.sh, under their own licences:
- ffmpeg, whisper.cpp, yt-dlp, Node.js, Python (Homebrew)
- the Whisper models `ggml-base.en.bin` and `ggml-medium.en.bin` (MIT, from huggingface.co/ggerganov/whisper.cpp)
- npm: Puppeteer (Apache-2.0), HyperFrames (HeyGen), GSAP (GreenSock's standard licence)
- `ob-editor/assets/sfx_real/`: Kenney "Interface Sounds" and "UI SFX Set" picks (kenney.nl), CC0.
- Python: NumPy, SciPy, Pillow, opencv-contrib-python-headless, faster-whisper (MIT; its bundled Silero VAD model, MIT)

Installed by you (step 3 of the README):
- HyperFrames skills: `npx skills add heygen-com/hyperframes`
- the `watch` skill: https://github.com/bradautomates/claude-video (MIT)

Optional, not shipped: `zsh ~/ob-editor/bin/install_sfx_tools.sh` downloads the exact GitHub releases OB reviewed, checks their sha256, and installs them (the skill works without them):
- earshot (MIT), pick a sound effect by ear from a folder: https://github.com/Leonxlnx/earshot (v0.4.0); the skill calls it as `~/ob-editor/bin/earshot`
- Real SFX by Clipwing (places recorded sound effects on exact frames): https://github.com/Clipwing/skills

Downloaded while you edit, under each source's licence (every download is logged with its source):
- sound effects from Openverse (`openverse_sfx.py`, CC0 first)
- stock video from Pexels and Mixkit (`stock_pexels.py`, `stock_mixkit.py`; both free for commercial use)
- photos from Wikimedia Commons (`commons_fetch.py`); CC BY and BY-SA photos need a credit line in the description

Made on your Mac, not shipped: Avenir Next and DIN Condensed come with macOS, and `font_setup.py` extracts them for the graphics.


## Added in Nov 2026

Check each source before reusing anything elsewhere.

- **rea-video skill:** JuneYaooo/rea-video (Apache-2.0, licence in the folder), OB's local copy. The CLI installs separately: see its `references/setup.md`.

- **Music:** Mixkit and Pixabay tracks and FunkAvenue's Feel Good Funk Anthem. Sources are in each `banks/music/*/SOURCES.txt`.
- **Sound effects:** Openverse (`banks/sfx-openverse/SOURCES.csv`), OB's Drive pack (`assets/sfx_ob_drive/SOURCES.csv`), and the Tai pack (`assets/sfx_tai`), which has no stated licence.
- **Skills:** HyperFrames skills (heygen-com/hyperframes), Real SFX (Clipwing/skills), watch (bradautomates/claude-video, MIT), each with OB's local changes. Do not run a bare `npx skills update` on them.
- **Blender docs:** arjun988/blender-skills (MIT). **Fonts:** SIL OFL, licence file in each folder.
