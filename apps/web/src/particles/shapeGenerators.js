// Mathematical and Vector Point Generators for BiteCheck
// Generates:
// 1. Dual-ribbon Shield/Eye Logo with open central safety aperture
// 2. Crisp "BiteCheck" Typography
// 3. True 3D Molecular Formations: Protein Alpha-Helix, Triglyceride Lipid, Glucose Ring, Micronutrient Lattice, Fiber Strands, Sodium Salt Cubes, Unspecified Cloud
// 4. Scanning Quantum Core (Convergent state covering network analysis)

/**
 * Generates vector points along a 3D line segment
 */
export function linePoints(p1, p2, count, outArr, startIdx, jitter = 0.3) {
  for (let i = 0; i < count; i++) {
    const t = i / count;
    const idx = (startIdx + i) * 3;
    outArr[idx] = p1[0] + (p2[0] - p1[0]) * t + (Math.random() - 0.5) * jitter;
    outArr[idx + 1] = p1[1] + (p2[1] - p1[1]) * t + (Math.random() - 0.5) * jitter;
    outArr[idx + 2] = p1[2] + (p2[2] - p1[2]) * t + (Math.random() - 0.5) * jitter;
  }
}

/**
 * Generates points for a spherical atom cluster
 */
export function atomPoints(center, radius, count, outArr, startIdx) {
  for (let i = 0; i < count; i++) {
    const idx = (startIdx + i) * 3;
    const u = Math.random();
    const v = Math.random();
    const theta = u * 2.0 * Math.PI;
    const phi = Math.acos(2.0 * v - 1.0);
    const r = Math.cbrt(Math.random()) * radius;
    const sinPhi = Math.sin(phi);
    outArr[idx] = center[0] + r * sinPhi * Math.cos(theta);
    outArr[idx + 1] = center[1] + r * sinPhi * Math.sin(theta);
    outArr[idx + 2] = center[2] + r * Math.cos(phi);
  }
}

/**
 * Generates points for a cube/lattice structure (e.g. sodium chloride salt)
 */
export function cubePoints(center, size, count, outArr, startIdx) {
  const half = size * 0.5;
  for (let i = 0; i < count; i++) {
    const idx = (startIdx + i) * 3;
    const face = Math.floor(Math.random() * 6);
    const u = (Math.random() - 0.5) * size;
    const v = (Math.random() - 0.5) * size;
    let x = 0, y = 0, z = 0;
    if (face === 0) { x = half; y = u; z = v; }
    else if (face === 1) { x = -half; y = u; z = v; }
    else if (face === 2) { x = u; y = half; z = v; }
    else if (face === 3) { x = u; y = -half; z = v; }
    else if (face === 4) { x = u; y = v; z = half; }
    else { x = u; y = v; z = -half; }

    outArr[idx] = center[0] + x + (Math.random() - 0.5) * 0.3;
    outArr[idx + 1] = center[1] + y + (Math.random() - 0.5) * 0.3;
    outArr[idx + 2] = center[2] + z + (Math.random() - 0.5) * 0.3;
  }
}

/**
 * Generates razor-sharp points and colors for the Barcode + Sprout Leaf Logo and BITECHECK typography
 */
