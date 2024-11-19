from django.shortcuts import render
from django.http import HttpResponse
from django.core.exceptions import ValidationError
# from django.views.decorators.csrf import csrf_exempt
# from django.http import JsonResponse
# import json
# from .models import User

def register(request):
    if request.method == "POST":
        # Get common fields
        name = request.POST.get('name')
        email = request.POST.get('email')
        password = request.POST.get('password')
        address = request.POST.get('address', None)  # Optional field

        # Get role from localStorage (mocked here)
        role = request.POST.get('role', None)  # Retrieve role from the frontend (adjust as necessary)

        # Role-specific fields
        nuid = request.POST.get('nuid') if role == 'student' else None
        school_email = request.POST.get('schoolEmail') if role == 'student' else None
        household_income = request.POST.get('householdIncome') if role == 'student' else None
        household_number = request.POST.get('householdNumber') if role == 'student' else None

        # Validation
        if not name or not email or not password or not role:
            return HttpResponse("Registration failed. Missing required fields.")

        # For simplicity, simulate saving to the database (replace this with actual DB logic)
        try:
            # Simulate database save (replace this with actual model logic)
            user_data = {
                "name": name,
                "email": email,
                "password": password,
                "address": address,
                "role": role,
                "nuid": nuid,
                "school_email": school_email,
                "household_income": household_income,
                "household_number": household_number,
            }

            # Log data (for demonstration only)
            print(f"Saved user data: {user_data}")

            return HttpResponse(f"Registration successful for {name} with role: {role}.")
        except ValidationError as e:
            return HttpResponse(f"Registration failed: {e.message}")

    return render(request, 'register.html')

'''def update(request):
    if request.method == "POST":
        # Get common fields
        email = request.POST.get('email')

        try:
            # Check if the user already exists
            user = User.objects.get(email=email)
            
            # Update the user's information
            user.name = request.POST.get('name')
            user.password = request.POST.get('password')
            user.address = request.POST.get('address', None)

            # Update role-specific fields
            role = request.POST.get('role', user.role)
            user.role = role
            if role == 'student':
                user.nuid = request.POST.get('nuid')
                user.school_email = request.POST.get('schoolEmail')
                user.household_income = request.POST.get('householdIncome')
                user.household_number = request.POST.get('householdNumber')

            user.save()
            return HttpResponse(f"User {user.name} updated successfully.")

        except User.DoesNotExist:
            # If the user does not exist, create a new one
            return register_new_user(request)  # Call the existing logic for new user registration

    return render(request, 'register.html')'''

def home(request):
    return render(request, 'home.html')


def chatbox(request):
    role = request.session.get('role')  # Retrieve user role from session
    return render(request, 'chatbox.html', {'role': role})

def donation(request):
    return render(request, 'donation.html')

# donation with backend integration
# donation model: uid, name, amount, date
'''@csrf_exempt
def donor_home(request):
    if request.method == "POST":
        # Handle donation form submission
        try:
            data = json.loads(request.body)  # Parse JSON payload
            uid = request.session.get("uid")  # Get UID from session storage
            name = request.session.get("name")  # Get user name from session storage
            amount = data.get("amount")  # Donation amount from the form

            if not uid or not name:
                return JsonResponse({"error": "User not authenticated."}, status=403)

            if not amount or float(amount) <= 0:
                return JsonResponse({"error": "Invalid donation amount."}, status=400)

            # Save the donation
            donation = Donation.objects.create(uid=uid, name=name, amount=amount)
            donation.save()

            return JsonResponse({"message": "Donation successful!"}, status=200)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

    elif request.method == "GET":
        # Retrieve previous donations for the user
        uid = request.session.get("uid")  # Get UID from session storage
        if not uid:
            return JsonResponse({"error": "User not authenticated."}, status=403)

        # Query user's donation history
        user_donations = Donation.objects.filter(uid=uid).order_by("-date")
        user_donation_list = [
            {"date": donation.date.strftime("%Y-%m-%d"), "amount": donation.amount}
            for donation in user_donations
        ]

        # Query all donations
        all_donations = Donation.objects.all().order_by("-date")
        all_donation_list = [
            {"name": donation.name, "amount": donation.amount} for donation in all_donations
        ]

        return JsonResponse({
            "user_donations": user_donation_list,
            "all_donations": all_donation_list,
        }, status=200)

    # Default to rendering the donor page
    return render(request, "donorHome.html")'''
