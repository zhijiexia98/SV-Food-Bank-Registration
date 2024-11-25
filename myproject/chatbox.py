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
    'database': 'sv_foodbank'
}

def get_sql_query(prompt, max_tokens=150):
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are an assistant that outputs only SQL queries, and nothing else."},
                {"role": "user", "content": prompt},
            ],
            max_tokens=max_tokens,
            n=1,
            stop=None,
            temperature=0.5,
        )
        sql_query = response['choices'][0]['message']['content'].strip()
        sql_query = re.sub(r"(?i)sql", "", sql_query)

        # Use regex to extract the SQL part between triple quotes
        match = re.search(r"```(.*?)```", sql_query, re.DOTALL)

        if match:
            sql_query = match.group(1).strip()
        else:
            # If no triple quotes found, use the entire response
            sql_query = sql_query.strip()

        return sql_query
    except Exception as e:
        print(f"Error in get_sql_query: {e}")
        return f"Error generating SQL query: {e}"

def execute_sql_query(query):
    try:
        # Connect to the database
        connection = mysql.connector.connect(**db_config)
        cursor = connection.cursor()

        cursor.execute(query)
        # Fetch the result if it's a SELECT query
        if query.strip().upper().startswith('SELECT'):
            result = cursor.fetchall()
            cursor.close()
            connection.close()
            return result
        else:
            connection.commit()
            cursor.close()
            connection.close()
            return "Query executed successfully."

    except mysql.connector.Error as err:
        print(f"Error executing SQL query: {err}")
        return f"Error executing SQL query: {err}"

def donor_suggestion(donor_id):
    """
    Generate suggestions for donor contributions based on donor balance.
    """
    try:
        donor = Users.objects.get(id=donor_id, role='donor')
        balance = donor.balance  # Assuming the Users table has a 'balance' field
        prompt = f"The donor's current balance is ${balance}. Suggest an optimal donation amount for food packages, ensuring the balance does not drop below $50."
        sql_query = get_sql_query(prompt, max_tokens=50)
        result = execute_sql_query(sql_query)
        # Return both query and result with appropriate wording
        response_text = f"Generated SQL Query:\n{sql_query}\n\nExecution Result:\n{result}"
        return response_text
    except Users.DoesNotExist:
        return "Donor not found."
    except Exception as e:
        print(f"Error in donor_suggestion: {e}")
        return f"Error in donor_suggestion: {e}"

def recommend_food_packages(student_id):
    """
    Recommend food packages for a student based on available packages and student needs.
    """
    try:
        student = Users.objects.get(id=student_id, role='student')
        food_packages = FoodPackages.objects.filter(quantity__gt=0)
        available_packages = "\n".join(
            [f"Package: {pkg.package_name}, Price: ${pkg.price_per_package}, Quantity: {pkg.quantity}" for pkg in food_packages]
        )
        last_request = Requests.objects.filter(student_id=student_id).order_by('-requested_at').first()
        reason = last_request.reason if last_request else "No specific reason provided."
        prompt = f"Available food packages:\n{available_packages}\nThe student is requesting help due to: \"{reason}\". Suggest the best package for the student."
        sql_query = get_sql_query(prompt, max_tokens=100)
        result = execute_sql_query(sql_query)
        response_text = f"Generated SQL Query:\n{sql_query}\n\nExecution Result:\n{result}"
        return response_text
    except Users.DoesNotExist:
        return "Student not found."
    except Exception as e:
        print(f"Error in recommend_food_packages: {e}")
        return f"Error in recommend_food_packages: {e}"

def prioritize_pending_requests():
    """
    Prioritize pending requests based on urgency and fairness.
    """
    try:
        pending_requests = Requests.objects.filter(status='pending')
        if not pending_requests.exists():
            return "There are no pending requests at the moment."
        requests_list = "\n".join(
            [f"Student: {req.student.username}, Package: {req.package.package_name}, Amount: {req.amount}, Requested at: {req.requested_at}" for req in pending_requests]
        )
        prompt = f"The following are pending requests:\n{requests_list}\nPrioritize them based on urgency and fairness."
        sql_query = get_sql_query(prompt, max_tokens=200)
        result = execute_sql_query(sql_query)
        response_text = f"Generated SQL Query:\n{sql_query}\n\nExecution Result:\n{result}"
        return response_text
    except Exception as e:
        print(f"Error in prioritize_pending_requests: {e}")
        return f"Error in prioritize_pending_requests: {e}"

