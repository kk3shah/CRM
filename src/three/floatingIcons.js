import * as THREE from 'three';

class ServiceIcon {
  constructor(canvas, type) {
    this.canvas = canvas;
    this.type = type;

    this.scene = new THREE.Scene();
    this.camera = new THREE.PerspectiveCamera(50, 1, 0.1, 100);
    this.camera.position.z = 3;

    this.renderer = new THREE.WebGLRenderer({
      canvas: this.canvas,
      antialias: true,
      alpha: true,
    });
    this.renderer.setSize(64, 64);
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    this.renderer.setClearColor(0x000000, 0);

    this.clock = new THREE.Clock();
    this.createGeometry();
    this.addLights();
    this.animate();
  }

  createGeometry() {
    const gold = new THREE.MeshStandardMaterial({
      color: 0xc8a45e,
      metalness: 0.8,
      roughness: 0.2,
      emissive: 0xc8a45e,
      emissiveIntensity: 0.15,
    });

    const wireGold = new THREE.MeshStandardMaterial({
      color: 0xc8a45e,
      metalness: 0.9,
      roughness: 0.1,
      wireframe: true,
      transparent: true,
      opacity: 0.4,
    });

    switch (this.type) {
      case 'chart': {
        this.mesh = new THREE.Group();
        const heights = [0.6, 1.0, 0.4, 0.8, 1.2];
        heights.forEach((h, i) => {
          const bar = new THREE.Mesh(
            new THREE.BoxGeometry(0.15, h, 0.15),
            gold.clone()
          );
          bar.position.x = (i - 2) * 0.25;
          bar.position.y = h / 2 - 0.5;
          this.mesh.add(bar);
        });
        break;
      }

      case 'database': {
        this.mesh = new THREE.Group();
        for (let i = 0; i < 3; i++) {
          const cylinder = new THREE.Mesh(
            new THREE.CylinderGeometry(0.5, 0.5, 0.2, 16),
            i === 0 ? gold.clone() : wireGold.clone()
          );
          cylinder.position.y = (i - 1) * 0.35;
          this.mesh.add(cylinder);
        }
        break;
      }

      case 'snowflake': {
        this.mesh = new THREE.Group();
        for (let i = 0; i < 6; i++) {
          const arm = new THREE.Mesh(
            new THREE.BoxGeometry(0.06, 0.8, 0.06),
            gold.clone()
          );
          arm.rotation.z = (i / 6) * Math.PI * 2;
          this.mesh.add(arm);

          // Branch tips
          const tip = new THREE.Mesh(
            new THREE.BoxGeometry(0.04, 0.3, 0.04),
            gold.clone()
          );
          tip.position.y = 0.3;
          tip.position.x = 0.12;
          tip.rotation.z = (i / 6) * Math.PI * 2 + 0.4;
          this.mesh.add(tip);
        }
        // Center gem
        const center = new THREE.Mesh(
          new THREE.OctahedronGeometry(0.12),
          gold.clone()
        );
        this.mesh.add(center);
        break;
      }

      case 'search': {
        this.mesh = new THREE.Group();
        // Lens ring
        const ring = new THREE.Mesh(
          new THREE.TorusGeometry(0.35, 0.04, 8, 32),
          gold.clone()
        );
        this.mesh.add(ring);

        // Handle
        const handle = new THREE.Mesh(
          new THREE.CylinderGeometry(0.04, 0.04, 0.5, 8),
          gold.clone()
        );
        handle.rotation.z = Math.PI / 4;
        handle.position.x = 0.4;
        handle.position.y = -0.4;
        this.mesh.add(handle);

        // Lens glow
        const lens = new THREE.Mesh(
          new THREE.CircleGeometry(0.3, 32),
          new THREE.MeshStandardMaterial({
            color: 0xc8a45e,
            transparent: true,
            opacity: 0.1,
            emissive: 0xc8a45e,
            emissiveIntensity: 0.3,
          })
        );
        this.mesh.add(lens);
        break;
      }

      default: {
        this.mesh = new THREE.Mesh(
          new THREE.OctahedronGeometry(0.5),
          gold
        );
      }
    }

    this.scene.add(this.mesh);
  }

  addLights() {
    const ambient = new THREE.AmbientLight(0xffffff, 0.4);
    this.scene.add(ambient);

    const point = new THREE.PointLight(0xc8a45e, 1, 10);
    point.position.set(2, 2, 3);
    this.scene.add(point);

    const backLight = new THREE.PointLight(0x8a6d2b, 0.5, 10);
    backLight.position.set(-2, -1, -2);
    this.scene.add(backLight);
  }

  animate() {
    if (!this.canvas.isConnected) return;

    requestAnimationFrame(() => this.animate());
    const elapsed = this.clock.getElapsedTime();

    if (this.mesh) {
      this.mesh.rotation.y = elapsed * 0.5;
      this.mesh.rotation.x = Math.sin(elapsed * 0.3) * 0.1;
      this.mesh.position.y = Math.sin(elapsed * 0.8) * 0.05;
    }

    this.renderer.render(this.scene, this.camera);
  }

  dispose() {
    this.renderer.dispose();
  }
}

export function initServiceIcons() {
  const canvases = document.querySelectorAll('.service-canvas');
  const icons = [];

  canvases.forEach((canvas) => {
    const type = canvas.dataset.type;
    if (type) {
      icons.push(new ServiceIcon(canvas, type));
    }
  });

  return icons;
}
