// Node test: the JS engine against numbers computed by the repo's Python code (tests/fixtures/engine_fixture.json,
// written by scripts/make_engine_fixture.py). Run: node web/static/engine.test.mjs
import { readFileSync } from 'node:fs';
import assert from 'node:assert/strict';
import { RandomState } from './np_random.js';
import { gaussianFilter, binaryDilation } from './ndimage.js';
import { line3d } from './cells_engine.js';
import { buildSample, summary } from './pipeline.js';

const fx = JSON.parse(readFileSync(new URL('../../tests/fixtures/engine_fixture.json', import.meta.url)));
let n = 0;
const close = (a, b, rtol, atol, what) => {
  assert.ok(Math.abs(a - b) <= atol + rtol * Math.abs(b), `${what}: JS ${a} vs Python ${b}`); n++;
};

// NumPy RandomState draws, in the fixture's order
{
  const r = new RandomState(fx.rng.seed);
  fx.rng.random.forEach((v, i) => close(r.random(), v, 0, 0, `random[${i}]`));
  [[-3, 3], [0, 10], [-1, 1], [0, 1], [5, 6], [0, 1000]].forEach(([lo, hi], i) => { assert.equal(r.randint(lo, hi), fx.rng.randint[i], `randint[${i}]`); n++; });
  fx.rng.uniform.forEach((v, i) => close(r.uniform(0, 2 * Math.PI), v, 1e-15, 0, `uniform[${i}]`));
  fx.rng.randn.forEach((v, i) => close(r.gauss(), v, 1e-13, 1e-15, `randn[${i}]`));
  fx.rng.normal.forEach((v, i) => close(r.normal(0, 0.5), v, 1e-13, 1e-15, `normal[${i}]`));
}

// line_3d
for (const [args, xyz] of fx.lines) { assert.deepEqual(line3d(...args), xyz, `line3d ${args}`); n++; }

// gaussian_filter and binary_dilation
{
  const dims = fx.volume.dims, vol = Float64Array.from(fx.volume.data);
  for (const g of fx.gauss) {
    const out = gaussianFilter(vol, dims, g.sigma);
    g.out.forEach((v, i) => close(out[i], v, 1e-12, 1e-14, `gaussian_filter sigma=${g.sigma} [${i}]`));
  }
  const mask = Uint8Array.from(fx.dilation.mask);
  for (const [k, ref] of Object.entries(fx.dilation.out)) { assert.deepEqual([...binaryDilation(mask, dims, +k)], ref, `dilation ${k}`); n++; }
}

// Seeded samples through the whole pipeline: cell shapes, nucleus, ER, blobs, diffusion, blur, noise
for (const s of fx.samples) {
  const p = s.params, tag = `${p.mode}/${p.cell_type} seed ${p.seed}`;
  const js = buildSample(p, { f64: true });
  assert.deepEqual(js.names, s.names, `${tag} channels`);
  assert.deepEqual([js.T, js.C, ...js.size], s.shape, `${tag} shape`);
  const sum = summary(js);
  s.summary.forEach((ref, i) => {
    const got = sum[i];
    assert.equal(got.channel, ref.channel); assert.equal(got.nonzero, ref.nonzero, `${tag} ${ref.channel} t${ref.t} nonzero`);
    close(got.sum, ref.sum, 1e-9, 1e-9, `${tag} ${ref.channel} t${ref.t} sum`);
    close(got.max, ref.max, 1e-9, 1e-12, `${tag} ${ref.channel} max`);
    close(got.checksum, ref.checksum, 1e-9, 1e-9, `${tag} ${ref.channel} checksum`);
  });
  let k = 0;
  for (let t = 0; t < js.T; t++) for (let c = 0; c < js.C; c++, k++) {
    s.probe_index.forEach((idx, j) => close(js.data[t][c][idx], s.probes[k][j], 1e-9, 1e-12, `${tag} t${t} c${c} voxel ${idx}`));
  }
}

console.log(`engine.test.mjs: ${n} checks passed (${fx.samples.length} seeded samples match NumPy/SciPy)`);
