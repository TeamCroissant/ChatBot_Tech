# Integración del Chatbot con Telegram y AWS Lambda

Este chatbot se conecta con Telegram utilizando un **webhook** configurado a través de **API Gateway**, el cual enruta directamente los mensajes a una **función AWS Lambda**.

## Conexión

Se estableció un webhook desde Telegram apuntando a un endpoint público de API Gateway (HTTP API). Este endpoint está vinculado a una función Lambda que recibe las actualizaciones enviadas por los usuarios del bot.

## Función Lambda

La Lambda:

- Recibe el mensaje del usuario directamente desde Telegram.
- Extrae datos clave como el **ID del usuario** y el **texto del mensaje**.
- Evalúa el **sentimiento del mensaje** utilizando un modelo de análisis emocional.
- Lleva un **seguimiento acumulado del estado emocional del usuario** calculando el promedio de los sentimientos recibidos durante toda la conversación.
- Registra cada mensaje recibido junto con el sentimiento detectado y otros metadatos.

## Conexión con el modelo LLM

Tanto el mensaje del usuario como su perfil emocional actualizado son enviados al **modelo LLM**, descrito en el archivo [`LLM.md`](./LLM.md).

El modelo LLM genera una respuesta teniendo en cuenta:

- El contenido textual del mensaje.
- El contexto emocional acumulado del usuario.
- El historial reciente de conversación si aplica.

Esto permite generar respuestas más humanas y empáticas, adaptadas a la situación emocional del usuario.

## Registro de conversaciones

Todos los mensajes y análisis emocionales se **guardan individualmente por usuario**. Esto permite:

- Analizar la evolución emocional de cada usuario.
- Realizar auditorías o revisiones por conversación.
- Entrenar futuros modelos con historiales reales etiquetados.

---

Esta arquitectura permite una experiencia de chatbot más consciente y adaptativa, combinando **comunicación en tiempo real (Telegram)** con **procesamiento emocional y cognitivo (Lambda + LLM)**.
