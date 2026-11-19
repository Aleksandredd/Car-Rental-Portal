from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Car, Notification, Rental, User

admin.site.register(User, UserAdmin)


@admin.register(Car)
class CarAdmin(admin.ModelAdmin):
    list_display = ['brand', 'model', 'year', 'city', 'price', 'owner', 'available_from', 'available_to']
    list_filter = ['city', 'transmission']
    search_fields = ['brand', 'model']


@admin.register(Rental)
class RentalAdmin(admin.ModelAdmin):
    list_display = ['user', 'car', 'start_date', 'end_date', 'days', 'total_price']


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['user', 'text', 'created_at']
