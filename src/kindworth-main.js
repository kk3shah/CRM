// Styles
import './styles/main.css';
import './styles/components.css';
import './styles/responsive.css';

// Three.js
import { getScene } from './three/scene.js';
import { KindworthNetwork } from './three/kindworthNetwork.js';

// Animations
import { initScrollAnimations, refreshScrollTrigger } from './animations/scrollAnimations.js';
import { initMicroInteractions } from './animations/microInteractions.js';

// GSAP
import gsap from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';

gsap.registerPlugin(ScrollTrigger);

function init() {
  console.log('Initializing Kindworth...');

  // FOUC prevention: show body
  document.body.classList.add('loaded');

  // Three.js scene with network graph
  const scene = getScene();
  const network = new KindworthNetwork();
  scene.addModule(network);

  // GSAP animations
  initScrollAnimations();
  initMicroInteractions();

  // Kindworth-specific animations
  initKindworthAnimations();

  // Visually extravagant hero: floating gradient orbs + cursor spotlight
  initHeroOrbs();
  initHeroSpotlight();

  // Navigation
  setupNavigation();

  // Contact form
  setupContactForm();

  // KQ Score pulse animation
  initKQPulse();

  // Refresh ScrollTrigger after load
  window.addEventListener('load', () => refreshScrollTrigger());

  console.log('Kindworth initialized');
}

function initKindworthAnimations() {
  // Hero entrance
  const heroTitle = document.querySelector('.kindworth-hero .hero-title');
  const heroSubtitle = document.querySelector('.kindworth-hero .hero-subtitle');
  const heroDesc = document.querySelector('.kindworth-hero .hero-desc');
  const kqScore = document.querySelector('.kq-score');
  const heroCta = document.querySelector('.kindworth-hero .hero-cta');

  if (heroTitle) {
    gsap.from(heroTitle, { y: 60, opacity: 0, duration: 1, ease: 'power3.out', delay: 0.3 });
  }
  if (heroSubtitle) {
    gsap.from(heroSubtitle, { y: 30, opacity: 0, duration: 0.8, ease: 'power3.out', delay: 0.6 });
  }
  if (heroDesc) {
    gsap.from(heroDesc, { y: 20, opacity: 0, duration: 0.7, ease: 'power3.out', delay: 0.8 });
  }
  if (kqScore) {
    gsap.from(kqScore, {
      scale: 0.5, opacity: 0, duration: 1,
      ease: 'back.out(1.7)', delay: 1.0
    });
  }
  if (heroCta) {
    gsap.from(heroCta.children, {
      y: 20, opacity: 0, stagger: 0.15,
      duration: 0.6, ease: 'power3.out', delay: 1.2
    });
  }

  // Feature cards staggered entrance
  const featureCards = document.querySelectorAll('.feature-card');
  featureCards.forEach((card, i) => {
    gsap.from(card, {
      y: 50, opacity: 0, duration: 0.7,
      delay: i * 0.1,
      ease: 'power3.out',
      scrollTrigger: {
        trigger: card,
        start: 'top 85%',
        toggleActions: 'play none none none',
      }
    });
  });

  // Dashboard module cards
  const dashModules = document.querySelectorAll('.dashboard-module');
  dashModules.forEach((mod, i) => {
    gsap.from(mod, {
      y: 40, opacity: 0, duration: 0.7,
      delay: i * 0.08,
      ease: 'power3.out',
      scrollTrigger: {
        trigger: mod,
        start: 'top 85%',
        toggleActions: 'play none none none',
      }
    });
  });

  // Pipeline steps
  const pipelineSteps = document.querySelectorAll('.pipeline-step');
  const pipelineArrows = document.querySelectorAll('.pipeline-arrow');
  pipelineSteps.forEach((step, i) => {
    gsap.from(step, {
      x: -30, opacity: 0, duration: 0.6,
      delay: i * 0.15,
      ease: 'power3.out',
      scrollTrigger: {
        trigger: step,
        start: 'top 85%',
        toggleActions: 'play none none none',
      }
    });
  });
  pipelineArrows.forEach((arrow, i) => {
    gsap.from(arrow, {
      opacity: 0, scale: 0.5, duration: 0.4,
      delay: 0.1 + i * 0.15,
      ease: 'back.out(1.7)',
      scrollTrigger: {
        trigger: arrow,
        start: 'top 85%',
        toggleActions: 'play none none none',
      }
    });
  });

  // Problem/Solution cards
  const problemCard = document.querySelector('.problem-card');
  const solutionCard = document.querySelector('.solution-card');
  if (problemCard) {
    gsap.from(problemCard, {
      x: -50, opacity: 0, duration: 0.8, ease: 'power3.out',
      scrollTrigger: { trigger: problemCard, start: 'top 80%' }
    });
  }
  if (solutionCard) {
    gsap.from(solutionCard, {
      x: 50, opacity: 0, duration: 0.8, ease: 'power3.out',
      scrollTrigger: { trigger: solutionCard, start: 'top 80%' }
    });
  }

  // Add tilt effect to feature cards
  const tiltCards = document.querySelectorAll('.feature-card, .dashboard-module');
  tiltCards.forEach(card => {
    card.addEventListener('mousemove', (e) => {
      const rect = card.getBoundingClientRect();
      const x = (e.clientX - rect.left) / rect.width;
      const y = (e.clientY - rect.top) / rect.height;
      const tiltX = (0.5 - y) * 8;
      const tiltY = (x - 0.5) * 8;
      card.style.transform = `perspective(800px) rotateX(${tiltX}deg) rotateY(${tiltY}deg) translateY(-4px)`;
    });
    card.addEventListener('mouseleave', () => {
      card.style.transform = '';
      card.style.transition = 'transform 0.5s ease, border-color 0.3s ease';
      setTimeout(() => { card.style.transition = 'border-color 0.3s ease, transform 0.3s ease'; }, 500);
    });
    card.addEventListener('mouseenter', () => {
      card.style.transition = 'none';
    });
  });
}

