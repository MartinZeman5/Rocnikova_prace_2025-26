import geopandas as gpd
import topojson as tp  # 1️⃣ Importujeme knihovnu pro TopoJSON

# Cesty k souborům (pro přehlednost v proměnných)
input_path = "country_data/_Eurasia/IND/ADM0/geoBoundaries-IND-ADM1_simplified.topojson"
output_path = "country_data/_Eurasia/IND/ADM0/India.topojson"

# 2️⃣ Načtení TopoJSON souboru
# Poznámka: GeoPandas načte TopoJSON a automaticky ho převede na geometrie (GeoDataFrame)
gdf = gpd.read_file(input_path).buffer(0)

# 3️⃣ Sjednocení polygonů (Dissolve / Union)
# Pokud máš nejnovější GeoPandas, union_all() je super. 
# Výsledkem je jeden Shapely objekt (Multipolygon nebo Polygon).
merged_geometry = gdf.union_all()

# 4️⃣ Vytvoření GeoDataFrame pro výsledek
# Musíme geometrii zabalit zpět do GeoDataFrame, aby s ní šlo pracovat
merged_gdf = gpd.GeoDataFrame(geometry=[merged_geometry], crs=gdf.crs)

# 5️⃣ Převod na TopoJSON a uložení
# Vytvoříme topologii. 'prequantize=False' zachová přesnost souřadnic.
# Můžeš zkusit 'k=1e6' pro mírné zjednodušení a zmenšení souboru.
topology = tp.Topology(merged_gdf, prequantize=False)

# Uložení do souboru
topology.to_json(output_path)

print(f"Hotovo! Soubor byl úspěšně uložen jako TopoJSON: {output_path}")
