// About page: what is simulated, units and conventions, what the web version leaves out, how to run, credits.
import { route, api, app, esc } from './core.js';

const ATLAS = 'https://gddickinson.github.io/microscope-atlas/';

route('about', async () => {
  const [info, P] = await Promise.all([api('/info'), api('/params')]);
  const unit = s => ({ um: 'µm', voxels: 'voxels', fraction: 'fraction', count: 'count' }[s.unit] ?? s.unit);
  const specRows = Object.entries(P.structure_specs).filter(([k]) => k !== 'nucleus_thickness')
    .map(([k, s]) => `<tr><td>${esc(s.label)}</td><td>${s.min}–${s.max}</td><td>${s.default}</td><td>${esc(unit(s))}</td></tr>`).join('');
  app().innerHTML = `
  <h1 class="glow">About</h1>
  <p class="lead">${esc(info.description)} The desktop application (PyQt5 + pyqtgraph) generates synthetic volumes for
  testing light-sheet analysis pipelines; this web version runs its simulation code in the browser.</p>
  <div class="two">
  <div>
  <h2>What the web simulator does</h2>
  <p><b>Cell structures</b> — <code>BiologicalSimulator.generate_cell_shape</code> for ${P.cell_types.map(esc).join(', ')}
  cells, then the membrane, a nucleus (<code>generate_nucleus</code>, placed by <code>find_suitable_center</code>) and
  endoplasmic reticulum (<code>generate_er</code>, random voxels in the cytoplasm, denser around the nucleus), exactly as
  the desktop "Simulate" button combines them (<code>structure_pipeline.py</code>).</p>
  <p><b>Moving blobs</b> — <code>DataGenerator.generate_multi_channel_time_series</code>: ${P.blob.channels} channels of
  Gaussian blobs (σ ${P.blob.sigma_range_voxels.join('–')} voxels, intensity ${P.blob.intensity_range.join('–')}) drifting
  with random velocities and wrapping round the volume — the data the desktop viewer opens with.</p>
  <p><b>Protein diffusion</b> — <code>simulate_protein_diffusion</code>: a unit point source at the centre, blurred
  each time step with σ = √(2D) voxels.</p>
  <p><b>Acquisition</b> — the web interface's own step, built from the repo's functions: a Gaussian blur
  (<code>VolumeProcessor.apply_gaussian_filter</code>, σ given in µm and converted per axis with the voxel size) and
  DataGenerator's noise model (additive Gaussian noise, clipped to 0–1). The axial σ stands in for light-sheet
  thickness. This is an approximation: the Python code has no optical PSF model (a PSF and camera-noise models are on
  the project's roadmap).</p>
  <p>Every draw uses NumPy's legacy random generator, ported to JavaScript, so a seed gives the same volume in the
  browser and in Python: see the <a href="#/check">cross-check</a>.</p>
  </div>
  <div>
  <h2>Units and conventions</h2>
  <ul>
    <li>Axes are (z, y, x); z is the detection axis, the direction the light sheet is stepped.</li>
    <li>Voxel size is in µm per voxel. The desktop form's "Pixel Size" boxes carry no unit; here they are read as
      micrometres. Default 1 µm, as in the desktop form.</li>
    <li>Radii are compared with distances computed as voxel offset × voxel size, so they are in µm. Axon and dendrite
      lengths and widths are voxel counts, as in <code>simulator.py</code>.</li>
    <li>Plane i covers i·d to (i + 1)·d µm from the volume edge; positions shown are voxel centres, (i + 0.5)·d µm.</li>
    <li>Intensities are arbitrary units in 0–1. Diffusion coefficient D is in voxel² per time step.</li>
  </ul>
  <h3>Cell parameters (desktop form ranges)</h3>
  <div class="scroll"><table><thead><tr><th>Parameter</th><th>Range</th><th>Default</th><th>Unit</th></tr></thead><tbody>${specRows}</tbody></table></div>
  </div></div>
  <h2>Exports</h2>
  <p><b>PNG</b>: the XY view as shown (current plane or max projection), at physical aspect ratio.
  <b>TIFF</b>: the whole acquired stack as an ImageJ hyperstack (32-bit float, all time points and channels) with the
  voxel size in the file (X/Y resolution in pixels per µm, <code>unit=micron</code>, <code>spacing</code> = z voxel
  size), so Fiji and tifffile read the scale back.</p>
  <h2>Not in the web version</h2>
  <p>Calcium signals and active transport (listed in the desktop form but not implemented in the Python code), the
  angular-recording rotation (<code>DataGenerator.simulate_angular_recording</code>, not wired into the GUI), blob
  detection and colocalization analysis (scikit-image / SciPy, desktop only) and the OpenGL 3D view.</p>
  <p class="small mute">Note on the nucleus: the desktop asks for radius max(5, min(r, soma radius ÷ 2)) and
  <code>generate_nucleus</code> then caps it at (min(volume size) ÷ 4) ÷ 3 — 2 at the default 30 × 100 × 100 volume — so
  the nucleus radius control has little effect; the ER uses the uncapped radius. The simulator readout shows both.</p>
  <h2>Run it yourself</h2>
  <div class="two"><div><h3>Desktop app</h3>
  <pre>pip install -r requirements.txt
python simulateLightSheetData.py</pre></div>
  <div><h3>Web app (local)</h3>
  <pre>pip install -r requirements-web.txt
python run_web.py      # http://127.0.0.1:8204</pre></div></div>
  <h2>Learn more about light-sheet microscopy</h2>
  <p>George's <a href="${ATLAS}" target="_blank" rel="noopener">Microscope Atlas</a> covers the technique:
  <a href="${ATLAS}#/technique/light-sheet" target="_blank" rel="noopener">light-sheet microscopy</a> and an interactive
  <a href="${ATLAS}#/sim/lightsheet" target="_blank" rel="noopener">light-sheet beam simulation</a> (sheet waist versus
  field of view).</p>
  <h2>Credits</h2>
  <p>Lightsheet Simulator by George D. Dickinson (University of California, Irvine), MIT licence. Built with AI assistance
  from <a href="https://claude.com/" target="_blank" rel="noopener">Claude (Anthropic)</a>.
  Source: <a href="https://github.com/gddickinson/lightsheet_simulator" target="_blank" rel="noopener">github.com/gddickinson/lightsheet_simulator</a>.</p>`;
});
