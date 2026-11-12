// Port of the cell-structure code: utils.line_3d, BiologicalSimulator.generate_cell_shape / generate_nucleus /
// find_suitable_center / generate_er (simulator.py) and structure_pipeline.simulate_structures. Volumes are (z, y, x),
// flat in C order. px is the voxel size (z, y, x) in micrometres: like the Python, distances are voxel offsets times
// px, so radii compared with them are in micrometres while axon/dendrite lengths are voxel counts.
// Random draws go through a RandomState (np_random.js) in exactly the Python order, so a seed reproduces the volume.
import { binaryDilation } from './ndimage.js';

const fdiv = (a, b) => Math.floor(a / b);

// utils.line_3d: 3D Bresenham from (x0, y0, z0) to (x1, y1, z1) (the three coordinates are generic axes)
export function line3d(x0, y0, z0, x1, y1, z1) {
  const dx = Math.abs(x1 - x0), dy = Math.abs(y1 - y0), dz = Math.abs(z1 - z0);
  const sx = x1 > x0 ? 1 : -1, sy = y1 > y0 ? 1 : -1, sz = z1 > z0 ? 1 : -1;
  let x = x0, y = y0, z = z0;
  const X = [x], Y = [y], Z = [z];
  const push = () => { X.push(x); Y.push(y); Z.push(z); };
  if (dx >= dy && dx >= dz) {
    let e1 = 2 * dy - dx, e2 = 2 * dz - dx;
    for (let i = 0; i < dx; i++) { x += sx; if (e1 >= 0) { y += sy; e1 -= 2 * dx; } if (e2 >= 0) { z += sz; e2 -= 2 * dx; } e1 += 2 * dy; e2 += 2 * dz; push(); }
  } else if (dy >= dx && dy >= dz) {
    let e1 = 2 * dx - dy, e2 = 2 * dz - dy;
    for (let i = 0; i < dy; i++) { y += sy; if (e1 >= 0) { x += sx; e1 -= 2 * dy; } if (e2 >= 0) { z += sz; e2 -= 2 * dy; } e1 += 2 * dx; e2 += 2 * dz; push(); }
  } else {
    let e1 = 2 * dy - dz, e2 = 2 * dx - dz;
    for (let i = 0; i < dz; i++) { z += sz; if (e1 >= 0) { y += sy; e1 -= 2 * dz; } if (e2 >= 0) { x += sx; e2 -= 2 * dz; } e1 += 2 * dy; e2 += 2 * dx; push(); }
  }
  return [X, Y, Z];
}

// Visit every voxel with its scaled distance from c: fn(index, z, y, x, dist)
function eachDist(size, c, px, fn) {
  const [nz, ny, nx] = size;
  let i = 0;
  for (let z = 0; z < nz; z++) {
    const dz = (z - c[0]) * px[0];
    for (let y = 0; y < ny; y++) {
      const dy = (y - c[1]) * px[1];
      for (let x = 0; x < nx; x++, i++) { const dx = (x - c[2]) * px[2]; fn(i, z, y, x, Math.sqrt(dz * dz + dy * dy + dx * dx)); }
    }
  }
}

