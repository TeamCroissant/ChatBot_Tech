import json
import urllib.request
import os
import boto3
from datetime import datetime
import uuid
from decimal import Decimal

print('Loading function')
BOT_TOKEN = os.environ['BOT_TOKEN']
CONVERSATIONS_DB = os.environ['CONVERSATIONS_DB']
USERS_DB = os.environ['USERS_DB']
BEDROCK_AGENT_ID = os.environ['BEDROCK_AGENT_ID']
BEDROCK_AGENT_ALIAS_ID = os.environ['BEDROCK_AGENT_ALIAS_ID']

def load_db(tabla):
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(tabla)
    return table

def load_user(user_id, first_name, date):
    table = load_db(USERS_DB)
    
    try:
        response = table.get_item(Key={'id': str(user_id)})
        if 'Item' in response:
            return response['Item']
        else:
            # Usuario no registrado, lo creamos
            new_user = {
                'id': str(user_id),
                'name': first_name,
                'last_message': date,
                'user_message_count': 0
            }
            table.put_item(Item=new_user)
            return new_user
    except Exception as e:
        print(f"Error al cargar o guardar usuario: {e}")
        return None

def call_sentiment_analysis(text):
    comprehend = boto3.client('comprehend')

    response = comprehend.detect_sentiment(
        Text=text,
        LanguageCode='es'  # o 'en'
    )

    sentimiento = response['Sentiment']
    puntajes = response['SentimentScore']

    return sentimiento, puntajes

def store_message(user_id, message_text, input_type="text", input_by="user"):
    """Store user message with sentiment analysis in conversations table"""
    table = load_db(CONVERSATIONS_DB)
    
    try:
        # Analyze sentiment
        sentiment_result, sentiment_scores = call_sentiment_analysis(message_text)
        
        # Create conversation record
        timestamp = int(datetime.now().timestamp())
        conversation_item = {
            'user_id': str(user_id),
            'timestamp': timestamp,
            'input': message_text,
            'input_by': input_by,
            'input_type': input_type,
            'sentiment': {
                'mixed': Decimal(str(sentiment_scores.get('Mixed', 0))),
                'negative': Decimal(str(sentiment_scores.get('Negative', 0))),
                'neutral': Decimal(str(sentiment_scores.get('Neutral', 0))),
                'positive': Decimal(str(sentiment_scores.get('Positive', 0)))
            }
        }
        
        table.put_item(Item=conversation_item)
        print(f"Message stored with sentiment: {sentiment_result}")
        
        # Return sentiment scores for user table update
        return sentiment_scores
        
    except Exception as e:
        print(f"Error storing message: {e}")
        return None

def call_bedrock_agent(user_id, message_text):
    """Call Bedrock agent with session management"""
    bedrock_agent_runtime = boto3.client('bedrock-agent-runtime')
    
    try:
        # Use user_id as session_id for continuity
        session_id = str(user_id)
        
        response = bedrock_agent_runtime.invoke_agent(
            agentId=BEDROCK_AGENT_ID,
            agentAliasId=BEDROCK_AGENT_ALIAS_ID,
            sessionId=session_id,
            inputText=message_text
        )
        
        # Extract response from the event stream
        event_stream = response['completion']
        agent_response = ""
        
        for event in event_stream:
            if 'chunk' in event:
                chunk = event['chunk']
                if 'bytes' in chunk:
                    agent_response += chunk['bytes'].decode('utf-8')
        
        return agent_response.strip()
        
    except Exception as e:
        print(f"Error calling Bedrock agent: {e}")
        return "Lo siento, hubo un error procesando tu mensaje. Por favor intenta de nuevo."

