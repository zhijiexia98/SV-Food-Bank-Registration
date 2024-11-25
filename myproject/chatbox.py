import json
from django.shortcuts import render
from django.http import JsonResponse
from django.utils.timezone import now
from django.db.models import Sum
from datetime import timedelta
from .models import Users, Requests, Donations, FoodPackages

from django.conf import settings
import openai


def call_gpt_api(prompt, max_tokens=100):
    """
    A helper function to call OpenAI's ChatCompletion API.
    """
    openai.api_key = settings.OPENAI_API_KEY  # Ensure your API key is correctly set
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",  # Use a supported model
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},  # System role defines behavior
                {"role": "user", "content": prompt},  # User input
            ],
            max_tokens=max_tokens,
            temperature=0.7,
        )
        return response['choices'][0]['message']['content'].strip()
    except openai.error.AuthenticationError as e:
        print(f"Authentication Error: {e}")
        return "Authentication error: Invalid API key."
    except openai.error.RateLimitError as e:
        print(f"Rate Limit Exceeded: {e}")
        return "Rate limit exceeded. Please try again later."
    except openai.error.OpenAIError as e:  # Catch all other OpenAI-specific errors
        print(f"OpenAI API Error: {e}")
        return "An OpenAI API error occurred."
    except Exception as e:  # Catch any other unforeseen errors
        print(f"Unexpected Error: {e}")
        return "An unexpected error occurred."


# Donor: Fetch donation suggestions
def donor_suggestion_internal(donor_id):
    try:
        donor = Users.objects.get(id=donor_id, role='donor')
        balance = donor.balance
        prompt = f"The donor's current balance is ${balance}. Suggest an optimal donation amount for food packages, ensuring the balance does not drop below $50."
        suggestion = call_gpt_api(prompt, max_tokens=50)
        return f"Suggested donation amount: {suggestion}"
    except Users.DoesNotExist:
        return "Donor not found."


# Student: Recommend food packages
def student_recommendation_internal(student_id):
    try:
        student = Users.objects.get(id=student_id, role='student')
        food_packages = FoodPackages.objects.filter(quantity__gt=0)
        package_list = "\n".join(
            [f"Package: {pkg.package_name}, Description: {pkg.description}, Price: ${pkg.price_per_package}, Quantity: {pkg.quantity}"
             for pkg in food_packages]
        )
        last_request = Requests.objects.filter(student_id=student_id).order_by('-requested_at').first()
        reason = last_request.reason if last_request else "No previous requests"
        prompt = f"Available food packages:\n{package_list}\nThe student is requesting for: \"{reason}\". Suggest the best package for the student."
        recommendation = call_gpt_api(prompt, max_tokens=100)
        return f"Recommended package: {recommendation}"
    except Users.DoesNotExist:
        return "Student not found."


# Admin: Prioritize pending requests
def admin_prioritize_requests_internal():
    pending_requests = Requests.objects.filter(status='pending')
    if not pending_requests.exists():
        return "There are no pending requests at the moment."
    requests_list = "\n".join(
        [f"Student: {req.student.username}, Package: {req.package.package_name}, Amount: {req.amount}, Reason: {req.reason}, Requested at: {req.requested_at}"
         for req in pending_requests]
    )
    prompt = f"The following are pending food package requests. Please prioritize the requests based on urgency and fairness:\n{requests_list}"
    priority_order = call_gpt_api(prompt, max_tokens=200)
    return f"Priority order:\n{priority_order}"


# Data Summary Visualization
def data_summary_visualization_internal():
    donations_summary = Donations.objects.aggregate(
        total_donations=Sum('amount'),
        donation_count=Sum('id')  # Number of donations
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
    summary = call_gpt_api(prompt)
    return f"Data summary and visualization suggestion:\n{summary}"


# Inventory Forecast
def inventory_forecast_internal():
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
    prompt = f"Based on the following historical distribution data of food packages in the last week:\n{package_data}\nPredict the demand for each package in the next 7 days."
    forecast = call_gpt_api(prompt)
    return f"Inventory demand forecast:\n{forecast}"


# Personalized Notification
def personalized_notification_internal(user_id):
    try:
        user = Users.objects.get(id=user_id)
        if user.role == 'donor':
            donations = Donations.objects.filter(donor_id=user_id)
            if not donations.exists():
                return "This donor has no donation records."
            donation_details = "\n".join(
                [f"Amount: ${donation.amount}, Date: {donation.donated_at}" for donation in donations]
            )
            prompt = f"Donor {user.username} has made the following donations:\n{donation_details}\nGenerate a thank-you notification summarizing their contributions."
        elif user.role == 'student':
            requests = Requests.objects.filter(student_id=user_id)
            if not requests.exists():
                return "This student has no request records."
            request_details = "\n".join(
                [f"Package: {req.package.package_name}, Status: {req.status}, Requested on: {req.requested_at}" for req in requests]
            )
            prompt = f"Student {user.username} has made the following requests:\n{request_details}\nGenerate a notification summarizing their approved requests and thanking them for their patience."
        else:
            return "Notifications are only available for donors and students."
        notification = call_gpt_api(prompt)
        return f"Personalized notification:\n{notification}"
    except Users.DoesNotExist:
        return "User not found."


# Chatbox Endpoint
def chatbox(request):
    if request.method == "GET":
        role = request.session.get('role', 'student')  # Example session role, default to 'student'
        return render(request, 'chatbox.html', {'role': role})

    elif request.method == "POST":
        try:
            data = json.loads(request.body)
            user_message = data.get("message", "").strip()

            if not user_message:
                return JsonResponse({"error": "No message provided."}, status=400)

            response_data = None
            if user_message.lower().startswith("donor suggestion"):
                parts = user_message.split()
                if len(parts) >= 3:
                    donor_id = int(parts[2])
                    response_data = donor_suggestion_internal(donor_id)
                else:
                    response_data = "Please provide the donor ID, e.g., 'Donor suggestion 1'."
            elif user_message.lower().startswith("student recommendation"):
                parts = user_message.split()
                if len(parts) >= 3:
                    student_id = int(parts[2])
                    response_data = student_recommendation_internal(student_id)
                else:
                    response_data = "Please provide the student ID, e.g., 'Student recommendation 2'."
            elif user_message.lower() == "admin prioritize requests":
                response_data = admin_prioritize_requests_internal()
            elif user_message.lower() == "data summary visualization":
                response_data = data_summary_visualization_internal()
            elif user_message.lower() == "inventory forecast":
                response_data = inventory_forecast_internal()
            elif user_message.lower().startswith("personalized notification"):
                parts = user_message.split()
                if len(parts) >= 3:
                    user_id = int(parts[2])
                    response_data = personalized_notification_internal(user_id)
                else:
                    response_data = "Please provide the user ID, e.g., 'Personalized notification 3'."
            else:
                response_data = call_gpt_api(user_message, max_tokens=150)

            return JsonResponse({"response": response_data})
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({"error": "Invalid request method."}, status=405)
