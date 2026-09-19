// High-Performance Three.js Particle Engine for BiteCheck
// Supports dynamic macro partitioning, scanning convergence, and semantic cluster colorization

import * as THREE from 'three';
import {
  generateLogoAndTextPoints,
  generateSpiritPoints,
  generateScanningCore,
  generateMacroPoints,
} from './shapeGenerators.js';
import { MACRO_CLASS_COLORS } from '../config.js';

export const PARTICLE_STATES = {
  INTRO_SWIRL: 'INTRO_SWIRL',
  INTRO_LOGO: 'INTRO_LOGO',
  INTRO_HOLD: 'INTRO_HOLD',
  INTRO_DISPERSE: 'INTRO_DISPERSE',
  AMBIENT: 'AMBIENT',
  SCANNING: 'SCANNING',
  MOLECULES: 'MOLECULES',
  NOT_FOOD: 'NOT_FOOD',
};

// 3D Centers for up to 8 dynamic macro clusters
// Widely spread across the open left canvas area so every molecule has its own space
const CLUSTER_CENTERS = [
  [-50, 16, 0],   // Cluster 0 (Top left)
  [-16, 16, 0],   // Cluster 1 (Top right of open area)
  [-50, -16, 0],  // Cluster 2 (Bottom left)
  [-16, -16, 0],  // Cluster 3 (Bottom right of open area)
  [-33, 0, 0],    // Cluster 4 (Center of open area)
  [-33, 24, 0],   // Cluster 5 (Upper center)
  [-33, -24, 0],  // Cluster 6 (Lower center)
  [-60, 0, 0],    // Cluster 7 (Far left)
];

export class ParticleEngine {
  constructor(scene, camera, renderer) {
    this.scene = scene;
    this.camera = camera;
    this.renderer = renderer;

    this.count = 36000;
    this.currentState = PARTICLE_STATES.INTRO_SWIRL;
    this.stateTime = 0;
    this.isInspectionActive = false;

    // Mouse tracking in 3D
    this.mouse = new THREE.Vector2(-9999, -9999);
    this.mouseTarget = new THREE.Vector2(-9999, -9999);
    this.mouseWorld = new THREE.Vector3(-9999, -9999, 0);

    // Buffers
    this.currentPos = new Float32Array(this.count * 3);
    this.targetPos = new Float32Array(this.count * 3);
    this.scales = new Float32Array(this.count);
    this.colors = new Float32Array(this.count * 3);
    this.clusterIds = new Float32Array(this.count);

    // Dynamic rotation angles for clusters
    this.clusterRotations = new Float32Array(8);

    // Target sets
    this.logoPoints = null;
    this.ambientPoints = null;

    // Callbacks
    this.onIntroComplete = null;
    this.onStateChange = null;

    this.initBuffers();
    this.createParticleMesh();
    this.setupEvents();
  }

  initBuffers() {
    const spiritPoints = generateSpiritPoints(this.count);
    for (let i = 0; i < this.count * 3; i++) {
      this.currentPos[i] = spiritPoints[i];
      this.targetPos[i] = spiritPoints[i];
      // Default pearl white/slate color
      this.colors[i] = 0.88 + (Math.random() - 0.5) * 0.12;
    }

    for (let i = 0; i < this.count; i++) {
      this.scales[i] = 0.85 + Math.random() * 0.45;
      this.clusterIds[i] = 0;
    }

    // Logo & BiteCheck typography
    this.logoPoints = generateLogoAndTextPoints(this.count);
    this.logoColors = this.logoPoints.colors;

    // Ambient points
    this.ambientPoints = new Float32Array(this.count * 3);
    for (let i = 0; i < this.count; i++) {
      const idx = i * 3;
      this.ambientPoints[idx] = (Math.random() - 0.5) * 220;
      this.ambientPoints[idx + 1] = (Math.random() - 0.5) * 120;
      this.ambientPoints[idx + 2] = (Math.random() - 0.5) * 60;
    }
  }