export function generateLogoAndTextPoints(count) {
  const positions = new Float32Array(count * 3);
  const colors = new Float32Array(count * 3);

  const width = 1600;
  const height = 1100;
  const canvas = document.createElement('canvas');
  canvas.width = width;
  canvas.height = height;
  const ctx = canvas.getContext('2d', { willReadFrequently: true });

  ctx.fillStyle = '#000000';
  ctx.fillRect(0, 0, width, height);

  // 1. Draw Barcode on top
  const bcLeft = 400;
  const bcRight = 1200;
  const bcTop = 120;
  const bcBottom = 480;
  const bcHeight = bcBottom - bcTop;

  // Cut-out notch for the green sprout leaf (lower right of barcode)
  const cutoutLeft = 900;
  const cutoutRight = 1150;
  const cutoutTop = 320;

  // Bar pattern generator with varying widths
  const barPattern = [
    12, 10, 6, 8, 16, 6, 10, 14, 6, 8, 20, 8, 6, 12, 10, 6, 18, 8, 14, 6, 10, 16,
    8, 6, 12, 8, 14, 10, 6, 16, 8, 10, 6, 14, 8, 18, 6, 10, 12, 8, 14, 6, 10, 16,
    8, 12, 6, 18, 10, 6, 14, 8, 20, 6, 10, 12, 8, 16, 6, 10, 14, 8, 12
  ];

  ctx.fillStyle = '#ffffff';
  let curX = bcLeft;
  for (let i = 0; i < barPattern.length && curX < bcRight; i++) {
    const barW = barPattern[i];
    const spaceW = (i % 3 === 0 ? 10 : i % 2 === 0 ? 8 : 6);

    // If bar falls inside the cut-out, shorten it to stop above cutoutTop
    if (curX + barW >= cutoutLeft && curX <= cutoutRight) {
      ctx.fillRect(curX, bcTop, barW, cutoutTop - bcTop - 12);
    } else {
      ctx.fillRect(curX, bcTop, barW, bcHeight);
    }

    curX += barW + spaceW;
  }

  // 2. Draw Green Sprout / Seedling inside the cutout
  const sproutCenterX = (cutoutLeft + cutoutRight) / 2;
  const sproutBaseY = bcBottom - 5;

  ctx.save();
  // Draw Left Leaf
  ctx.fillStyle = '#22c55e';
  ctx.beginPath();
  ctx.moveTo(sproutCenterX, sproutBaseY);
  ctx.bezierCurveTo(
    sproutCenterX - 60, sproutBaseY - 25,
    sproutCenterX - 95, sproutBaseY - 95,
    sproutCenterX - 55, sproutBaseY - 135
  );
  ctx.bezierCurveTo(
    sproutCenterX - 25, sproutBaseY - 135,
    sproutCenterX - 12, sproutBaseY - 60,
    sproutCenterX, sproutBaseY
  );
  ctx.fill();

  // Draw Right Leaf
  ctx.fillStyle = '#16a34a';
  ctx.beginPath();
  ctx.moveTo(sproutCenterX, sproutBaseY);
  ctx.bezierCurveTo(
    sproutCenterX + 60, sproutBaseY - 25,
    sproutCenterX + 95, sproutBaseY - 95,
    sproutCenterX + 55, sproutBaseY - 135
  );
  ctx.bezierCurveTo(
    sproutCenterX + 25, sproutBaseY - 135,
    sproutCenterX + 12, sproutBaseY - 60,
    sproutCenterX, sproutBaseY
  );
  ctx.fill();

  // Central stalk line
  ctx.strokeStyle = '#22c55e';
  ctx.lineWidth = 8;
  ctx.lineCap = 'round';
  ctx.beginPath();
  ctx.moveTo(sproutCenterX, sproutBaseY);
  ctx.lineTo(sproutCenterX, sproutBaseY - 45);
  ctx.stroke();
  ctx.restore();

  // 3. Draw "BITECHECK" Typography
  ctx.save();
  ctx.font = '900 155px "Space Grotesk", "Plus Jakarta Sans", "Inter", sans-serif';
  ctx.textBaseline = 'top';

  const biteText = 'BITE';
  const checkText = 'CHECK';
  const biteWidth = ctx.measureText(biteText).width;
  const checkWidth = ctx.measureText(checkText).width;
  const totalTextWidth = biteWidth + checkWidth + 12;
  const textStartX = 800 - totalTextWidth / 2;
  const textY = 560;

  // BITE in pure crisp white
  ctx.fillStyle = '#ffffff';
  ctx.fillText(biteText, textStartX, textY);

  // CHECK in vibrant emerald green
  ctx.fillStyle = '#22c55e';
  ctx.fillText(checkText, textStartX + biteWidth + 12, textY);
  ctx.restore();

  // 4. Sample canvas pixels into 3D points & colors
  const imgData = ctx.getImageData(0, 0, width, height);
  const data = imgData.data;
  const whitePixels = [];
  const greenPixels = [];

  for (let y = 0; y < height; y += 3) {
    for (let x = 0; x < width; x += 3) {
      const idx = (y * width + x) * 4;
      const r = data[idx];
      const g = data[idx + 1];
      const b = data[idx + 2];
      const a = data[idx + 3];

      if (a > 60 && (r > 35 || g > 35 || b > 35)) {
        // Map to 3D world space (centered nicely in view)
        const x3d = (x - 800) * 0.058;
        const y3d = -(y - 450) * 0.058;

        const isGreen = g > r + 25 && g > b + 20;
        if (isGreen) {
          greenPixels.push({ x: x3d, y: y3d });
        } else {
          whitePixels.push({ x: x3d, y: y3d });
        }
      }
    }
  }

  // 5. Populate particles with exact positions and colors
  const greenCount = Math.floor(count * 0.28);
  const whiteCount = count - greenCount;

  // Green particles (Leaf sprout + CHECK)
  for (let i = 0; i < greenCount; i++) {
    const idx = i * 3;
    if (greenPixels.length > 0) {
      const p = greenPixels[Math.floor(Math.random() * greenPixels.length)];
      positions[idx] = p.x + (Math.random() - 0.5) * 0.35;
      positions[idx + 1] = p.y + (Math.random() - 0.5) * 0.35;
      positions[idx + 2] = (Math.random() - 0.5) * 1.5;
    } else {
      positions[idx] = (Math.random() - 0.5) * 20;
      positions[idx + 1] = (Math.random() - 0.5) * 10;
      positions[idx + 2] = (Math.random() - 0.5) * 2;
    }
    colors[idx] = 0.13;
    colors[idx + 1] = 0.85;
    colors[idx + 2] = 0.37;
  }

  // White particles (Barcode bars + BITE)
  for (let i = 0; i < whiteCount; i++) {
    const idx = (greenCount + i) * 3;
    if (whitePixels.length > 0) {
      const p = whitePixels[Math.floor(Math.random() * whitePixels.length)];
      positions[idx] = p.x + (Math.random() - 0.5) * 0.35;
      positions[idx + 1] = p.y + (Math.random() - 0.5) * 0.35;
      positions[idx + 2] = (Math.random() - 0.5) * 1.5;
    } else {
      positions[idx] = (Math.random() - 0.5) * 40;
      positions[idx + 1] = (Math.random() - 0.5) * 20;
      positions[idx + 2] = (Math.random() - 0.5) * 2;
    }
    colors[idx] = 0.95;
    colors[idx + 1] = 0.98;
    colors[idx + 2] = 1.0;
  }

  positions.colors = colors;
  return positions;
}

