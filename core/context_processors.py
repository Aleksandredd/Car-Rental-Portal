# logged in user for templates
def current_user(request):
    return {'current_user': request.session.get('user')}
