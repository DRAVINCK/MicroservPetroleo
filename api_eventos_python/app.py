from flask import Flask, request, jsonify
import redis
import pika
import threading
import json
import os
import time
from datetime import datetime

app = Flask(__name__)

redis_host = os.environ.get('REDIS_HOST', 'localhost')
redis_port = int(os.environ.get('REDIS_PORT', 6379))
redis_client = None
try:
    redis_client = redis.StrictRedis(host=redis_host, port=redis_port, db=0, decode_responses=True)
    redis_client.ping()
    print("Python: Conectado ao Redis!")
except redis.exceptions.ConnectionError as e:
    print(f"Python: Não foi possível conectar ao Redis: {e}. Alguns recursos podem não funcionar.")


critical_events = []
events_cache_key = "critical_events_list"


RABBITMQ_HOST = os.environ.get('RABBITMQ_HOST', 'localhost')
RABBITMQ_QUEUE = 'logistics_queue'

def update_events_cache():
    """Atualiza o cache do Redis com a lista de eventos."""
    if not redis_client:
        print("Python: Cliente Redis não inicializado. Cache não será atualizado.")
        return
    try:
        redis_client.set(events_cache_key, json.dumps(critical_events))
        print("Python: Cache de eventos atualizado no Redis.")
    except redis.exceptions.RedisError as e:
        print(f"Python: Erro ao atualizar cache do Redis: {e}")

@app.route('/event', methods=['POST'])
def receive_event():
    event_data = request.json
    if not event_data:
        return jsonify({"error": "Dados do evento não fornecidos"}), 400

    print(f"Python: Evento HTTP recebido: {event_data}")
    event_data['received_at_python'] = datetime.utcnow().isoformat() + 'Z'
    critical_events.append(event_data)
    update_events_cache()
    return jsonify({"message": "Evento recebido com sucesso pela API Python!", "event_stored": event_data}), 201

@app.route('/events', methods=['GET'])
def get_events():
    if redis_client:
        try:
            cached_events = redis_client.get(events_cache_key)
            if cached_events:
                print("Python: Retornando eventos do cache Redis.")
                return jsonify(json.loads(cached_events)), 200
        except redis.exceptions.RedisError as e:
            print(f"Python: Erro ao acessar cache do Redis para eventos: {e}")

    print("Python: Retornando eventos da memória (cache não encontrado ou erro no Redis).")
    return jsonify(critical_events), 200

def rabbitmq_consumer_worker():
    print(f"Python (RabbitMQ Consumer): Tentando conectar ao RabbitMQ em {RABBITMQ_HOST}...")
    connection = None
    retry_interval = 5
    max_retries = 12

    for attempt in range(max_retries):
        try:
            connection = pika.BlockingConnection(pika.ConnectionParameters(host=RABBITMQ_HOST))
            print("Python (RabbitMQ Consumer): Conectado ao RabbitMQ!")
            break
        except pika.exceptions.AMQPConnectionError as e:
            print(f"Python (RabbitMQ Consumer): Falha ao conectar (tentativa {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                time.sleep(retry_interval)
            else:
                print("Python (RabbitMQ Consumer): Não foi possível conectar ao RabbitMQ após várias tentativas. O consumidor não iniciará.")
                return

    if not connection or connection.is_closed:
        return

    channel = connection.channel()
    channel.queue_declare(queue=RABBITMQ_QUEUE, durable=True)

    def callback(ch, method, properties, body):
        try:
            message_content = body.decode()
            print(f"Python (RabbitMQ Consumer): [x] Mensagem recebida da fila '{RABBITMQ_QUEUE}': {message_content}")
            message_data = json.loads(message_content)

            event_data = {
                "type": "logistics_dispatch_received",
                "details": message_data,
                "source": "rabbitmq_logistics_queue",
                "consumed_at_python": datetime.utcnow().isoformat() + 'Z'
            }
            critical_events.append(event_data)
            update_events_cache()
            ch.basic_ack(delivery_tag=method.delivery_tag)
            print(f"Python (RabbitMQ Consumer): [x] Mensagem processada e confirmada: {message_data.get('payload', {}).get('item_id', 'N/A')}")
        except json.JSONDecodeError:
            print(f"Python (RabbitMQ Consumer): Erro ao decodificar JSON da mensagem: {body.decode()}")
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
        except Exception as e:
            print(f"Python (RabbitMQ Consumer): Erro ao processar mensagem: {e}")
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)

    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(queue=RABBITMQ_QUEUE, on_message_callback=callback)

    print(f'Python (RabbitMQ Consumer): [*] Aguardando mensagens na fila {RABBITMQ_QUEUE}. Para sair pressione CTRL+C no terminal principal.')
    try:
        channel.start_consuming()
    except KeyboardInterrupt:
        print("Python (RabbitMQ Consumer): Consumo interrompido.")
    except Exception as e:
        print(f"Python (RabbitMQ Consumer): Erro crítico no loop de consumo: {e}")
    finally:
        if connection and not connection.is_closed:
            connection.close()
            print("Python (RabbitMQ Consumer): Conexão RabbitMQ fechada.")

if __name__ == '__main__':

    consumer_thread = threading.Thread(target=rabbitmq_consumer_worker, daemon=True)
    consumer_thread.start()

    app.run(host='0.0.0.0', port=5000, debug=False)