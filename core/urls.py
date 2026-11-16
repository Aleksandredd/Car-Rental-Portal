from django.urls import path

from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),

    path('cars/', views.filter_cars, name='filter'),
    path('cars/add/', views.car_add, name='car_add'),
    path('cars/<int:car_id>/', views.car_detail, name='car_detail'),
    path('cars/<int:car_id>/rent/', views.car_rent, name='car_rent'),
    path('cars/<int:car_id>/approve/', views.car_approve, name='car_approve'),
    path('cars/<int:car_id>/delete/', views.car_delete, name='car_delete'),

    path('profile/', views.profile, name='profile'),
    path('notifications/', views.notifications, name='notifications'),
]
