# Module 5 - Software Assurance + Secure SQL

[Read the Docs](https://jhu-software-concepts-siva.readthedocs.io/en/latest/)

## Fresh Install (pip + venv)

```bash
cd module_5
python -m venv venv
source venv/bin/activate        # Linux/Mac
# venv\Scripts\activate          # Windows

pip install -r requirements.txt
pip install -e .
```

## Fresh Install (uv)

```bash
cd module_5
uv venv
source .venv/bin/activate       # Linux/Mac
# .venv\Scripts\activate         # Windows

uv pip sync requirements.txt
uv pip install -e .
```

## Running the App

```bash
# Set up your .env file (copy from .env.example)
cp .env.example .env
# Edit .env with your database credentials

# Run the Flask app
python -m module_5.src.app
```

## Running Tests

```bash
pytest module_5 -v
```

## Pylint

```bash
pylint module_5/src/app.py module_5/src/query_data.py module_5/src/load_data.py module_5/src/sql_utils.py module_5/src/load_new_data.py module_5/src/run_pipeline.py --rcfile=module_5/.pylintrc
```

## Generating Dependency Graph

```bash
pip install pydeps graphviz
pydeps module_5/src/app.py --noshow -T svg -o module_5/dependency.svg
```
