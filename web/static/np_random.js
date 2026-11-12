// NumPy legacy RandomState (MT19937) in JavaScript, so a seed gives the same draws as np.random.seed(seed) in Python.
// Covers what the simulator uses: random_sample / rand, randint (masked rejection), uniform, the polar Box-Muller
// gauss behind randn / normal (with its cached second value), all as in numpy/random/src/legacy + mt19937.

const N = 624, M = 397;

export class RandomState {
  constructor(seed = 0) { this.mt = new Uint32Array(N); this.seed(seed); }

  // np.random.seed(int): mt19937_seed (Knuth's initialiser, the same as init_genrand), clears the cached gauss.
  seed(s) {
    const mt = this.mt;
    mt[0] = s >>> 0;
    for (let i = 1; i < N; i++) {
      const p = mt[i - 1] ^ (mt[i - 1] >>> 30);
      mt[i] = (Math.imul(1812433253, p) + i) >>> 0;
    }
    this.pos = N; this.hasGauss = false; this.gaussVal = 0;
  }

  _gen() {
    const mt = this.mt;
    let y, i = 0;
    for (; i < N - M; i++) { y = (mt[i] & 0x80000000) | (mt[i + 1] & 0x7fffffff); mt[i] = mt[i + M] ^ (y >>> 1) ^ (-(y & 1) & 0x9908b0df); }
    for (; i < N - 1; i++) { y = (mt[i] & 0x80000000) | (mt[i + 1] & 0x7fffffff); mt[i] = mt[i + M - N] ^ (y >>> 1) ^ (-(y & 1) & 0x9908b0df); }
    y = (mt[N - 1] & 0x80000000) | (mt[0] & 0x7fffffff);
    mt[N - 1] = mt[M - 1] ^ (y >>> 1) ^ (-(y & 1) & 0x9908b0df);
    this.pos = 0;
  }

  uint32() {
    if (this.pos >= N) this._gen();
    let y = this.mt[this.pos++];
    y ^= y >>> 11; y ^= (y << 7) & 0x9d2c5680; y ^= (y << 15) & 0xefc60000; y ^= y >>> 18;
    return y >>> 0;
  }

  // random_sample(): 53-bit double in [0, 1)
  random() { const a = this.uint32() >>> 5, b = this.uint32() >>> 6; return (a * 67108864 + b) / 9007199254740992; }

  // np.random.rand(n) / random_sample(n) in C order
  rand(n) { const out = new Float64Array(n); for (let i = 0; i < n; i++) out[i] = this.random(); return out; }

  // np.random.randint(low, high): integers in [low, high) by masked rejection sampling (32-bit path)
  randint(low, high) {
    if (high <= low) throw new Error(`randint: low >= high (${low}, ${high})`);
    const rng = high - 1 - low;
    if (rng === 0) return low;
    let mask = rng; mask |= mask >>> 1; mask |= mask >>> 2; mask |= mask >>> 4; mask |= mask >>> 8; mask |= mask >>> 16;
    mask >>>= 0;
    let v;
    while ((v = (this.uint32() & mask) >>> 0) > rng);
    return low + v;
  }

  uniform(low, high) { return low + (high - low) * this.random(); }

  // legacy_gauss: polar Box-Muller, returns f*x2 and caches f*x1 for the next call
  gauss() {
    if (this.hasGauss) { this.hasGauss = false; const g = this.gaussVal; this.gaussVal = 0; return g; }
    let x1, x2, r2;
    do { x1 = 2 * this.random() - 1; x2 = 2 * this.random() - 1; r2 = x1 * x1 + x2 * x2; } while (r2 >= 1 || r2 === 0);
    const f = Math.sqrt(-2 * Math.log(r2) / r2);
    this.gaussVal = f * x1; this.hasGauss = true;
    return f * x2;
  }

  randn(n) { const out = new Float64Array(n); for (let i = 0; i < n; i++) out[i] = this.gauss(); return out; }
  normal(loc, scale) { return loc + scale * this.gauss(); }
}
