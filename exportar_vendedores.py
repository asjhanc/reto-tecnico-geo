import pandas as pd
import json

ARCHIVO_EXCEL = "Puntos para examen.xlsx"

def exportar_vendedores():
    print(f"Leyendo la hoja 'Vendedores' de {ARCHIVO_EXCEL}...")
    
    # Leer solo la hoja de vendedores
    df = pd.read_excel(ARCHIVO_EXCEL, sheet_name='Vendedores')
    
    # Renombrar las columnas
    df.columns = ['id', 'nombre_vendedor']
    
    # Convertir a una lista de diccionarios
    vendedores_lista = df.to_dict(orient='records')
    
    # FIX: Lo guardamos en el mismo directorio donde estás ejecutando el script
    with open('vendedores.json', 'w', encoding='utf-8') as f:
        json.dump(vendedores_lista, f, ensure_ascii=False, indent=4)
        
    print("¡ÉXITO! Archivo 'vendedores.json' generado en tu carpeta C:\\Reto_Mapas")

if __name__ == "__main__":
    exportar_vendedores()