  createParticleMesh() {
    this.geometry = new THREE.BufferGeometry();
    this.geometry.setAttribute('position', new THREE.BufferAttribute(this.currentPos, 3));
    this.geometry.setAttribute('aScale', new THREE.BufferAttribute(this.scales, 1));
    this.geometry.setAttribute('aColor', new THREE.BufferAttribute(this.colors, 3));
    this.geometry.setAttribute('aCluster', new THREE.BufferAttribute(this.clusterIds, 1));

    // High performance shader with semantic cluster coloring & lighting
    this.material = new THREE.ShaderMaterial({
      uniforms: {
        uTime: { value: 0 },
        uPointSize: { value: 2.8 },
        uLightDir: { value: new THREE.Vector3(0.45, 0.75, 0.8).normalize() },
        uShadowDarkness: { value: 0.42 },
        uTurbulence: { value: 1.8 },
        uColorIntensity: { value: 0.0 }, // 0.0 for ambient white, 1.0 for vibrant cluster colors
      },
      vertexShader: `
        attribute float aScale;
        attribute vec3 aColor;
        attribute float aCluster;
        varying vec3 vColor;
        varying float vCluster;
        uniform float uPointSize;
        uniform float uTime;
        uniform float uTurbulence;
        uniform float uColorIntensity;

        void main() {
          vCluster = aCluster;
          // Blend particle color towards semantic color
          vec3 baseWhite = vec3(0.92, 0.94, 0.98);
          vColor = mix(baseWhite, aColor, uColorIntensity);

          vec3 pos = position;

          // GPU-accelerated fluid turbulence
          if (uTurbulence > 0.001) {
            vec3 wave = vec3(
              sin(pos.y * 0.06 + uTime * 0.8) * cos(pos.z * 0.06 + uTime * 0.5),
              cos(pos.x * 0.06 + uTime * 0.7) * sin(pos.z * 0.06 + uTime * 0.6),
              sin(pos.x * 0.06 + uTime * 0.6) * cos(pos.y * 0.06 + uTime * 0.7)
            ) * uTurbulence;
            pos += wave;
          }

          vec4 worldPos = modelMatrix * vec4(pos, 1.0);
          vec4 mvPosition = viewMatrix * worldPos;
          float vDepth = -mvPosition.z;

          float size = uPointSize * aScale * (120.0 / max(vDepth, 20.0));
          gl_PointSize = clamp(size, 2.0, 5.5);
          gl_Position = projectionMatrix * mvPosition;
        }
      `,
      fragmentShader: `
        varying vec3 vColor;
        varying float vCluster;
        uniform vec3 uLightDir;
        uniform float uShadowDarkness;

        void main() {
          vec2 coord = (gl_PointCoord - vec2(0.5)) * 2.0;
          float r2 = dot(coord, coord);
          if (r2 > 1.0) discard;

          float z = sqrt(1.0 - r2);
          vec3 normal = normalize(vec3(coord.x, -coord.y, z));

          float diffuse = max(dot(normal, uLightDir), 0.0);
          float ambient = 0.40;
          float lighting = ambient + diffuse * (1.0 - uShadowDarkness);

          float rim = pow(1.0 - z, 2.2) * 0.35;
          lighting += rim;

          vec3 finalColor = vColor * clamp(lighting, 0.3, 1.3);
          float edgeAlpha = smoothstep(1.0, 0.82, r2);

          gl_FragColor = vec4(finalColor, edgeAlpha);
        }
      `,
      transparent: true,
      depthTest: true,
      depthWrite: true,
      blending: THREE.NormalBlending,
    });

    this.points = new THREE.Points(this.geometry, this.material);
    this.scene.add(this.points);
  }

  setupEvents() {
    window.addEventListener('mousemove', (e) => {
      this.mouseTarget.x = (e.clientX / window.innerWidth) * 2 - 1;
      this.mouseTarget.y = -(e.clientY / window.innerHeight) * 2 + 1;
    });

    window.addEventListener(
      'touchmove',
      (e) => {
        if (e.touches.length > 0) {
          this.mouseTarget.x = (e.touches[0].clientX / window.innerWidth) * 2 - 1;
          this.mouseTarget.y = -(e.touches[0].clientY / window.innerHeight) * 2 + 1;
        }
      },
      { passive: true }
    );
  }

  updateMouseWorld() {
    this.mouse.lerp(this.mouseTarget, 0.2);

    const vector = new THREE.Vector3(this.mouse.x, this.mouse.y, 0.5);
    vector.unproject(this.camera);
    const dir = vector.sub(this.camera.position).normalize();
    const distance = -this.camera.position.z / dir.z;
    const pos = this.camera.position.clone().add(dir.multiplyScalar(distance));

    this.mouseWorld.copy(pos);
  }

