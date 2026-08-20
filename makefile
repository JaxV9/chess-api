VENV = venv/bin

run:
	fastapi dev main.py

test:
	$(VENV)/pytest test_main.py

install:
	pip install -r requirements.txt

clean:
	rm -rf __pycache__ .pytest_cache

cv:
	rm -f alembic/versions/*.py
	rm -rf alembic/versions/__pycache__/*.pyc

migrate:
	@read -p "Message: " msg; \
	$(VENV)/alembic revision --autogenerate -m "$$msg"
	$(VENV)/alembic upgrade head

dbreset:
	PYTHONPATH=. $(VENV)/python3 scripts/dbreset.py
	$(VENV)/alembic stamp --purge base
	@read -p "Message: " msg; \
	$(VENV)/alembic revision --autogenerate -m "$$msg"
	$(VENV)/alembic upgrade head

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