def update_user_sentiment(user_id, new_sentiment_scores):
    """Update user's rolling average sentiment and message count"""
    table = load_db(USERS_DB)
    
    try:
        # Get current user data
        response = table.get_item(Key={'id': str(user_id)})
        if 'Item' not in response:
            print(f"User {user_id} not found for sentiment update")
            return False
            
        user = response['Item']
        current_count = user.get('user_message_count', 0)
        
        # Calculate new rolling averages using the formula:
        # new_average = (current_sentiment * message_count + new_score) / (message_count + 1)
        new_count = current_count + 1
        
        if current_count == 0 or 'sentiment' not in user:
            # First message - use new sentiment scores directly
            new_sentiment = {
                'mixed': Decimal(str(new_sentiment_scores.get('Mixed', 0))),
                'negative': Decimal(str(new_sentiment_scores.get('Negative', 0))),
                'neutral': Decimal(str(new_sentiment_scores.get('Neutral', 0))),
                'positive': Decimal(str(new_sentiment_scores.get('Positive', 0)))
            }
        else:
            # Calculate rolling average for each sentiment
            current_sentiment = user['sentiment']
            new_sentiment = {}
            
            for sentiment_type in ['mixed', 'negative', 'neutral', 'positive']:
                # Convert current_avg from Decimal to float for calculation
                current_avg = float(current_sentiment.get(sentiment_type, 0))
                new_score = float(new_sentiment_scores.get(sentiment_type.capitalize(), 0))
                
                # Rolling average formula (all float calculations)
                new_avg = (current_avg * current_count + new_score) / new_count
                # Convert back to Decimal for DynamoDB storage
                new_sentiment[sentiment_type] = Decimal(str(new_avg))
        
        # Update user record
        table.update_item(
            Key={'id': str(user_id)},
            UpdateExpression='SET sentiment = :sentiment, user_message_count = :count',
            ExpressionAttributeValues={
                ':sentiment': new_sentiment,
                ':count': new_count
            }
        )
        
        print(f"User sentiment updated. New count: {new_count}")
        print(f"New rolling averages: {new_sentiment}")
        return True
        
    except Exception as e:
        print(f"Error updating user sentiment: {e}")
        return False

def store_agent_response(user_id, response_text):
    """Store agent response without sentiment analysis"""
    table = load_db(CONVERSATIONS_DB)
    
    try:
        timestamp = int(datetime.now().timestamp())
        conversation_item = {
            'user_id': str(user_id),
            'timestamp': timestamp,
            'input': response_text,
            'input_by': 'agent',
            'input_type': 'text'
            # Note: No sentiment analysis for agent responses
        }
        
        table.put_item(Item=conversation_item)
        print("Agent response stored successfully")
        return True
        
    except Exception as e:
        print(f"Error storing agent response: {e}")
        return False

def send_reply(chat_id, text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = json.dumps({"chat_id": chat_id, "text": text}).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
    urllib.request.urlopen(req)

def lambda_handler(event, context):
    print("EVENTO COMPLETO:")
    print(event)

    try:
        body = json.loads(event['body'])
        message = body['message']
        chat_id = message['chat']['id']
        user_id = message['from']['id']
        first_name = message['from'].get('first_name', 'Usuario')
        date = message.get('date', 0)
        message_text = message.get('text', '')

        # Skip processing if no text message
        if not message_text:
            return {
                'statusCode': 200,
                'body': json.dumps('OK - No text message')
            }

        # Load or create user
        user = load_user(user_id, first_name, date)
        if not user:
            send_reply(chat_id, "Error al procesar usuario. Por favor intenta de nuevo.")
            return {
                'statusCode': 200,
                'body': json.dumps('User processing error handled')
            }

        # Store user message with sentiment analysis
        print("Storing user message with sentiment analysis...")
        sentiment_scores = store_message(user_id, message_text, "text", "user")
        
        if sentiment_scores:
            # Update user's rolling average sentiment
            print("Updating user rolling sentiment average...")
            update_user_sentiment(user_id, sentiment_scores)

        # Call Bedrock agent
        print("Calling Bedrock agent...")
        agent_response = call_bedrock_agent(user_id, message_text)

        # Store agent response (without sentiment analysis)
        print("Storing agent response...")
        store_agent_response(user_id, agent_response)

        # Send response back to user
        send_reply(chat_id, agent_response)

        print("Processing completed successfully")

    except Exception as e:
        print("Error:", str(e))
        # Send error message to user
        try:
            # Try to extract chat_id from the event if possible
            if 'body' in event:
                body = json.loads(event['body'])
                if 'message' in body and 'chat' in body['message']:
                    chat_id = body['message']['chat']['id']
                    send_reply(chat_id, "Lo siento, hubo un error procesando tu mensaje. Por favor intenta de nuevo.")
        except:
            # If we can't send an error message, just log it
            print("Could not send error message to user")

    # ALWAYS return 200 to prevent Telegram retries
    return {
        'statusCode': 200,
        'body': json.dumps('OK')
    }
