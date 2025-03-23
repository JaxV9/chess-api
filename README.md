# chess-api

## Status of the project
Work in progress...

## Description of the project
This project is the back-end of https://chess-bay-nu.vercel.app/
It allows to play with players around the world in multiplayer games.

## Architecture
```
.
├── alembic     //here you have all the configs about db migrations
│   ├── __init__.py
│   ├── __pycache__
│   ├── env.py
│   ├── script.py.mako
│   └── versions
|
├── alembic.ini
|
├── constant    //constants usefull for the project
│   ├── __init__.py
│   ├── __pycache__
│   └── constant.py
|
├── database    //connection to the db and instance created
│   ├── __init__.py
│   ├── __pycache__
│   └── database.py
|
├── main.py     //the app
|
├── makefile    //alias to run quickly the most used commands
|
├── model   //link about the db and the app
│   ├── __init__.py
│   ├── __pycache__
│   └── model.py
|
├── requirements.txt //dependencies
|
├── schema      //structure of the APIs
│   ├── __init__.py
│   ├── __pycache__
│   └── schema.py
|
├── utils       //usefull functions used in main
│   ├── __pycache__
│   └── utils.py
```