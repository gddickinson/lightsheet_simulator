// The web interface's sample + acquisition pipeline (mirror of web/pipeline.py): seed NumPy's RandomState, build the
// sample with the ported simulator code, blur (Gaussian, sigma = blur_um / voxel_um per axis) and add Gaussian noise
// clipped to [0, 1] (DataGenerator's noise model). Returns { data[t][c] Float32Array, names, size, voxel_um, ... }.
import { RandomState } from './np_random.js';
import { gaussianFilter } from './ndimage.js';
import { simulateStructures } from './cells_engine.js';
import { proteinDiffusion, blobTimeSeries } from './dynamics_engine.js';

export const BLOB = { channels: 2, intensityRange: [0.8, 1.0], sigmaRange: [2, 6] };

function makeSample(rs, p) {
  const size = p.size.map(Number), n = size[0] * size[1] * size[2];
  if (p.mode === 'cell') {
    const ch = simulateStructures(rs, { ...p, size });
    return { vols: [ch.map(c => Float64Array.from(c.mask))], names: ch.map(c => c.name) };
  }
  if (p.mode === 'blobs') {
    const vols = blobTimeSeries(rs, { numVolumes: +p.num_volumes, numChannels: BLOB.channels, size, numBlobs: +p.num_blobs,
      intensityRange: BLOB.intensityRange, sigmaRange: BLOB.sigmaRange, noise: 0, speed: +p.movement_speed });
    return { vols, names: Array.from({ length: BLOB.channels }, (_, c) => `blobs ${c + 1}`) };
  }
  if (p.mode === 'diffusion') {
    return { vols: proteinDiffusion(size, +p.time_points, +p.diffusion_coefficient).map(v => [v]), names: ['protein'] };
  }
  throw new Error(`unknown mode ${p.mode} (${n})`);
}

export const blurSigmaVoxels = p => [p.blur_z_um / p.voxel_um[0], p.blur_xy_um / p.voxel_um[1], p.blur_xy_um / p.voxel_um[2]];

// opts.f64: keep Float64Array volumes (node tests compare with NumPy at full precision)
export function buildSample(p, opts = {}) {
  const t0 = performance.now();
  const rs = new RandomState(+p.seed);
  const size = p.size.map(Number);
  const { vols, names } = makeSample(rs, p);
  const sig = blurSigmaVoxels(p), noise = +p.noise;
  const data = vols.map(row => row.map(v => {
    let w = Math.max(...sig) > 0 ? gaussianFilter(v, size, sig) : v;
    if (noise > 0) { if (w === v) w = Float64Array.from(v); for (let i = 0; i < w.length; i++) w[i] = Math.min(1, Math.max(0, w[i] + noise * rs.gauss())); }
    return opts.f64 ? (w === v ? Float64Array.from(v) : w) : Float32Array.from(w);
  }));
  return { data, names, size, voxel_um: p.voxel_um.map(Number), T: data.length, C: names.length, ms: performance.now() - t0, params: p };
}

// web/pipeline.py checksum: sum(v * (1 + flat_index % 97))
export function checksum(v) { let s = 0; for (let i = 0; i < v.length; i++) s += v[i] * (1 + i % 97); return s; }

export function summary(sample) {
  const out = [];
  sample.names.forEach((name, c) => {
    for (const t of [...new Set([0, sample.T - 1])]) {
      const v = sample.data[t][c];
      let sum = 0, max = -Infinity, nz = 0;
      for (const x of v) { sum += x; if (x > max) max = x; if (x !== 0) nz++; }
      out.push({ channel: name, t, sum, max, nonzero: nz, checksum: checksum(v) });
    }
  });
  return out;
}
