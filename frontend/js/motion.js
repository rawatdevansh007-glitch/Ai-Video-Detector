/**
 * VeritasVideo Editorial Motion Layer
 * Vanilla slow-reveal animations, staggered children, and subtle parallax.
 * Strictly respects prefers-reduced-motion.
 */

/**
 * Checks if the user prefers reduced motion.
 * @returns {boolean}
 */
export function prefersReducedMotion() {
  return window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
}

/**
 * Initializes single-shot intersection observer reveal on [data-reveal] elements.
 * Threshold: 0.15, rootMargin: "0px 0px -10% 0px"
 */
export function revealInit() {
  const elements = document.querySelectorAll('[data-reveal]:not(.is-visible)');
  if (!elements.length) return;

  if (prefersReducedMotion()) {
    elements.forEach(el => el.classList.add('is-visible'));
    return;
  }

  const observer = new IntersectionObserver((entries, obs) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.classList.add('is-visible');
        obs.unobserve(entry.target);
      }
    });
  }, {
    threshold: 0.15,
    rootMargin: '0px 0px -10% 0px'
  });

  elements.forEach(el => observer.observe(el));
  return observer;
}

/**
 * Staggers reveal timing of children inside [data-reveal-stagger] containers.
 * Applies an 80ms stagger delay per child element.
 */
export function revealStagger() {
  const staggerContainers = document.querySelectorAll('[data-reveal-stagger]');
  if (!staggerContainers.length) return;

  staggerContainers.forEach(container => {
    const children = Array.from(container.children);
    children.forEach((child, index) => {
      child.style.setProperty('--i', index);
      if (!child.hasAttribute('data-reveal')) {
        child.setAttribute('data-reveal', '');
      }
    });
  });

  // Ensure newly tagged children are observed
  revealInit();
}

/**
 * Subtle parallax translateY on scroll for [data-parallax] elements.
 * Max translation clamped to 40px with requestAnimationFrame throttle.
 */
export function parallaxSubtle() {
  const elements = document.querySelectorAll('[data-parallax]');
  if (!elements.length || prefersReducedMotion()) return;

  let ticking = false;

  const updateParallax = () => {
    const scrollY = window.pageYOffset || document.documentElement.scrollTop;

    elements.forEach(el => {
      const rect = el.getBoundingClientRect();
      // Only compute when element is near or within viewport
      if (rect.top < window.innerHeight + 200 && rect.bottom > -200) {
        const speed = parseFloat(el.getAttribute('data-parallax-speed') || '0.06');
        const rawOffset = (scrollY - (el.offsetTop || 0)) * speed;
        // Clamp to maximum 40px
        const clampedOffset = Math.min(Math.max(rawOffset, -40), 40);
        el.style.transform = `translateY(${clampedOffset.toFixed(1)}px)`;
      }
    });

    ticking = false;
  };

  const onScroll = () => {
    if (!ticking) {
      requestAnimationFrame(updateParallax);
      ticking = true;
    }
  };

  window.addEventListener('scroll', onScroll, { passive: true });
  updateParallax();
}

// Global auto-init if loaded directly in browser context
if (typeof window !== 'undefined') {
  window.addEventListener('DOMContentLoaded', () => {
    revealStagger();
    revealInit();
    parallaxSubtle();
  });
}
