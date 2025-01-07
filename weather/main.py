import csv
import aiohttp
import asyncio
from fastapi import FastAPI, Request, Body
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates


# 创建FastAPI应用实例
bzy_app = FastAPI()

# 连接Jinja2模板以处理HTML模板（templates文件夹）
bzy_templates = Jinja2Templates(directory='templates')

# 全局城市字典，用于存储城市信息和温度
bzy_cities_dict = {}


def bzy_load_cities(csv_file_path: str) -> None:
    """
    从CSV文件加载城市列表，并将其存储到全局城市字典中。

    :param csv_file_path: CSV文件的路径，该文件包含城市名称、纬度和经度信息。
    """
    global bzy_cities_dict
    with open(csv_file_path, mode='r', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            bzy_city_name = row['city']
            bzy_latitude = row['latitude']
            bzy_longitude = row['longitude']
            bzy_cities_dict[bzy_city_name] = {
                'latitude': bzy_latitude,
                'longitude': bzy_longitude,
                'temperature': None
            }


# 加载城市列表
bzy_load_cities('europe.csv')


@bzy_app.get('/', response_class=HTMLResponse)
async def bzy_root(request: Request) -> HTMLResponse:
    """
    处理根路径的GET请求，返回初始页面index.html。

    :param request: FastAPI的请求对象。
    :return: 包含index.html内容的HTML响应。
    """
    return bzy_templates.TemplateResponse('index.html', {'request': request})


@bzy_app.get('/update')
async def bzy_update_weather() -> dict:
    """
    处理GET /update请求，获取每个城市的温度并返回城市及其温度的字典。

    此版本在获取温度后，按温度对城市进行排序。

    :return: 包含城市名称和对应温度的字典，按温度升序排列。
    """
    async def bzy_fetch_city_temperature(bzy_city: str) -> None:
        """
        内部异步函数，用于获取单个城市的温度。

        :param bzy_city: 城市名称。
        """
        bzy_latitude = bzy_cities_dict[bzy_city]['latitude']
        bzy_longitude = bzy_cities_dict[bzy_city]['longitude']
        bzy_url = f"https://api.open-meteo.com/v1/forecast?latitude={bzy_latitude}&longitude={bzy_longitude}&current_weather=true"
        async with aiohttp.ClientSession() as bzy_session:
            async with bzy_session.get(bzy_url) as bzy_response:
                bzy_data = await bzy_response.json()
                bzy_temperature = bzy_data['current_weather']['temperature']
                bzy_cities_dict[bzy_city]['temperature'] = bzy_temperature

    tasks = [bzy_fetch_city_temperature(bzy_city) for bzy_city in bzy_cities_dict]
    await asyncio.gather(*tasks)

    # 按温度对城市进行排序
    bzy_cities_sorted = sorted(bzy_cities_dict.items(), key=lambda item: item[1]['temperature'])
    bzy_cities_dict = dict(bzy_cities_sorted)

    return bzy_cities_dict


@bzy_app.post('/add_city')
async def bzy_add_city(bzy_city_data = Body(...)):
    global bzy_cities_dict
    bzy_city = bzy_city_data['city']
    bzy_latitude = bzy_city_data['latitude']
    bzy_longitude = bzy_city_data['longitude']
    bzy_cities_dict[bzy_city] = {'latitude': bzy_latitude, 'longitude': bzy_longitude, 'temperature': None}
    return JSONResponse(content={"message": f"{bzy_city} added successfully"})


@bzy_app.delete('/delete_city/{bzy_city_name}')
async def bzy_delete_city(bzy_city_name: str):
    global bzy_cities_dict
    if bzy_city_name in bzy_cities_dict:
        del bzy_cities_dict[bzy_city_name]
        return JSONResponse(content={"message": f"{bzy_city_name} deleted successfully"})
    else:
        return JSONResponse(content={"message": f"{bzy_city_name} not found"}, status_code = 404)


@bzy_app.post('/reset_cities')
async def bzy_reset_cities():
    global bzy_cities_dict
    bzy_load_cities('europe.csv')
    return JSONResponse(content={"message": "Cities list reset successfully"})
