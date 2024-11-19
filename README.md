To run the app locally

- gcloud auth application-default login
- virtualenv dbenv (create virtual environment with name of "dbenv")
- source dbenv/bin/activate (activate virtual environment)
- pip install -r requirements.txt (install all dependencies)
    - if the above command fails, try the following:
        - pip install django
        - pip install mysqlclient
        - pip install mysql-connector-python
        - pip install PyMySQL
- python manage.py runserver (run the app)
