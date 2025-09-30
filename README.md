# Nivel-de-pasto-por-municipios
Este proyecto descarga imágenes de Sentinel-2 y calcula el NDVI medio semanal sobre un área alrededor de un municipio en España. Está pensado para apoyar la gestión de pastos en explotaciones agropecuarias no intensivas.

Clonar el repositorio:

git clone https://github.com/DavidBarreales/estado-del-pasto.git
cd estado-del-pasto


Crear un entorno virtual e instalar dependencias:

pip install -r requirements.txt


Configurar las credenciales de Sentinel Hub en variables de entorno:

export SH_CLIENT_ID="tu_id"
export SH_CLIENT_SECRET="tu_secret"



Datos incluidos

data/municipios_coord.xls: listado de municipios españoles con sus coordenadas aproximadas.



Uso

Ejecutar el script principal:
python src/estado_del_pasto.py
El programa solicitará el nombre de un municipio. A partir de ahí:
Descarga imágenes Sentinel-2 semanales.
Calcula NDVI medio y cobertura válida.
Guarda resultados en la carpeta outputs/ (imágenes y CSV).


Resultados

Imágenes combinadas en formato True Color + NDVI por cada semana válida.
CSV con fechas, valores de NDVI y porcentaje de cobertura válida.


Dependencias

El proyecto requiere las siguientes librerías de Python (ya incluidas en requirements.txt):
numpy
pandas
geopandas
matplotlib
shapely
sentinelhub
Licencia

Este proyecto se distribuye bajo licencia MIT.
