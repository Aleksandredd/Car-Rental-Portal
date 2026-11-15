import datetime
import re

from django import forms
from django.conf import settings
from django.core.validators import MaxValueValidator

PHONE_RE = re.compile(r'^\+?\d{9,15}$')
NAME_RE = re.compile(r"^[^\W\d_]+(?:[ '\-][^\W\d_]+)*$")

ALLOWED_PHOTO_EXTENSIONS = ('.png', '.jpg', '.jpeg')
MAX_RENT_DAYS = 30

TRANSMISSION_CHOICES = [
    ('', 'Choose...'),
    ('Automatic', 'Automatic'),
    ('Manual', 'Manual'),
    ('Tiptronic', 'Tiptronic'),
]


# adds bootstrap classes to inputs
class BootstrapFormMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            widget = field.widget
            if isinstance(widget, forms.HiddenInput):
                continue
            css = 'form-select' if isinstance(widget, forms.Select) else 'form-control'
            if self.is_bound and name in self.errors:
                css += ' is-invalid'
            widget.attrs['class'] = (widget.attrs.get('class', '') + ' ' + css).strip()


# remove spaces and dashes from phone
def clean_phone(value):
    phone = re.sub(r'[\s\-()]', '', value or '')
    if not PHONE_RE.match(phone):
        raise forms.ValidationError('Enter a valid phone number: 9 to 15 digits, e.g. 555123456.')
    return phone


def clean_name(value, label):
    name = ' '.join((value or '').split())
    if len(name) < 2:
        raise forms.ValidationError(f'{label} must be at least 2 letters long.')
    if not NAME_RE.match(name):
        raise forms.ValidationError(f'{label} can contain only letters.')
    return name


# auth forms
class RegisterForm(BootstrapFormMixin, forms.Form):
    first_name = forms.CharField(label='First name', max_length=50,
                                 widget=forms.TextInput(attrs={'autocomplete': 'given-name'}))
    last_name = forms.CharField(label='Last name', max_length=50,
                                widget=forms.TextInput(attrs={'autocomplete': 'family-name'}))
    phone = forms.CharField(label='Phone number', max_length=20,
                            widget=forms.TextInput(attrs={'type': 'tel', 'autocomplete': 'tel',
                                                          'placeholder': '555123456'}))
    email = forms.EmailField(label='Email', max_length=100,
                             widget=forms.EmailInput(attrs={'autocomplete': 'email'}))
    password = forms.CharField(label='Password', min_length=8, max_length=64, strip=False,
                               widget=forms.PasswordInput(attrs={'autocomplete': 'new-password'}),
                               help_text='At least 8 characters, with a letter and a digit.')

    def clean_first_name(self):
        return clean_name(self.cleaned_data['first_name'], 'First name')

    def clean_last_name(self):
        return clean_name(self.cleaned_data['last_name'], 'Last name')

    def clean_phone(self):
        return clean_phone(self.cleaned_data['phone'])

    def clean_email(self):
        return self.cleaned_data['email'].lower()

    def clean_password(self):
        password = self.cleaned_data['password']
        if not re.search(r'[^\W\d_]', password) or not re.search(r'\d', password):
            raise forms.ValidationError('The password must contain at least one letter and one digit.')
        return password


class LoginForm(BootstrapFormMixin, forms.Form):
    phone = forms.CharField(label='Phone number', max_length=20,
                            widget=forms.TextInput(attrs={'type': 'tel', 'autocomplete': 'tel',
                                                          'placeholder': '555123456'}))
    password = forms.CharField(label='Password', max_length=64, strip=False,
                               widget=forms.PasswordInput(attrs={'autocomplete': 'current-password'}))

    def clean_phone(self):
        return clean_phone(self.cleaned_data['phone'])


def max_car_year():
    return datetime.date.today().year + 1


# car forms
class FilterForm(BootstrapFormMixin, forms.Form):

    city = forms.CharField(label='City', required=False, max_length=100, widget=forms.Select())
    start_year = forms.IntegerField(label='Year from', required=False, min_value=1900, max_value=2100,
                                    widget=forms.NumberInput(attrs={'placeholder': '1995'}))
    end_year = forms.IntegerField(label='Year to', required=False, min_value=1900, max_value=2100,
                                  widget=forms.NumberInput(attrs={'placeholder': '2005'}))
    capacity = forms.IntegerField(label='Seats', required=False, min_value=1, max_value=100,
                                  widget=forms.NumberInput(attrs={'placeholder': '6'}))

    def __init__(self, *args, cities=(), **kwargs):
        super().__init__(*args, **kwargs)
        choices = [('', 'Any city')] + [(city, city) for city in cities]
        selected = (self.data.get('city') or '').strip() if self.is_bound else ''
        if selected and selected not in cities:
            choices.append((selected, selected))
        self.fields['city'].widget.choices = choices

    def clean(self):
        cleaned = super().clean()
        start, end = cleaned.get('start_year'), cleaned.get('end_year')
        if start and end and start > end:
            self.add_error('end_year', '"Year to" cannot be earlier than "Year from".')
        return cleaned


