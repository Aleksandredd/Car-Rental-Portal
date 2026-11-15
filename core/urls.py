from django.urls import path

from . import views_auth, views_cars

urlpatterns = [
    path('', views_cars.home, name='home'),
    path('cars/', views_cars.filter_cars, name='filter'),
    path('cars/add/', views_cars.car_add, name='car_add'),
    path('cars/<int:car_id>/', views_cars.car_detail, name='car_detail'),
    path('cars/<int:car_id>/rent/', views_cars.car_rent, name='car_rent'),
    path('cars/<int:car_id>/approve/', views_cars.car_approve, name='car_approve'),

    path('register/', views_auth.register, name='register'),
    path('login/', views_auth.login, name='login'),
    path('logout/', views_auth.logout, name='logout'),

    path('profile/', views_cars.profile, name='profile'),
    path('notifications/', views_cars.notifications, name='notifications'),
]
