# RETHA CRM

#### Video Demo: [Youtube](https://youtu.be/guCN_1nxFtk)

#### Description:

CRM for real estate company

# CRM for Real Estate Company

## Features

- CRUD operations for users and real estate properties.
- UI determined by the user's role.
- Interactive map.
- Create and download presentations in PDF format.

## Structure

- `main.py` - Determines business logic and defines URLs.
- `components.py` - Service and component functions.
- `mysettings.py` - Database settings and initialization.
- `const.py` - Constant definitions.

## Stack

- **Languages**: Python, JavaScript, CSS.
- **Frameworks**: FastHTML.
- **Libraries**: ReportLab, asyncio, pandas, etc.

---

## About the Application

The application works with the following entities:

- **User**: Has access to the interactive map and property details.
- **Client**:
  - Has User functionality.
  - Can add and manage comparisons.
  - Can create and download presentations in PDF format based on selected comparisons.
- **Broker / Secretary**:
  - Has Client functionality.
  - Can create tasks.
  - Can edit property and user information.
- **Administrator**:
  - Has Secretary functionality.
  - Can create brokers and secretaries.

---

## Use Case

- **For clients**:  
  Search for properties on the main page → Check property details → Add units/modules for comparison → Check and edit comparisons → Download presentations with selected comparisons.

- **For employees**:  
  Create a task from client to broker → Search properties based on task parameters → Check and edit property details → Add units/modules to comparisons for a client as defined by the task → Check and edit added comparisons → Download presentations with selected comparisons.

---

## Installation

1. Clone the repository:

   ```bash
   git clone git@github.com:Artem-Ter/retha_crm.git
   ```

2. Create and activate virtual environment:

   ```bash
   python -m venv env
   source venv/bin/activate
   python -m pip install --upgrade pip
   ```

3. Install dependencies:

   ```bash
   cd retha_crm
   pip install -r requirements.txt
   ```

4. Create .env file with following data:

   ```
   GOOGLE_API=your_google_api_key
   ADMIN_PWD=your_password
   ADMIN_EMAIL=admin_email
   ```

5. Run application:

   ```bash
   python3 main.py
   ```

## License

[MIT](https://choosealicense.com/licenses/mit/)
