#!/usr/bin/env python3
"""Cut the speaker out of a clip: RobustVideoMatting (ONNX, on the CPU) -> VP9 webm with an alpha channel.

    python kit/cutout.py <clip.mp4> <out.webm> [--model mobilenetv3|resnet50]

The webm lines up frame for frame with the clip, so a skill can put graphics BEHIND the speaker (background video,
then the graphics, then this cutout on top). mobilenetv3 is the default: fast and good on a clean talking head.
resnet50 is slower and cleaner around hair and hands. Models download on first use into kit/models/.
RobustVideoMatting is by Shanchuan Lin et al. (GPL-3.0): https://github.com/PeterL1n/RobustVideoMatting
"""
import argparse
import json
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import numpy as np

KIT = Path(__file__).resolve().parent
URL = 'https://github.com/PeterL1n/RobustVideoMatting/releases/download/v1.0.0/rvm_{}_fp32.onnx'


def model_path(name):
    p = KIT / 'models' / f'rvm_{name}_fp32.onnx'
    if not p.exists():
        p.parent.mkdir(exist_ok=True)
        print(f'downloading the {name} matting model (one time)...', flush=True)
        urllib.request.urlretrieve(URL.format(name), p)
    return p


def probe(clip):
    s = json.loads(subprocess.check_output(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries',
                                            'stream=width,height,r_frame_rate,nb_frames', '-of', 'json', str(clip)]))['streams'][0]
    a, b = s['r_frame_rate'].split('/')
    return s['width'], s['height'], float(a) / float(b), int(s.get('nb_frames') or 0)


def cutout(clip, out, model='mobilenetv3', ratio=0.25):
    import onnxruntime as ort
    w, h, fps, n = probe(clip)
    sess = ort.InferenceSession(str(model_path(model)), providers=['CPUExecutionProvider'])
    rec = [np.zeros([1, 1, 1, 1], np.float32)] * 4
    dr = np.array([ratio], np.float32)
    dec = subprocess.Popen(['ffmpeg', '-v', 'error', '-i', str(clip), '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'],
                           stdout=subprocess.PIPE)
    enc = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgba', '-s', f'{w}x{h}',
                            '-r', f'{fps:.6f}', '-i', '-', '-c:v', 'libvpx-vp9', '-pix_fmt', 'yuva420p', '-b:v', '0',
                            '-crf', '22', '-deadline', 'good', '-cpu-used', '4', '-row-mt', '1', '-auto-alt-ref', '0',
                            str(out)], stdin=subprocess.PIPE)
    size, i, t0 = w * h * 3, 0, time.time()
    while True:
        buf = dec.stdout.read(size)
        if len(buf) < size:
            break
        rgb = np.frombuffer(buf, np.uint8).reshape(h, w, 3)
        src = (rgb.astype(np.float32) / 255).transpose(2, 0, 1)[None]
        fgr, pha, *rec = sess.run(None, {'src': src, 'r1i': rec[0], 'r2i': rec[1], 'r3i': rec[2], 'r4i': rec[3],
                                         'downsample_ratio': dr})
        a = (np.clip(pha[0, 0], 0, 1) * 255).astype(np.uint8)
        enc.stdin.write(np.dstack([rgb, a]).tobytes())
        i += 1
        if i % 30 == 0:
            print(f'  cutout {i}/{n or "?"} frames  {(time.time() - t0) / i:.2f}s/frame', flush=True)
    enc.stdin.close()
    enc.wait()
    dec.wait()
    if enc.returncode:
        sys.exit('ffmpeg could not write the cutout')
    print(f'wrote {out}  ({i} frames, {time.time() - t0:.0f}s)')
    return Path(out)


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('clip')
    ap.add_argument('out')
    ap.add_argument('--model', default='mobilenetv3', choices=['mobilenetv3', 'resnet50'])
    ap.add_argument('--ratio', type=float, default=0.25, help='downsample ratio (0.25 suits 1080x1920)')
    a = ap.parse_args()
    cutout(a.clip, a.out, a.model, a.ratio)
