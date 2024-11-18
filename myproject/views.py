from django.shortcuts import render
from django.http import HttpResponse

def register(request):
    if request.method == "POST":
        donor_id = request.POST.get('donorID')
        name = request.POST.get('name')
        email = request.POST.get('email')
        role = request.POST.get('role')

        # For simplicity, simulate an authentication process
        if donor_id and name and email and role:
            return HttpResponse(f"Registration successful for {name} with role: {role}.")
        else:
            return HttpResponse("Registration failed. Please fill in all the fields.")

    return render(request, 'register.html')
