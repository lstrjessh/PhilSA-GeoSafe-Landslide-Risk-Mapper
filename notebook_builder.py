import json
from pathlib import Path


def markdown_cell(text: str) -> dict:
    return {
        "cell_type": "markdown",
        "metadata": {},
        "source": [text],
    }


def code_cell(lines: list[str]) -> dict:
    return {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [f"{line}\n" for line in lines],
    }


cells: list[dict] = []

cells.append(
    markdown_cell(
        "# Geo-Safe Monitor PH: Landslide Risk POC\n\n"
        "This notebook mirrors the prototype workflow for monitoring vegetation change over Baungon, "
        "Bukidnon using Sentinel-2 imagery. It incorporates the fixes highlighted in the earlier code review, "
        "including reliable dependency handling, historical data availability checks, and explicit map rendering.\n"
    )
)

cells.append(
    code_cell(
        [
            "import importlib.util",
            "import subprocess",
            "import sys",
            "",
            "DEPENDENCIES = {",
            "    'ee': 'earthengine-api',",
            "    'geemap': 'geemap',",
            "    'pandas': 'pandas',",
            "    'matplotlib': 'matplotlib',",
            "}",
            "",
            "for module_name, package_name in DEPENDENCIES.items():",
            "    if importlib.util.find_spec(module_name) is None:",
            "        print(f'Installing {package_name}...')",
            "        subprocess.check_call([sys.executable, '-m', 'pip', 'install', package_name])",
        ]
    )
)

cells.append(
    code_cell(
        [
            "import ee",
            "import geemap",
            "import pandas as pd",
            "import matplotlib.pyplot as plt",
            "",
            "try:",
            "    ee.Initialize()",
            "    print('Google Earth Engine initialized.')",
            "except Exception:",
            "    print('Authenticating with Google Earth Engine...')",
            "    ee.Authenticate()",
            "    ee.Initialize()",
            "    print('Authentication complete.')",
        ]
    )
)

cells.append(
    markdown_cell(
        "## Configuration and Helper Functions\n\n"
        "Define the ROI, time windows, and utility functions for cloud masking, NDVI computation, and data sourcing with a fallback for historical imagery.\n"
    )
)

cells.append(
    code_cell(
        [
            "def mask_s2_clouds(image):",
            "    \"\"\"Mask clouds in a Sentinel-2 image using the QA60 band.\"\"\"",
            "    qa = image.select('QA60')",
            "    cloud_bit_mask = 1 << 10",
            "    cirrus_bit_mask = 1 << 11",
            "    mask = qa.bitwiseAnd(cloud_bit_mask).eq(0).And(qa.bitwiseAnd(cirrus_bit_mask).eq(0))",
            "    return image.updateMask(mask).divide(10000)",
            "",
            "",
            "def add_ndvi(image):",
            "    \"\"\"Add an NDVI band to a Sentinel-2 image.\"\"\"",
            "    ndvi = image.normalizedDifference(['B8', 'B4']).rename('NDVI')",
            "    return image.addBands(ndvi)",
            "",
            "",
            "def get_sentinel_collection(start_date, end_date, region, max_cloud=20):",
            "    sr_id = 'COPERNICUS/S2_SR_HARMONIZED'",
            "    sr_collection = (",
            "        ee.ImageCollection(sr_id)",
            "        .filterDate(start_date, end_date)",
            "        .filterBounds(region)",
            "        .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', max_cloud))",
            "    )",
            "",
            "    sr_count = sr_collection.size().getInfo() or 0",
            "    if sr_count > 0:",
            "        return sr_collection, sr_id",
            "",
            "    toa_id = 'COPERNICUS/S2'",
            "    toa_collection = (",
            "        ee.ImageCollection(toa_id)",
            "        .filterDate(start_date, end_date)",
            "        .filterBounds(region)",
            "        .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', max_cloud))",
            "    )",
            "",
            "    toa_count = toa_collection.size().getInfo() or 0",
            "    if toa_count == 0:",
            "        raise RuntimeError(",
            "            f'No Sentinel-2 imagery available for {start_date} to {end_date} in the selected ROI.'",
            "        )",
            "",
            "    print(f'Fallback to {toa_id} for {start_date} - {end_date}.')",
            "    return toa_collection, toa_id",
        ]
    )
)

