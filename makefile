run:
	fastapi dev main.py

test:
	pytest test_main.py

install:
	pip install -r requirements.txt

clean:
	rm -rf __pycache__ .pytest_cache

cv:
	rm -f alembic/versions/*.py
	rm -rf alembic/versions/__pycache__/*.pyc

migrate:
	@read -p "Message: " msg; \
	alembic revision --autogenerate -m "$$msg"
	alembic upgrade head

dbreset:
	@read -p "Message: " msg; \
	alembic revision --autogenerate -m "$$msg"
	alembic downgrade base
	alembic upgrade head

c:
	@read -p "Commit: " msg; \
	git commit -m "$$msg"

p:
	git push

pl:
	git pull

main:
	git checkout main

s:
	git stash

sp:
	git stash pop