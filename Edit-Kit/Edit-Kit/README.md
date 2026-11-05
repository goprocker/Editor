# Edit Kit

Type a prompt, get a finished, professionally edited video. Reels, YouTube edits, SaaS and product films,
explainers and special looks, built by Claude Code with [HyperFrames](https://github.com/heygen-com/hyperframes).
No editing experience needed. Works on Mac and Windows.

**Install:** read `START HERE.txt` (double-click installer, then the self-test).
**Start editing:** `/edit` in Claude Code.

## The core kit

| Skill | What it does |
|---|---|
| `/edit` | **Start here.** One command: checks your setup, picks the right skill, storyboards, builds, adds sound, runs QA |
| `/director` | the full editing pipeline with 11 styles (Creator Explainer, SaaS, Motion Graphics, Vox, Ali Abdaal, Real Estate, Construction, Gadzhi, Bold Impact, Podcast, Finance) |
| `/reels` | 9:16 Reels / TikTok / Shorts from talking-head footage |
| `/youtube` | 16:9 YouTube edits: kinetic key words, smooth zooms, side cards, charts |
| `/saas` | product / SaaS / agency promos built from a prompt, no footage needed |
| `/fx` | the build engine: MotionKit + CreatorFX effects, project scaffold, Premiere-safe export |
| `/theme` | colours and fonts: the client's brand kit, your own, or designed from the footage |
| `/sound` | SFX on the exact frame at -17 dB, a soft music bed under the voice, -14 LUFS mix |
| `/qa` | format, loudness, sync and frame checks before delivery |

## Extra skills

| Skill | What it does |
|---|---|
| `/product-launch-video`, `/pr-to-video` | launch videos from a website or a code change |
| `/faceless-explainer`, `/vox-director`, `/slideshow` | explainers from text, Vox-style docs, slide videos |
| `/video-clone` | copy the look of a reference video: `/anime-cel`, `/pixel-art`, `/whiteboard`, `/paper-cutout`, `/crayon-storybook`, `/painted-animation`, `/blender-product-film` |
| `/embedded-captions`, `/captions-overlay`, `/talking-head-recut` | captions and talking-head recuts |
| `/video-shotcraft`, `/cut-the-curve`, `/seam-craft`, `/motion-doctrine`, `/motion-graphics`, `/oversized-cursor` | camera moves, transitions and motion rules |
| `/threejs-animation`, `/particle-system`, `/shader-glsl` | 3D, particles and shaders |
| `/music-to-video`, `/general-video`, `/remotion-to-hyperframes`, `/figma`, `/ffmpeg`, `/frontend-design` | music videos, free-form builds, imports and tools |

## House rules built in
Kinetic typography only (no boxed captions), nothing on the face, every visual matches the words, smooth zooms
instead of jump cuts, human typography, client work in the client's brand only, no invented numbers,
free fonts and code-made audio so everything is safe to post.

## Requirements
Claude Code (Pro or Max plan), Node.js 22+, FFmpeg, Python 3.9+ with Pillow and NumPy.
HyperFrames runs through `npx hyperframes` and downloads itself.

## Also works as a Claude Code plugin
```
/plugin marketplace add /path/to/Edit-Kit
/plugin install edit-kit
```

## Credits
The core kit is by Sahil Sharma (MIT). The extra skills are open-source work by other creators, kept under their
original names and lightly adapted for this kit. Their authors and licences are listed in `CREDITS.md` and the `licenses` folder.