cells.append(
    code_cell(
        [
            "roi = ee.Geometry.Rectangle([124.60, 8.30, 124.70, 8.40])",
            "",
            "start_date_recent = '2024-01-01'",
            "end_date_recent = '2024-12-31'",
            "start_date_historical = '2015-01-01'",
            "end_date_historical = '2015-12-31'",
            "",
            "VEGETATION_LOSS_THRESHOLD = -0.15",
            "",
            "recent_collection, recent_dataset = get_sentinel_collection(start_date_recent, end_date_recent, roi)",
            "historical_collection, historical_dataset = get_sentinel_collection(start_date_historical, end_date_historical, roi)",
            "",
            "recent_image = recent_collection.map(mask_s2_clouds).median()",
            "recent_image_with_ndvi = add_ndvi(recent_image)",
            "",
            "historical_image = historical_collection.map(mask_s2_clouds).median()",
            "historical_image_with_ndvi = add_ndvi(historical_image)",
            "",
            "print(f'Using {recent_dataset} for the recent period and {historical_dataset} for the historical baseline.')",
        ]
    )
)

cells.append(
    code_cell(
        [
            "ndvi_difference = recent_image_with_ndvi.select('NDVI').subtract(",
            "    historical_image_with_ndvi.select('NDVI')",
            ")",
            "",
            "mean_ndvi_change_dict = ndvi_difference.reduceRegion(",
            "    reducer=ee.Reducer.mean(),",
            "    geometry=roi,",
            "    scale=30,",
            ")",
            "",
            "mean_ndvi_change_value = None",
            "mean_ndvi_change = mean_ndvi_change_dict.get('NDVI')",
            "if mean_ndvi_change is not None:",
            "    try:",
            "        mean_ndvi_change_value = mean_ndvi_change.getInfo()",
            "    except Exception as exc:",
            "        print(f'Unable to retrieve NDVI change: {exc}')",
            "",
            "if mean_ndvi_change_value is None:",
            "    alert_message = (",
            "        '>>> DATA WARNING: Unable to compute NDVI change for the selected period.\\n'",
            "        '>>> Please verify imagery availability or adjust the ROI and time range.\\n'",
            "    )",
            "    print('Average NDVI change could not be determined.')",
            "else:",
            "    print(f'Average NDVI Change from 2015 to 2024: {mean_ndvi_change_value:.4f}')",
            "    if mean_ndvi_change_value < VEGETATION_LOSS_THRESHOLD:",
            "        alert_message = (",
            "            '>>> RISK DETECTED: Significant vegetation loss identified.\\n'",
            "            '>>> This area is flagged as a high-risk hotspot.\\n'",
            "            '>>> Recommendation: Deploy Geo-Safe Sensor Nodes to this location.'",
            "        )",
            "    else:",
            "        alert_message = (",
            "            '>>> MONITORING: No significant large-scale vegetation loss detected.\\n'",
            "            '>>> Continue routine satellite monitoring of this area.'",
            "        )",
            "",
            "print('\n------------------------------------------------------------')",
            "print(''.join(alert_message))",
            "print('------------------------------------------------------------')",
        ]
    )
)

cells.append(
    code_cell(
        [
            "rgb_viz = {'min': 0.0, 'max': 0.3, 'bands': ['B4', 'B3', 'B2']}",
            "ndvi_viz = {'min': 0, 'max': 1, 'palette': ['blue', 'white', 'green']}",
            "change_viz = {'min': -0.5, 'max': 0.5, 'palette': ['red', 'white', 'green']}",
            "",
            "m = geemap.Map(center=[8.35, 124.65], zoom=12)",
            "m.add_layer(recent_image.clip(roi), rgb_viz, 'Recent Image (2024)')",
            "m.add_layer(historical_image.clip(roi), rgb_viz, 'Historical Image (2015)')",
            "m.add_layer(recent_image_with_ndvi.select('NDVI').clip(roi), ndvi_viz, 'Recent NDVI (Vegetation Health)')",
            "m.add_layer(ndvi_difference.clip(roi), change_viz, 'NDVI Change (Red indicates loss)')",
            "m.addLayerControl()",
            "m",
        ]
    )
)

notebook = {
    "cells": cells,
    "metadata": {
        "kernelspec": {
            "display_name": "Python 3",
            "language": "python",
            "name": "python3",
        },
        "language_info": {
            "file_extension": ".py",
            "mimetype": "text/x-python",
            "name": "python",
            "nbconvert_exporter": "python",
            "pygments_lexer": "ipython3",
            "version": "3.11",
        },
    },
    "nbformat": 4,
    "nbformat_minor": 5,
}

Path("GeoSafeMonitor.ipynb").write_text(json.dumps(notebook, indent=1))


cells_change: list[dict] = []