/**
 * Generates initial Spirit vortex swirl positions
 */
export function generateSpiritPoints(count) {
  const positions = new Float32Array(count * 3);
  const arms = 3;
  const turns = 4.5;
  const maxR = 90.0;

  for (let i = 0; i < count; i++) {
    const idx = i * 3;
    const prog = Math.pow(Math.random(), 0.75);
    const r = prog * maxR + 2.0;
    const armAngle = (Math.floor(Math.random() * arms) * (Math.PI * 2)) / arms;
    const swirl = prog * turns * Math.PI * 2;
    const angle = armAngle + swirl + (Math.random() - 0.5) * 0.35;

    const zDisp = (1.0 - prog) * 24.0 * Math.sin(swirl * 0.5);

    positions[idx] = Math.cos(angle) * r;
    positions[idx + 1] = Math.sin(angle) * r * 0.75;
    positions[idx + 2] = zDisp + (Math.random() - 0.5) * 6.0;
  }

  return positions;
}

/**
 * SCANNING STATE: Converges particles into an active, swirling inspection core.
 */
export function generateScanningCore(count, center = [0, 0, 0]) {
  const positions = new Float32Array(count * 3);
  const coreRadius = 8.5;
  const haloRadius = 22.0;

  for (let i = 0; i < count; i++) {
    const idx = i * 3;
    const isCore = Math.random() < 0.65;

    if (isCore) {
      // Dense central singularity
      const u = Math.random();
      const v = Math.random();
      const theta = u * 2.0 * Math.PI;
      const phi = Math.acos(2.0 * v - 1.0);
      const r = Math.pow(Math.random(), 0.5) * coreRadius;
      const sinPhi = Math.sin(phi);

      positions[idx] = center[0] + r * sinPhi * Math.cos(theta);
      positions[idx + 1] = center[1] + r * sinPhi * Math.sin(theta);
      positions[idx + 2] = center[2] + r * Math.cos(phi);
    } else {
      // Orbiting inspection accretion disk
      const angle = Math.random() * Math.PI * 2;
      const r = coreRadius + Math.random() * (haloRadius - coreRadius);
      positions[idx] = center[0] + Math.cos(angle) * r;
      positions[idx + 1] = center[1] + (Math.random() - 0.5) * 4.0;
      positions[idx + 2] = center[2] + Math.sin(angle) * r;
    }
  }

  return positions;
}

