# JHU Software Concepts

A Flask-based web application project for Johns Hopkins University software concepts coursework.

## Prerequisites

- Python 3.10 or higher
- pip (Python package manager)

## Installation

1. Clone or download the project
2. Install required dependencies:
```bash
pip install -r requirements.txt
```

## Running the Application

1. Navigate to the project directory
2. Run the application:
```bash
python run.py
```
3. Open your browser and navigate to `http://localhost:8080`

## Project Structure

```
Module 1/
├── run.py              # Application entry point
├── requirements.txt    # Project dependencies
├── README.md          # This file
└── board/             # Main application package
    ├── __init__.py
    ├── pages.py       # Page routes and logic
    ├── static/        # Static files (CSS, images)
    │   ├── styles.css
    │   └── profile.jfif
    └── templates/     # HTML templates
        ├── base.html
        ├── _navigation.html
        └── pages/
            ├── home.html
            ├── contact.html
            └── projects.html
```

## License

Johns Hopkins University - Educational Project