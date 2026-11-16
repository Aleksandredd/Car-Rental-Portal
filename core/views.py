from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render

from .forms import MAX_DAYS, CarForm, FilterForm, LoginForm, RegisterForm, RentForm
from .models import Car, Notification, Rental, User


def home(request):
    # popular = cars with the most rentals
    popular_cars = Car.objects.annotate(rent_count=Count('rentals')).order_by('-rent_count', '-created_at')[:4]
    popular_ids = [car.id for car in popular_cars]
    random_cars = Car.objects.exclude(id__in=popular_ids).order_by('?')[:8]
    return render(request, 'home.html', {
        'popular_cars': popular_cars,
        'random_cars': random_cars,
    })


def register_view(request):
    if request.user.is_authenticated:
        return redirect('home')

    form = RegisterForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        data = form.cleaned_data
        User.objects.create_user(
            username=data['phone'],
            password=data['password'],
            email=data['email'],
            first_name=data['first_name'],
            last_name=data['last_name'],
        )
        messages.success(request, 'Your account was created. You can log in now.')
        return redirect('login')
    return render(request, 'register.html', {'form': form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect('home')

    form = LoginForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = authenticate(request, username=form.cleaned_data['phone'],
                            password=form.cleaned_data['password'])
        if user is None:
            form.add_error(None, 'Wrong phone number or password.')
        else:
            login(request, user)
            messages.success(request, f'Welcome, {user.first_name}!')
            # go back to the page which needed login
            next_url = request.GET.get('next', '')
            if next_url.startswith('/') and not next_url.startswith('//'):
                return redirect(next_url)
            return redirect('home')
    return render(request, 'login.html', {'form': form})


def logout_view(request):
    if request.method == 'POST':
        logout(request)
        messages.info(request, 'You have been logged out.')
    return redirect('home')


def filter_cars(request):
    form = FilterForm(request.GET or None)
    cars = Car.objects.order_by('-created_at')

    if form.is_valid():
        data = form.cleaned_data
        if data['city']:
            cars = cars.filter(city=data['city'])
        if data['start_year']:
            cars = cars.filter(year__gte=data['start_year'])
        if data['end_year']:
            cars = cars.filter(year__lte=data['end_year'])
        if data['capacity']:
            cars = cars.filter(capacity=data['capacity'])
    elif form.is_bound:
        cars = Car.objects.none()

    paginator = Paginator(cars, 12)
    page = paginator.get_page(request.GET.get('page'))

    # filter values for pagination links
    params = request.GET.copy()
    params.pop('page', None)

    return render(request, 'filter.html', {
        'form': form,
        'page': page,
        'params': params.urlencode(),
    })


def car_detail(request, car_id):
    car = get_object_or_404(Car, id=car_id)
    is_approved = False
    if request.user.is_authenticated:
        is_approved = car.approved_by.filter(id=request.user.id).exists()
    return render(request, 'car_detail.html', {
        'car': car,
        'is_approved': is_approved,
        'days': range(1, MAX_DAYS + 1),
        'mapbox_token': settings.MAPBOX_TOKEN,
    })


@login_required
def car_rent(request, car_id):
    car = get_object_or_404(Car, id=car_id)
    if request.method != 'POST':
        return redirect('car_detail', car_id=car.id)

    if car.owner == request.user:
        messages.warning(request, 'You can not rent your own car.')
        return redirect('car_detail', car_id=car.id)

    form = RentForm(request.POST)
    if not form.is_valid():
        messages.error(request, f'Number of days must be from 1 to {MAX_DAYS}.')
        return redirect('car_detail', car_id=car.id)

    days = form.cleaned_data['days']
    total = days * car.price
    Rental.objects.create(user=request.user, car=car, days=days, total_price=total)

    # notification for the owner and for users who approved this car
    Notification.objects.create(
        user=car.owner,
        text=f'Your car {car.brand} {car.model} was rented for {days} days.',
    )
    for user in car.approved_by.exclude(id=request.user.id):
        Notification.objects.create(
            user=user,
            text=f'{car.brand} {car.model} which you approved was rented.',
        )

    messages.success(request, f'You rented {car.brand} {car.model} for {days} days. Total price: {total} GEL.')
    return redirect('profile')


@login_required
def car_approve(request, car_id):
    car = get_object_or_404(Car, id=car_id)
    if request.method == 'POST':
        if car.approved_by.filter(id=request.user.id).exists():
            car.approved_by.remove(request.user)
            messages.info(request, 'Car was removed from your approved cars.')
        else:
            car.approved_by.add(request.user)
            messages.success(request, 'Car was added to your approved cars.')
    return redirect('car_detail', car_id=car.id)


@login_required
def car_add(request):
    form = CarForm(request.POST or None, request.FILES or None)
    if request.method == 'POST' and form.is_valid():
        car = form.save(commit=False)
        # owner is the logged in user
        car.owner = request.user
        car.save()
        messages.success(request, 'Your car was added.')
        return redirect('car_detail', car_id=car.id)

    cities = Car.objects.values_list('city', flat=True).distinct()
    return render(request, 'car_add.html', {'form': form, 'cities': cities})


@login_required
def car_delete(request, car_id):
    car = get_object_or_404(Car, id=car_id)
    if request.method == 'POST' and car.owner == request.user:
        car.delete()
        messages.info(request, 'Your car was deleted.')
        return redirect('profile')
    return redirect('car_detail', car_id=car.id)


@login_required
def profile(request):
    return render(request, 'profile.html', {
        'rentals': request.user.rentals.select_related('car').order_by('-created_at'),
        'approved_cars': request.user.approved_cars.all(),
        'my_cars': request.user.cars.order_by('-created_at'),
    })


@login_required
def notifications(request):
    return render(request, 'notifications.html', {
        'notifications': request.user.notifications.order_by('-created_at'),
    })