/**
 * 1. Protein Alpha-Helix
 */
export function generateProteinMolecule(count, center = [-28, 2, 0]) {
  const positions = new Float32Array(count * 3);
  if (count <= 0) return positions;

  const height = 36.0;
  const radius = 5.0;
  const turns = 3.8;

  const strandCount = Math.floor(count * 0.5);
  const rungCount = Math.floor(count * 0.25);
  const atomCount = count - strandCount - rungCount;

  for (let i = 0; i < strandCount; i++) {
    const idx = i * 3;
    const prog = i / Math.max(strandCount, 1);
    const t = prog * Math.PI * 2 * turns;
    const strand = i % 2 === 0 ? 0 : 0.45;
    const r = radius + (strand > 0 ? 0.8 : -0.8) + (Math.random() - 0.5) * 0.5;
    const angle = t + strand;

    positions[idx] = center[0] + Math.cos(angle) * r;
    positions[idx + 1] = center[1] + (prog - 0.5) * height + (Math.random() - 0.5) * 0.5;
    positions[idx + 2] = center[2] + Math.sin(angle) * r;
  }

  let offset = strandCount;
  const numRungs = 18;
  const perRung = Math.floor(rungCount / numRungs);

  for (let r = 0; r < numRungs; r++) {
    const prog = r / numRungs;
    const t = prog * Math.PI * 2 * turns;
    const y = center[1] + (prog - 0.5) * height;

    const p1 = [center[0] + Math.cos(t) * radius, y, center[2] + Math.sin(t) * radius];
    const p2 = [center[0] + Math.cos(t + Math.PI) * (radius * 0.35), y, center[2] + Math.sin(t + Math.PI) * (radius * 0.35)];

    const curOffset = offset + r * perRung;
    const curCount = r === numRungs - 1 ? count - atomCount - curOffset : perRung;
    linePoints(p1, p2, curCount, positions, curOffset, 0.4);
  }

  offset = strandCount + rungCount;
  const numClusters = 10;
  const perCluster = Math.floor(atomCount / numClusters);

  for (let c = 0; c < numClusters; c++) {
    const prog = (c + 0.5) / numClusters;
    const t = prog * Math.PI * 2 * turns;
    const y = center[1] + (prog - 0.5) * height;
    const rDist = radius + 2.5;
    const clusterCenter = [center[0] + Math.cos(t) * rDist, y, center[2] + Math.sin(t) * rDist];

    const curOffset = offset + c * perCluster;
    const curCount = c === numClusters - 1 ? count - curOffset : perCluster;
    atomPoints(clusterCenter, 1.8, curCount, positions, curOffset);
  }

  return positions;
}

/**
 * 2. Triglyceride / Fat Molecule (Wavy tails)
 */
export function generateFatMolecule(count, center = [28, 14, 0]) {
  const positions = new Float32Array(count * 3);
  if (count <= 0) return positions;

  const tailCount = 3;
  const tailParticles = Math.floor(count * 0.82);
  const headParticles = count - tailParticles;

  const headSpacing = 4.5;
  const perHead = Math.floor(headParticles / 3);
  for (let h = 0; h < 3; h++) {
    const headPos = [center[0] + (h - 1) * headSpacing, center[1] + 8.0, center[2]];
    atomPoints(headPos, 1.6, perHead, positions, h * perHead);
  }

  const offset = headParticles;
  const perTail = Math.floor(tailParticles / tailCount);
  const tailLength = 22.0;

  for (let t = 0; t < tailCount; t++) {
    const xBase = center[0] + (t - 1) * headSpacing;
    const startIdx = offset + t * perTail;
    const curCount = t === tailCount - 1 ? count - startIdx : perTail;

    for (let p = 0; p < curCount; p++) {
      const idx = (startIdx + p) * 3;
      const prog = p / curCount;
      const yDist = prog * tailLength;
      const waveX = Math.sin(yDist * 0.6 + t * 2.0) * 2.4;
      const waveZ = Math.cos(yDist * 0.6 + t * 2.0) * 1.5;

      positions[idx] = xBase + waveX + (Math.random() - 0.5) * 0.4;
      positions[idx + 1] = center[1] + 6.0 - yDist + (Math.random() - 0.5) * 0.4;
      positions[idx + 2] = center[2] + waveZ + (Math.random() - 0.5) * 0.4;
    }
  }

  return positions;
}

