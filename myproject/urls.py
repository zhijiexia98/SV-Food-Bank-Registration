"""
URL configuration for myproject project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from django.shortcuts import redirect  # Import redirect
from myproject import chatbox, views  # Import your views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('register/', views.register, name='register'),
    path('login/', views.login, name='login'),
    path('home/', views.home),
    path('profile/', views.register),
    path('profile/edit/', views.register),
    path('', lambda request: redirect('home/', permanent=False)),
    path('chatbox/', views.chatbox, name='chatbox'),
    path('donation/<int:uid>/', views.donation, name='donation'),  # Dynamic UID
    path('studentHome/<int:uid>/', views.studentHome, name='studentHome'),  # Dynamic UID
    path('adminHome/<int:uid>/', views.adminHome, name='adminHome'),  # Dynamic UID
    path('api/student/info/<int:uid>', views.student_info, name='student_info'),  # Fetch student info
    path('api/food/available', views.available_food_items, name='available_food_items'),  # Fetch available food items
    path('api/food/search', views.search_food_items, name='search_food_items'),  # Search food items
    path("request/<int:uid>/", views.request_food_item, name="request_food_item"),
    path("donor/<int:user_id>/", views.fetch_donations, name="fetch_donations"),
    path("donor/<int:user_id>/submit/", views.submit_donation, name="submit_donation"),
]


