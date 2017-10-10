release: invoke create-settings --settings-path wger/settings.py --database-path wger/database.sqlite
web: gunicorn wger.wsgi:application