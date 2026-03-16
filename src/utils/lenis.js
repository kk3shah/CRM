import Lenis from 'lenis';

let lenisInstance = null;

export function initSmoothScroll() {
  lenisInstance = new Lenis({
    duration: 1.2,
    easing: (t) => Math.min(1, 1.001 - Math.pow(2, -10 * t)),
    orientation: 'vertical',
    gestureOrientation: 'vertical',
    smoothWheel: true,
    touchMultiplier: 2,
  });

  function raf(time) {
    lenisInstance.raf(time);
    requestAnimationFrame(raf);
  }
  requestAnimationFrame(raf);

  // Update scroll for GSAP ScrollTrigger
  lenisInstance.on('scroll', (e) => {
    // Dispatch custom event for Three.js scene
    window.dispatchEvent(new CustomEvent('smoothscroll', { detail: { scrollY: e.scroll } }));
  });

  // Anchor links
  document.querySelectorAll('a[href^="#"]').forEach((link) => {
    link.addEventListener('click', (e) => {
      const href = link.getAttribute('href');
      if (href === '#') return;

      const target = document.querySelector(href);
      if (target) {
        e.preventDefault();
        lenisInstance.scrollTo(target, { offset: -80 });
      }
    });
  });

  return lenisInstance;
}

export function getLenis() {
  return lenisInstance;
}
