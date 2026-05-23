# Reto Técnico: Optimización y Análisis Espacial

Plataforma administrativa de segmentación territorial y análisis geoespacial. Permite la visualización fluida de grandes volúmenes de datos y la generación matemática de polígonos de cobertura de clientes.

## Estrategia utilizada para el manejo de los 18k puntos

Para garantizar los 60 FPS y evitar el colapso del navegador, se descartó el uso de marcadores nativos del DOM (Google Maps Markers). La estrategia se fundamentó en dos pilares:
1. **Renderizado por GPU:** Se delegó el pintado de los 18,763 puntos a la tarjeta gráfica del dispositivo utilizando WebGL.
2. **Procesamiento en Paralelo:** Todos los cálculos matemáticos pesados (algoritmos de agrupación, Point-in-Polygon y generación de Bounding Boxes) se aislaron en un **Web Worker**. Esto garantiza que el Event Loop (hilo principal del navegador) nunca se bloquee, manteniendo la UI completamente responsiva durante las operaciones de CPU intensivo.

## Librerías externas utilizadas y justificación

* **Deck.gl (`@deck.gl/google-maps`, `@deck.gl/layers`):** Elegida por ser el estándar de la industria (desarrollada originalmente por Uber) para el manejo masivo de datos geoespaciales. Permite renderizar miles de geometrías como una sola capa gráfica sobre el mapa base sin latencia.
* **Turf.js (`@turf/turf`):** Utilizada para realizar operaciones GIS avanzadas directamente en el cliente. Fue esencial para el cálculo de distancias reales, generación de envolventes convexas (`turf.convex`), cajas delimitadoras de contingencia (`turf.envelope`) y validación de pertenencia espacial (`turf.pointsWithinPolygon`).
* **Vue 3 (Vite):** Seleccionado por su reactividad ligera basada en Proxies y su sistema de composición, lo que facilitó el manejo del estado entre el mapa, el Web Worker y el panel de KPIs.

## Escalabilidad a 500,000 puntos

Para escalar la aplicación a medio millón de puntos, la arquitectura actual basada en la descarga de un archivo `.geojson` estático saturaría la memoria RAM del cliente. La evolución requeriría trasladar el peso hacia el backend:

1.  **Vector Tiles (MVT):** En lugar de cargar todos los puntos, implementaría un servidor de teselas vectoriales (ej. *pg_tileserv* o *Martin*) conectado a PostgreSQL. Deck.gl usaría el `MVTLayer` para renderizar únicamente los datos visibles en el *Viewport* actual del usuario.
2.  **Procesamiento Espacial en BD (PostGIS):** La lógica del Web Worker migraría a la base de datos. Se utilizarían índices espaciales (`GiST`) en PostgreSQL. Los polígonos y las agrupaciones (K-Means o agrupaciones por radio) se calcularían del lado del servidor usando funciones nativas de PostGIS como `ST_ClusterKMeans` y `ST_ConvexHull`.
3.  **Paginación Dinámica:** Las listas de clientes en la UI dejarían de iterar sobre arrays gigantes y consumirían una API con paginación infinita, solicitando datos según el usuario haga scroll.