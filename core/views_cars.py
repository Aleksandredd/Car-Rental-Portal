import logging
import shutil
from pathlib import Path

from django.conf import settings
from django.contrib import messages
from django.http import Http404
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from . import api_client
from .api_client import ApiError
from .decorators import session_login_required
from .forms import MAX_RENT_DAYS, AddCarForm, FilterForm, RentForm

logger = logging.getLogger(__name__)

FILTER_PAGE_SIZE = 12


# call api function, show error message if it fails
def _try(request, func, *args, default=None, **kwargs):
    try:
        return func(*args, **kwargs)
    except ApiError as exc:
        shown = request.__dict__.setdefault('_api_errors_shown', set())
        if exc.message not in shown:
            shown.add(exc.message)
            messages.error(request, exc.message)
        return [] if default is None else default


def home(request):
    popular = _try(request, api_client.get_popular_cars)
    random_cars = _try(request, api_client.get_random_cars)
    # no same car in both sections
    popular_ids = {car['id'] for car in popular}
    random_cars = [car for car in random_cars if car['id'] not in popular_ids]
    return render(request, 'home.html', {'popular_cars': popular, 'random_cars': random_cars})


def filter_cars(request):
    cities = _try(request, api_client.get_cities)
    submitted = any(request.GET.get(key) for key in ('city', 'start_year', 'end_year', 'capacity'))
    form = FilterForm(request.GET if submitted else None, cities=cities)

    try:
        page = max(int(request.GET.get('page', 1)), 1)
    except ValueError:
        page = 1

    result = {'cars': [], 'total_items': 0, 'total_pages': 0, 'page': 1}
    if not submitted or form.is_valid():
        filters = form.cleaned_data if submitted else {}
        result = _try(
            request, api_client.filter_cars,
            city=filters.get('city'),
            start_year=filters.get('start_year'),
            end_year=filters.get('end_year'),
            capacity=filters.get('capacity'),
            page=page,
            page_size=FILTER_PAGE_SIZE,
            default=result,
        )

    # for pagination links
    query = request.GET.copy()
    query.pop('page', None)
    return render(request, 'filter.html', {
        'form': form,
        'submitted': submitted,
        'cars': result['cars'],
        'total_items': result['total_items'],
        'total_pages': result['total_pages'],
        'page': result['page'],
        'has_previous': result['page'] > 1,
        'has_next': result['page'] < result['total_pages'],
        'previous_page': result['page'] - 1,
        'next_page': result['page'] + 1,
        'base_query': query.urlencode(),
    })


def _get_car_or_404(car_id):
    car = api_client.get_car(car_id)
    if car is None:
        raise Http404('Car not found')
    return car


def car_detail(request, car_id):
    try:
        car = _get_car_or_404(car_id)
    except ApiError as exc:
        messages.error(request, exc.message)
        return redirect('home')

    user = request.session.get('user')
    return render(request, 'car_detail.html', {
        'car': car,
        'is_owner': bool(user and car.get('createdBy') == user['phone']),
        'max_days': MAX_RENT_DAYS,
        'day_options': range(1, MAX_RENT_DAYS + 1),
        'mapbox_token': settings.MAPBOX_TOKEN,
    })


@require_POST
@session_login_required
def car_rent(request, car_id):
    user = request.session['user']
    form = RentForm(request.POST)
    if not form.is_valid():
        for error in form.errors.get('days', []):
            messages.error(request, error)
        return redirect('car_detail', car_id=car_id)
    days = form.cleaned_data['days']

    try:
        car = _get_car_or_404(car_id)
        if car.get('createdBy') == user['phone']:
            messages.warning(request, 'This is your own car, so you cannot rent it.')
            return redirect('car_detail', car_id=car_id)
        ticket = api_client.rent_car(user['phone'], car_id, days)
    except ApiError as exc:
        messages.error(request, f'The car could not be rented: {exc.message}')
        return redirect('car_detail', car_id=car_id)

    # send message to car owner
    owner_phone = car.get('createdBy')
    if owner_phone:
        try:
            api_client.notify_owner(owner_phone, car_id)
        except ApiError as exc:
            logger.info('Owner of car %s could not be notified: %s', car_id, exc.message)

    paid = ticket.get('pricePaid')
    if paid is None:
        paid = (car.get('price') or 0) * days
    messages.success(
        request,
        f"You rented the {car.get('brand')} {car.get('model')} for {days} day{'s' if days != 1 else ''}. "
        f'Total paid: {paid:g} GEL.',
    )
    return redirect('profile')


