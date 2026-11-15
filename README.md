# Car Rental Portal

A university course project: a car rental web app built with **Python and Django**.

The app has no car or user database of its own. All data lives on an external REST API
([RentCar API](https://rentcar.stepprojects.ge/swagger/index.html)); Django renders the pages and acts as a
server-side proxy that calls the API with the `requests` library. Django's own SQLite database stores only
login sessions.

## Features

- **Home page** with "Popular cars" and "Random cars" sections.
- **Registration and login** by phone number, with server-side validation. The logged-in user is kept in the
  Django session.
- **Filter page**: filter cars by city, year range and number of seats, alone or combined, with pagination.
- **Car page**: full car information, photo gallery, total-price calculator (days x daily price), "Rent" and
  "Approve" buttons, and an optional Mapbox map of the car's location.
- **Add car** (logged-in users): three photos (.png / .jpg / .jpeg, checked on the server), the owner's phone is
  taken from the session, and the location comes from the browser's Geolocation API.
- **Profile**: rented cars (city, amount paid, rental days), approved cars and the cars you posted.
- **Notifications**: a car's owner gets a message when someone rents the car.
- Responsive Bootstrap 5 design, flash messages, friendly errors when the API is slow or down.

## Screenshots

_Add screenshots here, for example:_

| Home | Car page | Profile |
|---|---|---|
| `docs/screenshots/home.png` | `docs/screenshots/car.png` | `docs/screenshots/profile.png` |

## Setup

Requires Python 3.12 or newer.

```bash
git clone https://github.com/<your-username>/car-rental-portal.git
cd car-rental-portal

python -m venv venv
# Windows:
venv\Scripts\activate
# macOS / Linux:
source venv/bin/activate

pip install -r requirements.txt

# Windows: copy .env.example .env
cp .env.example .env

python manage.py migrate
python manage.py runserver
```

Then open http://127.0.0.1:8000/.

### Settings (`.env`)

| Name | Meaning |
|---|---|
| `SECRET_KEY` | Django secret key (any long random string) |
| `DEBUG` | `True` while developing |
| `API_BASE_URL` | Base URL of the RentCar API |
| `MAPBOX_TOKEN` | Optional Mapbox public token. Without it the car page shows coordinates instead of a map. |

## Project structure

```
carrental/            Django project (settings, root urls)
core/
  api_client.py       the only module that talks to the API: one function per endpoint
  decorators.py       session_login_required
  forms.py            validation for register, login, filter, rent, add car
  views_auth.py       register, login, logout
  views_cars.py       home, filter, car page, rent, approve, add car, profile, notifications
templates/            base.html, _car_card.html (reusable card) and one template per page
static/               css/style.css, js (rent total, geolocation, map), placeholder image
docs/                 api_spec.json (OpenAPI spec) and API_NOTES.md (endpoint summary)
```

## Notes about the API

The details are in [docs/API_NOTES.md](docs/API_NOTES.md). The important ones:

- The API has no "approved cars" feature, so **Approve** uses the API's *favorites* endpoints.
- The API does not create notifications by itself. The app sends one to the car's owner after each rental.
- At the time of writing the API fails when it receives photos (its upload folder is not writable). The app
  first sends the photos as the spec requires; if that fails it saves the car without photos and keeps the
  photos in the local `media/` folder, where the development server serves them. Cars added from another
  computer therefore show a placeholder image.
- The API has no authentication on its endpoints and no way to edit or delete cars.

## Credits

Data and API: [RentCar API](https://rentcar.stepprojects.ge/swagger/index.html)
([source code](https://github.com/Lashvardi/Rent-Car-API)) by Lashvardi / Step Projects.
Built with [Django](https://www.djangoproject.com/) and [Bootstrap 5](https://getbootstrap.com/).
