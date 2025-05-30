<?php
// Teste para git status
require_once __DIR__ . '/vendor/autoload.php';
//te
use PhpAmqpLib\Connection\AMQPStreamConnection;
use PhpAmqpLib\Message\AMQPMessage;
use PhpAmqpLib\Exception\AMQPConnectionBlockedException;
use PhpAmqpLib\Exception\AMQPConnectionClosedException;
use PhpAmqpLib\Exception\AMQPChannelClosedException;


header("Content-Type: application/json");

$requestMethod = $_SERVER['REQUEST_METHOD'];
$requestPath = parse_url($_SERVER['REQUEST_URI'], PHP_URL_PATH);


define('RABBITMQ_HOST', getenv('RABBITMQ_HOST_PHP') ?: 'localhost');
define('RABBITMQ_PORT', (int)(getenv('RABBITMQ_PORT_PHP') ?: 5672));
define('RABBITMQ_USER', getenv('RABBITMQ_USER_PHP') ?: 'guest');
define('RABBITMQ_PASS', getenv('RABBITMQ_PASS_PHP') ?: 'guest');
define('RABBITMQ_QUEUE_LOGISTICS', 'logistics_queue');


switch ($requestPath) {
    case '/equipments':
        if ($requestMethod == 'GET') {
            $equipments = [
                ["id" => "EQP001", "name" => "Sonda de Perfuração AlphaDrill X1", "status" => "available", "location" => "Warehouse A"],
                ["id" => "EQP002", "name" => "Bomba Submersível WaterTitan 5000", "status" => "in_use", "location" => "Wellsite 3B"],
                ["id" => "EQP003", "name" => "Gerador Diesel PowerMax 750kW", "status" => "maintenance", "location" => "Workshop"],
                ["id" => "EQP004", "name" => "Válvula de Segurança GateLock Pro", "status" => "available", "location" => "Warehouse B"],
            ];
            echo json_encode($equipments);
        } else {
            http_response_code(405);
            echo json_encode(["error" => "Método não permitido para /equipments. Use GET."]);
        }
        break;

    case '/dispatch':
        if ($requestMethod == 'POST') {
            $inputJSON = file_get_contents('php://input');
            $input = json_decode($inputJSON, true);

            if (empty($input) || !isset($input['item_id']) || !isset($input['destination']) || !isset($input['priority'])) {
                http_response_code(400);
                echo json_encode([
                    "error" => "Dados de despacho inválidos. 'item_id', 'destination', e 'priority' são obrigatórios.",
                    "received_payload" => $input ?? $inputJSON
                ]);
                exit;
            }

            $connection = null;
            try {
                $connection = new AMQPStreamConnection(
                    RABBITMQ_HOST,
                    RABBITMQ_PORT,
                    RABBITMQ_USER,
                    RABBITMQ_PASS
                );
                $channel = $connection->channel();

                $channel->queue_declare(
                    RABBITMQ_QUEUE_LOGISTICS,
                    false,
                    true,
                    false,
                    false 
                );

                $messageBody = json_encode([
                    'type' => 'urgent_logistics_dispatch',
                    'payload' => $input,
                    'dispatch_request_time' => date('c')
                ]);

                $msg = new AMQPMessage(
                    $messageBody,
                    ['delivery_mode' => AMQPMessage::DELIVERY_MODE_PERSISTENT]
                );

                $channel->basic_publish($msg, '', RABBITMQ_QUEUE_LOGISTICS);

                
                error_log("PHP: Mensagem enviada para RabbitMQ (" . RABBITMQ_QUEUE_LOGISTICS . "): " . $messageBody);

                echo json_encode([
                    "message" => "Mensagem de logística urgente enviada para a fila RabbitMQ!",
                    "queue" => RABBITMQ_QUEUE_LOGISTICS,
                    "data_sent" => json_decode($messageBody)
                ]);//aaaaaaaaaasss

                $channel->close();
                $connection->close();
            } catch (AMQPConnectionBlockedException | AMQPConnectionClosedException | AMQPChannelClosedException $e) {
                http_response_code(503);
                error_log("PHP: Erro de conexão/canal com RabbitMQ: " . $e->getMessage());
                echo json_encode([
                    "error" => "Serviçoo RabbitMQ temporariamente indisponível.",
                    "details" => get_class($e) . ": " . $e->getMessage()
                ]);
            } catch (Exception $e) {
                http_response_code(500);
                error_log("PHP: Erro ao enviar mensagem para RabbitMQ: " . $e->getMessage() . " Trace: " . $e->getTraceAsString());
                echo json_encode([
                    "error" => "Erro interno ao processar despacho para RabbitMQ.",
                    "details" => get_class($e) . ": " . $e->getMessage()
                ]);
            } finally {
                if ($connection !== null && $connection->isConnected()) {
                    try { $connection->close(); } catch (Exception $ex) { /* ignore */ }
                }
            }

        } else {
            http_response_code(405);
            echo json_encode(["error" => "Método não permitido para /dispatch. Use POST."]);
        }
        break;

    default:
        http_response_code(404);
        echo json_encode(["error" => "Endpoint não encontrado: " . htmlspecialchars($requestPath)]);
        break;
}
?>