class RentForm(forms.Form):
    days = forms.IntegerField(min_value=1, max_value=MAX_RENT_DAYS, error_messages={
        'required': 'Choose the number of days.',
        'invalid': 'The number of days must be a whole number.',
        'min_value': 'You must rent for at least 1 day.',
        'max_value': f'You can rent for at most {MAX_RENT_DAYS} days.',
    })


def validate_photo(photo):
    name = (photo.name or '').lower()
    if not name.endswith(ALLOWED_PHOTO_EXTENSIONS):
        raise forms.ValidationError('Only .png, .jpg and .jpeg photos are allowed.')
    if photo.size > settings.MAX_PHOTO_SIZE:
        raise forms.ValidationError(f'The photo is too large (max {settings.MAX_PHOTO_SIZE // (1024 * 1024)} MB).')
    # check that file is really png or jpg
    header = photo.read(8)
    photo.seek(0)
    is_png = header.startswith(b'\x89PNG\r\n\x1a\n')
    is_jpeg = header.startswith(b'\xff\xd8\xff')
    if not (is_png or is_jpeg):
        raise forms.ValidationError('This file is not a valid PNG or JPEG image.')
    if is_png != name.endswith('.png'):
        raise forms.ValidationError('The file extension does not match the image type.')


class AddCarForm(BootstrapFormMixin, forms.Form):
    brand = forms.CharField(label='Brand', max_length=50, widget=forms.TextInput(attrs={'placeholder': 'Toyota'}))
    model = forms.CharField(label='Model', max_length=50, widget=forms.TextInput(attrs={'placeholder': 'Prius'}))
    year = forms.IntegerField(label='Year', min_value=1950)
    price = forms.IntegerField(label='Daily price (GEL)', min_value=1, max_value=100000)
    capacity = forms.IntegerField(label='Capacity (seats)', min_value=1, max_value=60)
    transmission = forms.ChoiceField(label='Transmission', choices=TRANSMISSION_CHOICES)
    city = forms.CharField(label='City', max_length=60, widget=forms.TextInput(attrs={'placeholder': 'Batumi',
                                                                                   'list': 'city-list'}))
    fuel_capacity = forms.IntegerField(label='Fuel tank capacity (litres)', min_value=1, max_value=1000)

    photo_attrs = {'accept': '.png,.jpg,.jpeg'}
    image1 = forms.FileField(label='Photo 1', validators=[validate_photo],
                             widget=forms.ClearableFileInput(attrs=photo_attrs))
    image2 = forms.FileField(label='Photo 2', validators=[validate_photo],
                             widget=forms.ClearableFileInput(attrs=photo_attrs))
    image3 = forms.FileField(label='Photo 3', validators=[validate_photo],
                             widget=forms.ClearableFileInput(attrs=photo_attrs))

    # filled from js (geolocation)
    latitude = forms.CharField(required=False, widget=forms.HiddenInput())
    longitude = forms.CharField(required=False, widget=forms.HiddenInput())

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        year = self.fields['year']
        year.max_value = max_car_year()
        year.validators.append(MaxValueValidator(max_car_year()))
        year.widget.attrs.update({'min': 1950, 'max': max_car_year(), 'placeholder': '2015'})

    def clean_brand(self):
        return ' '.join(self.cleaned_data['brand'].split())

    def clean_model(self):
        return ' '.join(self.cleaned_data['model'].split())

    def clean_city(self):
        city = ' '.join(self.cleaned_data['city'].split())
        if not all(ch.isalpha() or ch in ' -' for ch in city) or len(city) < 2:
            raise forms.ValidationError('Enter a real city name (letters only).')
        return city

    def clean(self):
        cleaned = super().clean()
        # location is optional
        try:
            lat, lng = float(cleaned.get('latitude')), float(cleaned.get('longitude'))
            if not (-90 <= lat <= 90 and -180 <= lng <= 180):
                raise ValueError
        except (TypeError, ValueError):
            lat = lng = None
        cleaned['latitude'], cleaned['longitude'] = lat, lng
        return cleaned

    def photos(self):
        return [self.cleaned_data[name] for name in ('image1', 'image2', 'image3')]
