import pika

class AuthPika:

    def __init__(self):
        self.connection = pika.BlockingConnection(
            pika.ConnectionParameters(host='rabbitmq'))
        self.channel = self.connection.channel()
        self.channel.exchange_declare(exchange='app_events', exchange_type='topic')

    def send_event(self, routing_key: str, message: dict):
        self.channel.basic_publish(
            exchange='app_events', routing_key=routing_key, body=message)
