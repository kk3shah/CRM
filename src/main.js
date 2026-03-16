// Styles
import './styles/main.css';
import './styles/components.css';
import './styles/responsive.css';

// Three.js modules
import { getScene } from './three/scene.js';
import { HeroParticles } from './three/heroParticles.js';
import { ContactOrbs } from './three/contactOrbs.js';
// Service icons now use CSS-animated SVG logos (no Three.js)

// Animations
import { initScrollAnimations, refreshScrollTrigger } from './animations/scrollAnimations.js';
import { initHeroAnimations } from './animations/textAnimations.js';
import { initMicroInteractions } from './animations/microInteractions.js';

// Utils
import { initSmoothScroll } from './utils/lenis.js';

// GSAP ScrollTrigger integration with Lenis
import gsap from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';

gsap.registerPlugin(ScrollTrigger);

async function init() {
  console.log('Initializing Dedolytics 2.0...');

  // Initialize smooth scrolling
  const lenis = initSmoothScroll();

  // Connect Lenis to GSAP ScrollTrigger
  lenis.on('scroll', ScrollTrigger.update);
  gsap.ticker.add((time) => {
    lenis.raf(time * 1000);
  });
  gsap.ticker.lagSmoothing(0);

  // Initialize Three.js scene
  const scene = getScene();

  // Add particle systems
  const heroParticles = new HeroParticles();
  scene.addModule(heroParticles);

  const contactOrbs = new ContactOrbs();
  scene.addModule(contactOrbs);

  // Listen for smooth scroll events to update Three.js
  window.addEventListener('smoothscroll', (e) => {
    scene.updateScroll(e.detail.scrollY);
  });

  // Service logos are CSS-animated SVGs (no Three.js init needed)

  // Initialize animations
  initHeroAnimations();
  initScrollAnimations();
  initMicroInteractions();

  // Hero interactivity: cursor spotlight + interactive dashboards
  initHeroSpotlight();
  initInteractiveDashboards();

  // Navigation
  setupNavigation();

  // Contact form
  setupContactForm();

  // Loading screen
  hideLoader();

  // Refresh ScrollTrigger after all content loaded
  window.addEventListener('load', () => {
    refreshScrollTrigger();
  });

  console.log('Dedolytics 2.0 initialized successfully');
}

function setupNavigation() {
  const navToggle = document.querySelector('.nav-toggle');
  const navLinks = document.querySelector('.nav-links');

  navToggle?.addEventListener('click', () => {
    const isOpen = navLinks?.classList.toggle('open');
    navToggle.classList.toggle('open', isOpen);
    navToggle.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
    document.body.style.overflow = isOpen ? 'hidden' : '';
  });

  navLinks?.querySelectorAll('a').forEach((link) => {
    link.addEventListener('click', () => {
      navLinks.classList.remove('open');
      navToggle?.classList.remove('open');
      navToggle?.setAttribute('aria-expanded', 'false');
      document.body.style.overflow = '';
    });
  });
}

function setupContactForm() {
  const form = document.getElementById('contactForm');
  if (!form) return;

  form.addEventListener('submit', (e) => {
    e.preventDefault();

    const name = form.querySelector('[name="name"]')?.value || '';
    const email = form.querySelector('[name="email"]')?.value || '';
    const message = form.querySelector('[name="message"]')?.value || '';

    const subject = encodeURIComponent(`Inquiry from ${name}`);
    const body = encodeURIComponent(`From: ${name}\nEmail: ${email}\n\n${message}`);

    window.location.href = `mailto:hello@dedolytics.org?subject=${subject}&body=${body}`;
  });
}

function hideLoader() {
  const loader = document.getElementById('loader');

  // Show body immediately (FOUC prevention — inline CSS hides it)
  document.body.classList.add('loaded');

  if (!loader) return;

  // Wait for loader animation to complete, then hide
  setTimeout(() => {
    loader.classList.add('loaded');
  }, 1200);
}

function initHeroSpotlight() {
  const hero = document.querySelector('.hero');
  if (!hero) return;

  // Create cursor-following spotlight element
  const spotlight = document.createElement('div');
  spotlight.className = 'hero-spotlight';
  spotlight.style.cssText = `
    position: absolute; top: 0; left: 0;
    width: 500px; height: 500px;
    background: radial-gradient(circle, rgba(200,164,94,0.08) 0%, rgba(200,164,94,0.02) 30%, transparent 70%);
    border-radius: 50%; pointer-events: none; z-index: 1;
    transform: translate(-50%, -50%); transition: opacity 0.3s ease;
    opacity: 0; will-change: transform;
  `;
  hero.appendChild(spotlight);

  hero.addEventListener('mousemove', (e) => {
    const rect = hero.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    spotlight.style.left = x + 'px';
    spotlight.style.top = y + 'px';
    spotlight.style.opacity = '1';
  });

  hero.addEventListener('mouseleave', () => {
    spotlight.style.opacity = '0';
  });
}

function initInteractiveDashboards() {
  const dashboards = document.querySelectorAll('.dashboard-float');
  const caseStudyLinks = [
    'projects/redsticker.html',
    'projects/replenishment.html',
    'projects/executive.html',
    'projects/vendor.html',
    null, // Float 5 has no link
  ];

  dashboards.forEach((dash, i) => {
    // Make dashboards clickable (pointer events)
    dash.style.pointerEvents = 'auto';
    dash.style.cursor = caseStudyLinks[i] ? 'pointer' : 'default';

    // Hover: scale up, brighten, add stronger glow
    dash.addEventListener('mouseenter', () => {
      dash.style.zIndex = '10';
      dash.style.boxShadow = '0 30px 80px rgba(0,0,0,0.7), 0 0 40px rgba(200,164,94,0.2)';
      const img = dash.querySelector('img');
      if (img) img.style.filter = 'brightness(0.8) saturate(1.3) contrast(1.1)';
      // Scale up slightly
      const current = getComputedStyle(dash).transform;
      dash.style.transform = current + ' scale(1.08)';
    });

    dash.addEventListener('mouseleave', () => {
      dash.style.zIndex = '';
      dash.style.boxShadow = '';
      const img = dash.querySelector('img');
      if (img) img.style.filter = '';
      dash.style.transform = '';
    });

    // Click to navigate to case study
    if (caseStudyLinks[i]) {
      dash.addEventListener('click', () => {
        window.location.href = caseStudyLinks[i];
      });
    }
  });
}

// Start
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', init);
} else {
  init();
}
