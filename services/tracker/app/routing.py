import pika
import aio_pika
import httpx
import json
from db import crud, models, schemas, SessionLocal, engine


# async def get_user(public_id):
#     data = {'email': 'adminest@admin.com', 'password':'sesurity'}
#     async with httpx.AsyncClient() as client:
#         response = await client.post('http://auth:8080/login', json=data)
#     cookie_authorization = response.cookies.get("access_token_cookie")
#     cookies = httpx.Cookies()
#     cookies.set('access_token_cookie', cookie_authorization)
#     async with httpx.AsyncClient() as client:
#         user_info = await client.get(f'http://auth:8080/user_info/{public_id}', cookies=cookies)
#     return user_info.json()

async def process_incoming(message):
    print(message)
    body = json.loads(message.body)
    if 'Account.Created' in body['title']:
        data = body["properties"]["data"]
        db = SessionLocal()
        crud.create_user(db=db, user=schemas.User(**data))
    if 'Account.Updated' in body['title']:
        data = body["properties"]["data"]
        db = SessionLocal()
        crud.update_user(db=db, user=schemas.User(**data))
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