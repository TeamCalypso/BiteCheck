// Application Entry Point: Three.js Setup, Particle Engine, and UI Orchestration
import * as THREE from 'three';
import { ParticleEngine } from './particles/particleEngine.js';
import { setupUI } from './ui/interface.js';

class App {
  constructor() {
    this.container = document.getElementById('canvas-container');
    this.clock = new THREE.Clock();
    
    this.initThree();
    this.initEngine();
    this.initUI();
    this.setupListeners();
    this.animate();
  }

  initThree() {
    // 1. Scene
    this.scene = new THREE.Scene();
    this.scene.fog = new THREE.FogExp2(0x000000, 0.0018);

    // 2. Camera
    const aspect = window.innerWidth / window.innerHeight;
    this.camera = new THREE.PerspectiveCamera(55, aspect, 0.1, 1000);
    this.camera.position.set(0, 0, 95);

    // 3. Renderer with high performance WebGL config
    this.renderer = new THREE.WebGLRenderer({
      powerPreference: 'high-performance',
      antialias: false,
      stencil: false,
      depth: false,
      alpha: true
    });

    this.renderer.setSize(window.innerWidth, window.innerHeight);
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    this.renderer.setClearColor(0x000000, 1.0);
    this.container.appendChild(this.renderer.domElement);

    // Camera target for gentle cinematic parallax
    this.baseCameraX = 0;
    this.mouseParallaxX = 0;
    this.mouseParallaxY = 0;
    this.cameraTarget = new THREE.Vector3(0, 0, 95);
    this.lookTarget = new THREE.Vector3(0, 0, 0);
  }

  initEngine() {
    this.engine = new ParticleEngine(this.scene, this.camera, this.renderer);
    // Start intro sequence immediately
    this.engine.startIntro();
  }

  initUI() {
    setupUI(this.engine);
  }

  setupListeners() {
    window.addEventListener('resize', this.onWindowResize.bind(this));

    // Subtle 3D mouse parallax on camera
    window.addEventListener('mousemove', (e) => {
      this.mouseParallaxX = (e.clientX / window.innerWidth) * 2 - 1;
      this.mouseParallaxY = -(e.clientY / window.innerHeight) * 2 + 1;
    });
  }

  onWindowResize() {
    const width = window.innerWidth;
    const height = window.innerHeight;

    this.camera.aspect = width / height;
    this.camera.updateProjectionMatrix();

    this.renderer.setSize(width, height);
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  }

  animate() {
    requestAnimationFrame(this.animate.bind(this));

    const delta = Math.min(this.clock.getDelta(), 0.05); // prevent large delta spikes
    const time = this.clock.getElapsedTime();

    // Responsive cinematic camera framing when inspection bay is open
    const isInspection = Boolean(this.engine && this.engine.isInspectionActive);
    const targetBaseX = isInspection ? -6 : 0;
    const targetLookX = isInspection ? -6 : 0;

    this.baseCameraX = THREE.MathUtils.lerp(this.baseCameraX || 0, targetBaseX, 0.05);
    this.lookTarget.x = THREE.MathUtils.lerp(this.lookTarget.x, targetLookX, 0.05);

    this.cameraTarget.x = (this.baseCameraX || 0) + (this.mouseParallaxX || 0) * 4;
    this.cameraTarget.y = (this.mouseParallaxY || 0) * 4;
    this.cameraTarget.z = 95 - Math.abs((this.mouseParallaxX || 0) * 3);

    // Smooth camera parallax & view tracking
    this.camera.position.lerp(this.cameraTarget, 0.05);
    this.camera.lookAt(this.lookTarget);

    // Update Particle Engine simulation
    if (this.engine) {
      this.engine.update(delta, time);
    }

    this.renderer.render(this.scene, this.camera);
  }
}

// Bootstrap application on DOMContentLoaded
window.addEventListener('DOMContentLoaded', () => {
  new App();
});
