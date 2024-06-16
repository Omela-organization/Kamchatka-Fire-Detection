import ee
import datetime
import geopandas
import numpy as np
import pandas as pd

# Trigger the authentication flow.
ee.Authenticate()

# Initialize the library.
# Здесь нужно указать имя своего проекта в gee
ee.Initialize(project='ee-eliseynimka')

def ee_array_to_df(arr, list_of_bands, dropna=True):
    """Формирует из клиентского списка ee.Image.getRegion объект pandas.DataFrame.

    Аргументы:
    arr -- массив, возвращаемый методом .getInfo()
    list_of_bands -- список каналов
    dropna -- если True, исключает строки с пропущенными значениями (default True)
    """
    df = pd.DataFrame(arr)

    # Добавление звголовков
    headers = df.iloc[0]
    df = pd.DataFrame(df.values[1:], columns=headers)

    # Сохранение необходимых столбцов (и удаление остальных)
    df = df[['time', *list_of_bands]]
    if dropna:
      # Удаление строк, где есть хотя бы одно пропущенное значение
      df = df.dropna()

    # Перевод данных в числовые
    for band in list_of_bands:
        df[band] = pd.to_numeric(df[band], errors='coerce')

    # Перевод времени в милисикундак в datetime
    df['datetime'] = pd.to_datetime(df['time'], unit='ms')

    # Из времени оставляем только datetime
    df = df[['datetime', *list_of_bands]]

    return df

def get_FireMask_and_AdditionalData(points, first_date, res=250, save_GeoJson=False):
  # Создание полигона по заданным точкам
  roi =  ee.Geometry.BBox(*points)

  end_date = str(pd.date_range(start=first_date, periods=2)[1]).split()[0]

  try:
    # Получение снимка с MODIS
    MODIS = ee.ImageCollection('MODIS/061/MOD14A1').filter(ee.Filter.date(first_date, end_date))\
    .filterBounds(roi)\
    .select(['MaxFRP', 'FireMask'])\
    .getRegion(roi, res)\
    .getInfo()

    # Преобразование изображения с MODIS в pandas.DataFrame
    df = ee_array_to_df(MODIS, ['longitude', 'latitude', 'MaxFRP', 'FireMask'], dropna=False)

    # Вычисление различных характеристик зоны пожара
    temp = df[~df['MaxFRP'].isna()].describe()

    # Вычисление площади горящей территории
    size = (np.pi / 180) * (6371000) ** 2 * abs(np.sin(temp.loc['min', 'latitude']) - np.sin(temp.loc['max', 'latitude'])) * abs(temp.loc['min', 'longitude'] - temp.loc['max', 'longitude']) / 1000

    # Вычисление FRPS
    df['FRPS'] =  np.round((10 ** 6) * df['MaxFRP'] / size)

    df.dropna(inplace=True)

    if save_GeoJson:
      points = geopandas.points_from_xy(x=df.longitude, y=df.latitude)
      gdf = geopandas.GeoDataFrame(df, geometry=points)
      gdf.to_file('output.geojson', driver='GeoJSON')

    return df
  except:
    return 'No data'