  startIntro() {
    this.currentState = PARTICLE_STATES.INTRO_SWIRL;
    this.stateTime = 0;
    this.material.uniforms.uColorIntensity.value = 0.0;
    this.material.uniforms.uTurbulence.value = 2.4;

    const spiritPoints = generateSpiritPoints(this.count);
    for (let i = 0; i < this.count * 3; i++) {
      this.targetPos[i] = spiritPoints[i];
    }
  }

  skipIntro() {
    this.transitionToAmbient();
  }

  transitionToAmbient() {
    this.currentState = PARTICLE_STATES.AMBIENT;
    this.stateTime = 0;
    this.material.uniforms.uColorIntensity.value = 0.0;
    this.material.uniforms.uTurbulence.value = 1.4;

    for (let i = 0; i < this.count * 3; i++) {
      this.targetPos[i] = this.ambientPoints[i];
      this.colors[i] = 0.88 + (Math.random() - 0.5) * 0.12;
    }
    this.geometry.attributes.aColor.needsUpdate = true;

    if (this.onIntroComplete) {
      this.onIntroComplete();
    }
    if (this.onStateChange) {
      this.onStateChange(this.currentState);
    }
  }

  /**
   * SCANNING STATE: Converges particles into a swirling central quantum core
   * Covering the 3-5s network latency of the Bedrock pipeline.
   */
  startScanning() {
    this.currentState = PARTICLE_STATES.SCANNING;
    this.stateTime = 0;
    this.material.uniforms.uColorIntensity.value = 0.8;
    this.material.uniforms.uTurbulence.value = 2.2;

    const scanPoints = generateScanningCore(this.count, [0, 0, 0]);

    // Electric cyan and amber scanning colors
    for (let i = 0; i < this.count; i++) {
      const idx = i * 3;
      this.targetPos[idx] = scanPoints[idx];
      this.targetPos[idx + 1] = scanPoints[idx + 1];
      this.targetPos[idx + 2] = scanPoints[idx + 2];

      const isCyan = Math.random() < 0.7;
      if (isCyan) {
        this.colors[idx] = 0.22;
        this.colors[idx + 1] = 0.75;
        this.colors[idx + 2] = 0.98;
      } else {
        this.colors[idx] = 0.98;
        this.colors[idx + 1] = 0.75;
        this.colors[idx + 2] = 0.15;
      }
    }
    this.geometry.attributes.aColor.needsUpdate = true;

    if (this.onStateChange) {
      this.onStateChange(this.currentState);
    }
  }

  /**
   * Decomposes particles into 3D molecular clusters based on nutrition.macros[]
   */
  decomposeIntoMacros(nutrition) {
    if (!nutrition || !nutrition.macros || nutrition.macros.length === 0) {
      this.transitionToNonFoodState();
      return;
    }

    this.currentState = PARTICLE_STATES.MOLECULES;
    this.stateTime = 0;
    this.material.uniforms.uColorIntensity.value = 1.0;
    this.material.uniforms.uTurbulence.value = 0.4;

    const macros = nutrition.macros;
    let offset = 0;

    for (let c = 0; c < macros.length; c++) {
      const macro = macros[c];
      const isLast = c === macros.length - 1;
      const clusterCount = isLast
        ? this.count - offset
        : Math.floor(this.count * (macro.pct / 100));

      const center = CLUSTER_CENTERS[c % CLUSTER_CENTERS.length];
      const clusterPoints = generateMacroPoints(macro.key, clusterCount, center);

      // Color mapping from class (GOOD, NEUTRAL, WATCH, UNKNOWN)
      const colorToken = MACRO_CLASS_COLORS[macro.class] || MACRO_CLASS_COLORS.UNKNOWN;
      const [r, g, b] = colorToken.rgb;

      for (let i = 0; i < clusterCount; i++) {
        const targetIdx = (offset + i) * 3;
        const srcIdx = i * 3;

        this.targetPos[targetIdx] = clusterPoints[srcIdx];
        this.targetPos[targetIdx + 1] = clusterPoints[srcIdx + 1];
        this.targetPos[targetIdx + 2] = clusterPoints[srcIdx + 2];

        // Slight natural hue jitter
        const jitter = (Math.random() - 0.5) * 0.08;
        this.colors[targetIdx] = Math.max(0, Math.min(1, r + jitter));
        this.colors[targetIdx + 1] = Math.max(0, Math.min(1, g + jitter));
        this.colors[targetIdx + 2] = Math.max(0, Math.min(1, b + jitter));

        this.clusterIds[offset + i] = c;
      }

      offset += clusterCount;
    }

    this.geometry.attributes.aColor.needsUpdate = true;
    this.geometry.attributes.aCluster.needsUpdate = true;

    if (this.onStateChange) {
      this.onStateChange(this.currentState);
    }
  }