# approve = add to favorites in api
@require_POST
@session_login_required
def car_approve(request, car_id):
    user = request.session['user']
    try:
        already = any(car.get('id') == car_id for car in api_client.get_favorite_cars(user['phone']))
        if already:
            messages.info(request, 'This car is already in your approved cars.')
        else:
            api_client.add_favorite_car(user['phone'], car_id)
            messages.success(request, 'The car was added to your approved cars.')
    except ApiError as exc:
        messages.error(request, f'The car could not be approved: {exc.message}')
    return redirect('car_detail', car_id=car_id)


# save photos in media folder because api does not keep them
def _save_local_photos(car_id, photos):
    folder = Path(settings.MEDIA_ROOT) / 'cars' / str(car_id)
    try:
        folder.mkdir(parents=True, exist_ok=True)
        for index, photo in enumerate(photos, start=1):
            extension = Path(photo.name).suffix.lower()
            photo.seek(0)
            with open(folder / f'{index}{extension}', 'wb') as target:
                shutil.copyfileobj(photo, target)
    except OSError as exc:
        logger.warning('Could not save local photos for car %s: %s', car_id, exc)


@session_login_required
def car_add(request):
    user = request.session['user']
    form = AddCarForm(request.POST or None, request.FILES or None)

    if request.method == 'POST' and form.is_valid():
        data = form.cleaned_data
        fields = {
            'Brand': data['brand'],
            'Model': data['model'],
            'Year': data['year'],
            'Price': data['price'],
            'Capacity': data['capacity'],
            'Transmission': data['transmission'],
            'City': data['city'],
            'FuelCapacity': data['fuel_capacity'],
            # owner phone from session
            'CreatedBy': user['phone'],
            'CreatedByEmail': user.get('email', ''),
            'Latitude': data['latitude'],
            'Longitude': data['longitude'],
        }
        try:
            car = api_client.create_car(fields, form.photos())
        except ApiError as exc:
            messages.error(request, f'The car could not be saved: {exc.message}')
        else:
            _save_local_photos(car['id'], form.photos())
            messages.success(request, f"Your {data['brand']} {data['model']} is now listed.")
            if not car.get('photos_accepted'):
                messages.warning(request, 'The car service could not store the photos, so they are kept '
                                          'on this site only.')
            return redirect('car_detail', car_id=car['id'])

    cities = _try(request, api_client.get_cities) if request.method == 'GET' else []
    return render(request, 'car_add.html', {'form': form, 'cities': cities})


@session_login_required
def profile(request):
    user = request.session['user']
    rentals = []
    for item in _try(request, api_client.get_rentals, user['phone']):
        days = item.get('multiplier') or 0
        rentals.append({
            'car_id': item.get('carId'),
            'name': f"{item.get('carBrand') or ''} {item.get('carModel') or ''}".strip() or 'Car',
            'city': item.get('city'),
            'days': days,
            'paid': item.get('pricePaid'),
        })
    return render(request, 'profile.html', {
        'rentals': rentals,
        'approved_cars': _try(request, api_client.get_favorite_cars, user['phone']),
        'my_cars': _try(request, api_client.get_cars_by_owner, user['phone']),
    })


@session_login_required
def notifications(request):
    user = request.session['user']
    return render(request, 'notifications.html', {
        'notifications': _try(request, api_client.get_messages, user['phone']),
    })
