from functools import wraps

from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.http import urlencode


# checks that user is logged in (user is saved in session)
def session_login_required(view):
    @wraps(view)
    def wrapper(request, *args, **kwargs):
        if request.session.get('user'):
            return view(request, *args, **kwargs)
        messages.info(request, 'Please log in to continue.')
        next_url = request.get_full_path() if request.method == 'GET' else request.META.get('HTTP_REFERER', '')
        login_url = reverse('login')
        if next_url:
            login_url += '?' + urlencode({'next': next_url})
        return redirect(login_url)

    return wrapper
