---
name: liquid-glass
description: "Apple-inspired WebGL and SVG optical refraction Liquid Glass effect library based on dashersw/liquid-glass-js. Use when implementing realistic frosted glass, visionOS glassmorphism, Snell's law refraction, edge rim lighting, and nested glass UI elements."
---

# Liquid Glass UI Skill (`dashersw/liquid-glass-js`)

This skill provides comprehensive instructions, design tokens, mathematical principles, and implementation patterns for Apple-inspired **Liquid Glass** UI effects based on [`dashersw/liquid-glass-js`](https://github.com/dashersw/liquid-glass-js).

---

## 1. Core Principles of Liquid Glass

Traditional CSS glassmorphism relies solely on `backdrop-filter: blur(...)`. True **Liquid Glass** as pioneered in Apple visionOS and implemented in `dashersw/liquid-glass-js` simulates real physical optics:

1. **Optical Refraction (Snell's Law):**
   Light passing through curved glass bends inward toward the center and produces distortion along the perimeter bevels.
2. **Specular Rim Lighting & Bevel Highlights:**
   Glancing ambient light creates a continuous luminous edge highlight along top/left boundaries and a subtle shadow on opposite edges.
3. **Multi-layer Dispersion & Depth:**
   Backdrop defocus is paired with color saturation enhancement (`saturate(180% - 200%)`) and subtle tinting so content underneath remains vibrant without muddying.
4. **Nested Glass Architecture:**
   Child elements (buttons, pills, indicators) sit inside the parent glass container and act as optical lenses, sampling and refracting through the parent container's surface.
5. **Fluid Micro-Interactions:**
   Hover and active states alter the refraction index, producing a smooth liquid displacement and luminous caustic response.

---

## 2. Mathematical Shader & Optical Model

In `dashersw/liquid-glass-js`, the fragment shader computes the surface normal `N` based on the distance from the nearest boundary:

```glsl
// Surface normal calculation for rounded rects / capsules
float edgeDist = length(max(abs(p) - (size - radius), 0.0)) - radius;
float normalZ = sqrt(max(0.0, 1.0 - pow(clamp(-edgeDist / rimWidth, 0.0, 1.0), 2.0)));
vec3 normal = normalize(vec3(gradientXY, normalZ));

// Snell's Law refraction displacement vector
vec2 refractionOffset = normal.xy * (1.0 - 1.0 / ior) * refractionIntensity;
vec4 backgroundSample = texture2D(u_sceneTexture, screenUV + refractionOffset);
```

For zero-dependency web environments where running a heavy WebGL canvas context per element is impractical, SVG displacement shaders provide the exact same optical displacement:

```xml
<svg style="position: absolute; width: 0; height: 0; pointer-events: none;">
  <defs>
    <filter id="liquidGlassRefraction" x="-20%" y="-20%" width="140%" height="140%">
      <feTurbulence type="fractalNoise" baseFrequency="0.04 0.95" numOctaves="2" result="noise" />
      <feDisplacementMap in="SourceGraphic" in2="noise" scale="3.5" xChannelSelector="R" yChannelSelector="G" result="refracted" />
      <feGaussianBlur in="refracted" stdDeviation="0.4" result="smoothRefraction" />
      <feMerge>
        <feMergeNode in="smoothRefraction" />
        <feMergeNode in="SourceGraphic" opacity="0.8" />
      </feMerge>
    </filter>
  </defs>
</svg>
```

---

## 3. Design Tokens & CSS Variables

Use these standardized design tokens when applying Liquid Glass to containers, navigation docks, or cards:

```css
:root {
  /* Liquid Glass Surface Tints */
  --liquid-glass-bg-primary: linear-gradient(
    135deg,
    rgba(255, 255, 255, 0.28) 0%,
    rgba(240, 245, 255, 0.16) 40%,
    rgba(99, 102, 241, 0.12) 80%,
    rgba(79, 70, 229, 0.22) 100%
  );
  --liquid-glass-bg-hover: linear-gradient(
    135deg,
    rgba(255, 255, 255, 0.38) 0%,
    rgba(240, 245, 255, 0.24) 40%,
    rgba(99, 102, 241, 0.20) 80%,
    rgba(79, 70, 229, 0.32) 100%
  );

  /* Specular Rim & Bevel Highlights */
  --liquid-glass-border: 1px solid rgba(255, 255, 255, 0.45);
  --liquid-glass-border-luminous: 1.5px solid rgba(255, 255, 255, 0.65);

  /* Optical Inset & Caustic Shadows */
  --liquid-glass-shadow-dock: 
    inset 0 1.5px 2px 0 rgba(255, 255, 255, 0.7),
    inset -1.5px 0 3px 0 rgba(255, 255, 255, 0.35),
    inset 0 -1.5px 3px 0 rgba(99, 102, 241, 0.25),
    inset 1.5px 0 2px 0 rgba(255, 255, 255, 0.4),
    8px 0 36px 0 rgba(79, 70, 229, 0.16),
    2px 0 10px 0 rgba(0, 0, 0, 0.04);

  /* Lens Button Nested Inset Shadows */
  --liquid-glass-shadow-lens:
    inset 0 1px 1.5px 0 rgba(255, 255, 255, 0.75),
    inset 0 -1px 2px 0 rgba(0, 0, 0, 0.08),
    0 4px 14px 0 rgba(31, 38, 135, 0.14);

  /* Optical Blur Kernel */
  --liquid-glass-blur: blur(28px) saturate(190%) brightness(1.06);
  --liquid-glass-blur-heavy: blur(36px) saturate(210%) brightness(1.08);
}
```

---

## 4. Implementation Pattern: Fixed Liquid Glass Navigation Dock

For persistent sidebar navigation docks:

```css
.liquid-glass-dock {
  width: 76px;
  height: 100vh;
  position: fixed;
  top: 0;
  left: 0;
  z-index: 100;

  /* Optical Refraction & Frosted Glass Layer */
  background: var(--liquid-glass-bg-primary);
  backdrop-filter: var(--liquid-glass-blur);
  -webkit-backdrop-filter: var(--liquid-glass-blur);

  /* Specular Rim Light & Bevel Highlights */
  border-right: 1.5px solid rgba(255, 255, 255, 0.5);
  border-top: 1px solid rgba(255, 255, 255, 0.6);
  border-bottom: 1px solid rgba(255, 255, 255, 0.3);
  border-left: none;
  border-radius: 0 32px 32px 0;

  /* Inset Caustic Refraction Glow */
  box-shadow: var(--liquid-glass-shadow-dock);

  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: space-between;
  padding: 24px 0 28px 0;
  box-sizing: border-box;
  transition: backdrop-filter 0.3s ease, background 0.3s ease;
}

/* Nested Glass Active Lens Pill */
.liquid-glass-dock .dock-item-active {
  width: 44px;
  height: 44px;
  background: rgba(255, 255, 255, 0.88);
  backdrop-filter: blur(12px) saturate(180%);
  border: 1px solid rgba(255, 255, 255, 0.95);
  border-radius: 14px;
  color: #4f46e5;
  box-shadow:
    inset 0 1px 2px rgba(255, 255, 255, 0.9),
    0 4px 16px rgba(79, 70, 229, 0.25),
    0 2px 6px rgba(0, 0, 0, 0.08);
  transform: scale(1.04);
}

/* Nested Glass Nav Lens Buttons */
.liquid-glass-dock .dock-nav-btn {
  width: 42px;
  height: 42px;
  background: rgba(255, 255, 255, 0.08);
  border: 1px solid rgba(255, 255, 255, 0.18);
  border-radius: 12px;
  color: rgba(255, 255, 255, 0.92);
  transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1);
}

.liquid-glass-dock .dock-nav-btn:hover {
  background: rgba(255, 255, 255, 0.24);
  border-color: rgba(255, 255, 255, 0.55);
  box-shadow: var(--liquid-glass-shadow-lens);
  transform: translateY(-1.5px) scale(1.06);
  color: #ffffff;
}
```

---

## 5. Accessibility & Performance Checklist

- [x] **GPU Compositing:** Always declare `transform: translateZ(0)` or `will-change: transform` to force dedicated GPU layer allocation.
- [x] **Contrast Ratio:** Ensure icons and text achieve at least **4.5:1** contrast ratio against the blurred content underneath by maintaining a minimum tint opacity (0.15 - 0.25) and text drop-shadows where appropriate.
- [x] **Fallback Support:** Provide standard translucent solid or gradient fallback for browsers lacking `backdrop-filter` support via `@supports not (backdrop-filter: blur(10px))`.
- [x] **Touch Targets:** Maintain minimum 44x44px interactive tap dimensions for mobile devices.
- [x] **Nested Sampling:** Keep nested glass elements restricted to 2 hierarchy levels (Container -> Lens Button) to prevent GPU overdraw penalties.
