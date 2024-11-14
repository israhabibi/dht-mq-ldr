import psycopg2
from flask import Flask, request, jsonify
from datetime import datetime
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

if __name__ == "__main__":
    app.run(debug=False, host='0.0.0.0')
