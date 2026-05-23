import psycopg2
import json

# Configuración de tu base de datos local
DB_HOST = "localhost"
DB_NAME = "reto_geo"
DB_USER = "postgres"
DB_PASS = "JHA#22@j" 

def generar_geojson():
    print("Conectando a PostgreSQL para extraer puntos...")
    try:
        conn = psycopg2.connect(host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASS)
        cursor = conn.cursor()

        # Extraemos los datos y usamos PostGIS (ST_X y ST_Y) para obtener Longitud y Latitud exactas
        cursor.execute("""
            SELECT 
                id, cliente_codigo, cliente_nombre, 
                moneda, monto_compra_anual, 
                ST_X(geom) as lng, ST_Y(geom) as lat 
            FROM puntos_venta
        """)
        filas = cursor.fetchall()

        print(f"Formateando {len(filas)} puntos a GeoJSON...")
        
        features = []
        for fila in filas:
            features.append({
                "type": "Feature",
                "properties": {
                    "id": fila[0],
                    "cliente_codigo": fila[1],
                    "cliente_nombre": fila[2],
                    "moneda": fila[3],
                    "monto_compra_anual": float(fila[4]) if fila[4] else 0,
                    "color": [128, 128, 128] # El reto pide que todos inicien en gris (RGB)
                },
                "geometry": {
                    "type": "Point",
                    "coordinates": [fila[5], fila[6]] # Siempre Longitud primero, luego Latitud
                }
            })

        geojson_estructurado = {
            "type": "FeatureCollection",
            "features": features
        }

        # Guardar el archivo
        with open('puntos_venta.geojson', 'w', encoding='utf-8') as f:
            json.dump(geojson_estructurado, f, ensure_ascii=False)

        print("¡ÉXITO! Archivo 'puntos_venta.geojson' generado correctamente.")

    except Exception as e:
        print("Ocurrió un error:", e)
    finally:
        if conn:
            cursor.close()
            conn.close()

if __name__ == "__main__":
    generar_geojson()