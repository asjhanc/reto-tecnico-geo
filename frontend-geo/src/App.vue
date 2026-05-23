<template>
  <div class="app-container">
    <div v-if="isLoading" class="loader-overlay">
      <div class="spinner"></div>
      <h2>{{ loadingMessage }}</h2>
    </div>

    <div class="sidebar left-panel">
      <h3>Gestión Territorial</h3>
      
      <div class="search-box">
        <label>Buscar zona (Google Places):</label>
        <input 
          type="text" 
          ref="buscadorInput" 
          class="place-input" 
          placeholder="Ingresa una dirección o lugar..." 
        />
      </div>
      <hr>

      <div class="input-group">
        <label>Cantidad de Vendedores (Máx 90):</label>
        <input type="number" v-model="numVendedores" min="1" max="90" />
      </div>
      <div class="input-group">
        <label>Clientes por vendedor:</label>
        <input type="number" v-model="numClientes" min="1" />
      </div>
      
      <button @click="iniciarProcesamiento" class="btn-procesar" :disabled="isLoading">
        Generar Polígonos
      </button>
      <button @click="resetearMapa" class="btn-reset" :disabled="isLoading">
        Restaurar Mapa
      </button>
    </div>

    <div v-if="infoPoligono" class="sidebar right-panel">
      <div class="panel-header">
        <h3>Vendedor {{ infoPoligono.vendedor_codigo }}: {{ infoPoligono.vendedor_nombre }}</h3>
        <button class="btn-cerrar" @click="infoPoligono = null">✖</button>
      </div>
      
      <div class="kpi-box">
        <p><strong>Puntos en el área:</strong> {{ infoPoligono.cantidad_puntos }}</p>
        <p class="monto"><strong>Potencial:</strong> S/ {{ infoPoligono.monto_total.toLocaleString('es-PE', {minimumFractionDigits: 2}) }}</p>
      </div>
      
      <h4>Relación de Clientes</h4>
      <div class="clientes-tabla-header">
        <div class="h-id">ID</div>
        <div class="h-nombre">Nombre del Cliente</div>
        <div class="h-monto">Importe</div>
      </div>
      
      <div class="clientes-lista">
        <div v-for="c in infoPoligono.clientes" :key="c.id" class="cliente-item">
          <div class="c-id">{{ c.id }}</div>
          <div class="c-nombre" :title="c.nombre">{{ c.nombre }}</div>
          <div class="c-monto">{{ c.moneda }} {{ c.monto.toLocaleString('es-PE', {minimumFractionDigits: 2}) }}</div>
        </div>
      </div>
    </div>

    <div ref="mapContainer" class="map-container"></div>
  </div>
</template>

<script setup>
import { ref, onMounted, shallowRef } from 'vue';
import { GoogleMapsOverlay } from '@deck.gl/google-maps';
import { GeoJsonLayer } from '@deck.gl/layers';
import * as turf from '@turf/turf';

// Referencias de Vue
const mapContainer = ref(null);
const buscadorInput = ref(null); 
const isLoading = ref(true);
const loadingMessage = ref("Iniciando entorno geoespacial...");
const radioData = shallowRef(null);
const numVendedores = ref(5);
const numClientes = ref(100);
const infoPoligono = ref(null);
const mapRef = shallowRef(null);
const overlayRef = shallowRef(null);
const puntosDataOrigin = shallowRef(null); 
const puntosData = shallowRef(null); 
let autocompleteInstance = null; 
const listaVendedores = ref([]); // Variable para almacenar los vendedores reales


onMounted(() => {
  const esperarGoogle = setInterval(async () => {
    if (window.google && window.google.maps) {
      clearInterval(esperarGoogle);
      await iniciarApp();
    }
  }, 100);
});

