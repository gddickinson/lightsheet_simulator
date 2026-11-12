// Simulator page: controls (sim_controls.js) -> seeded sample built in a worker (pipeline.js) -> orthogonal views,
// plane and time sliders, max projection, PNG / TIFF export. Positions are voxel indices with their centres at
// (i + 0.5) x voxel size micrometres from the volume edge.
import { route, api, app, esc, animate, onLeave, download } from './core.js';
import { buildControls } from './sim_controls.js';
import { runSample } from './sample_runner.js';
import { COLORS, VIEWS, composite, draw, range } from './render.js';
import { writeTiff } from './tiff.js';

const TARGET_PX = 820;  // internal canvas width of XY + ZY at the chosen px/um scale

route('sim', async (_a, query) => {
  const P = await api('/params');
  const init = structuredClone(P.defaults);
  if (query.mode && P.modes.includes(query.mode)) init.mode = query.mode;
  if (query.cell && P.cell_types.includes(query.cell)) init.cell_type = query.cell;
  app().innerHTML = `
  <h1 class="glow">Simulator</h1>
  <p class="lead">Build a seeded 3D sample with the repo's simulation code (ported to JavaScript), blur and add noise
  as an acquisition step, and look through it in orthogonal slices and maximum projections. Units are micrometres.</p>
  <div class="sim">
    <aside class="controls" id="ctl" aria-label="Simulation parameters"></aside>
    <section aria-label="Views">
      <div class="toolbar">
        <span id="chans" role="group" aria-label="Channels"></span>
        <label class="inl"><input type="checkbox" id="mip"> Max projection</label>
        <button type="button" class="alt" id="png">PNG (XY)</button><button type="button" class="alt" id="tif">TIFF stack</button>
      </div>
      <div class="ortho" id="ortho">
        <figure><canvas id="v-xy" role="img" aria-label="XY view"></canvas><figcaption id="c-xy"></figcaption></figure>
        <figure><canvas id="v-yz" role="img" aria-label="ZY view"></canvas><figcaption id="c-yz"></figcaption></figure>
        <figure><canvas id="v-xz" role="img" aria-label="XZ view"></canvas><figcaption id="c-xz"></figcaption></figure>
        <div class="readout" id="readout" aria-live="polite"></div>
      </div>
      <div class="planes" id="planes"></div>
      <p class="small mute">Click a view to move the other planes there. Each channel is scaled to its own min–max at the shown time point.</p>
    </section>
  </div>`;
  const S = { sample: null, pos: [0, 0, 0], t: 0, mip: false, enabled: [], ranges: [], playing: null, gen: 0 };
  const params = buildControls(document.getElementById('ctl'), P, init, () => schedule());
  let timer = 0;
  const schedule = () => { clearTimeout(timer); timer = setTimeout(simulate, 250); };
  onLeave(() => { clearTimeout(timer); if (S.playing) S.playing(); });

  async function simulate() {
    const gen = ++S.gen;
    document.getElementById('readout').innerHTML = '<p class="mute">Simulating…</p>';
    try {
      const s = await runSample(structuredClone(params));
      if (gen !== S.gen) return;
      const same = S.sample && S.sample.size.join() === s.size.join();
      S.sample = s; S.t = Math.min(S.t, s.T - 1);
      if (!same) S.pos = s.size.map(n => Math.floor(n / 2));
      if (S.enabled.length !== s.C) S.enabled = s.names.map(() => true);
      setup(); render();
    } catch (e) {
      if (gen === S.gen) document.getElementById('readout').innerHTML = `<p class="err">${esc(e.message)}</p>`;
    }
  }

  function setup() {
    const s = S.sample, [nz, ny, nx] = s.size, [vz, vy, vx] = s.voxel_um;
    document.getElementById('ortho').style.gridTemplateColumns = `${nx * vx}fr ${nz * vz}fr`;
    document.getElementById('chans').innerHTML = s.names.map((n, c) => `<label class="inl chan" style="--c:rgb(${COLORS[c % COLORS.length]})">
      <input type="checkbox" data-c="${c}" ${S.enabled[c] ? 'checked' : ''}> ${esc(n)}</label>`).join('') || '<span class="mute small">no channels</span>';
    document.querySelectorAll('#chans input').forEach(i => i.addEventListener('change', () => { S.enabled[+i.dataset.c] = i.checked; render(); }));
    const host = document.getElementById('planes');
    const axes = [['z', 0, vz], ['y', 1, vy], ['x', 2, vx]];
    host.innerHTML = axes.map(([a, i]) => `<div class="ctl"><label for="pl-${a}">${a} plane <b id="pv-${a}"></b></label>
      <input type="range" id="pl-${a}" min="0" max="${s.size[i] - 1}" value="${S.pos[i]}"></div>`).join('') +
      (s.T > 1 ? `<div class="ctl trow"><label for="pl-t">time point <b id="pv-t"></b></label><input type="range" id="pl-t" min="0" max="${s.T - 1}" value="${S.t}">
        <button type="button" class="alt" id="play">Play</button></div>` : '');
    axes.forEach(([a, i]) => document.getElementById(`pl-${a}`).addEventListener('input', e => { S.pos[i] = +e.target.value; render(); }));
    if (s.T > 1) {
      document.getElementById('pl-t').addEventListener('input', e => { S.t = +e.target.value; render(); });
      document.getElementById('play').addEventListener('click', togglePlay);
    }
  }

  function togglePlay() {
    const btn = document.getElementById('play');
    if (S.playing) { S.playing(); S.playing = null; btn.textContent = 'Play'; return; }
    btn.textContent = 'Pause';
    let last = 0;
    S.playing = animate(now => {
      if (now - last < 200) return;
      last = now; S.t = (S.t + 1) % S.sample.T; document.getElementById('pl-t').value = S.t; render();
    });
  }

  function render() {
    const s = S.sample;
    if (!s) return;
    const [nz, ny, nx] = s.size, [vz, vy, vx] = s.voxel_um, um = [nz * vz, ny * vy, nx * vx];
    const k = TARGET_PX / (um[2] + um[0]);
    S.ranges = s.data[S.t].map(v => range(v));
    const c = i => (S.pos[i] + 0.5) * s.voxel_um[i];
    const views = { xy: [vx, vy, [c(2), c(1)]], yz: [vz, vy, [c(0), c(1)]], xz: [vx, vz, [c(2), c(0)]] };
    for (const [v, [uw, uh, cross]] of Object.entries(views)) {
      const comp = composite(s, S.t, v, S.pos, S.mip, S.enabled, S.ranges);
      draw(document.getElementById('v-' + v), comp, uw, uh, k, { cross: S.mip ? null : cross });
      const ax = VIEWS[v].across, i = { z: 0, y: 1, x: 2 }[ax];
      document.getElementById('c-' + v).textContent = S.mip ? `${VIEWS[v].label}: max projection along ${ax}`
        : `${VIEWS[v].label} at ${ax} = ${S.pos[i]} (${c(i).toFixed(2)} µm)`;
    }
    ['z', 'y', 'x'].forEach((a, i) => { const b = document.getElementById('pv-' + a); if (b) b.textContent = `${S.pos[i]} / ${s.size[i] - 1} · ${c(i).toFixed(2)} µm`; });
    const bt = document.getElementById('pv-t'); if (bt) bt.textContent = `${S.t + 1} / ${s.T}`;
    readout(s, um);
  }

  function readout(s, um) {
    const p = s.params;
    const rows = [
      ['Volume (z, y, x)', `${s.size.join(' × ')} voxels`], ['Voxel size', `${s.voxel_um.join(' × ')} µm`],
      ['Extent', `${um.map(v => v.toFixed(1)).join(' × ')} µm`], ['Time points', s.T], ['Seed', p.seed],
      ['Blur σ (z, y, x)', `${p.blur_z_um}, ${p.blur_xy_um}, ${p.blur_xy_um} µm`], ['Noise σ', p.noise],
      ['Built in', `${Math.round(s.ms)} ms`],
    ];
    const stats = s.names.map((n, c) => { const [lo, hi] = S.ranges[c]; return `<div><span>${esc(n)}</span><b>${lo.toFixed(3)}–${hi.toFixed(3)}</b></div>`; }).join('');
    document.getElementById('readout').innerHTML = rows.map(([a, b]) => `<div><span>${a}</span><b>${esc(b)}</b></div>`).join('') +
      (stats ? `<h3>Intensity range</h3>${stats}` : '');
  }

  document.getElementById('mip').addEventListener('change', e => { S.mip = e.target.checked; render(); });
  for (const [v, [ia, ib]] of Object.entries({ xy: [2, 1], yz: [0, 1], xz: [2, 0] })) {
    document.getElementById('v-' + v).addEventListener('click', e => {
      if (!S.sample) return;
      const r = e.target.getBoundingClientRect();
      S.pos[ia] = Math.min(S.sample.size[ia] - 1, Math.floor((e.clientX - r.left) / r.width * S.sample.size[ia]));
      S.pos[ib] = Math.min(S.sample.size[ib] - 1, Math.floor((e.clientY - r.top) / r.height * S.sample.size[ib]));
      ['z', 'y', 'x'].forEach((a, i) => { document.getElementById('pl-' + a).value = S.pos[i]; });
      render();
    });
  }
  const tag = () => { const p = S.sample.params; return `${p.mode}${p.mode === 'cell' ? '_' + p.cell_type : ''}_seed${p.seed}_vox${S.sample.voxel_um.join('x')}um`; };
  document.getElementById('png').addEventListener('click', () => {
    if (!S.sample) return;
    document.getElementById('v-xy').toBlob(b => download(`lightsheet_${tag()}_xy_${S.mip ? 'mip' : 'z' + S.pos[0]}_t${S.t}.png`, b), 'image/png');
  });
  document.getElementById('tif').addEventListener('click', () => {
    if (!S.sample) return;
    download(`lightsheet_${tag()}.tif`, new Blob([writeTiff(S.sample)], { type: 'image/tiff' }));
  });
  simulate();
});
