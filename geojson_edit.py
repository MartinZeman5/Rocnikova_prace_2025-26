import geopandas as gpd

# 1️⃣ Načtení GeoJSON souboru
gdf = gpd.read_file("worldmapp.geojson")

# 2️⃣ Sjednocení všech polygonů do jedné geometrie
merged = gdf.union_all()

# 3️⃣ Uložení jako GeoJSON
merged_gdf = gpd.GeoDataFrame(geometry=[merged], crs=gdf.crs)
merged_gdf.to_file("worldmapp.geojson", driver="GeoJSON")

print("Hotovo! Výsledek uložen do worldmap.geojson")