const iniciarApp = async () => {
  try {
    loadingMessage.value = "Cargando 18,000+ puntos y vendedores...";
    
    // Cargar datos espaciales y vendedores en paralelo
    const [resPuntos, resVendedores] = await Promise.all([
      fetch('/puntos_venta.geojson'),
      fetch('/vendedores.json')
    ]);

    const dataPuntos = await resPuntos.json();
    listaVendedores.value = await resVendedores.json(); 

    puntosDataOrigin.value = dataPuntos;
    puntosData.value = JSON.parse(JSON.stringify(dataPuntos));

    // Inicializar Mapa Base
    const map = new window.google.maps.Map(mapContainer.value, {
      center: { lat: -12.0464, lng: -77.0428 }, 
      zoom: 11, 
      mapId: 'DEMO_MAP_ID', 
      disableDefaultUI: true,
    });
    mapRef.value = map;

    actualizarCapaDeckGL(puntosData.value);

    // Inicializar el buscador de Google Places
    if (buscadorInput.value) {
      autocompleteInstance = new window.google.maps.places.Autocomplete(buscadorInput.value, {
        fields: ['geometry', 'name']
      });

      autocompleteInstance.addListener('place_changed', () => {
        const place = autocompleteInstance.getPlace();
        
        if (!place.geometry || !place.geometry.location) {
          console.warn("No se encontraron coordenadas para este lugar.");
          return;
        }

        const lat = place.geometry.location.lat();
        const lng = place.geometry.location.lng();
        
        filtrarPorRadio(lng, lat);
      });
    }

    isLoading.value = false;
  } catch (error) {
    console.error("❌ Error crítico de inicialización:", error);
    loadingMessage.value = "Error al cargar la aplicación.";
    isLoading.value = false;
  }
};

const filtrarPorRadio = (lng, lat) => {
  if (!puntosDataOrigin.value) return;
  
  // Lógica Espacial Turf.js (Radio de 3km)
  const center = turf.point([lng, lat]);
  const circle = turf.circle(center, 3, { units: 'kilometers', steps: 64 });
  
  radioData.value = circle; //GUARDAMOS EL CÍRCULO EN MEMORIA

  // Extraer Bounding Box para hacer ZOOM EXACTO
  const [minX, minY, maxX, maxY] = turf.bbox(circle);
  
  mapRef.value.fitBounds(
    new window.google.maps.LatLngBounds(
      { lat: minY, lng: minX }, 
      { lat: maxY, lng: maxX }  
    )
  );

  // Filtrar puntos
  const copiaDatos = JSON.parse(JSON.stringify(puntosDataOrigin.value));
  const puntosFiltrados = copiaDatos.features.filter(pt => {
    return turf.booleanPointInPolygon(pt, circle);
  });

  // Pintamos los puntos encontrados de verde
  puntosFiltrados.forEach(p => p.properties.color = [46, 204, 113, 255]);

  const nuevaColeccion = turf.featureCollection(puntosFiltrados);
  puntosData.value = nuevaColeccion;
  infoPoligono.value = null; 
  
  actualizarCapaDeckGL(nuevaColeccion, null);
};

const resetearMapa = () => {
  if (!puntosDataOrigin.value) return;
  
  puntosData.value = JSON.parse(JSON.stringify(puntosDataOrigin.value));
  puntosData.value.features.forEach(p => p.properties.color = [128, 128, 128]); 
  
  infoPoligono.value = null;
  radioData.value = null;
  
  mapRef.value.panTo({ lat: -12.0464, lng: -77.0428 });
  mapRef.value.setZoom(11);
  
  if (buscadorInput.value) {
    buscadorInput.value.value = ''; 
  }
  
  actualizarCapaDeckGL(puntosData.value, null);
};

const iniciarProcesamiento = async () => {
  if (!puntosData.value || !puntosData.value.features) return;
  infoPoligono.value = null;

  isLoading.value = true;
  loadingMessage.value = "Calculando áreas de cobertura...";

  const worker = new Worker(new URL('./worker.js', import.meta.url), { type: 'module' });
  
  // Convertimos los proxies reactivos a objetos limpios de JS para evitar el error de clonación
  const puntosClonados = JSON.parse(JSON.stringify(puntosData.value));
  const vendedoresClonados = JSON.parse(JSON.stringify(listaVendedores.value));

  worker.postMessage({
    puntosData: puntosClonados, 
    vendedores: vendedoresClonados, 
    numVendedores: numVendedores.value,
    numClientes: numClientes.value
  });

  worker.onmessage = (e) => {
    if (e.data.type === 'SUCCESS') {
      puntosData.value = e.data.points; 
      actualizarCapaDeckGL(e.data.points, e.data.polygons, null);
      isLoading.value = false;
      worker.terminate(); 
    }
  };
};

