# Car Rental Portal

University course project. Car rental website made with **Python** and **Django**.
All data (users, cars, rentals, notifications) is saved in SQLite database.

## Features

- Home page with "Popular cars" and "Random cars"
- Registration (first name, last name, phone number, email, password) and login with phone number
- Filter cars by city, year and number of seats (filters work together too)
- Car page with all information, 3 photos, "Rent" button with total price and map (Mapbox)
- Add car page with 3 photos (only .png, .jpg, .jpeg). Location is taken from the browser
- Owner can delete his car
- Profile page: rented cars, approved cars and cars I posted
- Notifications when somebody rents your car
- Admin panel for all data
- Bootstrap 5 design, works on phone

## Screenshots

_screenshots will be added here_

## How to run

```bash
git clone https://github.com/Aleksandredd/car-rental-portal.git
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

Then open http://127.0.0.1:8000/

To use admin panel (http://127.0.0.1:8000/admin/) create admin user:

```bash
python manage.py createsuperuser
```

## .env file

| Name | What is it |
|---|---|
| `SECRET_KEY` | Django secret key |
| `DEBUG` | `True` for development |
| `MAPBOX_TOKEN` | Mapbox token for the map (can be empty) |

## Project structure

```
carrental/        settings and main urls
core/
  models.py       User, Car, Rental, Notification
  forms.py        forms and validation
  views.py        all pages
  urls.py         urls of the pages
  admin.py        admin panel
templates/        html pages
static/           css, js, images
media/            uploaded car photos
```

## Used

- [Django](https://www.djangoproject.com/)
- [Bootstrap 5](https://getbootstrap.com/)
- [Mapbox](https://www.mapbox.com/)
