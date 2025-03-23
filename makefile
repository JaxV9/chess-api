run:
	fastapi dev main.py

install:
	pip install -r requirements.txt

clean:
	rm -rf __pycache__ .pytest_cache


migrate:
	@read -p "Message: " msg; \
	alembic revision --autogenerate -m "$$msg"
	alembic upgrade head