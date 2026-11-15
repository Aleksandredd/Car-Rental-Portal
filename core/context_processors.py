def current_user(request):
    """Make the logged-in user (from the session) available in every template."""
    return {'current_user': request.session.get('user')}
