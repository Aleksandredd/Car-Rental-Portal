"""
The single place where the app talks to the external RentCar REST API.

One function per endpoint (see docs/API_NOTES.md). Every function either
returns clean Python data or raises ApiError with a message that is safe
to show to the user. Views never use `requests` directly.
"""

import logging
from pathlib import Path
from urllib.parse import quote

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

PHOTO_FIELDS = ('imageUrl1', 'imageUrl2', 'imageUrl3')


class ApiError(Exception):
    """Raised when the API is unreachable or answers with an error."""

    def __init__(self, message, status=None):
        super().__init__(message)
        self.message = message
        self.status = status


# --------------------------------------------------------------------------
# Low-level helper
# --------------------------------------------------------------------------

def _request(method, path, *, ok_statuses=(200, 201), **kwargs):
    """Call the API and return the decoded body (JSON if possible, else text)."""
    url = f'{settings.API_BASE_URL}{path}'
    kwargs.setdefault('timeout', settings.API_TIMEOUT)
    try:
        response = requests.request(method, url, **kwargs)
    except requests.Timeout:
        logger.warning('API timeout: %s %s', method, path)
        raise ApiError('The car service is taking too long to answer. Please try again.')
    except requests.RequestException as exc:
        logger.warning('API connection error: %s %s (%s)', method, path, exc)
        raise ApiError('Could not reach the car service. Please try again later.')

    try:
        body = response.json()
    except ValueError:
        body = response.text.strip()

    if response.status_code not in ok_statuses:
        # The API answers errors with plain text ("User not found") or with
        # ASP.NET problem JSON ({"title": "Not Found", ...}).
        if isinstance(body, dict):
            detail = body.get('title') or ''
        else:
            detail = str(body)[:200]
        logger.info('API error %s: %s %s -> %r', response.status_code, method, path, detail)
        if response.status_code >= 500:
            # Server crashes come back as raw stack traces: never show those.
            detail = 'The car service had an internal error. Please try again later.'
        raise ApiError(detail or 'The car service returned an error.', status=response.status_code)
    return body


def _phone(phone):
    """Phone numbers go into URL paths, so '+' and friends must be escaped."""
    return quote(str(phone), safe='')


# --------------------------------------------------------------------------
# Cleaning helpers (the live data is messy: nulls, zeros, dead image hosts)
# --------------------------------------------------------------------------

def _local_photo_url(car_id, index):
    """URL of our local copy of an uploaded photo, if we have one."""
    folder = Path(settings.MEDIA_ROOT) / 'cars' / str(car_id)
    if folder.is_dir():
        for file in folder.glob(f'{index}.*'):
            return f'{settings.MEDIA_URL}cars/{car_id}/{file.name}'
    return None


def clean_car(raw):
    """Add a few convenience keys to a car dict coming from the API."""
    if not isinstance(raw, dict):
        return None
    car = dict(raw)
    photos = []
    for index, field in enumerate(PHOTO_FIELDS, start=1):
        url = _local_photo_url(car.get('id'), index) or car.get(field)
        if url:
            photos.append(url)
    car['photos'] = photos
    car['cover'] = photos[0] if photos else None
    lat, lng = car.get('latitude'), car.get('longitude')
    car['has_location'] = bool(
        isinstance(lat, (int, float)) and isinstance(lng, (int, float))
        and (lat or lng) and -90 <= lat <= 90 and -180 <= lng <= 180
    )
    return car


def _clean_cars(raw_list):
    if not isinstance(raw_list, list):
        return []
    return [car for car in (clean_car(item) for item in raw_list) if car]


# --------------------------------------------------------------------------
# Cars
# --------------------------------------------------------------------------

def get_random_cars():
    """GET /api/Car -> 12 random cars."""
    return _clean_cars(_request('GET', '/api/Car'))


def get_popular_cars():
    """GET /api/Car/popular -> 4 cars."""
    return _clean_cars(_request('GET', '/api/Car/popular'))


def get_car(car_id):
    """GET /api/Car/{id} -> one car, or None if it does not exist."""
    try:
        return clean_car(_request('GET', f'/api/Car/{int(car_id)}'))
    except ApiError as exc:
        if exc.status == 404:
            return None
        raise


def get_cities():
    """GET /api/Car/cities -> sorted list of usable city names."""
    raw = _request('GET', '/api/Car/cities')
    cities = set()
    for city in raw if isinstance(raw, list) else []:
        # Drop nulls and obvious junk such as '12' or '"Tbilisi",'
        if isinstance(city, str) and len(city.strip()) >= 3 and city == city.strip() \
                and all(ch.isalpha() or ch in ' -' for ch in city):
            cities.add(city)
    return sorted(cities, key=str.casefold)


def filter_cars(*, city=None, start_year=None, end_year=None, capacity=None, page=1, page_size=12):
    """GET /api/Car/filter. Every filter is optional; any subset works."""
    params = {'pageIndex': page, 'pageSize': page_size}
    if city:
        params['city'] = city
    if start_year:
        params['startYear'] = start_year
    if end_year:
        params['endYear'] = end_year
    if capacity:
        params['capacity'] = capacity

    empty = {'cars': [], 'total_items': 0, 'total_pages': 0, 'page': 1}
    try:
        body = _request('GET', '/api/Car/filter', params=params)
    except ApiError as exc:
        # With zero matches the API answers 400 "Invalid page index."
        if exc.status == 400:
            return empty
        raise
    if not isinstance(body, dict):
        return empty
    return {
        'cars': _clean_cars(body.get('data')),
        'total_items': body.get('totalItems') or 0,
        'total_pages': body.get('totalPages') or 0,
        'page': body.get('currentPage') or 1,
    }


