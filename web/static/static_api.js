// Static-site data layer: answers api() calls from the JSON files exported by scripts/build_static.py.
// GET /info, /params and /check were computed by the Python server at build time. POST /check (a Python run for
// custom parameters) needs the local server.
const files = new Map();
async function file(rel) {
  if (!files.has(rel)) files.set(rel, fetch('api/' + rel + '.json').then(r => { if (!r.ok) throw new Error(`${r.status} ${rel}`); return r.json(); }));
  return files.get(rel);
}

export async function staticApi(path, body) {
  if (body) throw new Error('Running the Python simulator on new parameters needs the local app (Python server).');
  return file(path.split('?')[0].replace(/^\/+/, ''));
}
