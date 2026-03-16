import * as THREE from 'three';

/**
 * HeroParticles — Premium ambient particle system.
 * 
 * Gold dust particles that drift gently across the hero section,
 * creating depth and atmosphere without competing with the
 * floating dashboard screenshots. Mouse-reactive for interactivity.
 */
export class HeroParticles {
  constructor() {
    this.group = new THREE.Group();
    this.particleCount = 180;
    this.velocities = [];

    this.createParticleField();
    this.createConnectionLines();
  }

  createParticleField() {
    const positions = new Float32Array(this.particleCount * 3);
    const colors = new Float32Array(this.particleCount * 3);
    const sizes = new Float32Array(this.particleCount);

    const goldColors = [
      new THREE.Color(0xc8a45e),  // gold
      new THREE.Color(0xe8d5a3),  // gold light
      new THREE.Color(0x8a6d2b),  // gold dark
      new THREE.Color(0xf0f0f0),  // white accent
    ];

    for (let i = 0; i < this.particleCount; i++) {
      // Spread particles in a wide, shallow volume
      positions[i * 3] = (Math.random() - 0.5) * 12;
      positions[i * 3 + 1] = (Math.random() - 0.5) * 7;
      positions[i * 3 + 2] = (Math.random() - 0.5) * 5 - 2;

      // Random gold-ish colors
      const color = goldColors[Math.floor(Math.random() * goldColors.length)];
      colors[i * 3] = color.r;
      colors[i * 3 + 1] = color.g;
      colors[i * 3 + 2] = color.b;

      // Varied sizes — mostly small, a few larger
      sizes[i] = Math.random() < 0.85
        ? 0.015 + Math.random() * 0.02
        : 0.04 + Math.random() * 0.03;

      // Store velocity for each particle
      this.velocities.push({
        x: (Math.random() - 0.5) * 0.003,
        y: (Math.random() - 0.5) * 0.002,
        z: (Math.random() - 0.5) * 0.001,
        bobSpeed: 0.3 + Math.random() * 0.4,
        bobAmp: 0.01 + Math.random() * 0.02,
      });
    }

    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
    geometry.setAttribute('color', new THREE.BufferAttribute(colors, 3));
    geometry.setAttribute('size', new THREE.BufferAttribute(sizes, 1));

    const material = new THREE.PointsMaterial({
      size: 0.03,
      vertexColors: true,
      transparent: true,
      opacity: 0.4,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
      sizeAttenuation: true,
    });

    this.particles = new THREE.Points(geometry, material);
    this.group.add(this.particles);
  }

  createConnectionLines() {
    // Subtle connection lines between nearby particles (like a data network)
    const lineCount = 30;
    const positions = new Float32Array(lineCount * 6);
    const pPos = this.particles.geometry.attributes.position.array;

    // Pick random pairs of nearby particles
    for (let i = 0; i < lineCount; i++) {
      const a = Math.floor(Math.random() * this.particleCount);
      let b = Math.floor(Math.random() * this.particleCount);
      if (b === a) b = (a + 1) % this.particleCount;

      positions[i * 6] = pPos[a * 3];
      positions[i * 6 + 1] = pPos[a * 3 + 1];
      positions[i * 6 + 2] = pPos[a * 3 + 2];
      positions[i * 6 + 3] = pPos[b * 3];
      positions[i * 6 + 4] = pPos[b * 3 + 1];
      positions[i * 6 + 5] = pPos[b * 3 + 2];
    }

    const lineGeo = new THREE.BufferGeometry();
    lineGeo.setAttribute('position', new THREE.BufferAttribute(positions, 3));

    const lineMat = new THREE.LineBasicMaterial({
      color: 0xc8a45e,
      transparent: true,
      opacity: 0.05,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
    });

    this.lines = new THREE.LineSegments(lineGeo, lineMat);
    this.group.add(this.lines);
  }

  update(elapsed, delta, mouse, scrollY) {
    if (!this.particles) return;

    const positions = this.particles.geometry.attributes.position.array;
    const scrollProg = Math.min(scrollY / window.innerHeight, 1);

    for (let i = 0; i < this.particleCount; i++) {
      const v = this.velocities[i];

      // Gentle drift
      positions[i * 3] += v.x;
      positions[i * 3 + 1] += v.y + Math.sin(elapsed * v.bobSpeed) * v.bobAmp * 0.01;
      positions[i * 3 + 2] += v.z;

      // Wrap around boundaries
      if (positions[i * 3] > 6) positions[i * 3] = -6;
      if (positions[i * 3] < -6) positions[i * 3] = 6;
      if (positions[i * 3 + 1] > 3.5) positions[i * 3 + 1] = -3.5;
      if (positions[i * 3 + 1] < -3.5) positions[i * 3 + 1] = 3.5;
    }

    this.particles.geometry.attributes.position.needsUpdate = true;

    // Mouse-reactive scene tilt
    this.group.rotation.y = mouse.x * 0.06;
    this.group.rotation.x = -mouse.y * 0.03;

    // Scroll: drift and fade
    this.group.position.y = scrollY * 0.0005;
    this.particles.material.opacity = 0.4 * (1 - scrollProg * 0.7);
    if (this.lines) {
      this.lines.material.opacity = 0.05 * (1 - scrollProg * 0.9);
    }
  }

  onResize() {
    // no special resize handling needed
  }
}
