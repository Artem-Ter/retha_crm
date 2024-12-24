# RETHA CRM

#### Video Demo: [Youtube]()

#### Description:

CRM for real estate company

Features:

- CRUD operations for users and real estates
- UI determent by user's role
- interactive map
- create and download presentation in pdf

Structure:

- main.py - determine buisness logic and define urls
- components.py - service and components functions
- mysettings.py - Database settings and inicialization
- const.py - constant's definition

Stack:

- Languages: Python, JS, CSS
- Frameworks: FastHTML
- Libraries: reportlab, asyncio, pandas, etc.

#### About application:

Application works with following entites:

- User - has access to interactive map and property detials
- Client - User's functionality + may add and manage his/her comparisons, create and dowload presentation in pdf based on selected comparisons
- Broker / Secretary - Client's functionality + craate tasks, edit properties and users infromation
- Administrator - Secretary's functionality + may create brokers and secretaries

Use Case:

- for clients: Search for properties on main page -> check property details -> add units/modules for comparison -> check and edit comparisons -> download presentation with selected comparisons
- for employees: Create task from client to broker -> search properties based on task parameters -> check and edit property details -> add units/modules to comparisons for client defined by task -> check and edit added comparisons -> download presentation with selected comparisons

## Installation

Clone the repository.

```bash
git clone git@github.com:Artem-Ter/retha_crm.git
```

Create and activate vitual enviroment

```bash
python -m venv env
source venv/bin/activate
python -m pip install --upgrade pip
```

Install dependencies

```bash
cd retha_crm
pip install -r requirements.txt
```

Create .env file with following data

```
GOOGLE_API=your_google_api_key
ADMIN_PWD=your_password
ADMIN_EMAIL=admin_email
```

Run application

```bash
python main.py
```

## License

[MIT](https://choosealicense.com/licenses/mit/)
