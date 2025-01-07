import csv
import asyncio
import aiohttp
from fastapi import FastAPI, Request, HTTPException, Depends, Body
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from typing import Dict

app = FastAPI()
templates = Jinja2Templates(directory='templates')

# 用于存储首都信息的全局字典
capitals_info = {}


def load_capitals_info(filename):
    global capitals_info
    capitals_info.clear()
    with open(filename, mode='r', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            capital = row['capital']
            latitude = float(row['latitude'])
            longitude = float(row['longitude'])
            capitals_info[capital] = {
                'latitude': latitude,
                'longitude': longitude,
                'temperature': None
            }


load_capitals_info('europe.csv')


async def fetch_single_capital_weather(lat, lon):
    url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    return data['current_weather']['temperature']
                else:
                    raise HTTPException(status_code=response.status, detail=f"API request failed with status {response.status}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching weather data: {str(e)}")


@app.get('/update')
async def fetch_weather():
    global capitals_info
    tasks = []
    for capital, info in capitals_info.items():
        lat = info['latitude']
        lon = info['longitude']
        tasks.append(fetch_single_capital_weather(lat, lon))

    temperatures = await asyncio.gather(*tasks)
    for i, capital in enumerate(capitals_info.keys()):
        capitals_info[capital]['temperature'] = temperatures[i]

    # 按温度升序排序
    sorted_capitals = sorted(capitals_info.items(), key=lambda x: x[1]['temperature'])
    return {capital: info for capital, info in sorted_capitals}


@app.post('/add_capital')
async def add_capital(capital_data: Dict[str, float] = Body(...)):
    capital = list(capital_data.keys())[0]
    latitude = capital_data[capital]['latitude']
    longitude = capital_data[capital]['longitude']
    if capital in capitals_info:
        raise HTTPException(status_code=400, detail=f"Capital {capital} already exists.")
    capitals_info[capital] = {
        'latitude': latitude,
        'longitude': longitude,
        'temperature': None
    }
    return JSONResponse(content={"message": f"Capital {capital} added successfully."})


@app.delete('/delete_capital/{capital_name}')
async def delete_capital(capital_name: str):
    if capital_name not in capitals_info:
        raise HTTPException(status_code=400, detail=f"Capital {capital_name} does not exist.")
    del capitals_info[capital_name]
    return JSONResponse(content={"message": f"Capital {capital_name} deleted successfully."})


@app.get('/reset')
async def reset_capitals():
    load_capitals_info('europe.csv')
    return JSONResponse(content={"message": "Capital list reset successfully."})


@app.get('/', response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse('index.html', {'request': request})
