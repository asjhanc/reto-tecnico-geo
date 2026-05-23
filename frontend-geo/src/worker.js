import * as turf from '@turf/turf';

self.onmessage = function (e) {
    let { puntosData, vendedores, numVendedores, numClientes } = e.data;
    const features = puntosData.features;

    // Asegurarnos de usar números enteros
    numVendedores = parseInt(numVendedores, 10) || 1;
    numClientes = parseInt(numClientes, 10) || 1;

    // Resetear todos los puntos a gris
    features.forEach(p => p.properties.color = [128, 128, 128]);
    const allPointsFC = turf.featureCollection(features);

    const polygons = [];
    const puntosYaAsignados = new Set();

    // 🔥 NUEVO ALGORITMO: Bucle estricto. Garantiza 1 polígono por vendedor.
    for (let i = 0; i < numVendedores; i++) {

        // 1. Obtener solo los puntos que NINGÚN vendedor haya tomado aún
        const puntosDisponibles = features.filter(p => !puntosYaAsignados.has(p.properties.id));

        if (puntosDisponibles.length === 0) {
            break; // Se acabaron los clientes en la base de datos
        }

        // 2. Tomar el primer punto disponible como "Centro" o "Semilla" de este vendedor
        const semilla = puntosDisponibles[0];

        // 3. Calcular la distancia de TODOS los puntos disponibles hacia esta semilla
        const conDistancia = puntosDisponibles.map(pt => {
            return { punto: pt, dist: turf.distance(semilla, pt) };
        });

        // 4. Ordenar de más cerca a más lejos y tomar exactamente la cantidad de clientes
        conDistancia.sort((a, b) => a.dist - b.dist);
        const puntosSeleccionados = conDistancia.slice(0, numClientes).map(item => item.punto);

        // 5. Marcar estos puntos como ASIGNADOS para que el siguiente vendedor no los robe
        puntosSeleccionados.forEach(p => puntosYaAsignados.add(p.properties.id));

        // 6. Construir la geometría
        const puntosFC = turf.featureCollection(puntosSeleccionados);
        let poly = null;

        if (puntosSeleccionados.length >= 3) {
            try {
                poly = turf.convex(puntosFC);
            } catch (err) {
                poly = null;
            }
        }

        // Si convex falla (ej. puntos en línea recta o muy pegados), forzamos una caja delimitadora con 50 metros de margen
        if (!poly || poly.geometry.type !== 'Polygon') {
            const puntosBuffer = turf.buffer(puntosFC, 0.05, { units: 'kilometers' });
            poly = turf.envelope(puntosBuffer);
        }

        // 7. Asignar la data al polígono (100% asegurado en este punto)
        if (poly) {
            const v = vendedores[i] || { nombre_vendedor: `Vendedor ${i + 1}` };

            // Colores RGB aleatorios para diferenciar los territorios
            const r = Math.floor(Math.random() * 200);
            const g = Math.floor(Math.random() * 200);
            const b = Math.floor(Math.random() * 200);
            const colorRGB = [r, g, b];

            // Point-in-Polygon: Identificamos qué puntos cayeron dentro del área dibujada
            const ptsInside = turf.pointsWithinPolygon(allPointsFC, poly);

            let montoTotal = 0;
            const clientesDetalle = [];

            ptsInside.features.forEach(p => {
                const puntoOriginal = features.find(orig => orig.properties.id === p.properties.id);
                if (puntoOriginal) {
                    // Cambiamos el color al punto
                    puntoOriginal.properties.color = [...colorRGB, 255];
                }

                montoTotal += p.properties.monto_compra_anual || 0;
                clientesDetalle.push({
                    id: p.properties.cliente_codigo,
                    nombre: p.properties.cliente_nombre,
                    moneda: p.properties.moneda,
                    monto: p.properties.monto_compra_anual
                });
            });

            // Llenamos las propiedades para el Panel Lateral
            poly.properties = {
                vendedor_codigo: v.id || (i + 1),       // Enviamos el número/código
                vendedor_nombre: v.nombre_vendedor,     // Enviamos el nombre
                color: [...colorRGB, 80], // Relleno semitransparente
                cantidad_puntos: ptsInside.features.length,
                monto_total: montoTotal,
                clientes: clientesDetalle
            };

            polygons.push(poly);
        }
    }

    // Devolver al hilo principal los datos procesados
    self.postMessage({
        type: 'SUCCESS',
        points: turf.featureCollection(features),
        polygons: turf.featureCollection(polygons)
    });
};