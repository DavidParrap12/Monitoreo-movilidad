import requests

# Endpoint del dataset Yellow Taxi 2023 en NYC Open Data con límite de 500.000 registros
url = "https://data.cityofnewyork.us/resource/4b4i-vvec.csv?$limit=500000"

response = requests.get(url, stream=True)
with open("nyc_taxi_500k.csv", "wb") as f:
    for chunk in response.iter_content(chunk_size=8192):
        f.write(chunk)

print("Descarga de 500.000 filas completada.")