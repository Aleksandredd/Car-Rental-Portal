# RentCar API notes

- Base URL: `https://rentcar.stepprojects.ge`
- Spec: [api_spec.json](api_spec.json) (OpenAPI 3.0.1, downloaded from `/swagger/v1/swagger.json`)
- API source: https://github.com/Lashvardi/Rent-Car-API (Controllers + DTO)
- Sources for this file: the spec, the controller source code, and live calls to every endpoint we use
  (GET and POST), made with test accounts.

## Auth

**No endpoint requires authentication.** The spec has no `securitySchemes`, and no controller uses `[Authorize]`.
Login returns a JWT `token` (valid 1 day), but nothing ever asks for it. The API identifies users only by the
`phoneNumber` passed in the query/path. We still store the token in the session, but every call is unauthenticated.

## Shared objects

**Car** (confirmed live)

| Field | Type | Notes |
|---|---|---|
| `id` | int | |
| `brand`, `model` | string | |
| `year` | int | |
| `price` | number | price per day |
| `capacity` | int | seats |
| `transmission` | string | free text; live data has Georgian, English and junk values |
| `fuelCapacity` | int | |
| `city` | string | free text, can be `null` |
| `imageUrl1`, `imageUrl2`, `imageUrl3` | string / null | often `null` |
| `latitude`, `longitude` | number | `0` when not set |
| `createdBy` | string | owner's phone number (free text in old data) |
| `createdByEmail` | string / null | |
| `multiplier` | int | unused by us |
| `image1..3`, `ownerPhoneNumber` | null | always `null` in responses |

**Paginated wrapper**: `{ totalItems, totalPages, currentPage, pageSize, data: [Car] }`

**Errors**: plain text body (e.g. `User not found`) or ASP.NET problem JSON (`{type, title, status, traceId}`).

## Cars

| Method | Path | Input | Response |
|---|---|---|---|
| GET | `/api/Car` | none | `[Car]`, **12 random cars** (different every call). This is the "random cars" endpoint. |
| GET | `/api/Car/popular` | none | `[Car]`, 4 cars. (The source picks them randomly too; there is no real popularity ranking.) |
| GET | `/api/Car/paginated` | query `pageIndex` (default 1), `pageSize` (default 10) | Paginated wrapper. 400 text if the page is out of range. |
| GET | `/api/Car/filter` | query `capacity`, `startYear`, `endYear`, `city`, `pageIndex`, `pageSize`, all optional | Paginated wrapper (the spec says `[Car]`, but the live API returns the wrapper). `capacity` and `city` are exact matches; years are inclusive. **No results gives 400 `Invalid page index.`**, which must be treated as an empty list. |
| GET | `/api/Car/cities` | none | `[string]`, distinct cities. Contains `null`, duplicates in different spellings and junk; needs cleaning. |
| GET | `/api/Car/byPhone` | query `PhoneNumber` | `[Car]` where `createdBy` equals the phone. **404 when the user has no cars.** |
| GET | `/api/Car/{id}` | path `id` | `Car`, or 404 problem JSON. |
| POST | `/api/Car` | `multipart/form-data`: `Brand`, `Model`, `Year`, `Price`, `Capacity`, `Transmission`, `CreatedBy`, `City`, `CreatedByEmail`, `FuelCapacity`, `Image1`, `Image2`, `Image3` (files), `Latitude`, `Longitude` | 201 with the created `Car`. Images must end in `.jpg`, `.png` or `.jpeg`; other files are silently dropped. |

## Users

| Method | Path | Input | Response |
|---|---|---|---|
| POST | `/api/Users/register` | JSON `UserDTO`: `phoneNumber`, `password`, `email`, `firstName`, `lastName`, `role` | `User` object. 400 text `User already exists`. The API sends a welcome email to `email`. `role` is ignored (always `"User"`). |
| POST | `/api/Users/login` | JSON `UserDTO` (only `phoneNumber` + `password` are used) | `{ token, firstName, lastName, role, phoneNumber, email }`. 400 text `User Not Found!` or `Wrong Password`. Note: an account with an empty phone and empty password exists on the live API, so empty values must be rejected on our side. |
| GET | `/api/Users/{phoneNumber}` | path | `User`: `phoneNumber`, `email`, `firstName`, `lastName`, `role`, `favoriteCars`, `message` (it also returns `passwordHash` / `passwordSalt`, which we must never display or store). 404 if unknown. |
| GET | `/api/Users/{phoneNumber}/favorite-cars` | path | `[Car]`. 404 text `User not found`. |
| POST | `/api/Users/{userId}/favorites/{carId}` | path; `userId` is the phone number | 200 with empty body. 404 text `User not found` / `Car not found`. |

## Renting

| Method | Path | Input | Response |
|---|---|---|---|
| POST | `/Purchase/purchase` | query `phoneNumber`, `carId`, `multiplier` (number of days, default 1) | Ticket: the car's fields plus `dayPrice` and `pricePaid` (= price × multiplier). 400 text `Car not found`. |
| GET | `/Purchase/{phoneNumber}` | path | `[ { carId, carBrand, carModel, city, multiplier, pricePaid } ]`. When there are none: **200 with the plain text `No products`**, not JSON. |

## Messages (notifications)

| Method | Path | Input | Response |
|---|---|---|---|
| GET | `/Message/Messages` | query `phoneNumber` | `[string]`, the message texts. 400 text `User not found`. |
| POST | `/Message/Message` | query `phoneNumber` (the receiver), `CarId` | `{ id, messageText }` with a random text such as "Hey Someone Rented Your BMW/X5". 400 text `User not found`. |

The API does **not** create a message by itself when a car is rented. Our app has to call
`POST /Message/Message` with the owner's phone (`car.createdBy`) right after a successful purchase.

## Gaps and workarounds

1. **"Approved cars"**: the API has no approval concept. The closest real feature is favorites
   (`favorite-cars` + `favorites/{carId}`).
2. **Uploaded photos do not work on the live API.** Any `POST /api/Car` that contains an image answers
   500 (`UnauthorizedAccessException`: the server cannot write to its `Uploads` folder). The same request
   without images succeeds. The API source also builds photo URLs on `rentcar.webwide.ge`, a domain that no
   longer resolves. Workaround: the app tries with photos first, retries without them on a 5xx, and keeps
   local copies in `media/cars/<id>/` which it shows instead.
3. **Popular cars** are random on the server side, so the two home sections differ only in size (4 vs 12).
4. **No edit/delete** endpoints for cars or users, no logout endpoint (logout = clear the Django session).
5. **Seed photos**: the seed cars use `loremflickr.com` image URLs, which currently answer 500, so those
   cars show the placeholder image.
6. **Data quality**: cities and transmissions are free text. Our own form will send clean values
   (`Automatic` / `Manual` / `Tiptronic`), and templates must tolerate `null` everywhere.
