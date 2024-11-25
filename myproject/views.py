from django.shortcuts import render
from django.http import JsonResponse, HttpResponse
from django.core.exceptions import ValidationError
from django.db.models import Sum
from datetime import timedelta, timezone
from django.utils.timezone import now
from django.conf import settings
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