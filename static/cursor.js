/**
 * Smooth Trailing Cursor
 * Growth Horizon - UIUX Pro Max
 * Cursor personalizado con cola de seguimiento suave.
 * Sin dependencias, 60fps con requestAnimationFrame.
 */
(function () {
    'use strict';

    // Solo en dispositivos con puntero fino (no touch)
    if (!window.matchMedia('(pointer: fine)').matches) return;

    const cursor = document.createElement('div');
    const trail = document.createElement('div');

    cursor.classList.add('gh-cursor');
    trail.classList.add('gh-cursor-trail');
    document.body.appendChild(cursor);
    document.body.appendChild(trail);

    let mouseX = -100;
    let mouseY = -100;
    let trailX = -100;
    let trailY = -100;
    let cursorX = -100;
    let cursorY = -100;
    let isHovering = false;
    let isClicking = false;
    let rafId = null;
    let visible = false;

    // Suavizado de la cola trailing (lerp factor - más alto = más rápido)
    const TRAIL_LERP = 0.22;
    const CURSOR_LERP = 0.4;

    // Selectores de elementos interactivos
    const interactiveSelectors = [
        'a',
        'button',
        'input[type="submit"]',
        'input[type="button"]',
        '[role="button"]',
        '.btn',
        '.interactive-click',
        'select',
        'textarea',
        'input:not([type="hidden"]):not([type="checkbox"]):not([type="radio"])',
        'label[for]',
        '[onclick]',
        'aside nav a'
    ].join(', ');

    const linkSelectors = 'a, [role="link"]';
    const buttonSelectors = 'button, input[type="submit"], input[type="button"], [role="button"], .btn';

    function lerp(start, end, factor) {
        return start + (end - start) * factor;
    }

    function onMouseMove(e) {
        mouseX = e.clientX;
        mouseY = e.clientY;

        if (!visible) {
            visible = true;
            cursor.classList.remove('hidden');
            trail.classList.remove('hidden');
        }
    }

    function onMouseDown() {
        isClicking = true;
        cursor.classList.add('clicking');
        trail.classList.add('clicking');
    }

    function onMouseUp() {
        isClicking = false;
        cursor.classList.remove('clicking');
        trail.classList.remove('clicking');
    }

    function onMouseLeave() {
        visible = false;
        cursor.classList.add('hidden');
        trail.classList.add('hidden');
    }

    function onMouseEnter() {
        visible = true;
        cursor.classList.remove('hidden');
        trail.classList.remove('hidden');
    }

    function updateHoverState(e) {
        const target = e.target;
        const onInteractive = target.closest(interactiveSelectors);
        const onLink = target.closest(linkSelectors);
        const onButton = target.closest(buttonSelectors);

        if (onInteractive) {
            if (!isHovering) {
                isHovering = true;
                cursor.classList.add('hovering');
                trail.classList.add('hovering');
            }

            // Clases especificas
            if (onButton) {
                cursor.classList.add('on-button');
                trail.classList.add('on-button');
                cursor.classList.remove('on-link');
                trail.classList.remove('on-link');
            } else if (onLink) {
                cursor.classList.add('on-link');
                trail.classList.add('on-link');
                cursor.classList.remove('on-button');
                trail.classList.remove('on-button');
            }
        } else {
            if (isHovering) {
                isHovering = false;
                cursor.classList.remove('hovering', 'on-link', 'on-button');
                trail.classList.remove('hovering', 'on-link', 'on-button');
            }
        }
    }

    function animate() {
        // Cursor principal: seguimiento rapido
        cursorX = lerp(cursorX, mouseX, CURSOR_LERP);
        cursorY = lerp(cursorY, mouseY, CURSOR_LERP);

        // Trail: seguimiento lento (efecto cola)
        trailX = lerp(trailX, mouseX, TRAIL_LERP);
        trailY = lerp(trailY, mouseY, TRAIL_LERP);

        // Aplicar transform para 60fps (no usar left/top)
        cursor.style.transform = `translate3d(${cursorX - 4}px, ${cursorY - 4}px, 0)`;
        trail.style.transform = `translate3d(${trailX - 18}px, ${trailY - 18}px, 0)`;

        rafId = requestAnimationFrame(animate);
    }

    // Eventos
    document.addEventListener('mousemove', onMouseMove, { passive: true });
    document.addEventListener('mousemove', updateHoverState, { passive: true });
    document.addEventListener('mousedown', onMouseDown, { passive: true });
    document.addEventListener('mouseup', onMouseUp, { passive: true });
    document.addEventListener('mouseleave', onMouseLeave);
    document.addEventListener('mouseenter', onMouseEnter);

    // Iniciar animacion
    animate();

    // Cleanup opcional (para SPA)
    window.__ghCursorCleanup = function () {
        cancelAnimationFrame(rafId);
        document.removeEventListener('mousemove', onMouseMove);
        document.removeEventListener('mousemove', updateHoverState);
        document.removeEventListener('mousedown', onMouseDown);
        document.removeEventListener('mouseup', onMouseUp);
        document.removeEventListener('mouseleave', onMouseLeave);
        document.removeEventListener('mouseenter', onMouseEnter);
        cursor.remove();
        trail.remove();
    };
})();
