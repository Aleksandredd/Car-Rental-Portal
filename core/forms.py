import datetime
import re

from django import forms

from .models import Car, User

MAX_DAYS = 30
MAX_PHOTO_SIZE = 5 * 1024 * 1024


# adds bootstrap classes to inputs
class BootstrapForm:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if isinstance(field.widget, forms.HiddenInput):
                continue
            if isinstance(field.widget, forms.Select):
                css = 'form-select'
            else:
                css = 'form-control'
            field.widget.attrs['class'] = css


def check_phone(phone):
    phone = phone.replace(' ', '').replace('-', '')
    if not re.match(r'^\+?\d{9,15}$', phone):
        raise forms.ValidationError('Enter a valid phone number, for example 555123456.')
    return phone


class RegisterForm(BootstrapForm, forms.Form):
    first_name = forms.CharField(label='First name', min_length=2, max_length=50)
    last_name = forms.CharField(label='Last name', min_length=2, max_length=50)
    phone = forms.CharField(label='Phone number', max_length=20,
                            widget=forms.TextInput(attrs={'placeholder': '555123456'}))
    email = forms.EmailField(label='Email')
    password = forms.CharField(label='Password', min_length=8, widget=forms.PasswordInput(),
                               help_text='At least 8 characters.')

    def clean_phone(self):
        phone = check_phone(self.cleaned_data['phone'])
        if User.objects.filter(username=phone).exists():
            raise forms.ValidationError('User with this phone number already exists.')
        return phone

    def clean_email(self):
        email = self.cleaned_data['email'].lower()
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError('User with this email already exists.')
        return email


class LoginForm(BootstrapForm, forms.Form):
    phone = forms.CharField(label='Phone number', max_length=20,
                            widget=forms.TextInput(attrs={'placeholder': '555123456'}))
    password = forms.CharField(label='Password', widget=forms.PasswordInput())

    def clean_phone(self):
        return check_phone(self.cleaned_data['phone'])


class FilterForm(BootstrapForm, forms.Form):
    city = forms.ChoiceField(label='City', required=False)
    start_year = forms.IntegerField(label='Year from', required=False, min_value=1900,
                                    widget=forms.NumberInput(attrs={'placeholder': '1995'}))
    end_year = forms.IntegerField(label='Year to', required=False, min_value=1900,
                                  widget=forms.NumberInput(attrs={'placeholder': '2005'}))
    capacity = forms.IntegerField(label='Seats', required=False, min_value=1,
                                  widget=forms.NumberInput(attrs={'placeholder': '6'}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # cities from database
        cities = Car.objects.values_list('city', flat=True).distinct().order_by('city')
        self.fields['city'].choices = [('', 'Any city')] + [(city, city) for city in cities]

    def clean(self):
        data = super().clean()
        start = data.get('start_year')
        end = data.get('end_year')
        if start and end and start > end:
            self.add_error('end_year', '"Year to" can not be less than "Year from".')
        return data


class RentForm(forms.Form):
    days = forms.IntegerField(min_value=1, max_value=MAX_DAYS)


class CarForm(BootstrapForm, forms.ModelForm):
    class Meta:
        model = Car
        fields = ['brand', 'model', 'year', 'price', 'capacity', 'transmission', 'city',
                  'fuel_capacity', 'image1', 'image2', 'image3', 'latitude', 'longitude']
        widgets = {
            'brand': forms.TextInput(attrs={'placeholder': 'Toyota'}),
            'model': forms.TextInput(attrs={'placeholder': 'Prius'}),
            'year': forms.NumberInput(attrs={'placeholder': '2015'}),
            'city': forms.TextInput(attrs={'placeholder': 'Batumi', 'list': 'city-list'}),
            'image1': forms.FileInput(attrs={'accept': '.png,.jpg,.jpeg'}),
            'image2': forms.FileInput(attrs={'accept': '.png,.jpg,.jpeg'}),
            'image3': forms.FileInput(attrs={'accept': '.png,.jpg,.jpeg'}),
            # latitude and longitude are filled from js
            'latitude': forms.HiddenInput(),
            'longitude': forms.HiddenInput(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # all 3 photos are required
        for name in ['image1', 'image2', 'image3']:
            self.fields[name].required = True

    def clean_year(self):
        year = self.cleaned_data['year']
        if year < 1950 or year > datetime.date.today().year + 1:
            raise forms.ValidationError('Enter a correct year.')
        return year

    def clean_price(self):
        price = self.cleaned_data['price']
        if price < 1:
            raise forms.ValidationError('Price must be more than 0.')
        return price

    def clean_capacity(self):
        capacity = self.cleaned_data['capacity']
        if capacity < 1 or capacity > 60:
            raise forms.ValidationError('Enter a correct number of seats.')
        return capacity

    def clean_city(self):
        return self.cleaned_data['city'].strip().title()

    def clean(self):
        data = super().clean()
        for name in ['image1', 'image2', 'image3']:
            photo = data.get(name)
            if photo and photo.size > MAX_PHOTO_SIZE:
                self.add_error(name, 'Photo is too big (max 5 MB).')
        return data
