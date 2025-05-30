const express = require('express');
const Redis = require('ioredis');
const axios = require('axios');
// te
const app = express();
const port = 3000;
const pythonApiUrl = 'http://localhost:5000/event';

app.use(express.json());

const redisClient = new Redis({
  host: 'localhost',
  port: 6379,
});

redisClient.on('error', (err) => console.error('Erro no Cliente Redis:', err));
redisClient.on('connect', () => console.log('Node.js: Conectado ao Redis!'));

app.get('/sensor-data', async (req, res) => {
  const cacheKey = 'sensor-data';
  try {
    const cachedData = await redisClient.get(cacheKey);
    if (cachedData) {
      console.log('Node.js: Retornando dados do cache Redis para /sensor-data.');
      return res.json(JSON.parse(cachedData));
    }

    const data = {
      temperature: (Math.random() * 100 + 50).toFixed(2) + " °C",
      pressure: (Math.random() * 1000 + 100).toFixed(2) + " PSI",
      timestamp: new Date().toISOString(),
    };

    await redisClient.set(cacheKey, JSON.stringify(data), 'EX', 60);
    console.log('Node.js: Dados do sensor gerados, cacheados e retornados.');
    res.json(data);
  } catch (error) {
    console.error('Node.js: Erro ao buscar dados do sensor:', error);
    res.status(500).send('Erro interno do servidor');
  }
});

app.post('/alert', async (req, res) => {
  const alertData = req.body;
  if (!alertData || Object.keys(alertData).length === 0) {
    return res.status(400).send('Corpo da requisição para alerta está vazio.');
  }

  console.log('Node.js: Recebido alerta para enviar:', alertData);
  try {
    const payloadToPython = {
        type: 'sensor_alert',
        details: alertData,
        source: 'nodejs-sensor-api',
        timestamp: new Date().toISOString()
    };
    console.log(`Node.js: Enviando alerta para API Python em ${pythonApiUrl} com payload:`, payloadToPython);
    const response = await axios.post(pythonApiUrl, payloadToPython);
    console.log('Node.js: Alerta enviado para API Python com sucesso:', response.data);
    res.status(200).json({ message: 'Alerta enviado com sucesso para a API Python!', dataSent: payloadToPython, pythonResponse: response.data });
  } catch (error) {
    console.error('Node.js: Erro ao enviar alerta para API Python:', error.message);
    if (error.response) {
        console.error('Node.js: Detalhes do erro da API Python:', error.response.data);
        res.status(error.response.status || 500).json({ message: 'Erro ao contatar API Python', error: error.response.data });
    } else if (error.request) {
        res.status(500).json({ message: 'API Python não respondeu ao alerta', error: error.message });
    } else {
        res.status(500).json({ message: 'Erro ao processar a requisição de alerta', error: error.message });
    }
  }
});

app.listen(port, () => {
  console.log(`API Node.js (Sensores) rodando em http://localhost:${port}`);
});