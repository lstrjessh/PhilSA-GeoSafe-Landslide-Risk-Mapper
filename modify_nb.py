from __future__ import annotations

import nbformat
from pathlib import Path


def ensure_list_source(cell):
    source = cell["source"]
    if isinstance(source, list):
        return source, True
    return source.splitlines(keepends=True), False


def assign_source(cell, lines, was_list):
    if was_list:
        cell["source"] = lines
    else:
        cell["source"] = "".join(lines)


def main():
    path = Path("GeoSafeMonitor_NDVI.ipynb")
    nb = nbformat.read(path, as_version=4)

    # Update processing cell (cell index 5)
    cell5 = nb["cells"][5]
    lines5, is_list5 = ensure_list_source(cell5)

    if not any("soil_moisture_layer" in line for line in lines5):
        block = [
            "soil_moisture_layer = None\n",
            "try:\n",
            "    soil_moisture_dataset = 'NASA_USDA/HSL/SMAP10KM_soil_moisture'\n",
            "    soil_moisture_collection = (\n",
            "        ee.ImageCollection(soil_moisture_dataset)\n",
            "        .filterDate(start_date_recent, end_date_recent)\n",
            "        .filterBounds(roi)\n",
            "    )\n",
            "    soil_moisture_count = soil_moisture_collection.size().getInfo() or 0\n",
            "    if soil_moisture_count > 0:\n",
            "        soil_moisture_layer = soil_moisture_collection.select('ssm').mean().clip(roi)\n",
            "        print(f'Soil moisture images used: {soil_moisture_count}')\n",
            "    else:\n",
            "        print('No soil moisture data available for the selected period.')\n",
            "except Exception as exc:\n",
            "    soil_moisture_layer = None\n",
            "    print(f'Soil moisture layer unavailable: {exc}')\n",
        ]
        if lines5 and lines5[-1] != "\n":
            lines5.append("\n")
        lines5.extend(["\n"] + block)
        assign_source(cell5, lines5, is_list5)

    # Update visualization cell (cell index 7)
    cell7 = nb["cells"][7]
    lines7, is_list7 = ensure_list_source(cell7)

    viz_inserted = False
    if not any("soil_moisture_viz" in line for line in lines7):
        idx = next(
            (i for i, line in enumerate(lines7) if line.startswith("change_viz")),
            None,
        )
        if idx is not None:
            lines7.insert(
                idx + 1,
                "soil_moisture_viz = {'min': 0.0, 'max': 0.6, 'palette': ['#f7fcf5', '#74c476', '#00441b']}\n",
            )
            viz_inserted = True
    if not any("slope_viz" in line for line in lines7):
        idx = next(
            (i for i, line in enumerate(lines7) if line.startswith("change_viz")),
            None,
        )
        if idx is not None:
            offset = 2 if viz_inserted else 1
            lines7.insert(
                idx + offset,
                "slope_viz = {'min': 0, 'max': 45, 'palette': ['#ffffcc', '#fd8d3c', '#800026']}\n",
            )

    if not any("Soil Moisture (SMAP)" in line for line in lines7):
        idx = next(
            (i for i, line in enumerate(lines7) if "m.add_layer(risk_hotspots" in line),
            None,
        )
        if idx is not None:
            additions = [
                "if soil_moisture_layer is not None:\n",
                "    m.add_layer(soil_moisture_layer, soil_moisture_viz, 'Soil Moisture (SMAP)')\n",
                "m.add_layer(slope.clip(roi), slope_viz, 'Slope (degrees)')\n",
            ]
            for offset, new_line in enumerate(additions):
                lines7.insert(idx + offset, new_line)
    elif not any("Slope (degrees)" in line for line in lines7):
        idx = next(
            (i for i, line in enumerate(lines7) if "m.add_layer(risk_hotspots" in line),
            None,
        )
        if idx is not None:
            lines7.insert(idx, "m.add_layer(slope.clip(roi), slope_viz, 'Slope (degrees)')\n")

    assign_source(cell7, lines7, is_list7)

    nbformat.write(nb, path)


if __name__ == "__main__":
    main()

