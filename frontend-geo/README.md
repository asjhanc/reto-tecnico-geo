# Reto Técnico: Plataforma de Optimización y Análisis Geoespacial

Mi solución al reto técnico. El objetivo principal fue construir una herramienta administrativa capaz de gestionar y segmentar más de 18,000 puntos de venta geolocalizados, garantizando una experiencia de usuario fluida (60 FPS), cálculos espaciales precisos y una interfaz moderna.

🔗 **Demo en Vivo:** [https://reto-tecnico-geo.vercel.app/](https://reto-tecnico-geo.vercel.app/)

---

## 1. Estrategia para el manejo masivo de datos (18k+ puntos)

Para procesar y visualizar 18,763 puntos sin experimentar "lag" al hacer zoom o scroll, mi enfoque se basó en proteger el **hilo principal (Main Thread)** del navegador a toda costa. 

1. **Renderizado por Hardware (GPU):** Descarté por completo el uso de marcadores nativos del DOM (como los de Google Maps API tradicional), ya que el navegador colapsaría al intentar renderizar tantos nodos. En su lugar, utilicé **WebGL** para compilar los puntos en una sola capa gráfica acelerada por la tarjeta de video.
2. **Web Workers para Procesamiento en Paralelo:** La agrupación de clientes, el cálculo de envolventes (polígonos) y la validación `Point-in-Polygon` son operaciones de CPU intensivas. Decidí aislar toda esta lógica algorítmica dentro de un **Web Worker**. Esto permite que, mientras la matemática pesada ocurre en segundo plano, la UI se mantenga 100% interactiva, mostrando animaciones de carga sin bloquear el Event Loop.
3. **Pipeline de Datos:** Para no saturar el frontend con lógica de parseo de Excel, desarrollé scripts auxiliares en Python (usando `pandas`) para migrar la data a PostgreSQL y exportar limpiamente un archivo `geojson` ultraligero y un `vendedores.json` estructurado.

---

## 2. Librerías externas y justificación de arquitectura

Las librerías externas elegidas fueron cuidadosamente seleccionadas para cumplir con los estándares modernos (ES6+) y la eficiencia exigida:

* **Vue 3 (Vite + Composition API):** Lo elegí por su sistema de reactividad basado en Proxies, que es extremadamente rápido. Además, Vite ofrece tiempos de compilación casi instantáneos, mejorando enormemente la experiencia de desarrollo.
* **Deck.gl (`@deck.gl/google-maps`, `@deck.gl/layers`):** Es el estándar para la visualización de grandes volúmenes de datos espaciales. Permitió superponer los puntos y polígonos directamente sobre el lienzo de Google Maps mediante renderizado GPU, logrando los 60 FPS deseados.
* **Turf.js (`@turf/turf`):** Fundamental para la lógica geoespacial. Se utilizó para:
  * Generar el anillo de búsqueda de 3km (`turf.circle`).
  * Calcular los límites exactos de cámara para hacer zoom inteligente (`turf.bbox`).
  * Calcular envolventes convexas para los territorios (`turf.convex`).
  * Validar qué puntos exactos caen dentro del área (`turf.pointsWithinPolygon`).

---

## 3. Lógica Geoespacial y Manejo de Casos Extremos (Edge Cases)

Durante el desarrollo de la Fase C (generación de territorios), implementé un **Algoritmo de Expansión por Semilla**. En lugar de usar métodos estadísticos impredecibles, el algoritmo garantiza matemáticamente que se generará la cantidad exacta de polígonos solicitada por el usuario.

**Manejo de errores geométricos:** Me percaté de una anomalía geográfica real en los datos (ej. clientes alineados en una misma avenida). Cuando esto ocurre, una figura convexa colapsa porque los puntos forman una "línea recta" en lugar de un área 2D. Para solucionarlo, implementé un sistema de contingencia (`fallback`) que detecta este fallo y envuelve los puntos utilizando un *Bounding Box* (`turf.envelope`) con un *buffer* adicional, asegurando que **ningún vendedor se quede sin su área asignada en el mapa**.

---

## 4. Escalabilidad: ¿Cómo manejar 500,000 puntos?

Si la empresa crece y la base de datos pasa de 18k a 500k puntos, la arquitectura actual (descargar un GeoJSON estático al cliente) saturaría la memoria RAM del navegador. La evolución técnica requeriría trasladar el peso hacia el Backend:

1. **Vector Tiles (Teselas Vectoriales - MVT):** Implementaría un servidor de teselas (como `pg_tileserv` o `Martin`). En lugar de cargar todos los puntos a la vez, Deck.gl solicitaría al servidor solo los "cuadrados" de datos visibles en la pantalla del usuario en ese nivel de zoom específico (usando `MVTLayer`).
2. **PostGIS (Procesamiento Espacial en BD):** Movería el Web Worker al backend. Usando **PostgreSQL + PostGIS**, aprovecharía los índices espaciales (`GiST`) para hacer las consultas ultrarrápidas. Las funciones como `ST_ClusterKMeans` y `ST_ConvexHull` procesarían los territorios a nivel de servidor, enviando al frontend únicamente el polígono final resultante.
3. **Paginación y Lazy Loading:** El panel lateral dejaría de guardar listas inmensas en memoria. Consumiría una API dinámica que traiga los clientes en bloques de 50 o 100 mediante un scroll infinito.

---

## 5. Experiencia de Usuario (UX/UI) y Uso de IA

* **Diseño Visual:** Se aplicó un diseño limpio inspirado en tendencias modernas (*Glassmorphism*), con paneles flotantes, sombras suaves y una paleta de colores vibrantes para facilitar la legibilidad de la data financiera y territorial. Se previno la "pérdida de contexto" manteniendo el radio azul visible incluso al generar subdivisiones internas.
* **Integración de IA:** Cumpliendo con los criterios de evaluación modernos, se utilizó IA a modo de *Pair Programming* para optimizar ciclos de iteración, refactorizar funciones algorítmicas repetitivas y depurar el pase de datos reactivos complejos hacia el contexto aislado del Web Worker.