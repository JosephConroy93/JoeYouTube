"""Promote each scene's latest attempt to its canonical name, before finalize-scenes.

    python promote-latest.py <series>/<slug> [--apply] [--root <project root>]

For every manifest scene id with `<scene_id>.attempt-N.jpg` files, the
highest N is the image that passed QC (a resubmit or rewrite always lands as
a new attempt): the bare `<scene_id>.jpg` is renamed to the next free
`.attempt-N` slot as history, and the highest attempt takes the bare name.
Without --apply it prints the plan and moves nothing. Use only when every
fix in the video followed resubmit-then-validate, so the newest attempt is
always the winner; otherwise promote by hand.
"""
import argparse
import glob
import os
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('project')
    ap.add_argument('--apply', action='store_true')
    ap.add_argument('--root', default=os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..')))
    a = ap.parse_args()
    series, slug = a.project.replace('\\', '/').split('/')
    vdir = os.path.join(a.root, 'content', series, slug)
    sg = os.path.join(vdir, 'scene-generation')
    ids = []
    for f in sorted(glob.glob(os.path.join(vdir, 'claude', 'scene-prompts', '*.md'))):
        ids += [m.group(1) for m in (re.match(r'\| (\d{3}_[\w-]+) \|', l) for l in open(f, encoding='utf-8')) if m]
    plan = []
    for sid in ids:
        attempts = sorted(glob.glob(os.path.join(sg, sid + '.attempt-*.jpg')),
                          key=lambda p: int(re.search(r'attempt-(\d+)', p).group(1)))
        if not attempts:
            continue
        top = attempts[-1]
        n_top = int(re.search(r'attempt-(\d+)', top).group(1))
        bare = os.path.join(sg, sid + '.jpg')
        used = {int(re.search(r'attempt-(\d+)', p).group(1)) for p in attempts}
        slot = next(i for i in range(1, n_top) if i not in used) if any(i not in used for i in range(1, n_top)) else n_top + 1
        plan.append((sid, bare, os.path.join(sg, f'{sid}.attempt-{slot}.jpg'), top))
    for sid, bare, hist, top in plan:
        print(f'{sid[:3]}: {os.path.basename(top)} -> {sid}.jpg' + (f'  (current bare -> {os.path.basename(hist)})' if os.path.exists(bare) else ''))
        if a.apply:
            if os.path.exists(bare):
                os.rename(bare, hist)
            os.rename(top, bare)
    print(f"{len(plan)} scenes {'promoted' if a.apply else 'to promote (dry run; --apply to move)'} of {len(ids)} in the manifest")
    return 0


if __name__ == '__main__':
    sys.exit(main())
