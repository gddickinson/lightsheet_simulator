// Cross-check page: the same seeded cases built by the Python code (served by /api/check, precomputed for the static
// site) and by the JS engine in this browser, compared channel by channel.
import { route, api, app, esc } from './core.js';
import { runSample } from './sample_runner.js';
import { summary } from './pipeline.js';

const RTOL = 1e-6;
const rel = (a, b) => Math.abs(a - b) / Math.max(1e-12, Math.abs(b));
const g = v => Number(v).toPrecision(10);

route('check', async () => {
  app().innerHTML = `
  <h1 class="glow">Cross-check</h1>
  <p class="lead">Each case below was built twice from the same seed: by the repo's Python code (NumPy legacy random
  generator, SciPy filters) and by the JavaScript port running in this page. The JS reproduces NumPy's Mersenne Twister,
  so random cell parts, ER voxels, blob positions and noise come out the same, voxel for voxel.</p>
  <p class="small mute">Compared per channel and time point: the sum of all voxels, the maximum, the number of non-zero
  voxels and a position-weighted checksum Σ v·(1 + i mod 97). Pass: relative difference below ${RTOL} (floating-point
  rounding differs between NumPy and JS only in the last digits).</p>
  <div id="out"><p class="mute">Loading the Python results…</p></div>
  <p class="small mute">The node test <code>web/static/engine.test.mjs</code> runs about 2,000 further comparisons on small
  volumes at full precision (random draws, line_3d, gaussian_filter, binary_dilation, sampled voxels).</p>`;
  const out = document.getElementById('out');
  const { cases } = await api('/check');
  let pass = 0, total = 0, rows = '';
  out.innerHTML = '<p class="mute">Running the JS engine…</p>';
  for (const c of cases) {
    const p = c.params, t0 = performance.now();
    const js = summary(await runSample(p, { f64: true })), ms = performance.now() - t0;
    const name = `${p.mode}${p.mode === 'cell' ? ' / ' + p.cell_type : ''} · seed ${p.seed} · ${p.voxel_um.join('×')} µm`;
    c.summary.forEach((ref, i) => {
      const got = js[i] || {};
      const ok = got.channel === ref.channel && got.nonzero === ref.nonzero && rel(got.sum, ref.sum) < RTOL &&
        rel(got.max, ref.max) < RTOL && rel(got.checksum, ref.checksum) < RTOL;
      pass += ok; total++;
      rows += `<tr><td>${i ? '' : esc(name) + `<br><span class="mute">Python ${c.seconds}s · JS ${(ms / 1000).toFixed(2)}s</span>`}</td>
        <td>${esc(ref.channel)} t${ref.t}</td><td>${g(ref.sum)}<br>${g(got.sum)}</td><td>${ref.nonzero}<br>${got.nonzero}</td>
        <td>${g(ref.checksum)}<br>${g(got.checksum)}</td><td class="${ok ? 'ok' : 'bad'}">${ok ? 'match' : 'differs'}<br>${rel(got.checksum, ref.checksum).toExponential(1)}</td></tr>`;
    });
    out.innerHTML = summaryLine(pass, total) + table(rows);
  }
});

const summaryLine = (pass, total) => `<p class="callout ${pass === total ? 'a' : ''}"><b>${pass} / ${total}</b> channel volumes match.</p>`;
const table = rows => `<div class="scroll"><table class="check"><thead><tr><th>Case (volume 30 × 100 × 100 voxels, as in the desktop app)</th><th>Channel</th>
  <th>Sum<br>Python / JS</th><th>Non-zero</th><th>Checksum</th><th>Result<br>rel. diff</th></tr></thead><tbody>${rows}</tbody></table></div>`;
