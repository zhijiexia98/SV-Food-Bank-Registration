from django.shortcuts import render
from django.http import JsonResponse, HttpResponse
from django.core.exceptions import ValidationError
from django.db.models import Sum
from datetime import timedelta, timezone
from django.utils.timezone import now
from django.conf import settings
import openai
from .models import Users, Student, FoodPackages, Requests, Donations  # 确保模型已正确导入
import json
from django.http import JsonResponse
from django.utils.timezone import now
# from openai.error import AuthenticationError, RateLimitError, OpenAIError

def fetch_donations(request, user_id):
    try:
        # Fetch user donations based on the user_id from the URL
        user_donations = Donations.objects.filter(donor_id=user_id).values(
            "amount", "donated_at"
        )

        # Fetch all donations for the carousel
        all_donations = Donations.objects.select_related("donor_id").values(
            "donor_id__username", "amount"
        )

        # Return the data
        return JsonResponse({
            "all_donations": list(all_donations),
            "user_donations": list(user_donations),
        })

    except Users.DoesNotExist:
        return JsonResponse({"error": "User not found"}, status=404)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

def submit_donation(request, user_id):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            amount = float(data.get("amount", 0))

            if amount <= 0:
                return JsonResponse({"error": "Invalid donation amount"}, status=400)

            user = Users.objects.get(id=user_id, role="donor")

            Donations.objects.create(
                donor_id=user.id,
                amount=amount,
                message="Thank you for your donation!",
                donated_at=now()  # Set the current timestamp
            )

            return JsonResponse({"message": "Donation submitted successfully"})
        except Users.DoesNotExist:
            return JsonResponse({"error": "Donor not found"}, status=404)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({"error": "Method not allowed"}, status=405)

def request_food_item(request, uid):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            package_id = data.get('itemId')

            # Fetch the user by UID
            try:
                user = Users.objects.get(id=uid, role='student')
            except Users.DoesNotExist:
                return JsonResponse({'error': 'Student not found'}, status=404)

            # Fetch the package
            try:
                package = FoodPackages.objects.get(id=package_id)
            except FoodPackages.DoesNotExist:
                return JsonResponse({'success': False, 'message': 'Package not found'}, status=404)

            if package.quantity > 0:
                # Create a new request
                Requests.objects.create(
                    student_id=user.student_id,  # Use the user's student_id
                    package_id=package.id,
                    amount=1,  # Assuming 1 package per request
                    reason="Student requested package",
                    status='pending'
                )

                # Decrement the package quantity
                package.quantity -= 1
                package.save()

                return JsonResponse({'success': True, 'message': 'Request submitted successfully'})
            else:
                return JsonResponse({'success': False, 'message': 'Package is out of stock'})

        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'message': 'Invalid JSON payload'}, status=400)
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=500)

    return JsonResponse({'error': 'Method not allowed'}, status=405)

def student_info(request, uid):
    if request.method == 'GET':
        try:
            user = Users.objects.get(id=uid, role='student')
            student = Student.objects.get(student_id=user.student_id)
            return JsonResponse({
                'name': student.name,
                'studentId': student.student_id,
                'points': student.point,
            })
        except Users.DoesNotExist:
            return JsonResponse({'error': 'Student not found'}, status=404)
    return JsonResponse({'error': 'Method not allowed'}, status=405)

def available_food_items(request):
    if request.method == 'GET':
        items = FoodPackages.objects.filter(quantity__gt=0).values(
            'id', 'package_name', 'description', 'quantity', 'price_per_package'
        )
        return JsonResponse(list(items), safe=False)
    return JsonResponse({'error': 'Method not allowed'}, status=405)

def search_food_items(request):
    if request.method == 'GET':
        category = request.GET.get('category', None)
        dietary = request.GET.get('dietary', None)
        filters = {}
        if category:
            filters['category'] = category
        if dietary:
            filters['dietary_preferences__icontains'] = dietary  # Assuming dietary_preferences is a field
        items = FoodPackages.objects.filter(**filters, quantity__gt=0).values(
            'id', 'package_name', 'description', 'quantity', 'price_per_package'
        )
        return JsonResponse(list(items), safe=False)
    return JsonResponse({'error': 'Method not allowed'}, status=405)


# 封装 GPT API 调用函数
def call_gpt_api(prompt, max_tokens=100):
    openai.api_key = settings.OPENAI_API_KEY  # Ensure your API key is correctly set
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",  # Use the newer ChatGPT models like "gpt-4" or "gpt-3.5-turbo"
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},  # System role defines behavior
                {"role": "user", "content": prompt},  # User input
            ],
            max_tokens=max_tokens,
            temperature=0.7,
        )
        return response['choices'][0]['message']['content'].strip()
    except AuthenticationError as e:
        print(f"Authentication Error: {e}")
        return "Authentication error: Invalid API key."
    except RateLimitError as e:
        print(f"Rate Limit Exceeded: {e}")
        return "Rate limit exceeded. Please try again later."
    except OpenAIError as e:  # Catch all other OpenAI-specific errors
        print(f"OpenAI API Error: {e}")
        return "An OpenAI API error occurred."
    except Exception as e:  # Catch any other unforeseen errors
        print(f"Unexpected Error: {e}")
        return "An unexpected error occurred."




