# PROJETO MICROSERVIÇOS PETRÓLEO
API Node.js (Sensores) - api_sensores_nodejs

Simula dados de sensor e manda alerta.


Rotas:

GET /sensor-data: Pega dado de sensor. usa cache nessa rota.
POST /alert: Manda JSON de alerta pra API Python (/event).


API Python (Eventos Críticos) - api_eventos_python

Recebe alerta do Node e msg do RabbitMQ.

Rotas:

POST /event: Recebe alerta do Node e Salva. (Atualiza cache do /events).
GET /events: Lista todos os eventos que chegaram. usa cache nessa rota.


API PHP (Logística) - api_logistica_php

Lista uns equipamentos e manda msg URGENTE pro RabbitMQ.

Rotas:

GET /equipments: Devolve lista de equipamentos.
POST /dispatch: Pega JSON e joga na fila logistics_queue do RabbitMQ.
Body de exemplo: { "item_id": "PECA1", "destination": "POCO_B", "priority": "alta" }


Como funciona a conversa entre as api:

Node.js para a Python: Chamada via HTTP direto. a POST/alert do node chama a POST/event.

PHP manda pro RabbitMQ que manda pro Python: API php manda via POST/dispatch msg pra fila logistics_queue no RabbitMQ (a api manda a msg e nao fica esperando retorno, caso tenha retorno ele mostra na hora). A API Python fica "escutando" essa fila, pega a msg e processa.


Cache Redis é usado nessas rotas:

API Node.js: No GET /sensor-data. Pra não ter que gerar dado toda hora
API Python: No GET /events. Pra retornar a lista de eventos mais rapido


Fila RabbitMQ como entra as msg:

A API PHP usa pra mandar mensagem de "despacho urgente" (pela fila logistics_queue) sem precisar que a API Python receba ou esteja pronta pra receber, ela fica na fila.
A API Python usa essa fila (logistics_queue) pra pegar essas mensagens e salvar como evento.

# COMO RODAR

1. Coisas que você precisa ter instalado ANTES:

Docker (pra rodar Redis e RabbitMQ fácil)
Node.js e npm
Python e pip
PHP e Composer
2. Preparar o Ambiente (uma vez só):

Docker (Redis e RabbitMQ):
Redis: docker run -d --name meu-redis -p 6379:6379 redis
RabbitMQ: docker run -d --name meu-rabbitmq -p 5672:5672 -p 15672:15672 rabbitmq:3-management
(Rode esses comandos no seu terminal se ainda não tiver os containers rodando)
3. Rodar cada API (cada uma em um terminal diferente):

API 1: Node.js (Sensores)

Vá para a pasta: cd api_sensores_nodejs
Instale dependências (só na primeira vez ou se mudar): npm install
Rode a API: node app.js
Vai rodar em: http://localhost:3000
API 2: Python (Eventos Críticos)

Vá para a pasta: cd api_eventos_python
Ative o ambiente virtual (ex: source venv/bin/activate ou venv\Scripts\activate no Windows)
Instale dependências (só na primeira vez ou se mudar): pip install Flask redis pika (ou pip install -r requirements.txt se tiver um)
Rode a API: python app.py
Vai rodar em: http://localhost:5000
API 3: PHP (Logística)

Vá para a pasta: cd api_logistica_php
Instale dependências (só na primeira vez ou se mudar): composer install
Rode a API: php -S localhost:8000
Vai rodar em: http://localhost:8000
