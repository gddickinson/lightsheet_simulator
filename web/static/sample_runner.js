// Runs buildSample in a Web Worker (falls back to the main thread if module workers are unavailable).
let worker = null, busy = null;

export async function runSample(params, opts = {}) {
  if (worker === null) {
    try { worker = new Worker(new URL('./worker.js', import.meta.url), { type: 'module' }); } catch { worker = false; }
  }
  if (!worker) return (await import("./pipeline.js")).buildSample(params, opts);
  if (busy) await busy.catch(() => {});
  busy = new Promise((resolve, reject) => {
    worker.onmessage = e => (e.data.ok ? resolve(e.data.sample) : reject(new Error(e.data.error)));
    worker.onerror = e => { worker = false; reject(new Error(e.message || 'worker failed')); };
    worker.postMessage({ params, opts });
  });
  return busy;
}
