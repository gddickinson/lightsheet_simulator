// Home page: hero with a live simulated neuron (max projections), counts from the API, entry cards.
import { route, api, app, esc } from './core.js';
import { runSample } from './sample_runner.js';
import { composite, draw, range } from './render.js';

const DOORS = [
  ['#/sim', 'Simulator', 'Four cell types with membrane, nucleus and ER, moving blobs or protein diffusion; blur and noise; orthogonal slices, z-stack, max projection, PNG / TIFF export.'],
  ['#/sim?mode=blobs', 'Moving blobs', 'The desktop app\'s default data: a two-channel time series of Gaussian blobs drifting through the volume.'],
  ['#/check', 'Cross-check', 'The browser engine against the Python code: the same seeded volumes built by NumPy / SciPy, compared channel by channel.'],
  ['#/about', 'About', 'What is simulated (and what is not), units and conventions, how to run the desktop and web apps, credits.'],
];

route('home', async () => {
  const [info, P] = await Promise.all([api('/info'), api('/params')]);
  app().innerHTML = `
  <section class="hero two">
    <div>
      <p class="kicker">Synthetic 3D data · light-sheet microscopy</p>
      <h1 class="glow">Lightsheet Simulator</h1>
      <p class="lead">${esc(info.description)} Generate seeded cells, nuclei and endoplasmic reticulum, moving blobs or
      diffusing protein, blur and add noise, and slice through the result. The simulation runs in your browser, ported
      from the Python code and checked against it.</p>
      <a class="btn" href="#/sim">Open the simulator</a><a class="btn alt" href="#/check">See the cross-check</a>
    </div>
    <figure class="fig"><div class="heroview"><canvas id="h-xy" role="img" aria-label="Maximum projection along z of a simulated neuron"></canvas>
      <canvas id="h-yz" role="img" aria-label="Maximum projection along x of the same neuron"></canvas></div>
      <figcaption id="hcap">Simulating…</figcaption></figure>
  </section>
  <div class="tiles">
    <div class="tile"><b>${info.cell_types}</b><span>cell types</span></div>
    <div class="tile"><b>${info.structures}</b><span>structure choices</span></div>
    <div class="tile"><b>${info.modes}</b><span>sample types</span></div>
    <div class="tile"><b>${info.voxels.toLocaleString('en')}</b><span>voxels (${info.volume_zyx.join(' × ')})</span></div>
  </div>
  <div class="grid wide">${DOORS.map(([href, t, d]) => `<a class="card door" href="${href}"><b>${t}</b><span>${d}</span></a>`).join('')}</div>
  <h2>Cell types</h2>
  <p>${P.cell_types.map(c => `<a class="tag a" href="#/sim?cell=${c}">${esc(c)}</a>`).join('')}</p>`;
  try {
    const s = await runSample(structuredClone(P.defaults));
    const on = s.names.map(() => true), ranges = s.data[0].map(range), [nz, ny, nx] = s.size, [vz, vy, vx] = s.voxel_um;
    const k = 640 / (nx * vx + nz * vz);
    document.querySelector('.heroview').style.gridTemplateColumns = `${nx * vx}fr ${nz * vz}fr`;
    draw(document.getElementById('h-xy'), composite(s, 0, 'xy', [0, 0, 0], true, on, ranges), vx, vy, k);
    draw(document.getElementById('h-yz'), composite(s, 0, 'yz', [0, 0, 0], true, on, ranges), vz, vy, k, { bar: false });
    const p = s.params;
    document.getElementById('hcap').textContent = `Seed ${p.seed} ${p.cell_type}: ${s.names.map((n, i) => `${n} (${['red', 'green', 'blue', 'yellow'][i]})`).join(', ')} — max projections along z (left) and x (right); ${s.size.join(' × ')} voxels of ${s.voxel_um.join(' × ')} µm`;
  } catch (e) { document.getElementById('hcap').textContent = e.message; }
});
