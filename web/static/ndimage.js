// The scipy.ndimage pieces the simulator uses, for (z, y, x) volumes stored flat in C order (index (z*ny + y)*nx + x).
// gaussianFilter matches gaussian_filter(vol, sigma) (mode 'reflect', truncate 4.0, axes in order z, y, x);
// binaryDilation matches binary_dilation(mask, iterations=n) with the default 6-connected cross and border 0.

// scipy _gaussian_kernel1d (order 0): radius int(4*sigma + 0.5), normalised exp(-x^2 / (2 sigma^2))
export function gaussianKernel(sigma, truncate = 4.0) {
  const r = Math.trunc(truncate * sigma + 0.5);
  const w = new Float64Array(2 * r + 1);
  let s = 0;
  for (let i = -r; i <= r; i++) { w[i + r] = Math.exp(-0.5 / (sigma * sigma) * i * i); s += w[i + r]; }
  for (let i = 0; i < w.length; i++) w[i] /= s;
  return w;
}

// scipy mode 'reflect' (half-sample symmetric: d c b a | a b c d | d c b a)
export function reflectIndex(j, n) {
  if (n === 1) return 0;
  const p = 2 * n;
  j = ((j % p) + p) % p;
  return j >= n ? p - 1 - j : j;
}

function filterAxis(src, dims, axis, w) {
  const [nz, ny, nx] = dims, n = dims[axis], r = (w.length - 1) / 2;
  const stride = axis === 0 ? ny * nx : axis === 1 ? nx : 1;
  const out = new Float64Array(src.length), line = new Float64Array(n + 2 * r);
  const outer = axis === 0 ? [ny, nx] : axis === 1 ? [nz, nx] : [nz, ny];
  for (let a = 0; a < outer[0]; a++) {
    for (let b = 0; b < outer[1]; b++) {
      const base = axis === 0 ? a * nx + b : axis === 1 ? a * ny * nx + b : (a * ny + b) * nx;
      for (let j = -r; j < n + r; j++) line[j + r] = src[base + reflectIndex(j, n) * stride];
      for (let i = 0; i < n; i++) {
        let s = 0;
        for (let k = 0; k < w.length; k++) s += w[k] * line[i + k];
        out[base + i * stride] = s;
      }
    }
  }
  return out;
}

// gaussian_filter with a sigma per axis (z, y, x) in voxels; axes with sigma <= 1e-15 are skipped.
export function gaussianFilter(vol, dims, sigma) {
  const sig = Array.isArray(sigma) ? sigma : [sigma, sigma, sigma];
  let out = vol;
  for (let ax = 0; ax < 3; ax++) if (sig[ax] > 1e-15) out = filterAxis(out, dims, ax, gaussianKernel(sig[ax]));
  return out === vol ? Float64Array.from(vol) : out;
}

// binary_dilation(mask, iterations) with the 6-neighbour cross; mask is a Uint8Array of 0/1.
export function binaryDilation(mask, dims, iterations = 1) {
  const [nz, ny, nx] = dims;
  let cur = mask;
  for (let it = 0; it < iterations; it++) {
    const out = Uint8Array.from(cur);
    for (let z = 0; z < nz; z++) for (let y = 0; y < ny; y++) for (let x = 0; x < nx; x++) {
      const i = (z * ny + y) * nx + x;
      if (!cur[i]) continue;
      if (z > 0) out[i - ny * nx] = 1; if (z < nz - 1) out[i + ny * nx] = 1;
      if (y > 0) out[i - nx] = 1; if (y < ny - 1) out[i + nx] = 1;
      if (x > 0) out[i - 1] = 1; if (x < nx - 1) out[i + 1] = 1;
    }
    cur = out;
  }
  return cur === mask ? Uint8Array.from(mask) : cur;
}