const actualizarCapaDeckGL = (pointsFC, polygonsFC = null) => {
  const layers = [];

  if (radioData.value) {
    layers.push(new GeoJsonLayer({
      id: 'radio-3km-layer',
      data: radioData.value,
      stroked: true,
      filled: true,
      lineWidthMinPixels: 2,
      getLineColor: [52, 152, 219, 200],
      getFillColor: [52, 152, 219, 20], 
      pickable: false
    }));
  }

  if (polygonsFC) {
    layers.push(new GeoJsonLayer({
      id: 'polygons-layer',
      data: polygonsFC,
      stroked: true,
      filled: true,
      lineWidthMinPixels: 2,
      getLineColor: [255, 255, 255],
      getFillColor: d => d.properties.color,
      pickable: true,
      autoHighlight: true, 
      onClick: (info) => {
        if (info.object) {
          infoPoligono.value = info.object.properties;
        }
      }
    }));
  }

  layers.push(new GeoJsonLayer({
    id: 'puntos-layer',
    data: pointsFC,
    filled: true,
    pointRadiusMinPixels: 3, 
    getPointRadius: 25, 
    getFillColor: d => d.properties.color || [128, 128, 128, 200], 
    pickable: false, 
  }));

  if (!overlayRef.value) {
    overlayRef.value = new GoogleMapsOverlay({ layers });
    overlayRef.value.setMap(mapRef.value);
  } else {
    overlayRef.value.setProps({ layers });
  }
};
</script>

<style scoped>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');


.app-container { 
  width: 100vw; 
  height: 100vh; 
  position: relative; 
  background: #f1f5f9; 
  overflow: hidden; 
  font-family: 'Inter', system-ui, sans-serif;
  color: #1a202c; /* Texto principal más profundo */
  -webkit-font-smoothing: antialiased;
}

.map-container { 
  position: absolute; 
  top: 0; left: 0; width: 100vw; height: 100vh; 
  z-index: 1; 
}

.sidebar {
  position: absolute;
  top: 16px; 
  background: rgba(255, 255, 255, 0.9); 
  backdrop-filter: blur(10px);
  padding: 18px; /* Reducido drásticamente */
  border-radius: 12px; /* Reducido para compactación */
  box-shadow: 0 4px 20px -2px rgba(0,0,0,0.08); 
  border: 1px solid rgba(255, 255, 255, 0.4);
  z-index: 100;
  max-height: calc(100vh - 32px);
  display: flex;
  flex-direction: column;
}

.left-panel { left: 16px; width: 290px; } 
.right-panel { right: 16px; width: 370px; }


h3 { 
  margin: 0 0 16px 0; 
  color: #000000; 
  font-size: 1.1rem; 
  font-weight: 700;
  letter-spacing: -0.01em;
}