/**
 * 3. Carbohydrate Ring / Polymer
 */
export function generateCarbMolecule(count, center = [28, -14, 0]) {
  const positions = new Float32Array(count * 3);
  if (count <= 0) return positions;

  const numRings = 3;
  const ringParticles = Math.floor(count / numRings);
  const ringRadius = 4.5;

  for (let r = 0; r < numRings; r++) {
    const ringCenter = [
      center[0] + (r - 1) * 7.2,
      center[1] + (r % 2 === 0 ? 1.8 : -1.8),
      center[2] + (r - 1) * 1.2,
    ];
    const startIdx = r * ringParticles;
    const curCount = r === numRings - 1 ? count - startIdx : ringParticles;

    for (let i = 0; i < curCount; i++) {
      const idx = (startIdx + i) * 3;
      const angle = (i / curCount) * Math.PI * 2;
      positions[idx] = ringCenter[0] + Math.cos(angle) * ringRadius + (Math.random() - 0.5) * 0.5;
      positions[idx + 1] = ringCenter[1] + Math.sin(angle) * ringRadius + (Math.random() - 0.5) * 0.5;
      positions[idx + 2] = ringCenter[2] + (Math.random() - 0.5) * 1.0;
    }
  }

  return positions;
}

/**
 * 4. Fiber Linear Strands
 */
export function generateFiberStrands(count, center = [-12, -22, 0]) {
  const positions = new Float32Array(count * 3);
  if (count <= 0) return positions;

  const strands = 3;
  const perStrand = Math.floor(count / strands);
  const len = 25.0;

  for (let s = 0; s < strands; s++) {
    const startIdx = s * perStrand;
    const curCount = s === strands - 1 ? count - startIdx : perStrand;
    const yOffset = (s - 1.0) * 3.2;

    for (let i = 0; i < curCount; i++) {
      const idx = (startIdx + i) * 3;
      const prog = i / curCount;
      const x = center[0] + (prog - 0.5) * len;
      const y = center[1] + yOffset + Math.sin(prog * Math.PI * 4 + s) * 1.8;
      const z = center[2] + Math.cos(prog * Math.PI * 4 + s) * 1.2;

      positions[idx] = x + (Math.random() - 0.5) * 0.35;
      positions[idx + 1] = y + (Math.random() - 0.5) * 0.35;
      positions[idx + 2] = z + (Math.random() - 0.5) * 0.35;
    }
  }

  return positions;
}

/**
 * 5. Sodium / Salt Crystalline Cube
 */
export function generateSodiumCrystal(count, center = [14, 2, 0]) {
  const positions = new Float32Array(count * 3);
  if (count <= 0) return positions;
  cubePoints(center, 9.0, count, positions, 0);
  return positions;
}

/**
 * 6. Diffuse Unspecified / Other Nutrient Cloud
 */
export function generateDiffuseCloud(count, center = [0, 0, 0], radius = 7.5) {
  const positions = new Float32Array(count * 3);
  if (count <= 0) return positions;
  atomPoints(center, radius, count, positions, 0);
  return positions;
}

/**
 * Universal dynamic macro point dispatcher.
 * Maps any backend macro key to its 3D molecular structure at an assigned 3D center.
 */
export function generateMacroPoints(macroKey, count, center) {
  switch (macroKey) {
    case 'protein':
      return generateProteinMolecule(count, center);
    case 'fat':
    case 'saturated_fat':
      return generateFatMolecule(count, center);
    case 'carbohydrate':
    case 'sugar':
      return generateCarbMolecule(count, center);
    case 'fiber':
      return generateFiberStrands(count, center);
    case 'sodium':
      return generateSodiumCrystal(count, center);
    default:
      return generateDiffuseCloud(count, center);
  }
}