cells_change.append(
    markdown_cell(
        "# Geo-Safe Monitor PH: Land Use Change Analysis\n\n"
        "This notebook runs a supervised classification over Baungon, Bukidnon, then compares land cover between 2015 and 2025."
    )
)

cells_change.append(
    code_cell(
        [
            "import importlib.util",
            "import subprocess",
            "import sys",
            "",
            "DEPENDENCIES = {",
            "    'ee': 'earthengine-api',",
            "    'geemap': 'geemap',",
            "}",
            "",
            "for module_name, package_name in DEPENDENCIES.items():",
            "    if importlib.util.find_spec(module_name) is None:",
            "        print(f'Installing {package_name}...')",
            "        subprocess.check_call([sys.executable, '-m', 'pip', 'install', package_name])",
        ]
    )
)

cells_change.append(
    code_cell(
        [
            "import ee",
            "import geemap",
            "",
            "try:",
            "    ee.Initialize()",
            "    print('Google Earth Engine initialized.')",
            "except Exception:",
            "    print('Authenticating with Google Earth Engine...')",
            "    ee.Authenticate()",
            "    ee.Initialize()",
            "    print('Authentication complete.')",
        ]
    )
)

cells_change.append(
    markdown_cell(
        "## Configuration and Training Data\n\n"
        "Define ROI, land cover classes, and sample points used for the supervised classifier."
    )
)

cells_change.append(
    code_cell(
        [
            "roi = ee.Geometry.Rectangle([124.60, 8.30, 124.70, 8.40])",
            "",
            "GLAD_HEX = [",
            "    'FEFECC','FAFAC3','F7F7BB','F4F4B3','F1F1AB','EDEDA2','EAEA9A','E7E792','E4E48A',",
            "    'E0E081','DDDD79','DADA71','D7D769','D3D360','D0D058','CDCD50','CACA48','C6C63F','C3C337','C0C02F',",
            "    'BDBD27','B9B91E','B6B616','B3B30E','B0B006','609C60','5C985C','589558','549254','508E50','4C8B4C','488848',",
            "    '448544','408140','3C7E3C','387B38','347834','317431','2D712D','296E29','256B25','216721','1D641D','196119','155E15',",
            "    '115A11','0D570D','095409','065106','643700','643A00','643D00','644000','644300','644600','644900','654C00','654F00',",
            "    '655200','655500','655800','655A00','655D00','656000','656300','666600','666900','666C00','666F00','667200','667500',",
            "    '667800','667B00','FF99FF','FC92FC','F98BF9','F685F6','F37EF3','F077F0','ED71ED','EA6AEA','E763E7','E45DE4','E156E1',",
            "    'DE4FDE','DB49DB','D842D8','D53BD5','D235D2','CF2ECF','CC27CC','C921C9','C61AC6','C313C3','C00DC0','BD06BD','BB00BB',",
            "    '000003','000004','000005','BFC0C0','B7BDC2','AFBBC4','A8B8C6','A0B6C9','99B3CB','91B1CD','89AFD0','82ACD2','7AAAD4',",
            "    '73A7D6','6BA5D9','64A3DB','5CA0DD','549EE0','4D9BE2','4599E4','3E96E6','3694E9','2E92EB','278FED','1F8DF0','188AF2',",
            "    '1088F4','0986F7','55A5A5','53A1A2','519E9F','4F9B9C','4D989A','4B9597','499294','478F91','458B8F','43888C','418589',",
            "    '3F8286','3D7F84','3B7C81','39797E','37767B','357279','336F76','316C73','2F6970','2D666E','2B636B','296068','285D66',",
            "    'BB93B0','B78FAC','B48CA9','B189A6','AE85A2','AA829F','A77F9C','A47B99','A17895','9E7592','9A718F','976E8C','946B88',",
            "    '916885','8D6482','8A617F','875E7B','845A78','815775','7D5472','7A506E','774D6B','744A68','714765','DE7CBB','DA77B7',",
            "    'D772B3','D46EAF','D169AB','CE64A8','CB60A4','C85BA0','C4579C','C15298','BE4D95','BB4991','B8448D','B54089','B23B86',",
            "    'AF3682','AB327E','A82D7A','A52976','A22473','9F1F6F','9C1B6B','991667','961264','000000','000000','000000','1964EB',",
            "    '1555E4','1147DD','0E39D6','0A2ACF','071CC8','030EC1','0000BA','0000BA','040464','0000FF','3051CF','000000','000000',",
            "    '000000','000000','000000','000000','000000','000000','000000','000000','000000','000000','000000','000000','000000',",
            "    '000000','000000','547FC4','4D77BA','466FB1','4067A7','395F9E','335895','335896','335897','FF2828','FFFFFF','D0FFFF',",
            "    'FFE0D0','FF7D00','FAC800','C86400','FFF000','AFCD96','AFCD96','64DCDC','00FFFF','00FFFF','00FFFF','111133','000000'",
            "]",
            "GLAD_PALETTE = [f'#{c}' for c in GLAD_HEX]",
            "",
            "print('Configuration set for GLAD Global Land Cover and Land Use Change analysis.')",
        ]
    )
)

