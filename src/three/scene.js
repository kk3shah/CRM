import * as THREE from 'three';

class SceneManager {
  constructor() {
    this.canvas = document.getElementById('three-canvas');
    this.scene = new THREE.Scene();
    this.camera = new THREE.PerspectiveCamera(60, window.innerWidth / window.innerHeight, 0.1, 1000);
    this.camera.position.z = 5;

    this.renderer = new THREE.WebGLRenderer({
      canvas: this.canvas,
      antialias: true,
      alpha: true,
    });
    this.renderer.setSize(window.innerWidth, window.innerHeight);
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    this.renderer.setClearColor(0x000000, 0);

    this.clock = new THREE.Clock();
    this.mouse = new THREE.Vector2(0, 0);
    this.scrollY = 0;
    this.modules = [];

    this.setupListeners();
    this.animate();
  }

  setupListeners() {
    window.addEventListener('resize', () => this.onResize());
    window.addEventListener('mousemove', (e) => {
      this.mouse.x = (e.clientX / window.innerWidth) * 2 - 1;
      this.mouse.y = -(e.clientY / window.innerHeight) * 2 + 1;
    });
  }

  onResize() {
    const w = window.innerWidth;
    const h = window.innerHeight;
    this.camera.aspect = w / h;
    this.camera.updateProjectionMatrix();
    this.renderer.setSize(w, h);
    this.modules.forEach(m => m.onResize?.(w, h));
  }

  addModule(module) {
    this.modules.push(module);
    if (module.mesh) this.scene.add(module.mesh);
    if (module.group) this.scene.add(module.group);
  }

  updateScroll(scrollY) {
    this.scrollY = scrollY;
  }

  animate() {
    requestAnimationFrame(() => this.animate());
    const delta = this.clock.getDelta();
    const elapsed = this.clock.getElapsedTime();

    this.modules.forEach(m => m.update?.(elapsed, delta, this.mouse, this.scrollY));
    this.renderer.render(this.scene, this.camera);
  }
}

let instance = null;

export function getScene() {
  if (!instance) {
    instance = new SceneManager();
  }
  return instance;
}

export { SceneManager };
