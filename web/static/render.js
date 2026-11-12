// Orthogonal slice views and maximum projections of a sample (data[t][c] Float32Array, (z, y, x) C order) on canvas.
// Each channel is scaled to its own min..max at the shown time point (as the desktop viewer does) and coloured red,
// green, blue (the desktop's first three channel colours), added and clipped. Views are drawn at physical aspect:
// one canvas pixel is 1/k micrometres in both directions, whatever the voxel size.

export const COLORS = [[255, 70, 70], [70, 255, 120], [90, 150, 255], [255, 220, 60]];
export const VIEWS = {
  xy: { label: 'XY', across: 'z', w: 2, h: 1 },   // width along x, height along y, plane chosen by z
  xz: { label: 'XZ', across: 'y', w: 2, h: 0 },   // width along x, height along z
  yz: { label: 'ZY', across: 'x', w: 0, h: 1 },   // width along z, height along y (sits right of XY)
};
const AX = { z: 0, y: 1, x: 2 };

export function range(v) {
  let lo = Infinity, hi = -Infinity;
  for (let i = 0; i < v.length; i++) { const a = v[i]; if (a < lo) lo = a; if (a > hi) hi = a; }
  return [lo, hi];
}

// 2D image (w*h Float32Array) of one channel: a plane at index pos[across], or the max projection along that axis
export function plane(v, size, view, pos, mip) {
  const V = VIEWS[view], [nz, ny, nx] = size, W = size[V.w], H = size[V.h], out = new Float32Array(W * H);
  const a = AX[V.across], n = size[a];
  const k0 = mip ? 0 : pos[a], k1 = mip ? n : pos[a] + 1;
  out.fill(-Infinity);
  for (let k = k0; k < k1; k++) for (let r = 0; r < H; r++) for (let c = 0; c < W; c++) {
    const zyx = [0, 0, 0]; zyx[a] = k; zyx[V.w] = c; zyx[V.h] = r;
    const val = v[(zyx[0] * ny + zyx[1]) * nx + zyx[2]];
    if (val > out[r * W + c]) out[r * W + c] = val;
  }
  return { W, H, img: out };
}

// RGBA ImageData-compatible array combining the enabled channels
export function composite(sample, t, view, pos, mip, enabled, ranges) {
  let W = 0, H = 0, rgba = null;
  sample.data[t].forEach((v, c) => {
    if (!enabled[c]) return;
    const p = plane(v, sample.size, view, pos, mip);
    if (!rgba) { W = p.W; H = p.H; rgba = new Float32Array(W * H * 3); }
    const [lo, hi] = ranges[c], span = hi - lo || 1, col = COLORS[c % COLORS.length];
    for (let i = 0; i < W * H; i++) { const u = (p.img[i] - lo) / span; for (let j = 0; j < 3; j++) rgba[i * 3 + j] += u * col[j]; }
  });
  if (!rgba) { const V = VIEWS[view]; W = sample.size[V.w]; H = sample.size[V.h]; rgba = new Float32Array(W * H * 3); }
  const out = new Uint8ClampedArray(W * H * 4);
  for (let i = 0; i < W * H; i++) { out[i * 4] = rgba[i * 3]; out[i * 4 + 1] = rgba[i * 3 + 1]; out[i * 4 + 2] = rgba[i * 3 + 2]; out[i * 4 + 3] = 255; }
  return { W, H, rgba: out };
}

const NICE = [0.5, 1, 2, 5, 10, 20, 50, 100, 200, 500, 1000];
export const niceBar = um => NICE.reduce((b, v) => (v <= um ? v : b), NICE[0]);

// Draw a composite into canvas at k px/um; cross = [u, v] position (um) of the other two planes, or null
export function draw(canvas, comp, umW, umH, k, { cross = null, bar = true } = {}) {
  const cw = Math.max(1, Math.round(comp.W * umW * k)), ch = Math.max(1, Math.round(comp.H * umH * k));
  if (canvas.width !== cw || canvas.height !== ch) { canvas.width = cw; canvas.height = ch; }
  const off = new OffscreenCanvas(comp.W, comp.H);
  off.getContext('2d').putImageData(new ImageData(comp.rgba, comp.W, comp.H), 0, 0);
  const g = canvas.getContext('2d');
  g.imageSmoothingEnabled = false;
  g.drawImage(off, 0, 0, cw, ch);
  if (cross) {
    g.strokeStyle = 'rgba(255,255,255,.35)'; g.lineWidth = 1; g.setLineDash([4, 4]);
    g.beginPath(); g.moveTo(cross[0] * k + .5, 0); g.lineTo(cross[0] * k + .5, ch); g.moveTo(0, cross[1] * k + .5); g.lineTo(cw, cross[1] * k + .5); g.stroke();
    g.setLineDash([]);
  }
  if (bar) {
    const len = niceBar(comp.W * umW / 4), px = len * k, x = 10, y = ch - 12;
    if (px > 8 && ch > 40) {
      g.fillStyle = '#fff'; g.fillRect(x, y, px, 3);
      g.font = '12px ui-monospace, Menlo, monospace'; g.fillText(`${len} µm`, x, y - 5);
    }
  }
}