# 用户注册
def register(request):
    if request.method == "POST":
        try:
            # Get common fields
            name = request.POST.get('name')
            email = request.POST.get('email', None) or request.POST.get('schoolEmail', None)
            password = request.POST.get('password')
            role = request.POST.get('role')
            address = request.POST.get('address', None)
            phone = request.POST.get('phone', None)

            # Role-specific fields
            nuid = request.POST.get('nuid') if role == 'student' else None

            # Validation
            if not name or not email or not password or not role:
                return HttpResponse("Registration failed. Missing required fields.", status=400)

            # Prepare data for the new user
            user_data = {
                'username': name,
                'email': email,
                'password': password,
                'role': role,
                'phone': phone,
                'balance': 0 if role in ['donor', 'student'] else None,  # Balance for donors and students
                'is_active': True,
                'created_at': now(),
                'point': 0,  # Default point value
                'student_id': nuid if role == 'student' else None  # Assign NUID for students
            }

            # Save user to database
            user = Users.objects.create(**user_data)

            return JsonResponse({'success': True, 'message': f"Registration successful for {name} with role: {role}."})

        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=500)

    return render(request, 'register.html')


def login(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)  # Parse JSON payload
            email = data.get("email")
            password = data.get("password")

            if not email or not password:
                return JsonResponse({"error": "Email and password are required."}, status=400)

            # Check user credentials
            try:
                user = Users.objects.get(email=email, password=password)
                return JsonResponse({
                    "uid": user.id,
                    "name": user.username,
                    "role": user.role,
                })
            except Users.DoesNotExist:
                return JsonResponse({"error": "Invalid credentials."}, status=401)
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON payload."}, status=400)

    return render(request, 'login.html')


# Home 页面
def home(request):
    return render(request, 'home.html')

def chatbox(request):
    role = request.session.get('role')  # Retrieve user role from session
    return render(request, 'chatbox.html', {'role': role})

def donation(request, uid):
    # Use the uid to fetch user-specific data
    user = Users.objects.get(id=uid)
    return render(request, 'donation.html', {'user': user})

def studentHome(request, uid):
    # Use the uid to fetch user-specific data
    user = Users.objects.get(id=uid)
    return render(request, 'studentHome.html', {'user': user})

def adminHome(request, uid):
    # Use the uid to fetch user-specific data
    user = Users.objects.get(id=uid)
    return render(request, 'adminHome.html', {'user': user})

# API endpoints for food queries
def food_dietary(request):
    restriction = request.GET.get('restriction')
    # 实现查询逻辑
    items = [] # 从数据库查询符合条件的食物
    return JsonResponse(items, safe=False)

def food_allergies(request):
    allergies = json.loads(request.body).get('allergies', [])
    # 实现查询逻辑
    items = [] # 从数据库查询不含过敏原的食物
    return JsonResponse(items, safe=False)

def food_nutrition(request):
    data = json.loads(request.body)
    nutrient_type = data.get('nutrientType')
    serving_size = data.get('servingSize')
    # 实现查询逻辑
    items = [] # 从数据库查询符合营养需求的食物
    return JsonResponse(items, safe=False)

# Donor: 获取捐赠建议
def donor_suggestion_internal(donor_id):
    try:
        donor = Users.objects.get(id=donor_id, role='donor')
        balance = donor.balance
        print(f"Debug: Donor ID {donor_id}, Balance {balance}")  # Log donor details
        prompt = f"The donor's current balance is ${balance}. Suggest an optimal donation amount for food packages, ensuring the balance does not drop below $50."
        suggestion = call_gpt_api(prompt, max_tokens=50)
        return f"Suggested donation amount: {suggestion}"
    except Users.DoesNotExist:
        print(f"Error: Donor ID {donor_id} not found")
        return "Donor not found."





# Student: 推荐食品包
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


# Admin: 请求优先级排序
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



# 数据总结和可视化建议
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



# 库存预测
def inventory_forecast_internal():
    last_week = timezone.now() - timedelta(days=7)
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



# 个性化通知生成
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

def chatbox(request):
    if request.method == "GET":
        # Render the chatbox page for GET requests
        role = request.session.get('role', 'student')  # Example session role, default to 'student'
        return render(request, 'chatbox.html', {'role': role})

    elif request.method == "POST":
        # Handle chatbox messages for POST requests
        try:
            data = json.loads(request.body)  # Parse the POST request JSON body
            user_message = data.get("message", "").strip()

            if not user_message:
                return JsonResponse({"error": "No message provided."}, status=400)

            # Command parsing
            response_data = None

            # Define commands and corresponding handling functions
            if user_message.lower().startswith("donor suggestion"):
                # Extract donor_id, e.g., "Donor suggestion 1"
                parts = user_message.split()
                if len(parts) >= 3:
                    donor_id = int(parts[2])
                    response_data = donor_suggestion_internal(donor_id)
                else:
                    response_data = "Please provide the donor ID, e.g., 'Donor suggestion 1'."

            elif user_message.lower().startswith("student recommendation"):
                # Extract student_id, e.g., "Student recommendation 2"
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
                # Extract user_id, e.g., "Personalized notification 3"
                parts = user_message.split()
                if len(parts) >= 3:
                    user_id = int(parts[2])
                    response_data = personalized_notification_internal(user_id)
                else:
                    response_data = "Please provide the user ID, e.g., 'Personalized notification 3'."

            else:
                # Default behavior: Call OpenAI API with the user message
                response_data = call_gpt_api(user_message, max_tokens=150)

            return JsonResponse({"response": response_data})

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

    # Return error for unsupported methods
    return JsonResponse({"error": "Invalid request method."}, status=405)