// generate_cell_shape -> { shape, interior, membrane } as Uint8Array masks
export function generateCellShape(rs, cellType, size, px = [1, 1, 1], membraneThickness = 1, kw = {}) {
  const [nz, ny, nx] = size, n = nz * ny * nx, c = size.map(s => fdiv(s, 2)), mt = membraneThickness;
  let shape = new Uint8Array(n), interior = new Uint8Array(n), membrane;
  const minS = Math.min(...size);
  if (cellType === 'spherical') {
    const radius = kw.cell_radius ?? fdiv(minS, 4);
    eachDist(size, c, px, (i, z, y, x, d) => {
      interior[i] = d <= radius - mt; const m = d <= radius && d > radius - mt; shape[i] = interior[i] || m;
    });
    membrane = shape.map((v, i) => v && !interior[i] ? 1 : 0);
  } else if (cellType === 'neuron') {
    const somaR = kw.soma_radius ?? fdiv(minS, 8), axonLen = kw.axon_length ?? fdiv(nx, 2);
    const axonW = kw.axon_width ?? fdiv(ny, 20), nDend = kw.num_dendrites ?? 5, dendLen = kw.dendrite_length ?? fdiv(ny, 4);
    const axonStart = c[2] + somaR, half = fdiv(axonW, 2);
    eachDist(size, c, px, (i, z, y, x, d) => {
      interior[i] = (d <= somaR) || (x >= axonStart && x < axonStart + axonLen && Math.abs(y - c[1]) <= half && Math.abs(z - c[0]) <= half);
    });
    const axonEnd = axonStart + axonLen;
    for (let k = 0; k < 3; k++) {
      const tz = c[0] + rs.randint(-axonW, axonW), ty = c[1] + rs.randint(-axonW, axonW), tx = axonEnd + rs.randint(0, fdiv(nx, 10));
      const tr = fdiv(axonW, 2);
      eachDist(size, [tz, ty, tx], px, (i, z, y, x, d) => { if (d <= tr) interior[i] = 1; });
    }
    let dend = new Uint8Array(n);
    for (let k = 0; k < nDend; k++) {
      const a = rs.uniform(0, 2 * Math.PI);
      const e = [Math.trunc(c[0] + dendLen * Math.sin(a) * Math.cos(a)), Math.trunc(c[1] + dendLen * Math.sin(a)), Math.trunc(c[2] - dendLen * Math.cos(a))];
      const [R, C, Z] = line3d(c[0], c[1], c[2], e[0], e[1], e[2]);
      for (let j = 0; j < R.length; j++) {
        if (R[j] >= 0 && R[j] < nz && C[j] >= 0 && C[j] < ny && Z[j] >= 0 && Z[j] < nx) dend[(R[j] * ny + C[j]) * nx + Z[j]] = 1;
      }
    }
    dend = binaryDilation(dend, size, 2);
    for (let i = 0; i < n; i++) interior[i] = interior[i] || dend[i];
    shape = binaryDilation(interior, size, mt);
    membrane = shape.map((v, i) => v && !interior[i] ? 1 : 0);
  } else if (cellType === 'epithelial') {
    const h = fdiv(nz, 3);
    for (let i = 0; i < n; i++) { const z = fdiv(i, ny * nx); interior[i] = z < h - mt; shape[i] = (z < h) !== (z < h - mt); }
    membrane = Uint8Array.from(shape);
  } else if (cellType === 'muscle') {
    const R = fdiv(minS, 4);
    eachDist(size, c, px, (i, z, y, x) => {
      const dy = (y - c[1]) * px[1], dz = (z - c[0]) * px[0], r2 = dy * dy + dz * dz;
      const outer = r2 <= R * R, inner = r2 <= (R - mt) * (R - mt);
      interior[i] = inner; shape[i] = outer !== inner;
    });
    membrane = Uint8Array.from(shape);
  } else throw new Error(`Unknown cell type: ${cellType}`);
  if (!shape.some(v => v)) throw new Error('The cell shape is empty for these parameters (the Python raises here too).');
  return { shape, interior, membrane };
}

// Count voxels of cell within distance r (um, offsets scaled by the voxel size px) of c
function countInSphere(cell, size, c, r, px) {
  const [nz, ny, nx] = size, R = px.map(v => Math.floor(r / v));
  let k = 0;
  for (let z = Math.max(0, c[0] - R[0]); z <= Math.min(nz - 1, c[0] + R[0]); z++)
    for (let y = Math.max(0, c[1] - R[1]); y <= Math.min(ny - 1, c[1] + R[1]); y++)
      for (let x = Math.max(0, c[2] - R[2]); x <= Math.min(nx - 1, c[2] + R[2]); x++) {
        const dz = (z - c[0]) * px[0], dy = (y - c[1]) * px[1], dx = (x - c[2]) * px[2];
        if (Math.sqrt(dz * dz + dy * dy + dx * dx) <= r && cell[(z * ny + y) * nx + x]) k++;
      }
  return k;
}

