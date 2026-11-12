// Port of the time-series generators: BiologicalSimulator.simulate_protein_diffusion (simulator.py) and
// DataGenerator.generate_multi_channel_time_series / _generate_single_volume (data_generator.py).
// Volumes are (z, y, x) Float64Arrays in C order; positions, sigmas and speeds are in voxels.
import { gaussianFilter } from './ndimage.js';

// simulate_protein_diffusion from a unit point source at the volume centre: each step is a Gaussian blur with
// sigma = sqrt(2 D) voxels (D in voxel^2 per step). Returns T volumes.
export function proteinDiffusion(size, T, D) {
  const [nz, ny, nx] = size, n = nz * ny * nx;
  const v0 = new Float64Array(n);
  v0[(Math.floor(nz / 2) * ny + Math.floor(ny / 2)) * nx + Math.floor(nx / 2)] = 1;
  const out = [v0];
  for (let t = 1; t < T; t++) out.push(gaussianFilter(out[t - 1], size, Math.sqrt(2 * D)));
  return out;
}

// Python float modulo (result has the sign of the divisor)
const pymod = (a, b) => { let m = a % b; if (m !== 0 && (m < 0) !== (b < 0)) m += b; return m; };

// _generate_single_volume: Gaussian blobs cut off at 3 sigma, plus normal(0, noise) noise, clipped to [0, 1]
function singleVolume(rs, size, pos, iRange, sRange, noise) {
  const [nz, ny, nx] = size, vol = new Float64Array(nz * ny * nx);
  for (const [bz, by, bx] of pos) {
    const sigma = rs.uniform(sRange[0], sRange[1]), inten = rs.uniform(iRange[0], iRange[1]);
    const lo = v => Math.max(0, Math.trunc(v - 3 * sigma)), den = 2 * sigma * sigma;
    const z1 = Math.min(nz, Math.trunc(bz + 3 * sigma)), y1 = Math.min(ny, Math.trunc(by + 3 * sigma)), x1 = Math.min(nx, Math.trunc(bx + 3 * sigma));
    for (let z = lo(bz); z < z1; z++) for (let y = lo(by); y < y1; y++) for (let x = lo(bx); x < x1; x++) {
      const dz = z - bz, dy = y - by, dx = x - bx;
      vol[(z * ny + y) * nx + x] += inten * Math.exp(-(dz * dz + dy * dy + dx * dx) / den);
    }
  }
  for (let i = 0; i < vol.length; i++) vol[i] = Math.min(1, Math.max(0, vol[i] + noise * rs.gauss()));
  return vol;
}

// generate_multi_channel_time_series -> out[t][c] volumes; blobs move by a fixed random velocity and wrap round
export function blobTimeSeries(rs, { numVolumes, numChannels = 2, size, numBlobs, intensityRange = [0.8, 1], sigmaRange = [2, 6], noise = 0, speed = 1 }) {
  const pos = [], vel = [];
  for (let c = 0; c < numChannels; c++) pos.push(Array.from({ length: numBlobs }, () => [0, 0, 0].map((_, k) => rs.random() * size[k])));
  for (let c = 0; c < numChannels; c++) vel.push(Array.from({ length: numBlobs }, () => [0, 0, 0].map(() => rs.gauss() * speed)));
  const out = [];
  for (let t = 0; t < numVolumes; t++) {
    const row = [];
    for (let c = 0; c < numChannels; c++) {
      row.push(singleVolume(rs, size, pos[c], intensityRange, sigmaRange, noise));
      for (const [i, p] of pos[c].entries()) for (let k = 0; k < 3; k++) p[k] = pymod(p[k] + vel[c][i][k], size[k]);
    }
    out.push(row);
  }
  return out;
}
