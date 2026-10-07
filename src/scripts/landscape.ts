// Draws a loss landscape as contour lines and runs gradient descent across it.
// Every <canvas class="landscape" data-seed="..."> gets its own surface, generated from its seed.

interface Well {
  x: number; // centre, as a fraction of the canvas width
  y: number; // centre, as a fraction of the canvas height
  depth: number; // negative for a basin, positive for a hill
  spread: number; // radius, as a fraction of the canvas half-diagonal
}

interface Descent {
  points: number[]; // x0, y0, x1, y1, ...
  born: number;
}

const CELL = 5; // contour sampling grid, in CSS pixels
const LEVELS = 20;
const DRAW_MS = 2200;
const MAX_DESCENTS = 14;

function hash(text: string) {
  let h = 1779033703 ^ text.length;
  for (let i = 0; i < text.length; i++) {
    h = Math.imul(h ^ text.charCodeAt(i), 3432918353);
    h = (h << 13) | (h >>> 19);
  }
  return h >>> 0;
}

function random(seed: number) {
  return () => {
    seed = (seed + 0x6d2b79f5) | 0;
    let t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

class Landscape {
  private ctx: CanvasRenderingContext2D;
  private contours = document.createElement('canvas');
  private wells: Well[] = [];
  private starts: [number, number][] = [];
  private descents: Descent[] = [];
  private rand: () => number;
  private width = 0;
  private height = 0;
  private radius = 1;
  private frame = 0;
  private still = matchMedia('(prefers-reduced-motion: reduce)').matches;

  constructor(private canvas: HTMLCanvasElement) {
    this.ctx = canvas.getContext('2d')!;
    this.rand = random(hash(canvas.dataset.seed ?? ''));

    for (let i = 0; i < 8; i++) {
      this.wells.push({
        x: 0.06 + this.rand() * 0.88,
        y: 0.1 + this.rand() * 0.8,
        depth: i % 3 === 2 ? 0.45 + this.rand() * 0.5 : -(0.5 + this.rand() * 0.5),
        spread: 0.14 + this.rand() * 0.2,
      });
    }
    const count = Number(canvas.dataset.paths ?? 2);
    for (let i = 0; i < count; i++) this.starts.push([0.08 + this.rand() * 0.84, 0.12 + this.rand() * 0.76]);

    new ResizeObserver(() => this.resize()).observe(canvas);
    matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => this.resize());
    canvas.addEventListener('pointerdown', (event) => {
      const box = canvas.getBoundingClientRect();
      this.descend(event.clientX - box.left, event.clientY - box.top, performance.now());
    });
  }

  private value(x: number, y: number) {
    let total = 0;
    for (const well of this.wells) {
      const dx = x - well.x * this.width;
      const dy = y - well.y * this.height;
      const s = well.spread * this.radius;
      total += well.depth * Math.exp(-(dx * dx + dy * dy) / (2 * s * s));
    }
    return total;
  }

  private gradient(x: number, y: number): [number, number] {
    let gx = 0;
    let gy = 0;
    for (const well of this.wells) {
      const dx = x - well.x * this.width;
      const dy = y - well.y * this.height;
      const s2 = (well.spread * this.radius) ** 2;
      const slope = (-well.depth * Math.exp(-(dx * dx + dy * dy) / (2 * s2))) / s2;
      gx += slope * dx;
      gy += slope * dy;
    }
    return [gx, gy];
  }

  private resize() {
    const box = this.canvas.getBoundingClientRect();
    if (!box.width || !box.height) return;
    const first = this.width === 0;
    const scale = Math.min(devicePixelRatio || 1, 2);
    this.width = box.width;
    this.height = box.height;
    this.radius = Math.hypot(box.width, box.height) / 2;
    for (const layer of [this.canvas, this.contours]) {
      layer.width = Math.round(box.width * scale);
      layer.height = Math.round(box.height * scale);
    }
    this.ctx.setTransform(scale, 0, 0, scale, 0, 0);
    this.drawContours(scale);

    // Paths are in pixels, so a resize starts them over from the same seeded points.
    const now = performance.now();
    this.descents = [];
    this.starts.forEach(([x, y], i) => this.descend(x * this.width, y * this.height, first ? now + 350 + i * 450 : -Infinity));
    this.paint(now);
  }

  private drawContours(scale: number) {
    const ctx = this.contours.getContext('2d')!;
    const cols = Math.ceil(this.width / CELL) + 1;
    const rows = Math.ceil(this.height / CELL) + 1;
    const grid = new Float32Array(cols * rows);
    let low = Infinity;
    let high = -Infinity;
    for (let r = 0; r < rows; r++) {
      for (let c = 0; c < cols; c++) {
        const v = this.value(c * CELL, r * CELL);
        grid[r * cols + c] = v;
        if (v < low) low = v;
        if (v > high) high = v;
      }
    }

    const step = (high - low) / LEVELS;
    const paths = Array.from({ length: LEVELS }, () => new Path2D());
    // Marching squares: for each cell, join the points where a level crosses its edges.
    for (let r = 0; r < rows - 1; r++) {
      for (let c = 0; c < cols - 1; c++) {
        const a = grid[r * cols + c];
        const b = grid[r * cols + c + 1];
        const d = grid[(r + 1) * cols + c];
        const e = grid[(r + 1) * cols + c + 1];
        const from = Math.max(0, Math.ceil((Math.min(a, b, d, e) - low) / step - 0.5));
        const to = Math.min(LEVELS - 1, Math.floor((Math.max(a, b, d, e) - low) / step - 0.5));
        for (let k = from; k <= to; k++) {
          const level = low + (k + 0.5) * step;
          const x = c * CELL;
          const y = r * CELL;
          const cross: number[] = [];
          if (a < level !== b < level) cross.push(x + (CELL * (level - a)) / (b - a), y);
          if (b < level !== e < level) cross.push(x + CELL, y + (CELL * (level - b)) / (e - b));
          if (d < level !== e < level) cross.push(x + (CELL * (level - d)) / (e - d), y + CELL);
          if (a < level !== d < level) cross.push(x, y + (CELL * (level - a)) / (d - a));
          for (let i = 0; i + 3 < cross.length; i += 4) {
            paths[k].moveTo(cross[i], cross[i + 1]);
            paths[k].lineTo(cross[i + 2], cross[i + 3]);
          }
        }
      }
    }

    ctx.setTransform(scale, 0, 0, scale, 0, 0);
    ctx.clearRect(0, 0, this.width, this.height);
    ctx.strokeStyle = getComputedStyle(this.canvas).color;
    ctx.lineWidth = 1;
    paths.forEach((path, k) => {
      // Every fifth line is heavier, like the index contours on a survey map.
      ctx.globalAlpha = k % 5 === 2 ? 0.55 : 0.2;
      ctx.stroke(path);
    });
  }

  /** Gradient descent with momentum and a little noise, from (x, y) until it settles. */
  private descend(x: number, y: number, born: number) {
    const rate = 0.0011 * this.radius * this.radius;
    const points = [x, y];
    let vx = 0;
    let vy = 0;
    let calm = 0;
    for (let i = 0; i < 700 && calm < 12; i++) {
      const [gx, gy] = this.gradient(x, y);
      const kick = Math.hypot(gx, gy) * 0.9;
      vx = 0.82 * vx - rate * (gx + (this.rand() - 0.5) * kick);
      vy = 0.82 * vy - rate * (gy + (this.rand() - 0.5) * kick);
      x += vx;
      y += vy;
      if (x < 0 || y < 0 || x > this.width || y > this.height) break;
      points.push(x, y);
      calm = Math.hypot(vx, vy) < 0.08 ? calm + 1 : 0;
    }
    this.descents.push({ points, born: this.still ? -Infinity : born });
    if (this.descents.length > MAX_DESCENTS) this.descents.shift();
    if (!this.frame) this.frame = requestAnimationFrame((now) => this.paint(now));
  }

  private paint(now: number) {
    const { ctx } = this;
    const style = getComputedStyle(this.canvas);
    const accent = style.getPropertyValue('--accent').trim();
    const paper = style.getPropertyValue('--paper').trim();
    ctx.clearRect(0, 0, this.width, this.height);
    ctx.drawImage(this.contours, 0, 0, this.width, this.height);

    let moving = false;
    ctx.lineWidth = 1.75;
    ctx.lineJoin = 'round';
    ctx.strokeStyle = accent;
    for (const { points, born } of this.descents) {
      const t = Math.min(1, Math.max(0, (now - born) / DRAW_MS));
      if (t < 1) moving = true;
      if (now < born) continue;
      const eased = 1 - (1 - t) ** 3;
      const last = Math.max(1, Math.round(eased * (points.length / 2 - 1)));
      ctx.beginPath();
      ctx.moveTo(points[0], points[1]);
      for (let i = 1; i <= last && i * 2 < points.length; i++) ctx.lineTo(points[i * 2], points[i * 2 + 1]);
      ctx.stroke();

      // where it started (open ring) and where it is now (solid dot)
      ctx.fillStyle = paper;
      ctx.beginPath();
      ctx.arc(points[0], points[1], 3.5, 0, Math.PI * 2);
      ctx.fill();
      ctx.stroke();
      const head = Math.min(last, points.length / 2 - 1) * 2;
      ctx.fillStyle = accent;
      ctx.beginPath();
      ctx.arc(points[head], points[head + 1], 4.5, 0, Math.PI * 2);
      ctx.fill();
    }
    this.frame = moving ? requestAnimationFrame((next) => this.paint(next)) : 0;
  }
}

for (const canvas of document.querySelectorAll<HTMLCanvasElement>('canvas.landscape')) new Landscape(canvas);
