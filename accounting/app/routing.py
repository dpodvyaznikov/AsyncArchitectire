import pika
import aio_pika
import httpx
import json
import numpy as np
from db import crud, models, schemas, SessionLocal, engine


async def get_task(id):
    data = {'email': 'adminest@admin.com', 'password':'sesurity'}
    async with httpx.AsyncClient() as client:
        response = await client.post('http://auth:8080/login', json=data)
    cookie_authorization = response.cookies.get("access_token_cookie")
    cookies = httpx.Cookies()
    cookies.set('access_token_cookie', cookie_authorization)
    async with httpx.AsyncClient() as client:
        task_info = await client.get(f'http://tracker:8081/task/{id}', cookies=cookies)
    return task_info.json()

async def get_user(public_id):
    data = {'email': 'adminest@admin.com', 'password':'sesurity'}
    async with httpx.AsyncClient() as client:
        response = await client.post('http://auth:8080/login', json=data)
    cookie_authorization = response.cookies.get("access_token_cookie")
    cookies = httpx.Cookies()
    cookies.set('access_token_cookie', cookie_authorization)
    async with httpx.AsyncClient() as client:
        user_info = await client.get(f'http://auth:8080/user_info/{public_id}', cookies=cookies)
    return user_info.json()

async def process_incoming(message):
    body = json.loads(message.body)
    id = body["properties"]["data"]["public_id"]
    if 'Account.Created' in body['title']:
        ...
    if 'Account.Updated' in body['title']:
        ...
    if 'Task.Created' in body['title']:
        task = await get_task(id)
        print(task)
        db = SessionLocal()
        cost, reward = np.random.randint(-10,-20), np.random.randint(20,40)
        crud.create_task(db, task.id, task.title, cost, reward, task.assignee)
    if 'Task.Finished' in body['title']:
        db = SessionLocal()
        crud.finish_task(db, id)
    if 'Task.Shuffled' in body['title']:
        task = await get_task(id)
        print(task)
        db = SessionLocal()
        crud.create_task(db=db, )
    await message.ack()

class TrackerPika:

    def __init__(self):
        self.connection = pika.BlockingConnection(
            pika.ConnectionParameters(host='rabbitmq'))
        self.channel = self.connection.channel()
        self.channel.exchange_declare(exchange='app_events', exchange_type='topic')
        self.process_incoming = process_incoming

    def send_event(self, routing_key: str, message: str):
        self.channel.basic_publish(
            exchange='app_events', routing_key=routing_key, body=message)

    async def consume(self, loop):
        """Setup message listener with the current running loop"""
        connection = await aio_pika.connect_robust(host='rabbitmq', port=5672, loop=loop)
        channel = await connection.channel()

        exchange = await channel.declare_exchange(name='app_events', type='topic')
        queue =  await channel.declare_queue('', exclusive=True)

        binding_keys = ('account.*',)
        for binding_key in binding_keys:
            await queue.bind(exchange='app_events', routing_key=binding_key)

        await queue.consume(process_incoming, no_ack=False)
        return connection