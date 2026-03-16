import * as THREE from 'three';

/**
 * KindworthNetwork — A floating, pulsating network graph
 * representing culture connections between people.
 * 
 * Teal-themed nodes connected by animated lines,
 * mouse-reactive for interactivity.
 */
export class KindworthNetwork {
    constructor() {
        this.group = new THREE.Group();
        this.nodeCount = 50;
        this.nodes = [];
        this.connections = [];

        this.createNodes();
        this.createConnections();
        this.createAmbientDust();
    }

    createNodes() {
        const tealColors = [
            0x1da1b5,  // primary teal
            0x0d8c9e,  // darker teal
            0x4fd1c5,  // bright mint
            0x2ec4b6,  // warm teal
            0x16a085,  // deep teal
        ];

        for (let i = 0; i < this.nodeCount; i++) {
            const isHub = i < 6; // First 6 nodes are "hub" nodes (bigger)
            const radius = isHub ? 0.06 + Math.random() * 0.04 : 0.02 + Math.random() * 0.03;

            const geometry = new THREE.SphereGeometry(radius, 16, 16);
            const color = tealColors[Math.floor(Math.random() * tealColors.length)];
            const material = new THREE.MeshBasicMaterial({
                color,
                transparent: true,
                opacity: isHub ? 0.7 : 0.35 + Math.random() * 0.25,
            });

            const node = new THREE.Mesh(geometry, material);

            // Spread in a wide, shallow volume
            node.position.set(
                (Math.random() - 0.5) * 10,
                (Math.random() - 0.5) * 6,
                (Math.random() - 0.5) * 3 - 2
            );

            node.userData = {
                basePos: node.position.clone(),
                speed: 0.15 + Math.random() * 0.25,
                phase: Math.random() * Math.PI * 2,
                amplitude: 0.02 + Math.random() * 0.04,
                isHub,
                color: new THREE.Color(color),
            };

            // Add glow ring around hub nodes
            if (isHub) {
                const ringGeo = new THREE.RingGeometry(radius * 1.6, radius * 2.2, 24);
                const ringMat = new THREE.MeshBasicMaterial({
                    color,
                    transparent: true,
                    opacity: 0.12,
                    side: THREE.DoubleSide,
                });
                const ring = new THREE.Mesh(ringGeo, ringMat);
                node.add(ring);
            }

            this.nodes.push(node);
            this.group.add(node);
        }
    }

    createConnections() {
        // Connect nearby nodes with lines
        const positions = [];
        const maxDist = 2.8;

        for (let i = 0; i < this.nodeCount; i++) {
            for (let j = i + 1; j < this.nodeCount; j++) {
                const dist = this.nodes[i].position.distanceTo(this.nodes[j].position);
                if (dist < maxDist) {
                    positions.push(
                        this.nodes[i].position.x, this.nodes[i].position.y, this.nodes[i].position.z,
                        this.nodes[j].position.x, this.nodes[j].position.y, this.nodes[j].position.z
                    );
                    this.connections.push({ i, j, dist });
                }
            }
        }

        if (positions.length > 0) {
            const geometry = new THREE.BufferGeometry();
            geometry.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3));

            const material = new THREE.LineBasicMaterial({
                color: 0x1da1b5,
                transparent: true,
                opacity: 0.08,
                blending: THREE.AdditiveBlending,
                depthWrite: false,
            });

            this.linesMesh = new THREE.LineSegments(geometry, material);
            this.group.add(this.linesMesh);
        }
    }

    createAmbientDust() {
        const count = 80;
        const positions = new Float32Array(count * 3);
        const colors = new Float32Array(count * 3);

        const teal = new THREE.Color(0x1da1b5);
        const mint = new THREE.Color(0x4fd1c5);

        for (let i = 0; i < count; i++) {
            positions[i * 3] = (Math.random() - 0.5) * 12;
            positions[i * 3 + 1] = (Math.random() - 0.5) * 8;
            positions[i * 3 + 2] = -2 + (Math.random() - 0.5) * 4;

            const c = Math.random() > 0.5 ? teal : mint;
            colors[i * 3] = c.r;
            colors[i * 3 + 1] = c.g;
            colors[i * 3 + 2] = c.b;
        }

        const geo = new THREE.BufferGeometry();
        geo.setAttribute('position', new THREE.BufferAttribute(positions, 3));
        geo.setAttribute('color', new THREE.BufferAttribute(colors, 3));

        this.dust = new THREE.Points(geo, new THREE.PointsMaterial({
            size: 0.02,
            vertexColors: true,
            transparent: true,
            opacity: 0.2,
            blending: THREE.AdditiveBlending,
            depthWrite: false,
            sizeAttenuation: true,
        }));
        this.group.add(this.dust);
    }

    update(elapsed, delta, mouse, scrollY) {
        const scrollProg = Math.min(scrollY / window.innerHeight, 1);

        // Animate nodes: gentle floating motion
        this.nodes.forEach(node => {
            const { basePos, speed, phase, amplitude, isHub } = node.userData;
            node.position.x = basePos.x + Math.sin(elapsed * speed + phase) * amplitude * 30;
            node.position.y = basePos.y + Math.cos(elapsed * speed * 0.7 + phase) * amplitude * 20;

            // Hub nodes pulse glow
            if (isHub && node.children.length > 0) {
                node.children[0].material.opacity = 0.08 + Math.sin(elapsed * 1.5 + phase) * 0.06;
            }
        });

        // Update connection line positions
        if (this.linesMesh) {
            const posArr = this.linesMesh.geometry.attributes.position.array;
            let idx = 0;
            this.connections.forEach(({ i, j }) => {
                posArr[idx++] = this.nodes[i].position.x;
                posArr[idx++] = this.nodes[i].position.y;
                posArr[idx++] = this.nodes[i].position.z;
                posArr[idx++] = this.nodes[j].position.x;
                posArr[idx++] = this.nodes[j].position.y;
                posArr[idx++] = this.nodes[j].position.z;
            });
            this.linesMesh.geometry.attributes.position.needsUpdate = true;
        }

        // Mouse-reactive scene tilt
        this.group.rotation.y = mouse.x * 0.08;
        this.group.rotation.x = -mouse.y * 0.04;

        // Scroll fade
        this.group.position.y = scrollY * 0.0005;
        this.nodes.forEach(n => {
            n.material.opacity = n.userData.isHub
                ? 0.7 * (1 - scrollProg * 0.6)
                : (0.35 + Math.random() * 0.05) * (1 - scrollProg * 0.6);
        });

        // Dust drift
        if (this.dust) {
            const dp = this.dust.geometry.attributes.position.array;
            for (let i = 0; i < dp.length; i += 3) {
                dp[i + 1] += Math.sin(elapsed * 0.3 + dp[i] * 1.5) * 0.0003;
            }
            this.dust.geometry.attributes.position.needsUpdate = true;
            this.dust.material.opacity = 0.2 * (1 - scrollProg * 0.8);
        }
    }

    onResize() {
        // no special resize handling needed
    }
}
