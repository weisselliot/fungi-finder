import fiona
import json
import os
from shapely.geometry import shape, mapping, box

GDB = "data/S_USA.EVMid_R05_CentralCoast.gdb"
OUT = "data/oak_habitat_v3.geojson"

# Full East Bay hills — GDB western extent is -122.521 so this covers Richmond→Oakland→Hayward
BBOX        = (-122.52, 37.60, -122.00, 38.05)
SIMPLIFY    = 0.002       # matches 0.002° grid cell resolution; sub-cell detail is wasted
KEEP_FIELDS = ("REGIONAL_DOMINANCE_TYPE", "REGIONAL_DOMINANCE_TYPE_2",
               "COVERTYPE", "CWHR_TYPE")

print(f"=== Exporting {OUT} ===")
print(f"  bbox      : {BBOX}")
print(f"  simplify  : {SIMPLIFY}")

clip_geom = box(*BBOX)
features  = []

with fiona.open(GDB, layer="EVMid_R05_CentralCoast", bbox=BBOX) as src:
    candidates = len(src)
    print(f"  bbox pre-filter: {candidates} candidates")

    for feat in src:
        props = feat["properties"]
        rdt1  = (props.get("REGIONAL_DOMINANCE_TYPE")   or "").strip()
        rdt2  = (props.get("REGIONAL_DOMINANCE_TYPE_2") or "").strip()
        rdt3  = (props.get("REGIONAL_DOMINANCE_TYPE_3") or "").strip()

        if not (rdt1.startswith("Q") or rdt2.startswith("Q") or rdt3.startswith("Q")):
            continue

        geom = shape(feat["geometry"])
        if not geom.is_valid:
            geom = geom.buffer(0)

        clipped = geom.intersection(clip_geom)
        if clipped.is_empty:
            continue

        # Drop features smaller than one grid cell (~0.002° × 0.002°)
        if clipped.area < SIMPLIFY ** 2:
            continue

        simplified = clipped.simplify(SIMPLIFY, preserve_topology=True)
        if simplified.is_empty:
            continue

        features.append({
            "type": "Feature",
            "geometry": mapping(simplified),
            "properties": {k: props.get(k) for k in KEEP_FIELDS},
        })

geojson = {"type": "FeatureCollection", "features": features}
with open(OUT, "w") as f:
    json.dump(geojson, f)

size_kb = os.path.getsize(OUT) / 1024
print(f"  Quercus features : {len(features)}")
print(f"  Output file      : {OUT}")
print(f"  File size        : {size_kb:.1f} KB")
