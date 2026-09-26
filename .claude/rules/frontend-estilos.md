---
paths:
  - "**/*.css"
  - "**/components/**/*.tsx"
  - "**/pages/**/*.tsx"
---

# Frontend — estilos y UI

- Utilidades de Tailwind v4 en el markup. CSS a mano solo para lo que Tailwind no cubre
  (animaciones, scrollbar), en un único archivo global.
- Colores, radios y tipografía como tokens `@theme` en el CSS global; no colores hex sueltos en
  los componentes.
- No agregar otra librería de estilos o de componentes sin consultarlo.
- Toda vista con datos muestra tres estados: cargando, vacío y error (componentes compartidos de
  `components/ui/`).
- Accesibilidad mínima: `label` asociado a cada input, botones con texto o `aria-label`, foco
  visible, contraste AA, navegación por teclado en modales (trap de foco y `Esc`).
- Formularios: deshabilitar el envío mientras está en curso y mostrar los errores del backend
  junto al campo.
- Para diseño nuevo o revisión de UI, usar las skills `frontend-design` y `web-design-guidelines`.
