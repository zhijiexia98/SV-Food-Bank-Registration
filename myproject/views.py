from django.shortcuts import render
from django.http import JsonResponse, HttpResponse
from django.core.exceptions import ValidationError
from django.db.models import Sum
from datetime import timedelta
from django.utils.timezone import now
from django.conf import settings
import openai
from .models import Users, Student, FoodPackages, Requests, Donations  # 确保模型已正确导入
import json
from django.http import JsonResponse
from django.utils.timezone import now

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
def call_gpt_api(prompt, max_tokens=150):
    try:
        openai.api_key = settings.OPENAI_API_KEY
        response = openai.Completion.create(
            engine="text-davinci-003",
            prompt=prompt,
            max_tokens=max_tokens
        )
        return response.choices[0].text.strip()
    except Exception as e:
        return f"Error: {str(e)}"


# 用户注册
def register(request):
    if request.method == "POST":
        # Get common fields
        name = request.POST.get('name')
        email = request.POST.get('email')
        password = request.POST.get('password')
        address = request.POST.get('address', None)
        role = request.POST.get('role', None)

        # Role-specific fields
        nuid = request.POST.get('nuid') if role == 'student' else None
        school_email = request.POST.get('schoolEmail') if role == 'student' else None
        household_income = request.POST.get('householdIncome') if role == 'student' else None
        household_number = request.POST.get('householdNumber') if role == 'student' else None

        # Validation
        if not name or not email or not password or not role:
            return HttpResponse("Registration failed. Missing required fields.", status=400)

        # 保存用户数据到数据库
        try:
            user = Users.objects.create(
                name=name,
                email=email,
                password=password,
                address=address,
                role=role,
                nuid=nuid,
                school_email=school_email,
                household_income=household_income,
                household_number=household_number
            )
            user.save()
            return HttpResponse(f"Registration successful for {name} with role: {role}.")
        except ValidationError as e:
            return HttpResponse(f"Registration failed: {e.message}")

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
def donor_suggestion(request, donor_id):
    try:
        donor = Users.objects.get(id=donor_id, role='donor')
        balance = donor.balance
        prompt = f"The donor's current balance is ${balance}. Suggest an optimal donation amount for food packages, considering the balance should not drop below $50."
        suggestion = call_gpt_api(prompt, max_tokens=50)
        return JsonResponse({'donor_id': donor_id, 'balance': balance, 'suggestion': suggestion})
    except Users.DoesNotExist:
        return JsonResponse({'error': 'Donor not found'}, status=404)


# Student: 推荐食品包
def student_recommendation(request, student_id):
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
        return JsonResponse({'student_id': student_id, 'recommendation': recommendation})
    except Users.DoesNotExist:
        return JsonResponse({'error': 'Student not found'}, status=404)


# Admin: 请求优先级排序
def admin_prioritize_requests(request):
    pending_requests = Requests.objects.filter(status='pending')
    if not pending_requests.exists():
        return JsonResponse({'priority_order': 'No pending requests.'})
    requests_list = "\n".join(
        [f"Student: {req.student.username}, Package: {req.package.package_name}, Amount: {req.amount}, Reason: {req.reason}, Requested at: {req.requested_at}"
         for req in pending_requests]
    )
    prompt = f"Below are pending food package requests. Prioritize the requests based on urgency and fairness:\n{requests_list}"
    priority_order = call_gpt_api(prompt, max_tokens=200)
    return JsonResponse({'priority_order': priority_order})


# 数据总结和可视化建议
def data_summary_visualization(request):
    donations_summary = Donations.objects.aggregate(
        total_donations=Sum('amount'),
        donation_count=Sum('id')  # 捐赠次数
    )
    total_donations = donations_summary.get('total_donations', 0)
    donation_count = donations_summary.get('donation_count', 0)
    package_distribution = FoodPackages.objects.all().values('package_name').annotate(
        total_distributed=Sum('quantity')
    )
    distribution_details = "\n".join(
        [f"{pkg['package_name']}: {pkg['total_distributed']} units" for pkg in package_distribution]
    )
    prompt = f"In the last month, the total donations amounted to ${total_donations} from {donation_count} donors. Below are the food packages distributed:\n{distribution_details}\nGenerate a natural language summary and suggest the best visualization type for this data."
    summary = call_gpt_api(prompt)
    return JsonResponse({'summary': summary})


# 库存预测
def inventory_forecast(request):
    last_week = now() - timedelta(days=7)
    package_distribution = Requests.objects.filter(
        status='approved',
        requested_at__gte=last_week
    ).values('package_id').annotate(
        total_requested=Sum('amount')
    )
    if not package_distribution.exists():
        return JsonResponse({'forecast': 'No data available for forecast.'})
    package_data = "\n".join(
        [f"Package ID: {pkg['package_id']}, Requested: {pkg['total_requested']} times in the last week" for pkg in package_distribution]
    )
    prompt = f"Based on the historical distribution data of food packages in the last week:\n{package_data}\nPredict the demand for each package in the next 7 days."
    forecast = call_gpt_api(prompt)
    return JsonResponse({'forecast': forecast})


# 个性化通知生成
def personalized_notification(request, user_id):
    try:
        user = Users.objects.get(id=user_id)
        if user.role == 'donor':
            donations = Donations.objects.filter(donor_id=user_id)
            donation_details = "\n".join(
                [f"Amount: ${donation.amount}, Date: {donation.donated_at}" for donation in donations]
            )
            prompt = f"Donor {user.username} has made the following donations:\n{donation_details}\nGenerate a thank-you notification summarizing their contributions."
        elif user.role == 'student':
            requests = Requests.objects.filter(student_id=user_id)
            request_details = "\n".join(
                [f"Package: {req.package.package_name}, Status: {req.status}, Requested on: {req.requested_at}" for req in requests]
            )
            prompt = f"Student {user.username} has made the following requests:\n{request_details}\nGenerate a notification summarizing their approved requests and thanking them for their patience."
        else:
            return JsonResponse({'error': 'Notifications only available for donors and students.'})
        notification = call_gpt_api(prompt)
        return JsonResponse({'notification': notification})
    except Users.DoesNotExist:
        return JsonResponse({'error': 'User not found'}, status=404)