def get_cars_by_owner(phone):
    """GET /api/Car/byPhone -> cars posted by this phone number."""
    try:
        return _clean_cars(_request('GET', '/api/Car/byPhone', params={'PhoneNumber': phone}))
    except ApiError as exc:
        if exc.status == 404:  # the API answers 404 when the user has no cars
            return []
        raise


def create_car(fields, photos):
    """
    POST /api/Car (multipart/form-data).

    `fields` uses the API's own names (Brand, Model, Year, Price, Capacity,
    Transmission, CreatedBy, City, CreatedByEmail, FuelCapacity and optionally
    Latitude, Longitude). `photos` is a list of up to three uploaded files,
    sent as Image1..Image3. The returned car has an extra key,
    `photos_accepted`, telling whether the API stored the photos.
    """
    data = {key: value for key, value in fields.items() if value not in (None, '')}

    def send(with_photos):
        files = {}
        if with_photos:
            for index, photo in enumerate(photos, start=1):
                photo.seek(0)
                files[f'Image{index}'] = (photo.name, photo, photo.content_type or 'application/octet-stream')
        return _request('POST', '/api/Car', data=data, files=files or None, timeout=60)

    try:
        body = send(with_photos=True)
        photos_accepted = True
    except ApiError as exc:
        # Known problem of the live API: its upload folder is not writable, so
        # any request that contains a photo crashes with a 500. Save the car
        # without photos instead (the view keeps local copies of them).
        if not photos or exc.status is None or exc.status < 500:
            raise
        logger.warning('API rejected the photo upload (%s); retrying without photos', exc.status)
        body = send(with_photos=False)
        photos_accepted = False
    if not isinstance(body, dict) or 'id' not in body:
        raise ApiError('The car service did not confirm that the car was saved.')
    body['photos_accepted'] = photos_accepted
    return body


# --------------------------------------------------------------------------
# Users
# --------------------------------------------------------------------------

def register_user(*, first_name, last_name, phone, email, password):
    """POST /api/Users/register."""
    payload = {
        'phoneNumber': phone,
        'password': password,
        'email': email,
        'firstName': first_name,
        'lastName': last_name,
        'role': 'User',
    }
    try:
        _request('POST', '/api/Users/register', json=payload)
    except ApiError as exc:
        if exc.status == 400 and 'exists' in exc.message.lower():
            raise ApiError('An account with this phone number already exists.', status=400)
        raise


def login_user(*, phone, password):
    """POST /api/Users/login -> {token, firstName, lastName, role, phoneNumber, email}."""
    try:
        body = _request('POST', '/api/Users/login', json={'phoneNumber': phone, 'password': password})
    except ApiError as exc:
        if exc.status == 400:
            # "User Not Found!" / "Wrong Password": don't reveal which one.
            raise ApiError('Wrong phone number or password.', status=400)
        raise
    if not isinstance(body, dict) or not body.get('token'):
        raise ApiError('Login failed. Please try again.')
    return body


def get_favorite_cars(phone):
    """GET /api/Users/{phoneNumber}/favorite-cars -> list of cars."""
    cars = _clean_cars(_request('GET', f'/api/Users/{_phone(phone)}/favorite-cars'))
    unique = {}
    for car in cars:  # the API allows adding the same favourite twice
        unique.setdefault(car.get('id'), car)
    return list(unique.values())


def add_favorite_car(phone, car_id):
    """POST /api/Users/{userId}/favorites/{carId} (userId is the phone number)."""
    _request('POST', f'/api/Users/{_phone(phone)}/favorites/{int(car_id)}')


# --------------------------------------------------------------------------
# Renting
# --------------------------------------------------------------------------

def rent_car(phone, car_id, days):
    """POST /Purchase/purchase -> ticket with dayPrice and pricePaid."""
    body = _request('POST', '/Purchase/purchase',
                    params={'phoneNumber': phone, 'carId': int(car_id), 'multiplier': int(days)})
    return body if isinstance(body, dict) else {}


def get_rentals(phone):
    """GET /Purchase/{phoneNumber} -> [{carId, carBrand, carModel, city, multiplier, pricePaid}]."""
    body = _request('GET', f'/Purchase/{_phone(phone)}')
    # With no rentals the API answers 200 with the plain text "No products".
    return body if isinstance(body, list) else []


# --------------------------------------------------------------------------
# Messages (notifications)
# --------------------------------------------------------------------------

def get_messages(phone):
    """GET /Message/Messages -> list of message texts, newest first."""
    body = _request('GET', '/Message/Messages', params={'phoneNumber': phone})
    texts = [text for text in body if isinstance(text, str)] if isinstance(body, list) else []
    return list(reversed(texts))


def notify_owner(owner_phone, car_id):
    """POST /Message/Message: tell a car's owner that the car was rented."""
    _request('POST', '/Message/Message', params={'phoneNumber': owner_phone, 'CarId': int(car_id)})
