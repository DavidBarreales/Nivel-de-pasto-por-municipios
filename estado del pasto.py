import pandas as pd
import numpy as np
import os
import time
from datetime import datetime, timedelta
from sentinelhub import (
    SHConfig, BBox, CRS, SentinelHubRequest, MimeType,
    bbox_to_dimensions, DataCollection, SentinelHubCatalog
)
from sentinelhub.exceptions import DownloadFailedException
import matplotlib.pyplot as plt
from matplotlib.patches import Circle

# CONFIGURAR CREDENCIALES (Introduce las credenciales de sentinel-hub)
#https://www.sentinel-hub.com/explore/apps-and-utilities/
config = SHConfig()
config.sh_client_id = ''
config.sh_client_secret = ''

# LEER EXCEL
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
df = pd.read_excel(os.path.join(BASE_DIR, "municipios_coord.xls"))

# PEDIR MUNICIPIO
nombre = input("\U0001F50D Introduce el nombre del municipio: ").strip().lower()
filtro = df['Población'].str.lower() == nombre
if not filtro.any():
    print("Municipio no encontrado.")
    import sys
    sys.exit()
fila = df[filtro].iloc[0]
lat, lon = fila['Latitud'], fila['Longitud']
nombre_municipio = fila['Población']

# BBox de ~5 km
buffer = 0.045
bbox = BBox([lon - buffer, lat - buffer, lon + buffer, lat + buffer], crs=CRS.WGS84)
size = bbox_to_dimensions(bbox, resolution=10)

# Evalscript NDVI
evalscript_ndvi = """
//VERSION=3
function setup() {
  return { input: ["B04", "B08"], output: { bands: 1, sampleType: "FLOAT32" } };
}
function evaluatePixel(s) {
  return [(s.B08 - s.B04) / (s.B08 + s.B04)];
}
"""

# Evalscript True Color
evalscript_true = """
//VERSION=3
function setup() {
  return { input: ["B04", "B03", "B02"], output: { bands: 3 } };
}
function evaluatePixel(s) {
  return [s.B04, s.B03, s.B02];
}
"""

# Crear carpeta
output_dir = f"imagenes_{nombre_municipio.replace(' ', '_')}"
os.makedirs(output_dir, exist_ok=True)

# Inicializar catálogo
catalog = SentinelHubCatalog(config=config)

# Fechas semanales de todo el año
año = 2024
fecha_inicio = datetime(año, 1, 1)
fecha_fin = datetime(año + 1, 1, 1)
semanas = []
while fecha_inicio < fecha_fin:
    semana_fin = fecha_inicio + timedelta(days=6)
    semanas.append((fecha_inicio.strftime("%Y-%m-%d"), semana_fin.strftime("%Y-%m-%d")))
    fecha_inicio += timedelta(days=7)

ndvi_resultados = []

# Bucle semanal
for i, (inicio, fin) in enumerate(semanas):
    print(f"\n\U0001F50D Semana {i + 1}: {inicio} → {fin}")

    search = catalog.search(
        DataCollection.SENTINEL2_L2A,
        bbox=bbox,
        time=(inicio, fin),
        filter='eo:cloud_cover < 30',
        fields={"include": ["id", "properties.datetime"], "exclude": []}
    )

    # Reintento en caso de error 503
    max_intentos = 3
    espera_segundos = 60
    for intento in range(1, max_intentos + 1):
        try:
            results = list(search)
            break
        except DownloadFailedException as e:
            if "503" in str(e):
                print(f"Error 503 recibido. Intento {intento}/{max_intentos}. Esperando {espera_segundos} segundos...")
                time.sleep(espera_segundos)
            else:
                raise
    else:
        print(f"No se pudo obtener resultados para la semana {i + 1}. Se omite.")
        ndvi_resultados.append({
            'Semana': i + 1,
            'Fecha_inicio': inicio,
            'Fecha_imagen': None,
            'NDVI_medio': None,
            'Cobertura_valida_%': 0
        })
        continue

    imagen_valida = False
    for r in results[:10]:
        best_date = r['properties']['datetime'][:10]
        print(f"🛰️ Probando imagen: {best_date}")

        # NDVI
        req_ndvi = SentinelHubRequest(
            evalscript=evalscript_ndvi,
            input_data=[SentinelHubRequest.input_data(
                data_collection=DataCollection.SENTINEL2_L2A,
                time_interval=(best_date, best_date)
            )],
            responses=[SentinelHubRequest.output_response("default", MimeType.TIFF)],
            bbox=bbox,
            size=size,
            config=config
        )
        img_ndvi = req_ndvi.get_data()[0].squeeze()

        cobertura = ~np.isnan(img_ndvi)
        cobertura_ratio = np.sum(cobertura) / cobertura.size
        ndvi_medio = np.nanmean(img_ndvi)

        if cobertura_ratio < 0.3:
            print(f"Imagen descartada: cobertura válida {round(cobertura_ratio*100)}%")
            continue
        if ndvi_medio < 0.1:
            print(f"Imagen descartada: NDVI demasiado bajo ({round(ndvi_medio, 3)})")
            continue

        # True Color
        req_true = SentinelHubRequest(
            evalscript=evalscript_true,
            input_data=[SentinelHubRequest.input_data(
                data_collection=DataCollection.SENTINEL2_L2A,
                time_interval=(best_date, best_date)
            )],
            responses=[SentinelHubRequest.output_response("default", MimeType.TIFF)],
            bbox=bbox,
            size=size,
            config=config
        )
        img_true = req_true.get_data()[0].astype(np.float32)
        p2, p98 = np.percentile(img_true, 2), np.percentile(img_true, 98)
        img_true = np.clip((img_true - p2) / (p98 - p2), 0, 1)

        fig, axes = plt.subplots(1, 2, figsize=(12, 6))
        axes[0].imshow(img_true)
        circle = Circle((size[0] / 2, size[1] / 2), 5000 / 10, edgecolor='red', facecolor='none', linewidth=2)
        axes[0].add_patch(circle)
        axes[0].set_title(f"{nombre_municipio} - {best_date}")
        axes[0].axis('off')

        ndvi_plot = axes[1].imshow(img_ndvi, cmap='YlGn', vmin=0, vmax=1)
        axes[1].set_title(f"NDVI (\U0001F331 {round(ndvi_medio, 3)})")
        axes[1].axis('off')
        fig.colorbar(ndvi_plot, ax=axes[1], label='NDVI')

        plt.tight_layout()
        filename = f"{nombre_municipio}_semana{i+1}_{best_date}.png".replace(" ", "_")
        plt.savefig(os.path.join(output_dir, filename))
        plt.close()

        ndvi_resultados.append({
            'Semana': i + 1,
            'Fecha_inicio': inicio,
            'Fecha_imagen': best_date,
            'NDVI_medio': round(ndvi_medio, 3),
            'Cobertura_valida_%': round(cobertura_ratio * 100, 1)
        })

        imagen_valida = True
        break

    if not imagen_valida:
        print("No se encontró ninguna imagen válida esta semana.")
        ndvi_resultados.append({
            'Semana': i + 1,
            'Fecha_inicio': inicio,
            'Fecha_imagen': None,
            'NDVI_medio': None,
            'Cobertura_valida_%': 0
        })

# Guardar CSV
df_resultados = pd.DataFrame(ndvi_resultados)
csv_path = os.path.join(output_dir, "NDVI_semanal.csv")
df_resultados.to_csv(csv_path, index=False)
print(f"\nNDVI semanal guardado en: {csv_path}")