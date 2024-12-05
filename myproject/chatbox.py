import sys
import re
import json
import os
from django.shortcuts import render
from django.http import JsonResponse
from django.utils.timezone import now
from django.db.models import Sum
from datetime import timedelta
from django.views.decorators.csrf import csrf_exempt

from .models import Users, Requests, Donations, FoodPackages

import openai
import mysql.connector

# Set OpenAI API key securely
openai.api_key = os.environ.get('OPENAI_API_KEY')

# MySQL connection details (ensure host value is correct)
db_config = {
    'user': 'dbuser',
    'password': 'Cs5200!pass',
    'host': '35.212.172.227',  # Corrected host value
    'database': 'foodbank'
}

def process_natural_language_query(user_query):
    """
    Process a user's natural language query, convert it into SQL using OpenAI, and execute the SQL query.
    """
    try:
        # Step 1: Generate SQL Query using OpenAI
        prompt = f"""

         You are an assistant that generates valid SQL queries for a food bank database based on natural language queries.

         The database schema is as follows:

         ### Tables and Fields:

         **category**
         - category (unique, varchar)
         - points (integer)

         **donations**
         - id (auto-incremented primary key)
         - donor_id (foreign key to users)
         - amount (decimal)
         - message (text, nullable)
         - donated_at (datetime)

         **food_packages**
         - id (auto-incremented primary key)
         - package_name (varchar)
         - description (text, nullable)
         - quantity (integer)
         - price_per_package (decimal)
         - purchased_at (datetime)
         - admin_id (foreign key to users)
         - category (varchar)
         - dietary (varchar)
         - point_per_package (integer)

         **requests**
        # - id (auto-incremented primary key)
         - student_id (foreign key to users)
         - amount (decimal)
         - reason (text)
         - status (varchar, nullable)
         - requested_at (datetime)
         - processed_at (datetime)
         - admin_id (foreign key to users, nullable)
         - package_id (foreign key to food_packages, nullable)
         - request_id (unique integer, nullable)

         **student**
         - user_id (primary key, foreign key to users)
         - nuid (varchar)
         - name (varchar)
         - email (unique, varchar)
         - point (integer, nullable)

         **users**
         - id (auto-incremented primary key)
         - username (unique, varchar)
         - password (varchar)
         - role (varchar)
         - email (varchar, nullable)
         - phone (varchar, nullable)
         - balance (decimal, nullable)
         - is_active (integer, nullable)
         - created_at (datetime)
        #  - point (integer, nullable)
        #  - student_id (unique integer, nullable)

         ### Instructions:

         - Use proper SQL syntax compliant with MySQL.
         - **Use the exact table and column names as provided, including correct casing (all lowercase).**
         - Handle necessary joins, groupings, and aggregations.
         - Return **only** the SQL query and nothing else.

         Convert the following natural language query into a valid SQL query:

         "{user_query}"

        """
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "system", "content": prompt}],
            max_tokens=150,
            temperature=0.3,  # Lower temperature for deterministic output
        )
        raw_query = response['choices'][0]['message']['content'].strip()

        # Step 2: Clean SQL Query
        sql_query = re.sub(r"^```[a-zA-Z]*\n|```$", "", raw_query).strip()

        # Step 3: Fix SQL for MySQL Compliance
        if "GROUP BY" in sql_query and "ORDER BY" in sql_query:
            # Extract aggregation used in ORDER BY
            match = re.search(r"ORDER BY (.+?)(ASC|DESC|LIMIT|$)", sql_query, re.IGNORECASE)
            if match:
                aggregation = match.group(1).strip()

                # Ensure the aggregation is included in SELECT
                select_part, rest_of_query = sql_query.split("FROM", 1)
                if aggregation not in select_part:
                    # Add aggregation to SELECT
                    select_part = select_part.strip() + f", {aggregation} AS total_donated"
                    sql_query = f"{select_part} FROM {rest_of_query}"

                # Ensure alias is referenced in ORDER BY
                sql_query = sql_query.replace(f"ORDER BY {aggregation}", "ORDER BY total_donated")

        # Strip leading/trailing whitespace
        sql_query = sql_query.strip()

        # Validate SQL Query
        if not sql_query.lower().startswith(("select", "insert", "update", "delete")):
            return f"Generated query is invalid: {sql_query}"

        # Step 4: Execute the SQL Query
        connection = mysql.connector.connect(**db_config)
        cursor = connection.cursor(dictionary=True)
        cursor.execute(sql_query)

        # Step 5: Fetch and Return Results
        if sql_query.lower().startswith("select"):
            results = cursor.fetchall()
        else:
            connection.commit()
            results = f"Query executed successfully: {sql_query}"

        cursor.close()
        connection.close()

        return results

    except openai.error.OpenAIError as e:
        return f"Error generating SQL query: {str(e)}"
    except mysql.connector.Error as e:
        return f"Database error: {str(e)}"
    except Exception as e:
        return f"An error occurred: {str(e)}"




def chatbox_view(request, uid):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            user_message = data.get('message', '').strip().lower()

            # Process the natural language query
            result = process_natural_language_query(user_message)

            # Format the result into a string for frontend display
            if isinstance(result, list):
                # If the result is a list of dictionaries (e.g., from SELECT queries), format it
                #response_text = "\n".join([str(row) for row in result])
                response_text = generate_natural_language_response(result)
            elif isinstance(result, str):
                # If the result is already a string (e.g., for INSERT/UPDATE), use it directly
                response_text = result
            else:
                # Handle other unexpected cases
                response_text = str(result)

            return JsonResponse({'response': response_text})
        except Exception as e:
            # Log the exception for debugging
            print(f"Error in chatbox_view: {e}")
            return JsonResponse({'error': 'An error occurred while processing your request.'}, status=500)
    else:
        # For GET request, render the chatbox.html template
        return render(request, 'chatbox.html')

def generate_natural_language_response(query_results):
    """将数据库查询结果转换为自然语言描述"""
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": 
                 "change the querying result to simple, friendly and understandable natural language."},
                {"role": "user", "content": str(query_results)}
            ],
            max_tokens=300,
            temperature=0.7
        )
        
        natural_language_result = response['choices'][0]['message']['content'].strip()
        return natural_language_result
    
    except Exception as e:
        return f"error when generating natural language response: {str(e)}"