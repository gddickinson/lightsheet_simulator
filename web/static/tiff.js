// Minimal ImageJ hyperstack TIFF writer (no library): 32-bit float, uncompressed, little-endian, one page per
// (t, z, c) plane in ImageJ's default order (channel fastest, then slice, then frame). The voxel size goes in the
// file: X/YResolution = pixels per micrometre and "unit=micron", "spacing=<z voxel>" in the ImageJ description, so
// Fiji / tifffile read the physical scale back.

export function writeTiff(sample, { frames = null } = {}) {
  const [nz, ny, nx] = sample.size, [vz, vy, vx] = sample.voxel_um, C = sample.C;
  const ts = frames ?? sample.data.map((_, t) => t), T = ts.length, pages = T * nz * C;
  const desc = `ImageJ=1.11a\nimages=${pages}\nchannels=${C}\nslices=${nz}\nframes=${T}\nhyperstack=true\n` +
    `unit=micron\nspacing=${vz}\nloop=false\nmin=0.0\nmax=1.0\n\0`;
  const NT = 14, ifdSize = 2 + NT * 12 + 4, extra = 16, plane = nx * ny * 4;
  const descOff = 8, metaStart = descOff + desc.length + (desc.length % 2);
  const dataStart = metaStart + pages * (ifdSize + extra);
  const buf = new ArrayBuffer(dataStart + pages * plane), dv = new DataView(buf), u8 = new Uint8Array(buf);
  dv.setUint16(0, 0x4949); dv.setUint16(2, 42, true); dv.setUint32(4, metaStart, true);
  for (let i = 0; i < desc.length; i++) u8[descOff + i] = desc.charCodeAt(i) & 0x7f;
  const rat = um => [1000000, Math.max(1, Math.round(um * 1000000))];  // pixels per micrometre = 1 / voxel size
  let p = 0;
  for (const t of ts) for (let z = 0; z < nz; z++) for (let c = 0; c < C; c++, p++) {
    const ifd = metaStart + p * (ifdSize + extra), ext = ifd + ifdSize, img = dataStart + p * plane;
    const tags = [
      [256, 4, 1, nx], [257, 4, 1, ny], [258, 3, 1, 32], [259, 3, 1, 1], [262, 3, 1, 1],
      [270, 2, desc.length, descOff], [273, 4, 1, img], [277, 3, 1, 1], [278, 4, 1, ny],
      [279, 4, 1, plane], [282, 5, 1, ext], [283, 5, 1, ext + 8], [296, 3, 1, 1], [339, 3, 1, 3],
    ];
    const list = p === 0 ? tags : tags.filter(tg => tg[0] !== 270);  // description on the first page only
    dv.setUint16(ifd, list.length, true);
    list.forEach(([tag, type, count, val], i) => {
      const o = ifd + 2 + i * 12;
      dv.setUint16(o, tag, true); dv.setUint16(o + 2, type, true); dv.setUint32(o + 4, count, true);
      if (type === 3) dv.setUint16(o + 8, val, true); else dv.setUint32(o + 8, val, true);
    });
    dv.setUint32(ifd + 2 + list.length * 12, p === pages - 1 ? 0 : ifd + ifdSize + extra, true);
    const [xn, xd] = rat(vx), [yn, yd] = rat(vy);
    dv.setUint32(ext, xn, true); dv.setUint32(ext + 4, xd, true); dv.setUint32(ext + 8, yn, true); dv.setUint32(ext + 12, yd, true);
    const v = sample.data[t][c], base = z * ny * nx;
    for (let i = 0; i < ny * nx; i++) dv.setFloat32(img + i * 4, v[base + i], true);
  }
  return new Uint8Array(buf);
}