def data_summary_visualization():
    """
    Generate a summary of data and suggest a visualization.
    """
    try:
        donations_summary = Donations.objects.aggregate(
            total_donations=Sum('amount'),
            donation_count=Sum('id')
        )
        total_donations = donations_summary.get('total_donations', 0)
        donation_count = donations_summary.get('donation_count', 0)
        package_distribution = FoodPackages.objects.all().values('package_name').annotate(
            total_distributed=Sum('quantity')
        )
        distribution_details = "\n".join(
            [f"{pkg['package_name']}: {pkg['total_distributed']} units" for pkg in package_distribution]
        )
        prompt = f"In the last month, a total of ${total_donations} was donated by {donation_count} donors. The following food packages were distributed:\n{distribution_details}\nGenerate a natural language summary and suggest the best type of visualization for this data."
        sql_query = get_sql_query(prompt, max_tokens=150)
        result = execute_sql_query(sql_query)
        response_text = f"Generated SQL Query:\n{sql_query}\n\nExecution Result:\n{result}"
        return response_text
    except Exception as e:
        print(f"Error in data_summary_visualization: {e}")
        return f"Error in data_summary_visualization: {e}"

def inventory_forecast():
    """
    Predict inventory needs for the next 7 days.
    """
    try:
        last_week = now() - timedelta(days=7)
        package_distribution = Requests.objects.filter(
            status='approved',
            requested_at__gte=last_week
        ).values('package_id').annotate(
            total_requested=Sum('amount')
        )
        if not package_distribution.exists():
            return "No data available for forecast."
        package_data = "\n".join(
            [f"Package ID: {pkg['package_id']}, Requested {pkg['total_requested']} times in the last week" for pkg in package_distribution]
        )
        prompt = f"Based on the following historical data, forecast the inventory needs for the next 7 days:\n{package_data}"
        sql_query = get_sql_query(prompt, max_tokens=150)
        result = execute_sql_query(sql_query)
        response_text = f"Generated SQL Query:\n{sql_query}\n\nExecution Result:\n{result}"
        return response_text
    except Exception as e:
        print(f"Error in inventory_forecast: {e}")
        return f"Error in inventory_forecast: {e}"

def personalized_notification(user_id):
    """
    Generate a personalized notification for a user.
    """
    try:
        user = Users.objects.get(id=user_id)
        if user.role == 'donor':
            donations = Donations.objects.filter(donor_id=user_id)
            donation_details = "\n".join(
                [f"Amount: ${donation.amount}, Date: {donation.donated_at}" for donation in donations]
            )
            prompt = f"The donor {user.username} has made the following donations:\n{donation_details}\nGenerate a thank-you notification."
        elif user.role == 'student':
            requests = Requests.objects.filter(student_id=user_id)
            request_details = "\n".join(
                [f"Package: {req.package.package_name}, Status: {req.status}, Requested on: {req.requested_at}" for req in requests]
            )
            prompt = f"The student {user.username} has made the following requests:\n{request_details}\nGenerate a notification summarizing their approved requests."
        else:
            return "Notifications are only available for donors and students."
        sql_query = get_sql_query(prompt, max_tokens=100)
        result = execute_sql_query(sql_query)
        response_text = f"Generated SQL Query:\n{sql_query}\n\nExecution Result:\n{result}"
        return response_text
    except Users.DoesNotExist:
        return "User not found."
    except Exception as e:
        print(f"Error in personalized_notification: {e}")
        return f"Error in personalized_notification: {e}"

@csrf_exempt
def chatbox_view(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            user_message = data.get('message', '').strip().lower()

            # Process the user_message and call the appropriate function
            if user_message.startswith('donor suggestion'):
                # Extract donor_id from the message
                donor_id = int(user_message.split('donor suggestion')[-1].strip())
                response_text = donor_suggestion(donor_id)
            elif user_message.startswith('recommend food packages'):
                student_id = int(user_message.split('recommend food packages')[-1].strip())
                response_text = recommend_food_packages(student_id)
            elif user_message.startswith('prioritize pending requests'):
                response_text = prioritize_pending_requests()
            elif user_message.startswith('data summary visualization'):
                response_text = data_summary_visualization()
            elif user_message.startswith('inventory forecast'):
                response_text = inventory_forecast()
            elif user_message.startswith('personalized notification'):
                user_id = int(user_message.split('personalized notification')[-1].strip())
                response_text = personalized_notification(user_id)
            else:
                # Default response or handle unknown commands
                response_text = "I'm sorry, I didn't understand that command."

            return JsonResponse({'response': response_text})
        except Exception as e:
            # Log the exception (optional)
            print(f"Error in chatbox_view: {e}")
            return JsonResponse({'error': 'An error occurred while processing your request.'}, status=500)
    else:
        # For GET request, render the chatbox.html template
        return render(request, 'chatbox.html')
