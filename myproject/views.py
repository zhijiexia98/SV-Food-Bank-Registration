from django.shortcuts import render
from django.http import JsonResponse, HttpResponse
from django.core.exceptions import ValidationError
from django.db.models import Sum, Count, F
from datetime import timedelta, timezone
from django.utils.timezone import now
from django.conf import settings
from .models import Users, Student, FoodPackages, Requests, Donations  
import json
from django.http import JsonResponse
from django.utils.timezone import now
from django.utils.dateparse import parse_date
from django.utils.timezone import make_aware
from django.shortcuts import get_object_or_404
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
                    student_id=user.student_id,
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
            student = Student.objects.get(user=user)
            return JsonResponse({
                'name': student.name,
                'nuid': student.nuid,
                'point': student.point,
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


def register(request, uid=None):
    if request.method == "POST":
        try:
            # print(f"Received UID: {uid}")
            # print(f"Request path: {request.path}")
            # print(f"POST data: {request.POST}")
            if uid:
                user = get_object_or_404(Users, id=uid)
                
                # Update fields
                user.username = request.POST.get('name', user.username)
                user.email = request.POST.get('email', user.email) or request.POST.get('schoolEmail', user.email)
                user.role = request.POST.get('role', user.role)
                user.phone = request.POST.get('phone', user.phone)
                user.password = request.POST.get('password', user.password)
                # user.address = request.POST.get('address', user.address)
                if user.role == 'student':
                    user.student_id = request.POST.get('nuid', user.student_id)
                user.save()

                user_data = {
                    'name': user.username,
                    'email': user.email,
                    'password': user.password,
                    'role': user.role,
                    'phone': user.phone,
                    'balance': 0 if user.role in ['donor', 'student'] else None,  # Balance for donors and students
                    'is_active': True,
                    'point': user.point,  # Default point value
                    'student_id': user.student_id if user.role == 'student' else None  # Assign NUID for students
                }

                return JsonResponse({
                    'success': True,
                    'message': f"Profile updated successfully for {user.username}.",
                    'uid': user.id,
                    'user_data': user_data
                })
            # Get common fields
            name = request.POST.get('name')
            email = request.POST.get('email', None) or request.POST.get('schoolEmail', None)
            password = request.POST.get('password')
            role = request.POST.get('role')
            # address = request.POST.get('address', None)
            phone = request.POST.get('phone', None)

            # Role-specific fields
            nuid = request.POST.get('nuid') if role == 'student' else None

            # Validation
            if not name or not email or not password or not role:
                return HttpResponse("Registration failed. Missing required fields.", status=400)

            # Prepare data for the new user
            user_data = {
                'name': name,
                'email': email,
                'password': password,
                'role': role,
                'phone': phone,
                'balance': 0 if role in ['donor', 'student'] else None,
                'is_active': True,
                'created_at': now(),
                'student_id': nuid if role == 'student' else None,
                'point': 100,
            }

            # Save user to database
            user = Users.objects.create(**user_data)

            # If the role is student, create a Student record
            if role == 'student':
                Student.objects.create(
                    user=user,
                    nuid=nuid,
                    name=name,
                    email=email,
                    point=0
                )

            localhost = 'http://localhost:8000'
            redirect_url = localhost
            if role == 'student':
                redirect_url = f'{localhost}/studentHome/{user.id}/'
            elif role == 'donor':
                redirect_url = f'{localhost}/donation/{user.id}/'
            elif role == 'admin':
                redirect_url = f'{localhost}/adminHome/{user.id}/'
                
            return JsonResponse({
                'success': True,
                'message': f"Registration successful for {name} with role: {role}.",
                'redirect': redirect_url,
                'uid': user.id
            })

        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e), 'uid': uid}, status=500)

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
                user_data = {
                    "uid": user.id,
                    "name": user.username,
                    "email": user.email,
                    "role": user.role,
                    "phone": user.phone,
                    "student_id": getattr(user, 'student_id', None),
                    "password": password,
                }
                return JsonResponse({"success": True, "data": user_data})
            except Users.DoesNotExist:
                return JsonResponse({"error": "Invalid credentials."}, status=401)
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON payload."}, status=400)

    return render(request, 'login.html')

def adminDashboard(request):
    try:
        # Get package statistics
        packages = FoodPackages.objects.annotate(
            distributed_count=Count('requests'),
            remaining=F('quantity')
        ).values('package_name', 'distributed_count', 'remaining')

        # Get student points
        students = Users.objects.filter(role='student').values(
            'name', 'point', 'nuid'
        )

        # Get distribution history
        distributions = Requests.objects.select_related(
            'student', 'package'
        ).filter(
            status='approved'
        ).values(
            'student__username',
            'package__package_name',
            'requested_at',
            'amount'
        ).order_by('-requested_at')[:50]

        return JsonResponse({
            'packages': list(packages),
            'students': list(students),
            'distributions': list(distributions)
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
    
# Home 页面
def home(request):
    return render(request, 'home.html')

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

def filter_donations(request):
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
    if start_date and end_date:
        start_date = parse_date(start_date)
        end_date = parse_date(end_date) + timedelta(days=1)  # Add one day to include the end date
        donations = Donations.objects.filter(donated_at__range=(start_date, end_date))
    else:
        donations = Donations.objects.all()
    
    donations_data = list(donations.values('donor_id__username', 'amount', 'donated_at'))
    return JsonResponse({'donations': donations_data})

def all_food_packages(request):
    packages = FoodPackages.objects.annotate(
        distributed_count=Count('requests'),
        remaining=F('quantity')
    ).values('package_name', 'distributed_count', 'remaining')
    print(packages)
    return JsonResponse({'packages': list(packages)})

def all_students(request):
    students = Student.objects.all().values('name', 'nuid', 'point')
    return JsonResponse({'students': list(students)})

def all_donations(request):
    donations = Donations.objects.select_related('donor_id').values('donor_id__username', 'amount', 'donated_at')
    return JsonResponse({'donations': list(donations)})

def student_by_nuid(request):
    nuid = request.GET.get('nuid')
    try:
        student = Student.objects.get(nuid=nuid)
        return JsonResponse({'student': {'name': student.name, 'nuid': student.nuid, 'point': student.point}})
    except Student.DoesNotExist:
        return JsonResponse({'student': None})

def top_requested_items(request):
    top_items = Requests.objects.values('package__package_name').annotate(
        total_requested=Sum('amount')
    ).order_by('-total_requested')[:5]  # Top 5 requested items
    return JsonResponse({'top_items': list(top_items)})

def student_request_history(request, uid):
    requests = Requests.objects.filter(student_id=uid).values(
        'package__package_name', 'amount', 'requested_at', 'status'
    ).order_by('-requested_at')
    return JsonResponse({'request_history': list(requests)})

def available_items_by_category(request):
    items = FoodPackages.objects.filter(quantity__gt=0).values(
        'category', 'id', 'package_name', 'description', 'quantity', 'price_per_package'
    ).order_by('category')
    return JsonResponse({'items_by_category': list(items)})