// Web Worker: builds the sample off the main thread so the page stays responsive on large volumes.
import { buildSample } from './pipeline.js';

self.onmessage = e => {
  try {
    const s = buildSample(e.data.params, e.data.opts);
    self.postMessage({ ok: true, sample: s }, s.data.flat().map(v => v.buffer));
  } catch (err) {
    self.postMessage({ ok: false, error: err.message });
  }
};
