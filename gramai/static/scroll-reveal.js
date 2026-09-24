/* Scroll reveal: text sharpens word by word (opacity + blur + slight rotation) as it scrolls in.
   Vanilla port of the React Bits <ScrollReveal /> component, driven by GSAP ScrollTrigger.

   The page translator works on whole text nodes, so splitting a sentence into word spans would make it
   translate word by word. In English the sentence is split into words; in any other language the
   whole paragraph is revealed as one unit and its text is left alone for the translator. */
(function (w) {
  var SEL = '.lp-split-copy > p, .lp-sec-head .lp-sub, .lp-why-item p, .lp-final-copy p';
  var OPT = { baseOpacity: 0.1, enableBlur: true, baseRotation: 3, blurStrength: 4 };
  var made = [];

  function lang() { return (w.I18N && w.I18N.lang && w.I18N.lang()) || 'en'; }

  function reset() {
    made.forEach(function (m) {
      m.tweens.forEach(function (t) { if (t.scrollTrigger) t.scrollTrigger.kill(); t.kill(); });
      w.gsap.set(m.el, { clearProps: 'transform,transformOrigin,opacity,filter,willChange' });
      if (m.split) m.el.textContent = m.en;
    });
    made = [];
  }

  function words(el, text) {
    el.textContent = '';
    text.split(/(\s+)/).forEach(function (part) {
      if (!part) return;
      if (/^\s+$/.test(part)) { el.appendChild(document.createTextNode(part)); return; }
      var s = document.createElement('span');
      s.className = 'word';
      s.textContent = part;
      el.appendChild(s);
    });
    return el.querySelectorAll('.word');
  }

  function build() {
    var gsap = w.gsap, ST = w.ScrollTrigger;
    if (!gsap || !ST) return;
    if (w.matchMedia && w.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
    gsap.registerPlugin(ST);
    reset();

    var english = lang() === 'en';
    document.querySelectorAll(SEL).forEach(function (el) {
      if (!el.offsetParent && el.getClientRects().length === 0) return;
      var m = { el: el, tweens: [], split: false, en: '' };

      gsap.set(el, { transformOrigin: '0% 50%' });
      m.tweens.push(gsap.fromTo(el, { rotate: OPT.baseRotation }, {
        ease: 'none', rotate: 0,
        scrollTrigger: { trigger: el, start: 'top bottom', end: 'bottom bottom', scrub: true }
      }));

      var targets = el;
      var splittable = english && el.children.length === 0 && el.textContent.trim();
      if (splittable) {
        m.split = true;
        m.en = el.textContent;
        targets = words(el, m.en);
      }
      var st = { trigger: el, start: 'top bottom-=20%', end: 'bottom bottom', scrub: true };
      var stagger = m.split ? 0.05 : 0;

      m.tweens.push(gsap.fromTo(targets, { opacity: OPT.baseOpacity, willChange: 'opacity' },
        { ease: 'none', opacity: 1, stagger: stagger, scrollTrigger: st }));
      if (OPT.enableBlur) {
        m.tweens.push(gsap.fromTo(targets, { filter: 'blur(' + OPT.blurStrength + 'px)' },
          { ease: 'none', filter: 'blur(0px)', stagger: stagger, scrollTrigger: st }));
      }
      made.push(m);
    });
    ST.refresh();
  }

  var timer;
  w.ScrollReveal = {
    // Debounced: language switches and font loads can both ask for a rebuild.
    refresh: function () { clearTimeout(timer); timer = setTimeout(build, 60); }
  };
})(window);
