from telnetlib import SE
import pika
import aio_pika
import httpx
import json
import numpy as np
from db import crud, models, schemas, SessionLocal, engine


def send_payment(email, sum):
    # Not implemented :(
    _ = email, sum
    pass

def wrap_day():
    db = SessionLocal()
    users = db.query(models.User).distinct().all()
    for user in users:
        if user.balance > 0:
            send_payment(user.email, user.balance)
            crud.create_transaction(db, user_public_id=user.public_id, transaction=-user.balance,
                                    transaction_type='BalancePaid',
                                    comment=f'Daily payoff for {crud.cur_date()}')


async def process_incoming(message):
    body = json.loads(message.body)
    data = body["properties"]["data"]
    print(body)
    if 'Account.Created' in body['title']:
        db = SessionLocal()
        crud.create_user(db=db, user=schemas.User(**data))
    if 'Account.Updated' in body['title']:
        db = SessionLocal()
        crud.update_user(db=db, user=schemas.User(**data))
    if 'Task.Created' in body['title']:
        db = SessionLocal()
        cost, reward = np.random.randint(-20,-10), np.random.randint(20,40)
        crud.create_task(db, task=schemas.Task(**data), cost=cost, reward=reward)
    if 'Task.Finished' in body['title']:
        db = SessionLocal()
        crud.finish_task(db, **data)
    if 'Task.Reassigned' in body['title']:
        db = SessionLocal()
        crud.reassign_task(db=db, **data)
    if 'Accounting.DayEnded' in body['title']:
        wrap_day()
    await message.ack()

class AccountingPika:

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

        binding_keys = ('account.*', 'task.*', 'accounting.*')
        for binding_key in binding_keys:
            await queue.bind(exchange='app_events', routing_key=binding_key)

        await queue.consume(process_incoming, no_ack=False)
        return connection