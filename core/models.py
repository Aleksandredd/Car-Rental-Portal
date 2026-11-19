from django.contrib.auth.models import AbstractUser
from django.core.validators import FileExtensionValidator
from django.db import models

photo_validator = FileExtensionValidator(['png', 'jpg', 'jpeg'])


# username is the phone number
class User(AbstractUser):
    def __str__(self):
        return f'{self.first_name} {self.last_name} ({self.username})'


class Car(models.Model):
    TRANSMISSIONS = [
        ('automatic', 'Automatic'),
        ('manual', 'Manual'),
        ('tiptronic', 'Tiptronic'),
    ]

    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='cars')
    brand = models.CharField(max_length=50)
    model = models.CharField(max_length=50)
    year = models.PositiveIntegerField()
    price = models.PositiveIntegerField('Daily price (GEL)')
    capacity = models.PositiveIntegerField('Capacity (seats)')
    transmission = models.CharField(max_length=20, choices=TRANSMISSIONS)
    city = models.CharField(max_length=60)
    fuel_capacity = models.PositiveIntegerField('Fuel tank capacity (litres)')

    image1 = models.ImageField('Photo 1', upload_to='cars/', blank=True, validators=[photo_validator])
    image2 = models.ImageField('Photo 2', upload_to='cars/', blank=True, validators=[photo_validator])
    image3 = models.ImageField('Photo 3', upload_to='cars/', blank=True, validators=[photo_validator])

    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)

    # days when the car can be rented
    available_from = models.DateField(null=True, blank=True)
    available_to = models.DateField(null=True, blank=True)

    # users who approved this car
    approved_by = models.ManyToManyField(User, related_name='approved_cars', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.brand} {self.model} ({self.year})'

    def photos(self):
        result = []
        for image in [self.image1, self.image2, self.image3]:
            if image:
                result.append(image.url)
        return result

    # True if somebody already rented the car on any of these days
    def is_busy(self, start, end):
        return self.rentals.filter(start_date__lte=end, end_date__gte=start).exists()


class Rental(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='rentals')
    car = models.ForeignKey(Car, on_delete=models.CASCADE, related_name='rentals')
    start_date = models.DateField()
    end_date = models.DateField()
    days = models.PositiveIntegerField()
    total_price = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.user.username} - {self.car} - {self.start_date} to {self.end_date}'


class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    text = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.text