  /**
   * Non-Food or Empty Nutrition State
   */
  transitionToNonFoodState() {
    this.currentState = PARTICLE_STATES.NOT_FOOD;
    this.stateTime = 0;
    this.material.uniforms.uColorIntensity.value = 0.8;
    this.material.uniforms.uTurbulence.value = 1.0;

    for (let i = 0; i < this.count; i++) {
      const idx = i * 3;
      this.targetPos[idx] = this.ambientPoints[idx] * 0.75;
      this.targetPos[idx + 1] = this.ambientPoints[idx + 1] * 0.75;
      this.targetPos[idx + 2] = this.ambientPoints[idx + 2] * 0.75;

      // Soft slate warning hue
      this.colors[idx] = 0.55;
      this.colors[idx + 1] = 0.60;
      this.colors[idx + 2] = 0.68;
    }

    this.geometry.attributes.aColor.needsUpdate = true;

    if (this.onStateChange) {
      this.onStateChange(this.currentState);
    }
  }

  setInspectionActive(active) {
    this.isInspectionActive = active;
  }

  update(delta, time) {
    this.stateTime += delta;
    this.updateMouseWorld();

    const uniforms = this.material.uniforms;
    uniforms.uTime.value = time;

    // State sequencer for initial sequence
    if (this.currentState === PARTICLE_STATES.INTRO_SWIRL) {
      if (this.stateTime > 1.0) {
        this.currentState = PARTICLE_STATES.INTRO_LOGO;
        this.stateTime = 0;
        uniforms.uTurbulence.value = 0.35;
        uniforms.uColorIntensity.value = 1.0;

        for (let i = 0; i < this.count * 3; i++) {
          this.targetPos[i] = this.logoPoints[i];
          if (this.logoColors) {
            this.colors[i] = this.logoColors[i];
          }
        }
        this.geometry.attributes.aColor.needsUpdate = true;
        if (this.onStateChange) this.onStateChange(this.currentState);
      }
    } else if (this.currentState === PARTICLE_STATES.INTRO_LOGO) {
      if (this.stateTime > 1.6) {
        this.currentState = PARTICLE_STATES.INTRO_HOLD;
        this.stateTime = 0;
        uniforms.uTurbulence.value = 0.12;
      }
    } else if (this.currentState === PARTICLE_STATES.INTRO_HOLD) {
      if (this.stateTime > 0.8) {
        this.transitionToAmbient();
      }
    }

    // Smooth Euler integration / attraction
    const positions = this.geometry.attributes.position.array;
    const lerpSpeed =
      this.currentState === PARTICLE_STATES.SCANNING
        ? 0.08
        : this.currentState === PARTICLE_STATES.INTRO_LOGO
        ? 0.065
        : 0.045;

    for (let i = 0; i < this.count * 3; i++) {
      positions[i] += (this.targetPos[i] - positions[i]) * lerpSpeed;
    }

    // Interactive mouse repulsion in ambient and molecule states
    if (
      this.currentState === PARTICLE_STATES.AMBIENT ||
      this.currentState === PARTICLE_STATES.MOLECULES
    ) {
      const mx = this.mouseWorld.x;
      const my = this.mouseWorld.y;
      const repelDistSq = 24.0 * 24.0;

      for (let i = 0; i < this.count; i++) {
        const idx = i * 3;
        const dx = positions[idx] - mx;
        const dy = positions[idx + 1] - my;
        const d2 = dx * dx + dy * dy;

        if (d2 < repelDistSq && d2 > 0.01) {
          const force = (1.0 - Math.sqrt(d2) / 24.0) * 1.8;
          positions[idx] += (dx / Math.sqrt(d2)) * force;
          positions[idx + 1] += (dy / Math.sqrt(d2)) * force;
        }
      }
    }

    this.geometry.attributes.position.needsUpdate = true;
  }
}
