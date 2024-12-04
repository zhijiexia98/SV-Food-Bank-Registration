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
    path('studentHome/<int:uid>/profile/', views.register),
    path('studentHome/<int:uid>/profile/edit/', views.register, name="student_profile_edit"),
    path('donation/<int:uid>/profile/', views.register),
    path('donation/<int:uid>/profile/edit/', views.register, name="donor_profile_edit"),
    path('adminHome/<int:uid>/profile/', views.register),
    path('adminHome/<int:uid>/profile/edit/', views.register, name="admin_profile_edit"),
    path('', lambda request: redirect('home/', permanent=False)),
    path('chatbox/', chatbox.chatbox_view, name='chatbox'),
    path('donation/<int:uid>/', views.donation, name='donation'),  # Dynamic UID
    path('studentHome/<int:uid>/', views.studentHome, name='studentHome'),  # Dynamic UID
    path('adminHome/<int:uid>/', views.adminHome, name='adminHome'),  # Dynamic UID
    path('api/student/info/<int:uid>', views.student_info, name='student_info'),  # Fetch student info
    path('api/food/available', views.available_food_items, name='available_food_items'),  # Fetch available food items
    path('api/food/search', views.search_food_items, name='search_food_items'),  # Search food items
    path("request/<int:uid>/", views.request_food_item, name="request_food_item"),
    path("donor/<int:user_id>/", views.fetch_donations, name="fetch_donations"),
    path("donor/<int:user_id>/submit/", views.submit_donation, name="submit_donation"),
    path('api/admin/filter_donations', views.filter_donations, name='filter_donations'),
    path('api/admin/dashboard', views.adminDashboard, name='adminDashboard'),
    path('api/admin/all_food_packages', views.all_food_packages, name='all_food_packages'),
    path('api/admin/all_students', views.all_students, name='all_students'),
    path('api/admin/all_donations', views.all_donations, name='all_donations'),
    path('api/admin/student_by_nuid', views.student_by_nuid, name='student_by_nuid'),
    path('api/admin/add_food_package', views.add_food_package, name='add_food_package'),
    path('api/student/request_history/<int:uid>', views.student_request_history, name='student_request_history'),
    path('api/food/top_requested', views.top_requested_items, name='top_requested_items'),
    path('api/food/items_by_category', views.available_items_by_category, name='available_items_by_category'),
    path('api/admin/all_requests', views.all_requests, name='all_requests'),
    path('api/admin/pending_requests', views.pending_requests, name='pending_requests'),
    path('api/admin/approve_request/<int:request_id>/<int:uid>/', views.approve_request, name='approve_request'),
    path('api/admin/approved_requests', views.approved_requests, name='approved_requests'),
]