// find_suitable_center: grow a search radius r = 0, 1, ... around the soma; at each r try the in-cell voxels within r,
// farthest first (numpy argsort of -distance; ties here in C order), and return the first that has >= 7 cell voxels
// within the nucleus radius (um, with voxel size px). Falls back to the truncated centre of mass, or null for an empty cell.
export function findSuitableCenter(cell, size, soma, nr, px = [1, 1, 1]) {
  const [nz, ny, nx] = size, cand = [];
  eachDist(size, soma, [1, 1, 1], (i, z, y, x, d) => { if (cell[i]) cand.push([d, z, y, x, i]); });
  cand.sort((a, b) => a[0] - b[0] || a[4] - b[4]);
  let lo = 0;
  for (let r = 0; r < Math.max(...size); r++) {
    let hi = lo;
    while (hi < cand.length && cand[hi][0] <= r) hi++;
    const fresh = cand.slice(lo, hi).sort((a, b) => b[0] - a[0] || a[4] - b[4]);
    for (const [, z, y, x] of fresh) if (countInSphere(cell, size, [z, y, x], nr, px) >= 7) return [z, y, x];
    lo = hi;
  }
  if (!cand.length) return null;
  const s = [0, 0, 0];
  for (const [, z, y, x] of cand) { s[0] += z; s[1] += y; s[2] += x; }
  return s.map(v => Math.trunc(v / cand.length));
}

// generate_nucleus -> { nucleus (Uint8Array), center }
export function generateNucleus(interior, size, soma, nucleusRadius, px = [1, 1, 1]) {
  const nr = Math.max(1, nucleusRadius);  // no fixed cap: the nucleus is clipped to the cell interior
  const center = findSuitableCenter(interior, size, soma, nr, px);
  const nucleus = new Uint8Array(interior.length);
  if (!center) return { nucleus, center: soma, radius: nr };
  eachDist(size, center, px, (i, z, y, x, d) => { nucleus[i] = d <= nr && interior[i] ? 1 : 0; });
  return { nucleus, center, radius: nr };
}

// generate_er: random ER voxels in the cytoplasm, twice as likely in a shell just outside the nucleus radius
export function generateEr(rs, shape, size, soma, nr, density = 0.1, px = [1, 1, 1]) {
  const n = shape.length, dist = new Float64Array(n);
  eachDist(size, soma, px, (i, z, y, x, d) => { dist[i] = d; });
  const cyto = i => shape[i] && !(dist[i] <= nr);
  const er = new Uint8Array(n);
  const r1 = rs.rand(n);
  for (let i = 0; i < n; i++) er[i] = cyto(i) && r1[i] < density ? 1 : 0;
  const r2 = rs.rand(n);
  for (let i = 0; i < n; i++) if (dist[i] > nr && dist[i] <= nr * 1.5 && cyto(i) && r2[i] < density * 2) er[i] = 1;
  return er;
}

// structure_pipeline.nucleus_radius_used
export const nucleusRadiusUsed = p => p.nucleus_radius;

// structure_pipeline.simulate_structures -> [{ name, mask }]
export function simulateStructures(rs, p) {
  const st = p.cellular_structure;
  if (st === 'None') return [];
  const size = p.size, soma = size.map(s => fdiv(s, 2)), px = p.voxel_um;
  const { shape, interior, membrane } = generateCellShape(rs, p.cell_type, size, px, p.membrane_thickness, p);
  const nr = nucleusRadiusUsed(p), out = [];
  if (st.includes('Cell Membrane')) out.push({ name: 'membrane', mask: membrane });
  if (st.includes('Nucleus')) out.push({ name: 'nucleus', mask: generateNucleus(interior, size, soma, nr, px).nucleus });
  if (st.includes('ER')) out.push({ name: 'ER', mask: generateEr(rs, shape, size, soma, nr, p.er_density, px) });
  return out;
}
