from django.contrib import messages
from django.shortcuts import redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from . import api_client
from .api_client import ApiError
from .forms import LoginForm, RegisterForm


def _safe_next(request):
    """Return the ?next= target only if it points back to this site."""
    target = request.POST.get('next') or request.GET.get('next') or ''
    if target and url_has_allowed_host_and_scheme(target, allowed_hosts={request.get_host()},
                                                  require_https=request.is_secure()):
        return target
    return ''


def register(request):
    if request.session.get('user'):
        return redirect('home')

    form = RegisterForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        data = form.cleaned_data
        try:
            api_client.register_user(
                first_name=data['first_name'],
                last_name=data['last_name'],
                phone=data['phone'],
                email=data['email'],
                password=data['password'],
            )
        except ApiError as exc:
            if exc.status == 400:
                form.add_error('phone', exc.message)
            else:
                messages.error(request, exc.message)
        else:
            messages.success(request, 'Your account was created. You can log in now.')
            return redirect('login')
    return render(request, 'register.html', {'form': form})


def login(request):
    if request.session.get('user'):
        return redirect('home')

    form = LoginForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        try:
            data = api_client.login_user(phone=form.cleaned_data['phone'],
                                         password=form.cleaned_data['password'])
        except ApiError as exc:
            if exc.status == 400:
                form.add_error(None, exc.message)
            else:
                messages.error(request, exc.message)
        else:
            next_url = _safe_next(request)
            request.session.cycle_key()  # new session id after login
            request.session['api_token'] = data.get('token')
            request.session['user'] = {
                'phone': data.get('phoneNumber') or form.cleaned_data['phone'],
                'first_name': data.get('firstName') or '',
                'last_name': data.get('lastName') or '',
                'email': data.get('email') or '',
                'role': data.get('role') or 'User',
            }
            messages.success(request, f"Welcome back, {request.session['user']['first_name'] or 'driver'}!")
            return redirect(next_url or 'home')
    return render(request, 'login.html', {'form': form, 'next': _safe_next(request)})


@require_POST
def logout(request):
    request.session.flush()
    messages.info(request, 'You have been logged out.')
    return redirect('home')