h4 { 
  margin: 12px 0 8px 0; 
  color: #4a5568; 
  font-size: 0.85rem; /* Más pequeño */
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

hr { 
  border: 0; height: 1px; 
  background: linear-gradient(to right, transparent, #e2e8f0, transparent); 
  margin: 16px 0; 
}

.search-box label, .input-group label { 
  display: block; 
  font-size: 0.8rem; 
  margin-bottom: 6px; 
  color: #4a5568; 
  font-weight: 600;
}

.search-box label { color: #ff6b35; }

.place-input, .input-group input {
  width: 100%;
  padding: 10px 12px; 
  background-color: #ffffff;
  border: 1px solid #d1d5db;
  border-radius: 8px; 
  font-size: 0.9rem; 
  color: #1a202c;
  box-sizing: border-box;
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
  font-family: inherit;
}

.place-input:focus, .input-group input:focus {
  outline: none;
  border-color: #0066FF; /* Azul más vivo */
  box-shadow: 0 0 0 3px rgba(0, 102, 255, 0.1);
}

.input-group { margin-bottom: 14px; } 

.btn-procesar { 
  width: 100%; 
  padding: 12px; 
  background: linear-gradient(135deg, #0055EE 0%, #0066FF 100%); 
  color: white; 
  border: none; 
  border-radius: 8px; 
  cursor: pointer; 
  font-weight: 600; 
  font-size: 0.95rem; /* Más pequeño */
  margin-bottom: 10px;
  box-shadow: 0 2px 8px rgba(0, 102, 255, 0.15);
  transition: all 0.2s ease;
}

.btn-procesar:hover { 
  box-shadow: 0 4px 12px rgba(0, 102, 255, 0.25);
}

.btn-procesar:disabled { background: #cbd5e1; box-shadow: none; cursor: not-allowed; }

.btn-reset { 
  width: 100%; 
  padding: 10px; /* Reducido */
  background: #e2e8f0; 
  color: #4a5568; 
  border: none; 
  border-radius: 8px; 
  cursor: pointer; 
  font-weight: 600;
  font-size: 0.9rem;
  transition: background 0.2s ease;
}

.btn-reset:hover { background: #cbd5e1; color: #1a202c; }


.panel-header { 
  display: flex; 
  justify-content: space-between; 
  align-items: center; 
  margin-bottom: 16px;
}

.panel-header h3 {
  color: #000000;
  margin: 0;
  font-size: 1.1rem;
}

.btn-cerrar { 
  background: transparent; 
  border: none; 
  width: 28px; height: 28px; /* Reducido */
  border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  font-size: 14px; cursor: pointer; color: #718096; 
  transition: background 0.2s ease;
}

.btn-cerrar:hover { background: #fee2e2; color: #ef4444; }

.kpi-box { 
  background: linear-gradient(135deg, #E8F5E9 0%, #C8E6C9 100%); /* Menta/Esmeralda Vibrante */
  border-left: 3px solid #00C896; /* Verde más vivo */
  padding: 12px; /* Reducido */
  border-radius: 10px; 
  margin-bottom: 20px; 
}

.kpi-box p { margin: 4px 0; font-size: 0.9rem; color: #1B5E20;}
.kpi-box .monto { font-size: 1.2rem; font-weight: 700; color: #008060; margin-top: 6px;}

.clientes-tabla-header {
  display: grid;
  grid-template-columns: 1fr 3.5fr 1.8fr; 
  gap: 6px;
  background-color: #f7fafc;
  color: #718096;
  padding: 10px 14px; /* Reducido */
  font-size: 0.7rem; /* Más pequeño */
  font-weight: 700;
  border-radius: 8px 8px 0 0;
  border-bottom: 1px solid #e2e8f0;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.h-id, .c-id { text-align: left; }
.h-nombre, .c-nombre { text-align: left; }
.h-monto, .c-monto { text-align: right; }

.clientes-lista { 
  overflow-y: auto; 
  flex-grow: 1; 
  background: #ffffff;
  border: 1px solid #e2e8f0; border-top: none;
  border-radius: 0 0 8px 8px;
  /* Altura máxima para forzar scroll y que quepa en pantallas pequeñas */
  max-height: 300px; 
}

/* Personalización del Scrollbar (más fino) */
.clientes-lista::-webkit-scrollbar { width: 5px; }
.clientes-lista::-webkit-scrollbar-track { background: transparent; }
.clientes-lista::-webkit-scrollbar-thumb { background-color: #cbd5e1; border-radius: 10px; }

.cliente-item { 
  padding: 10px 14px; /* Reducido */
  border-bottom: 1px solid #f1f5f9; 
  display: grid; 
  grid-template-columns: 1fr 3.5fr 1.8fr; /* Tenedor más ajustado */
  gap: 6px; 
  font-size: 0.8rem; /* Más pequeño */
  align-items: center;
}

.cliente-item:last-child { border-bottom: none; }
.cliente-item:hover { background-color: #f7fafc; }

.c-id { color: #a0aec0; font-family: monospace; font-size: 0.75rem; }
.c-nombre { color: #1a202c; font-weight: 500; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.c-monto { font-weight: 600; color: #000000; font-family: monospace; }


.loader-overlay { 
  position: absolute; 
  top: 0; left: 0; right: 0; bottom: 0; 
  background-color: rgba(255, 255, 255, 0.85); 
  backdrop-filter: blur(6px);
  display: flex; flex-direction: column; justify-content: center; align-items: center; z-index: 1000; 
}

.loader-overlay h2 {
  color: #1a202c;
  font-weight: 600;
  margin-top: 16px;
  font-size: 1.1rem;
}

.spinner { 
  border: 3px solid #e2e8f0; 
  border-top: 3px solid #0066FF; /* Azul vivo */
  border-radius: 50%; 
  width: 40px; height: 40px; /* Reducido */
  animation: spin 1s linear infinite; 
}

@keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
</style>