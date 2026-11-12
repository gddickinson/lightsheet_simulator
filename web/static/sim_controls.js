// Control panel of the simulator page, built from the specs served by /api/params (sim_params.py + web specs).
// Units are shown on every control: "um" lengths are compared with voxel offset x voxel size (micrometres),
// "voxels" lengths are voxel counts, as in simulator.py.
import { esc, slider } from './core.js';

const UNIT = { um: ' µm', voxels: ' vox', 'voxels/volume': ' vox/volume', 'voxels^2/step': ' vox²/step', fraction: '', count: '', steps: '', volumes: '', 'a.u.': '', '': '' };
const MODE_LABEL = { cell: 'Cell structures', blobs: 'Moving blobs', diffusion: 'Protein diffusion' };
const BY_TYPE = {
  spherical: ['cell_radius', 'membrane_thickness'],
  neuron: ['soma_radius', 'axon_length', 'axon_width', 'num_dendrites', 'dendrite_length', 'membrane_thickness'],
  epithelial: ['membrane_thickness'], muscle: ['membrane_thickness'],
};

export function buildControls(host, P, initial, onChange) {
  const p = structuredClone(initial);
  const specs = { ...P.structure_specs, ...P.blob_specs, ...P.dynamics_specs, ...P.web_specs };
  const decimals = s => (String(s.step).split('.')[1] || '').length;
  host.innerHTML = `
    <h3>Sample</h3>
    <div class="seg" role="group" aria-label="Sample type" id="modes">${P.modes.map(m => `<button type="button" data-mode="${m}">${MODE_LABEL[m] || m}</button>`).join('')}</div>
    <div class="row seedrow"><div><label for="seed">Random seed</label><input id="seed" type="number" min="0" max="4294967295" step="1" value="${p.seed}"></div>
      <button type="button" class="alt" id="reroll">New seed</button></div>
    <div id="g-cell"><label for="ctype">Cell type</label><select id="ctype">${P.cell_types.map(c => `<option>${c}</option>`).join('')}</select>
      <label for="struct">Structures</label><select id="struct">${P.structures.map(c => `<option>${esc(c)}</option>`).join('')}</select><div id="cellp"></div></div>
    <div id="g-blobs"></div><div id="g-diffusion"></div>
    <h3>Volume</h3><div id="vol"></div>
    <fieldset class="vox"><legend>Voxel size (µm per voxel)</legend>
      ${['z', 'y', 'x'].map((a, i) => `<label for="vox${a}">${a}</label><input id="vox${a}" type="number" min="${specs.pixel_size.min}" max="${specs.pixel_size.max}" step="${specs.pixel_size.step}" value="${p.voxel_um[i]}">`).join('')}
    </fieldset>
    <h3>Acquisition</h3><div id="acq"></div>
    <p class="small mute">Blur: Gaussian, σ in µm converted to voxels per axis. Noise: additive Gaussian (σ in intensity units), then clipped to 0–1, as in DataGenerator.</p>`;
  const $ = s => host.querySelector(s);
  const fire = () => onChange(p);
  const add = (where, key, { set = v => { p[key] = v; }, value = p[key], label } = {}) => {
    const s = specs[key];
    return slider($(where), { id: key, label: `${label || s.label}`, min: s.min, max: s.max, step: s.step, value, unit: UNIT[s.unit] ?? '',
      fmt: v => (+v).toFixed(decimals(s)) }, v => { set(v); fire(); });
  };
  for (const k of Object.keys(P.structure_specs)) if (!['pixel_size', 'nucleus_thickness'].includes(k)) add('#cellp', k).closest('.ctl').dataset.k = k;
  ['num_volumes', 'num_blobs', 'movement_speed'].forEach(k => add('#g-blobs', k));
  add('#g-diffusion', 'diffusion_coefficient'); add('#g-diffusion', 'time_points');
  add('#vol', 'size_z', { value: p.size[0], set: v => { p.size[0] = v; } });
  add('#vol', 'size_yx', { value: p.size[1], set: v => { p.size[1] = v; p.size[2] = v; } });
  add('#acq', 'blur_xy_um'); add('#acq', 'blur_z_um');
  add('#acq', 'noise_level', { value: p.noise, set: v => { p.noise = v; }, label: 'Noise σ' });

  const sync = () => {
    host.querySelectorAll('#modes button').forEach(b => { b.classList.toggle('on', b.dataset.mode === p.mode); b.setAttribute('aria-pressed', b.dataset.mode === p.mode); });
    for (const m of P.modes) $(`#g-${m}`).hidden = m !== p.mode;
    const show = new Set(BY_TYPE[p.cell_type] || []);
    if (/Nucleus|ER/.test(p.cellular_structure)) show.add('nucleus_radius');
    if (/ER/.test(p.cellular_structure)) show.add('er_density');
    host.querySelectorAll('#cellp .ctl').forEach(el => { el.hidden = !show.has(el.dataset.k); });
  };
  host.querySelectorAll('#modes button').forEach(b => b.addEventListener('click', () => { p.mode = b.dataset.mode; sync(); fire(); }));
  $('#ctype').value = p.cell_type; $('#struct').value = p.cellular_structure;
  $('#ctype').addEventListener('change', e => { p.cell_type = e.target.value; sync(); fire(); });
  $('#struct').addEventListener('change', e => { p.cellular_structure = e.target.value; sync(); fire(); });
  $('#seed').addEventListener('change', e => { p.seed = Math.max(0, Math.trunc(+e.target.value || 0)); fire(); });
  $('#reroll').addEventListener('click', () => { p.seed = Math.floor(Math.random() * 10000); $('#seed').value = p.seed; fire(); });
  ['z', 'y', 'x'].forEach((a, i) => $(`#vox${a}`).addEventListener('change', e => {
    const v = Math.min(specs.pixel_size.max, Math.max(specs.pixel_size.min, +e.target.value || 1));
    e.target.value = v; p.voxel_um[i] = v; fire();
  }));
  sync();
  return p;
}

// Effective nucleus radius: the desktop rule max(5, min(r, soma_radius // 2)), then the simulator's clamp to
// (min(size) // 4) // 3 inside generate_nucleus.
export function nucleusRadii(p) {
  const asked = Math.max(5, Math.min(p.nucleus_radius, Math.floor(p.soma_radius / 2)));
  return { asked, used: Math.min(Math.max(1, asked), Math.floor(Math.floor(Math.min(...p.size) / 4) / 3)) };
}
