# Knjižnica

A small library web app where an administrator manages the book catalogue and students reserve books.

Built with **Python + Flask** and **SQLite**. The only dependency is Flask.

## Features

- Registration and login with two roles: **student** and **administrator**
- Catalogue with cover, title, author and availability
- Search by title, author or category, with category filters, an "only available" toggle and sorting
- Book detail page with the description and the number of remaining copies
- Reserve and cancel (students). A reservation takes one copy off the count and a cancellation gives it back
- "Moje rezervacije" page with each student's active reservations and history
- Admin dashboard for adding, editing and deleting books and for viewing all reservations

## Requirements

- Python **3.9+**
- pip

## Installation

```bash
# 1. Clone the repository
git clone <repo-url> knjiznica
cd knjiznica

# 2. (Recommended) create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt
```

## Running

```bash
python3 app.py                     # Windows: python app.py
```

Open **http://localhost:5000** in your browser. Stop the server with `Ctrl+C`.

On first start, the app creates the SQLite database `knjiznica.db` in the project folder. It fills it with 16 sample books and two demo accounts.

### Demo accounts

| Role          | Email                | Password     |
|---------------|----------------------|--------------|
| Student       | `ana@student.si`     | `student123` |
| Administrator | `admin@knjiznica.si` | `admin123`   |

New students can sign up on the **Registracija** page. Registering as an administrator requires the admin code, which is `KNJIZNICA-ADMIN` by default.

## Configuration

Optional environment variables:

| Variable               | Default                   | Purpose                              |
|------------------------|---------------------------|--------------------------------------|
| `PORT`                 | `5000`                    | Port the server listens on           |
| `KNJIZNICA_DB`         | `./knjiznica.db`          | Path to the SQLite database file     |
| `KNJIZNICA_ADMIN_CODE` | `KNJIZNICA-ADMIN`         | Code required to register as admin   |
| `KNJIZNICA_SECRET`     | derived from project path | Secret key for signing session cookies |

Example:

```bash
PORT=8000 KNJIZNICA_ADMIN_CODE=secret123 python3 app.py
```

On Windows PowerShell, set each variable first with `$env:PORT=8000`, then run the app.

## Resetting the database

Stop the server, delete the database file, and start the app again. It is recreated with the sample data:

```bash
rm knjiznica.db
python3 app.py
```

## Project structure

```
app.py               Flask app: routes, auth, database schema and seed data
requirements.txt     Python dependencies
static/style.css     All styling
templates/           Jinja2 templates
  base.html          Layout (header, ticker, footer, toasts)
  _macros.html       Reusable book card, cover and availability components
  catalog.html       Catalogue with search and filters
  book.html          Book details and the reserve / cancel button
  login.html         Login
  register.html      Registration
  my_reservations.html
  error.html
  admin/
    dashboard.html   Book management and all reservations
    book_form.html   Add / edit book
```

## Tech stack

- **Backend:** Python 3, Flask 3 (Jinja2 templates, Werkzeug password hashing)
- **Database:** SQLite through Python's built-in `sqlite3` module, written in plain SQL with no ORM
- **Frontend:** pages rendered on the server, one hand-written CSS file and a little plain JavaScript. There is no build step.

## Note

The server runs in Flask's debug mode, so it is meant for local development and demos only. To deploy it, set a strong `KNJIZNICA_SECRET`, change the demo passwords, and run it behind a production WSGI server such as `gunicorn app:app`.