cells_change.append(
    code_cell(
        [
            "def get_glad_lcluc(year):",
            "    assets = {",
            "        2000: 'projects/glad/GLCLU2020/v2/LCLUC_2000',",
            "        2005: 'projects/glad/GLCLU2020/v2/LCLUC_2005',",
            "        2010: 'projects/glad/GLCLU2020/v2/LCLUC_2010',",
            "        2015: 'projects/glad/GLCLU2020/v2/LCLUC_2015',",
            "        2020: 'projects/glad/GLCLU2020/v2/LCLUC_2020',",
        "    }",
            "    asset_id = assets.get(year)",
            "    if asset_id is None:",
            "        raise ValueError(f'No GLAD land cover asset configured for {year}.')",
            "    return ee.Image(asset_id)",
        ]
    )
)

cells_change.append(
    code_cell(
        [
            "credit_text = ('This data is made available by the Global Land Analysis and Discovery (GLAD) lab at the University of Maryland. '",
            "               'P.V. Potapov, M.C. Hansen, A.H. Pickens, A. Hernandez-Serna, A. Tyukavina, S. Turubanova, V. Zalles, X. Li, '"
            "               'A. Khan, F. Stolle, N. Harris, X.-P. Song, A. Baggett, I. Kommareddy, A. Komareddy (2022).')",
            "print(credit_text)",
            "print('For more information please visit: https://glad.umd.edu/dataset/GLCLUC2020')",
            "print('The official legend is published at: https://storage.googleapis.com/earthenginepartners-hansen/GLCLU2000-2020/v2/legend.xlsx')",
        ]
    )
)

cells_change.append(
    code_cell(
        [
            "land_mask = ee.Image('projects/glad/OceanMask').lte(1)",
            "glad_images = {year: get_glad_lcluc(year).updateMask(land_mask).clip(roi) for year in [2000, 2005, 2010, 2015, 2020]}",
            "glad_change = ee.Image('projects/glad/GLCLU2020/v2/LCLUC').updateMask(land_mask).clip(roi)",
            "print('GLAD Global Land Cover and Land Use images loaded successfully.')",
        ]
    )
)

cells_change.append(
    code_cell(
        [
            "m = geemap.Map(center=[8.35, 124.65], zoom=9)",
            "m.add_basemap('SATELLITE')",
            "vis_params = {'min': 0, 'max': 255, 'palette': GLAD_PALETTE}",
            "m.add_layer(glad_images[2000], vis_params, 'GLAD Land Cover 2000')",
            "m.add_layer(glad_images[2005], vis_params, 'GLAD Land Cover 2005')",
            "m.add_layer(glad_images[2010], vis_params, 'GLAD Land Cover 2010')",
            "m.add_layer(glad_images[2015], vis_params, 'GLAD Land Cover 2015')",
            "m.add_layer(glad_images[2020], vis_params, 'GLAD Land Cover 2020')",
            "m.add_layer(glad_change, vis_params, 'GLAD Land Cover Change 2000-2020')",
            "legend_items = {",
            "    'Forest → Cropland': '#E67E22',",
            "    'Forest → Bare Ground': '#C0392B',",
            "    'Forest → Grassland': '#27AE60'",
            "}",
            "m.add_legend(title='Forest Conversion Drivers (2000→2020)', legend_dict=legend_items)",
            "m.addLayerControl()",
            "print('Displaying GLAD Global Land Cover and Land Use Change map ...')",
            "m",
        ]
    )
)

Path('GeoSafeMonitor_LandUseChange.ipynb').write_text(
    json.dumps(
        {
            "cells": cells_change,
            "metadata": {
                "kernelspec": {
                    "display_name": "Python 3",
                    "language": "python",
                    "name": "python3",
                },
                "language_info": {
                    "file_extension": ".py",
                    "mimetype": "text/x-python",
                    "name": "python",
                    "nbconvert_exporter": "python",
                    "pygments_lexer": "ipython3",
                    "version": "3.11",
                },
            },
            "nbformat": 4,
            "nbformat_minor": 5,
        },
        indent=1,
    )
)