function initKQPulse() {
  const kq = document.querySelector('.kq-score');
  if (!kq) return;

  // Pulse animation loop
  gsap.to(kq, {
    boxShadow: '0 0 80px rgba(29, 161, 181, 0.5)',
    scale: 1.05,
    duration: 1.5,
    ease: 'sine.inOut',
    yoyo: true,
    repeat: -1,
  });
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
    const company = form.querySelector('[name="company"]')?.value || '';
    const message = form.querySelector('[name="message"]')?.value || '';

    const subject = encodeURIComponent(`Kindworth Demo Request from ${name}`);
    const body = encodeURIComponent(`From: ${name}\nEmail: ${email}\nCompany: ${company}\n\n${message}`);

    window.location.href = `mailto:hello@dedolytics.org?subject=${subject}&body=${body}`;
  });
}

function initHeroOrbs() {
  const hero = document.querySelector('.kindworth-hero');
  if (!hero) return;

  // Create floating gradient orbs for visual extravagance
  const orbConfigs = [
    { size: 400, color: 'rgba(29, 161, 181, 0.12)', x: '15%', y: '20%', delay: 0 },
    { size: 300, color: 'rgba(79, 209, 197, 0.08)', x: '75%', y: '35%', delay: -3 },
    { size: 250, color: 'rgba(46, 196, 182, 0.1)', x: '60%', y: '70%', delay: -6 },
    { size: 350, color: 'rgba(22, 160, 133, 0.07)', x: '25%', y: '65%', delay: -2 },
    { size: 180, color: 'rgba(29, 161, 181, 0.15)', x: '85%', y: '15%', delay: -4 },
  ];

  const orbContainer = document.createElement('div');
  orbContainer.style.cssText = `
    position: absolute; inset: 0; overflow: hidden;
    pointer-events: none; z-index: 0;
  `;
  hero.style.position = 'relative';
  hero.insertBefore(orbContainer, hero.firstChild);

  orbConfigs.forEach((cfg, i) => {
    const orb = document.createElement('div');
    orb.className = 'kw-hero-orb';
    orb.style.cssText = `
      position: absolute;
      width: ${cfg.size}px; height: ${cfg.size}px;
      left: ${cfg.x}; top: ${cfg.y};
      background: radial-gradient(circle, ${cfg.color} 0%, transparent 70%);
      border-radius: 50%;
      filter: blur(60px);
      animation: kwOrbFloat ${8 + i * 1.5}s ease-in-out infinite;
      animation-delay: ${cfg.delay}s;
      transform: translate(-50%, -50%);
      will-change: transform;
    `;
    orbContainer.appendChild(orb);
  });

  // Inject keyframes for orb animation
  if (!document.getElementById('kw-orb-keyframes')) {
    const style = document.createElement('style');
    style.id = 'kw-orb-keyframes';
    style.textContent = `
      @keyframes kwOrbFloat {
        0%, 100% { transform: translate(-50%, -50%) scale(1) rotate(0deg); }
        25% { transform: translate(-45%, -55%) scale(1.15) rotate(5deg); }
        50% { transform: translate(-55%, -48%) scale(0.9) rotate(-3deg); }
        75% { transform: translate(-48%, -52%) scale(1.1) rotate(4deg); }
      }
    `;
    document.head.appendChild(style);
  }

  // Mouse-reactive: orbs drift toward cursor
  hero.addEventListener('mousemove', (e) => {
    const rect = hero.getBoundingClientRect();
    const x = (e.clientX - rect.left) / rect.width - 0.5;
    const y = (e.clientY - rect.top) / rect.height - 0.5;

    const orbs = orbContainer.querySelectorAll('.kw-hero-orb');
    orbs.forEach((orb, i) => {
      const intensity = 15 + i * 8;
      orb.style.marginLeft = `${x * intensity}px`;
      orb.style.marginTop = `${y * intensity}px`;
    });
  });
}

function initHeroSpotlight() {
  const hero = document.querySelector('.kindworth-hero');
  if (!hero) return;

  const spotlight = document.createElement('div');
  spotlight.style.cssText = `
    position: absolute; top: 0; left: 0;
    width: 600px; height: 600px;
    background: radial-gradient(circle, rgba(29,161,181,0.06) 0%, rgba(79,209,197,0.02) 30%, transparent 70%);
    border-radius: 50%; pointer-events: none; z-index: 1;
    transform: translate(-50%, -50%); transition: opacity 0.3s ease;
    opacity: 0; will-change: transform;
  `;
  hero.appendChild(spotlight);

  hero.addEventListener('mousemove', (e) => {
    const rect = hero.getBoundingClientRect();
    spotlight.style.left = (e.clientX - rect.left) + 'px';
    spotlight.style.top = (e.clientY - rect.top) + 'px';
    spotlight.style.opacity = '1';
  });

  hero.addEventListener('mouseleave', () => {
    spotlight.style.opacity = '0';
  });
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', init);
} else {
  init();
}
