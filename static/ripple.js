/**
 * Ripple & Click Micro-interactions
 * Growth Horizon
 * Ligero, sin dependencias, usa delegacion de eventos global para maximo rendimiento.
 */
(function () {
    'use strict';

    document.addEventListener('pointerdown', function (e) {
        // Buscar el elemento interactivo mas cercano
        const target = e.target.closest(
            'button, a, input[type="submit"], input[type="button"], [role="button"], .interactive-click, aside nav a'
        );

        if (!target) return;

        // Evitar aplicar ripple si el elemento esta deshabilitado o si se especifica data-no-ripple
        if (target.disabled || target.getAttribute('disabled') !== null || target.dataset.noRipple !== undefined) {
            return;
        }

        const rect = target.getBoundingClientRect();
        if (rect.width === 0 || rect.height === 0) return;

        // Añadir clase host para overflow y relative
        target.classList.add('gh-ripple-host');

        // Calcular diametro para cubrir todo el elemento desde el punto de clic
        const diameter = Math.max(rect.width, rect.height) * 1.5;
        const radius = diameter / 2;

        const x = e.clientX - rect.left - radius;
        const y = e.clientY - rect.top - radius;

        const wave = document.createElement('span');
        wave.classList.add('gh-ripple-wave');

        // Detectar si el fondo es claro o transparente para usar onda contrastada
        try {
            const comp = window.getComputedStyle(target);
            const bg = comp.backgroundColor;
            // Si el color de fondo tiene luminosidad alta o es blanco/gris claro
            const rgb = bg.match(/\d+/g);
            if (rgb && rgb.length >= 3) {
                const brightness = (parseInt(rgb[0]) * 299 + parseInt(rgb[1]) * 587 + parseInt(rgb[2]) * 114) / 1000;
                if (brightness > 180) {
                    wave.classList.add('gh-ripple-dark');
                }
            } else if (comp.color && comp.color.includes('rgb(15') || comp.color.includes('rgb(30') || comp.color.includes('rgb(51')) {
                // Si el texto es oscuro probablemente el fondo sea claro
                wave.classList.add('gh-ripple-dark');
            }
        } catch (err) {
            // Ignorar y usar onda por defecto
        }

        wave.style.width = diameter + 'px';
        wave.style.height = diameter + 'px';
        wave.style.left = x + 'px';
        wave.style.top = y + 'px';

        target.appendChild(wave);

        // Limpiar elemento de onda al finalizar animacion
        setTimeout(function () {
            if (wave.parentNode) {
                wave.parentNode.removeChild(wave);
            }
        }, 600);
    }, { passive: true });
})();
