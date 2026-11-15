# all requests to the rentcar api are in this file
import logging
from pathlib import Path
from urllib.parse import quote

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

PHOTO_FIELDS = ('imageUrl1', 'imageUrl2', 'imageUrl3')


class ApiError(Exception):
    def __init__(self, message, status=None):
        super().__init__(message)
        self.message = message
        self.status = status


# sends request to api and returns json (or text)
def _request(method, path, *, ok_statuses=(200, 201), **kwargs):
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
        if isinstance(body, dict):
            detail = body.get('title') or ''
        else:
            detail = str(body)[:200]
        logger.info('API error %s: %s %s -> %r', response.status_code, method, path, detail)
        # don't show server error text to user
        if response.status_code >= 500:
            detail = 'The car service had an internal error. Please try again later.'
        raise ApiError(detail or 'The car service returned an error.', status=response.status_code)
    return body


def _phone(phone):
    return quote(str(phone), safe='')


def _local_photo_url(car_id, index):
    folder = Path(settings.MEDIA_ROOT) / 'cars' / str(car_id)
    if folder.is_dir():
        for file in folder.glob(f'{index}.*'):
            return f'{settings.MEDIA_URL}cars/{car_id}/{file.name}'
    return None


# add photos list and location flag to car
def clean_car(raw):
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


# cars
def get_random_cars():
    return _clean_cars(_request('GET', '/api/Car'))


def get_popular_cars():
    return _clean_cars(_request('GET', '/api/Car/popular'))


def get_car(car_id):
    try:
        return clean_car(_request('GET', f'/api/Car/{int(car_id)}'))
    except ApiError as exc:
        if exc.status == 404:
            return None
        raise


def get_cities():
    raw = _request('GET', '/api/Car/cities')
    cities = set()
    for city in raw if isinstance(raw, list) else []:
        # skip empty and wrong city names
        if isinstance(city, str) and len(city.strip()) >= 3 and city == city.strip() \
                and all(ch.isalpha() or ch in ' -' for ch in city):
            cities.add(city)
    return sorted(cities, key=str.casefold)


def filter_cars(*, city=None, start_year=None, end_year=None, capacity=None, page=1, page_size=12):
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
        # api gives 400 when nothing is found
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
    try:
        return _clean_cars(_request('GET', '/api/Car/byPhone', params={'PhoneNumber': phone}))
    except ApiError as exc:
        # api gives 404 if user has no cars
        if exc.status == 404:
            return []
        raise


def create_car(fields, photos):
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
        # photo upload fails on api side, so send again without photos
        if not photos or exc.status is None or exc.status < 500:
            raise
        logger.warning('API rejected the photo upload (%s); retrying without photos', exc.status)
        body = send(with_photos=False)
        photos_accepted = False
    if not isinstance(body, dict) or 'id' not in body:
        raise ApiError('The car service did not confirm that the car was saved.')
    body['photos_accepted'] = photos_accepted
    return body


# users
def register_user(*, first_name, last_name, phone, email, password):
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
    try:
        body = _request('POST', '/api/Users/login', json={'phoneNumber': phone, 'password': password})
    except ApiError as exc:
        if exc.status == 400:
            raise ApiError('Wrong phone number or password.', status=400)
        raise
    if not isinstance(body, dict) or not body.get('token'):
        raise ApiError('Login failed. Please try again.')
    return body


def get_favorite_cars(phone):
    cars = _clean_cars(_request('GET', f'/api/Users/{_phone(phone)}/favorite-cars'))
    # remove duplicates
    unique = {}
    for car in cars:
        unique.setdefault(car.get('id'), car)
    return list(unique.values())


def add_favorite_car(phone, car_id):
    _request('POST', f'/api/Users/{_phone(phone)}/favorites/{int(car_id)}')


# rent
def rent_car(phone, car_id, days):
    body = _request('POST', '/Purchase/purchase',
                    params={'phoneNumber': phone, 'carId': int(car_id), 'multiplier': int(days)})
    return body if isinstance(body, dict) else {}


def get_rentals(phone):
    body = _request('GET', f'/Purchase/{_phone(phone)}')
    # api returns text "No products" if there are no rentals
    return body if isinstance(body, list) else []


# messages
def get_messages(phone):
    body = _request('GET', '/Message/Messages', params={'phoneNumber': phone})
    texts = [text for text in body if isinstance(text, str)] if isinstance(body, list) else []
    return list(reversed(texts))


def notify_owner(owner_phone, car_id):
    _request('POST', '/Message/Message', params={'phoneNumber': owner_phone, 'CarId': int(car_id)})
