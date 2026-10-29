# Revisión de presentación de portal_stitch

Fecha: 29 oct 2026, America/Lima.

Archivos funcionales modificados: templates/base.html, templates/analytics.html, static/css/portal.css, static/js/ui_helpers.js y static/js/analytics.js, dentro de 04_Dashboard/portal_stitch. También se agregaron pruebas focalizadas y se actualizó su README/manifiesto. Sin escrituras a bases ni cambios al cubo.

Cambios: periodo aplicado con meses escritos; lectura textual junto a cada selector; ayuda sobre formato nativo y valor ISO; barra blanca opaca con separación adaptable; encabezado/filtros compactos; navegación lateral única, con apertura accesible en móvil. Las tarjetas se disponen en cuatro columnas de escritorio desde 992 px.

## Pruebas realizadas

- 8/8 pruebas unitarias JavaScript: meses, fechas ambiguas, bisiesto, vacío, parámetros ISO, limpieza y cuatro decimales. Entradas de prueba, sin navegador y sin resultados ficticios en gráficos. Reporte: portal_presentacion_js.json.
- 12/12 comprobaciones Python: recepción de fechas, miembros diarios en MDX, consulta real SSAS mediante el cliente Flask, exportación real, marcado de navegación/ayudas, reglas CSS y cinco hashes de archivos protegidos. Reporte: portal_presentacion_pruebas.json. No se trata de navegación HTTP desde un navegador.
- SSAS real: 3–9 abr 2010, 5.434 operaciones. Respuesta completa en portal_presentacion_respuesta_real.json. Exportación sin modificación en portal_presentacion_exportacion_real.csv; importe monetario con cuatro decimales.
- Se corrigió el lector de la prueba CSV para usar coma, el separador existente. La primera ejecución interpretó erróneamente punto y coma y falló la extracción de columnas; no hubo un fallo de exportación ni se modificó su implementación. La ejecución final pasa.
- El lanzador de Python del entorno virtual no accedió a Python desde el sandbox (`No Python at ...`); Python global carecía de Flask. La prueba final se ejecutó con el entorno virtual existente fuera del sandbox, sin instalar dependencias ni cambiar configuración.

## Revisión visual pendiente

Se intentó acceso con cua.getState y sky.list_apps. Errores reales:

```
The browser access host is unavailable
Computer Use native pipe is unavailable: failed to connect native pipe: El sistema no puede encontrar el archivo especificado. (os error 2)
```

No se observaron ventanas ni se generaron capturas. Pendiente abrir 1440×900 y 390×844, comprobar fechas nativas y lectura textual, desplazamiento sin transparencias/superposiciones, altura de indicadores y abrir/cerrar/recorrer el menú con teclado. La revisión estática cubre las reglas para estos tamaños; no reemplaza su comprobación visual. No se inició ningún servidor temporal en esta revisión.

## Observación fuera del ajuste de presentación

Para 3–9 abr 2010, la tarjeta Importe devuelve 117470.7600 y la fila mensual exportada 590580.4320. No son importes conciliados. El filtro recibido y los miembros diarios del MDX son correctos. Se conserva la evidencia sin alterar consultas: queda pendiente investigar el cruce entre atributos Mes/Fecha en SSAS y las consultas existentes. Las 20 comprobaciones aprobadas cubren presentación, transporte de fechas, precisión e invariantes; no certifican esa conciliación de datos.
