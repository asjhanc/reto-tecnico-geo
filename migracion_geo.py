import pandas as pd
import psycopg2
from psycopg2.extras import execute_values
import numpy as np

# 1. Configuración de tu base de datos local
DB_HOST = "localhost"
DB_NAME = "reto_geo"
DB_USER = "postgres"
DB_PASS = "JHA#22@j"  # Tu contraseña configurada

# 2. Nombre exacto de tu archivo Excel
ARCHIVO_EXCEL = "Puntos para examen.xlsx"

def migrar_datos():
    print("Conectando a PostgreSQL...")
    conn = None
    try:
        conn = psycopg2.connect(host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASS)
        cursor = conn.cursor()

        # 3. Crear las tablas con las columnas reales del examen
        print("Preparando la estructura de las tablas...")
        cursor.execute("""
            DROP TABLE IF EXISTS puntos_venta;
            DROP TABLE IF EXISTS vendedores;
            
            CREATE TABLE vendedores (
                codigo VARCHAR(50) PRIMARY KEY,
                nombre_vendedor VARCHAR(255)
            );

            CREATE TABLE puntos_venta (
                id SERIAL PRIMARY KEY,
                cliente_codigo VARCHAR(50),
                cliente_nombre VARCHAR(255),
                ultima_fecha_compra VARCHAR(50), 
                moneda VARCHAR(10),
                monto_compra_anual DECIMAL(15,2),
                vendedor_codigo VARCHAR(50) REFERENCES vendedores(codigo) NULL, 
                geom GEOMETRY(Point, 4326) 
            );
        """)
        conn.commit()

        # 4. Leer y procesar la hoja de Vendedores
        print("Leyendo la hoja 'Vendedores'...")
        df_vendedores = pd.read_excel(ARCHIVO_EXCEL, sheet_name='Vendedores')
        df_vendedores = df_vendedores.replace({np.nan: None})
        
        valores_vendedores = []
        for _, fila in df_vendedores.iterrows():
            valores_vendedores.append((
                str(fila['CODIGO']),
                fila['APELLIDOS Y NOMBRES DEL VENDEDOR']
            ))
        
        print(f"Insertando {len(valores_vendedores)} vendedores...")
        query_vendedores = "INSERT INTO vendedores (codigo, nombre_vendedor) VALUES %s"
        execute_values(cursor, query_vendedores, valores_vendedores)
        conn.commit()

        # 5. Leer y procesar la hoja de Geo puntos (CON LA CORRECCIÓN)
        print("Leyendo la hoja 'Geo puntos'...")
        df_puntos = pd.read_excel(ARCHIVO_EXCEL, sheet_name='Geo puntos')
        
        # FIX: Eliminamos cualquier fila (como la de Totales) que no tenga coordenadas
        df_puntos = df_puntos.dropna(subset=['Latitud', 'Longitud'])
        
        # Limpieza de nulos restantes
        df_puntos = df_puntos.replace({np.nan: None})

        print("Procesando coordenadas geográficas para PostGIS...")
        valores_puntos = []
        for _, fila in df_puntos.iterrows():
            cliente_code = str(fila['Cliente'])
            cliente_name = fila['Nombre_del_cliente']
            fecha_compra = str(fila['Ultima_fecha_de_compra']) if fila['Ultima_fecha_de_compra'] else None
            longitud = fila['Longitud']
            latitud = fila['Latitud']
            monto = fila['Monto_Compra_anual']
            moneda = fila['Moneda']

            # Formato WKT con el SRID 4326
            punto_geom = f"SRID=4326;POINT({longitud} {latitud})"
            
            valores_puntos.append((cliente_code, cliente_name, fecha_compra, moneda, monto, punto_geom))

        # 6. Inserción masiva ultra rápida
        print(f"Inyectando {len(valores_puntos)} puntos espaciales en la base de datos...")
        query_puntos = """
            INSERT INTO puntos_venta (cliente_codigo, cliente_nombre, ultima_fecha_compra, moneda, monto_compra_anual, geom) 
            VALUES %s
        """
        execute_values(cursor, query_puntos, valores_puntos)
        conn.commit()

        print("\n¡MIGRACIÓN EXITOSA!")
        print(f"-> Vendedores cargados correctamente.")
        print(f"-> {len(valores_puntos)} puntos con geometría PostGIS listos para ser consumidos.")

    except Exception as e:
        print("\n[ERROR] Ocurrió un fallo durante la migración:", e)
        if conn:
            conn.rollback()
    finally:
        if conn:
            cursor.close()
            conn.close()

if __name__ == "__main__":
    migrar_datos()