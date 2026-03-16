import * as THREE from 'three';

export class ContactOrbs {
  constructor() {
    this.group = new THREE.Group();
    this.orbCount = 6;
    this.orbs = [];

    this.createOrbs();
  }

  createOrbs() {
    const goldColors = [0xc8a45e, 0xe8d5a3, 0x8a6d2b, 0xd4af37];

    for (let i = 0; i < this.orbCount; i++) {
      const geometry = new THREE.SphereGeometry(0.05 + Math.random() * 0.1, 16, 16);
      const material = new THREE.MeshBasicMaterial({
        color: goldColors[Math.floor(Math.random() * goldColors.length)],
        transparent: true,
        opacity: 0.15 + Math.random() * 0.15,
      });

      const orb = new THREE.Mesh(geometry, material);

      // Position in a spread around the contact section area
      orb.position.set(
        (Math.random() - 0.5) * 8,
        (Math.random() - 0.5) * 4 - 8, // Lower in the scene for contact section
        (Math.random() - 0.5) * 3 - 2
      );

      orb.userData = {
        speed: 0.2 + Math.random() * 0.5,
        offsetX: Math.random() * Math.PI * 2,
        offsetY: Math.random() * Math.PI * 2,
        amplitude: 0.3 + Math.random() * 0.5,
      };

      this.orbs.push(orb);
      this.group.add(orb);
    }

    // Add subtle glow particles around orbs
    const glowGeo = new THREE.BufferGeometry();
    const glowCount = 50;
    const positions = new Float32Array(glowCount * 3);

    for (let i = 0; i < glowCount; i++) {
      positions[i * 3] = (Math.random() - 0.5) * 10;
      positions[i * 3 + 1] = (Math.random() - 0.5) * 5 - 8;
      positions[i * 3 + 2] = (Math.random() - 0.5) * 4 - 2;
    }

    glowGeo.setAttribute('position', new THREE.BufferAttribute(positions, 3));

    const glowMat = new THREE.PointsMaterial({
      color: 0xc8a45e,
      size: 2,
      transparent: true,
      opacity: 0.08,
      blending: THREE.AdditiveBlending,
      sizeAttenuation: true,
    });

    this.glowParticles = new THREE.Points(glowGeo, glowMat);
    this.group.add(this.glowParticles);
  }

  update(elapsed) {
    this.orbs.forEach((orb) => {
      const { speed, offsetX, offsetY, amplitude } = orb.userData;
      orb.position.x += Math.sin(elapsed * speed + offsetX) * 0.002;
      orb.position.y += Math.cos(elapsed * speed + offsetY) * 0.001;
      orb.scale.setScalar(1 + Math.sin(elapsed * speed * 2) * 0.1);
    });
  }
}
