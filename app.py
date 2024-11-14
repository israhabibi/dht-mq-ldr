import psycopg2
from flask import Flask, request, jsonify, render_template
from datetime import datetime, timedelta
from dotenv import load_dotenv
import logging
import os

# Load environment variables from .env file
load_dotenv()

# Access environment variables
db_host = os.getenv('DB_HOST')
db_port = os.getenv('DB_PORT')
db_name = os.getenv('DB_NAME')
db_user = os.getenv('DB_USER')
db_password = os.getenv('DB_PASSWORD')

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

app = Flask(__name__)

# Insert data into PostgreSQL
def insert_data_to_postgres(temperature, humidity, mq2_value, mq135_value, ldr_value):
    try:
        # Connect to PostgreSQL
        connection = psycopg2.connect(
            host=db_host,
            port=db_port,
            dbname=db_name,
            user=db_user,
            password=db_password
        )
        cursor = connection.cursor()

        # Insert query
        insert_query = """
        INSERT INTO dht_mq_ldr 
        (temperature, humidity, mq2_value, mq135_value, ldr_value, timestamp)
        VALUES (%s, %s, %s, %s, %s, %s)
        """
        cursor.execute(insert_query, (
            temperature,
            humidity,
            mq2_value,
            mq135_value,
            ldr_value,
            datetime.now()  # timestamp in Asia/Jakarta
        ))

        # Commit the transaction
        connection.commit()
        logging.info("Data inserted successfully")

    except (Exception, psycopg2.DatabaseError) as error:
        logging.error(f"Error inserting data: {error}")
    finally:
        if connection:
            cursor.close()
            connection.close()

# Route for inserting data
@app.route('/insert_data', methods=['POST'])
def insert_data():
    if request.method == 'POST':
        # Fetch sensor data from ESP32
        temperature = request.form.get('temperature')
        humidity = request.form.get('humidity')
        mq2_value = request.form.get('mq2Value')
        mq135_value = request.form.get('mq135Value')
        ldr_value = request.form.get('ldrValue')

        # Check if any sensor data is missing
        if any(param is None for param in [temperature, humidity, mq2_value, mq135_value, ldr_value]):
            logging.warning("Missing sensor data in the request")
            return jsonify({"error": "Missing sensor data"}), 400

        # Insert sensor data into PostgreSQL
        insert_data_to_postgres(
            temperature,
            humidity,
            mq2_value,
            mq135_value,
            ldr_value
        )

        return jsonify({"message": "Data inserted successfully"}), 201

    logging.warning("Invalid request method")
    return jsonify({"message": "Invalid request method"}), 405

# Helper function to connect to the PostgreSQL database
def get_db_connection():
    return psycopg2.connect(
        host=db_host,
        port=db_port,
        dbname=db_name,
        user=db_user,
        password=db_password
    )

# Get the latest data from the database
@app.route('/latest_data', methods=['GET'])
def get_latest_data():
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute("SELECT temperature, humidity, mq2_value, mq135_value, ldr_value, timestamp FROM dht_mq_ldr ORDER BY timestamp DESC LIMIT 1")
        latest_data = cursor.fetchone()
        
        if latest_data:
            data = {
                "temperature": latest_data[0],
                "humidity": latest_data[1],
                "mq2_value": latest_data[2],
                "mq135_value": latest_data[3],
                "ldr_value": latest_data[4],
                "timestamp": latest_data[5].strftime('%Y-%m-%d %H:%M:%S')
            }
        else:
            data = {}

        return jsonify(data)
    except (Exception, psycopg2.DatabaseError) as error:
        logging.error(f"Error fetching latest data: {error}")
        return jsonify({"error": "Error fetching latest data"}), 500
    finally:
        if connection:
            cursor.close()
            connection.close()

# Get last week's history: min, max, avg per hour
@app.route('/history_last_week', methods=['GET'])
def get_history_last_week():
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        
        query = """
        SELECT
            date_trunc('hour', timestamp) AS hour,
            MIN(temperature) AS min_temp,
            MAX(temperature) AS max_temp,
            AVG(temperature) AS avg_temp
        FROM dht_mq_ldr
        WHERE timestamp > NOW() - INTERVAL '7 days'
        GROUP BY hour
        ORDER BY hour;
        """
        cursor.execute(query)
        history_data = cursor.fetchall()

        result = []
        for row in history_data:
            result.append({
                "hour": row[0].strftime('%Y-%m-%d %H:%M:%S'),
                "min_temp": row[1],
                "max_temp": row[2],
                "avg_temp": row[3]
            })
        
        return jsonify(result)
    except (Exception, psycopg2.DatabaseError) as error:
        logging.error(f"Error fetching history data: {error}")
        return jsonify({"error": "Error fetching history data"}), 500
    finally:
        if connection:
            cursor.close()
            connection.close()

# Get daily summary
@app.route('/daily_summary', methods=['GET'])
def get_daily_summary():
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        
        query = """
        SELECT
            date_trunc('day', timestamp) AS day,
            MIN(temperature) AS min_temp,
            MAX(temperature) AS max_temp,
            AVG(temperature) AS avg_temp
        FROM dht_mq_ldr
        GROUP BY day
        ORDER BY day DESC;
        """
        cursor.execute(query)
        daily_summary_data = cursor.fetchall()

        result = []
        for row in daily_summary_data:
            result.append({
                "day": row[0].strftime('%Y-%m-%d'),
                "min_temp": row[1],
                "max_temp": row[2],
                "avg_temp": row[3]
            })
        
        return jsonify(result)
    except (Exception, psycopg2.DatabaseError) as error:
        logging.error(f"Error fetching daily summary: {error}")
        return jsonify({"error": "Error fetching daily summary"}), 500
    finally:
        if connection:
            cursor.close()
            connection.close()

# Route to render the UI page
@app.route('/')
def index():
    return render_template('index.html')

if __name__ == "__main__":
    app.run(debug=False, host='0.0.0.0')
