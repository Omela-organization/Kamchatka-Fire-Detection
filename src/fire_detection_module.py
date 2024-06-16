import geojson
import rasterio
import numpy as np
from PIL import Image
from rasterio.transform import xy

from sentry_sdk.crons import monitor


def scaler(arr: np.array) -> np.array:
    return (arr - arr.min()) / (arr.max() - arr.min())


@monitor(monitor_slug='monitoring-fire-detection')
def fire_detection(paths: dict, path_to_save_result: str, save_img=False) -> None:
    if len(paths.keys()) != 6:
        raise 'Invalid lenght of the paths'

    # Загрузка одноканальных снимков
    with rasterio.open(paths['B2'], "r", driver='JP2OpenJPEG') as src:
        B2 = src.read()

    with rasterio.open(paths['B3'], "r", driver='JP2OpenJPEG') as src:
        B3 = src.read()

    with rasterio.open(paths['B4'], "r", driver='JP2OpenJPEG') as src:
        B4 = src.read()

    with rasterio.open(paths['B8'], "r", driver='JP2OpenJPEG') as src:
        B8 = src.read()

    with rasterio.open(paths['B11'], "r", driver='JP2OpenJPEG') as src:
        B11 = src.read()

    with rasterio.open(paths['B12'], "r", driver='JP2OpenJPEG') as src:
        B12 = src.read()
        transform = src.transform

    # Шкалирование снимков
    B2 = scaler(B2)
    B3 = scaler(B3)
    B4 = scaler(B4)
    B8 = scaler(B8)
    B11 = scaler(B11)
    B12 = scaler(B12)

    # Подсчет индексов и создание маски для детекции гари
    NDWI = (B3 - B8) / (B3 + B8)
    NDVI = (B8 - B4) / (B8 + B4)
    INDEX = ((B11 - B12) / (B11 + B12)) + B8
    mask = (INDEX > 0.1) | (B2 > 0.1) | (B11 < 0.1) | (NDVI > 0.3) | (NDWI > 0.1)

    # Формирование итогового массива с выделенными участками гари
    red_pixel = np.array([1, 0, 0])
    res = np.where(mask[0][:, :, None], 2.5 * np.stack((B4[0], B3[0], B2[0]), axis=-1), red_pixel)

    # Создание изображения
    if save_img:
        RGBRes = (255 * res).astype(np.uint8)
        img = Image.fromarray(RGBRes, 'RGB')
        img.save('final.jpg')

    # Формирование маски
    mask_ = np.where(mask[0][:, :, None], np.array([1, 0, 0]), np.array([0, 0, 0]))

    # Подготовка координат для создания GeoJSON
    coordinates = np.column_stack(np.where(mask_))
    lonlats = [xy(transform, x, y) for x, y, _ in coordinates]
    gj = geojson.FeatureCollection([
        geojson.Feature(geometry=geojson.Polygon([lonlats]), properties={})
    ])

    with open(path_to_save_result, 'w') as f:
        geojson.dump(gj, f)
