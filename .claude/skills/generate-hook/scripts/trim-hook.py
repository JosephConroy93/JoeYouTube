"""Cut each raw hook clip to its scene's measured span, audio stripped.

    python trim-hook.py <series>/<slug> [--root <project root>]

Reads `claude/hook-plan.md` (shot -> scene_id) and `claude/scene-timing.md`.
A shot's span runs from its scene's start to the next scene's start in the
same voiceover segment (the same rule place-scenes uses). Writes
`hook/shot-NN.mp4` at 24 fps, H.264, no audio: trimmed when the raw clip is
longer, the last frame held when it is shorter (reported). Prints the frame
count and duration of every output so the cut is measured, not assumed.
"""
import argparse
import os
import re
import subprocess
import sys

sys.stdout.reconfigure(encoding='utf-8')


def probe(path, entries):
    return subprocess.check_output(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-count_frames',
                                    '-show_entries', entries, '-of', 'csv=p=0', path]).decode().split()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('project')
    ap.add_argument('--root', default=os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..')))
    a = ap.parse_args()
    series, slug = a.project.replace('\\', '/').split('/')
    vdir = os.path.join(a.root, 'content', series, slug)
    timing = [l.split('|') for l in open(os.path.join(vdir, 'claude', 'scene-timing.md'), encoding='utf-8')
              if re.match(r'\|\s*`?\d{3}_', l)]
    order = [r[1].strip().strip('`') for r in timing]
    start = {r[1].strip().strip('`'): float(r[4]) for r in timing}
    seg = {r[1].strip().strip('`'): r[3].strip() for r in timing}
    plan = [l.split('|') for l in open(os.path.join(vdir, 'claude', 'hook-plan.md'), encoding='utf-8')
            if re.match(r'\|\s*\d+\s*\|', l)]
    for p in plan:
        n, sid = int(p[1]), p[2].strip().strip('`')
        i = order.index(sid)
        nxt = order[i + 1] if i + 1 < len(order) else None
        if not nxt or seg[nxt] != seg[sid]:
            sys.exit(f'shot {n}: {sid} is the last scene of its segment; set its span by hand')
        span = start[nxt] - start[sid]
        raw = os.path.join(vdir, 'hook', 'raw', f'shot-{n:02d}.mp4')
        clip = float(subprocess.check_output(['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
                                             '-of', 'csv=p=0', raw]).decode())
        out = os.path.join(vdir, 'hook', f'shot-{n:02d}.mp4')
        vf = f'tpad=stop_mode=clone:stop_duration={span - clip + 0.5:.3f}' if span > clip else 'null'
        subprocess.check_call(['ffmpeg', '-v', 'error', '-y', '-i', raw, '-an', '-vf', vf, '-t', f'{span:.3f}',
                               '-c:v', 'libx264', '-crf', '16', '-pix_fmt', 'yuv420p', '-r', '24', out])
        frames, dur = probe(out, 'stream=nb_read_frames:format=duration')
        held = f' (last frame held {span - clip:.2f} s)' if span > clip else ''
        print(f'shot {n} {sid[:3]}: span {span:.2f} s, raw {clip:.0f} s -> {frames} frames, {float(dur):.3f} s{held}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
