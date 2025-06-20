import os
from flask import Flask, render_template_string, request, redirect, url_for

# Змінено: pyodbc видалено, додано mysql.connector
import mysql.connector
from mysql.connector import Error

app = Flask(__name__)

DB_CONNECTION_STRING = os.environ.get("DB_CONNECTION_STRING")

if not DB_CONNECTION_STRING:
    print("ERROR: DB_CONNECTION_STRING environment variable is not set.")
    @app.route('/')
    def index_no_db():
        return "<h1>Помилка: DB_CONNECTION_STRING не встановлено. Перевірте конфігурацію App Service.</h1>"
else:
    def get_db_connection():
        """
        Парсить рядок DB_CONNECTION_STRING і повертає об'єкт підключення до MySQL.
        Очікує формат: "host=...;port=...;user=...;password=...;database=...;ssl_disabled=..."
        """
        params = {}
        try:
            # Розпарсити рядок підключення.
            # Наприклад: "host=your_host;port=3306;user=your_user;password=your_password;database=your_db"
            for part in DB_CONNECTION_STRING.split(';'):
                if '=' in part:
                    key, value = part.split('=', 1)
                    params[key.strip().lower()] = value.strip()

            # Створити підключення до MySQL
            conn = mysql.connector.connect(
                host=params.get('host'),
                port=int(params.get('port', 3306)),
                user=params.get('user'),
                password=params.get('password'),
                database=params.get('database'),
                # Додано налаштування SSL з урахуванням ssl_disabled
                ssl_disabled=params.get('ssl_disabled', 'False').lower() == 'true'
                # Якщо потрібен SSL CA сертифікат, його потрібно завантажити
                # на App Service і вказати шлях: ssl_ca=params.get('ssl_ca')
            )
            return conn
        except Error as e:
            print(f"Помилка підключення до MySQL: {e}")
            raise # Перекидаємо виняток далі

    HTML_TEMPLATE = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Azure Todo App</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; background-color: #f4f4f4; }
            .container { max-width: 600px; margin: auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 0 10px rgba(0,0,0,0.1); }
            h1 { text-align: center; color: #333; }
            form { display: flex; margin-bottom: 20px; }
            form input[type="text"] { flex-grow: 1; padding: 10px; border: 1px solid #ddd; border-radius: 4px; }
            form button { padding: 10px 15px; background-color: #007bff; color: white; border: none; border-radius: 4px; cursor: pointer; margin-left: 10px; }
            form button:hover { background-color: #0056b3; }
            ul { list-style: none; padding: 0; }
            li { background: #e9ecef; padding: 10px; margin-bottom: 8px; border-radius: 4px; display: flex; justify-content: space-between; align-items: center; }
            li .delete-btn { background-color: #dc3545; color: white; border: none; padding: 5px 10px; border-radius: 4px; cursor: pointer; font-size: 0.8em; }
            li .delete-btn:hover { background-color: #c82333; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Azure Todo List</h1>
            <form action="/add" method="post">
                <input type="text" name="item" placeholder="Add a new todo item" required>
                <button type="submit">Add Todo</button>
            </form>
            <ul>
                {% for item in todos %}
                    <li>
                        <span>{{ item[1] }}</span>
                        <form action="/delete/{{ item[0] }}" method="post" style="display:inline;">
                            <button type="submit" class="delete-btn">Delete</button>
                        </form>
                    </li>
                {% endfor %}
            </ul>
        </div>
    </body>
    </html>
    """

    @app.route('/')
    def index():
        conn = None
        cursor = None
        todos = []
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            # Змінено: Створення таблиці для MySQL (UNSIGNED INT, AUTO_INCREMENT)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS Todos (
                    Id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
                    Description VARCHAR(255) NOT NULL
                )
            """)
            conn.commit()

            cursor.execute("SELECT Id, Description FROM Todos ORDER BY Id DESC")
            todos = cursor.fetchall()
        except Error as ex: # Змінено тип винятку на mysql.connector.Error
            print(f"Database error: {ex}")
            return f"Database error: {ex}. Is DB_CONNECTION_STRING correct and DB accessible from App Service? Check App Service logs.", 500
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
        return render_template_string(HTML_TEMPLATE, todos=todos)

    @app.route('/add', methods=['POST'])
    def add_todo():
        item = request.form['item']
        conn = None
        cursor = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            # Змінено: Використання %s для плейсхолдерів в MySQL
            cursor.execute("INSERT INTO Todos (Description) VALUES (%s)", (item,))
            conn.commit()
        except Error as ex: # Змінено тип винятку
            print(f"Database error: {ex}")
            return f"Database error: {ex}. Could not add item.", 500
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
        return redirect(url_for('index'))

    @app.route('/delete/<int:item_id>', methods=['POST'])
    def delete_todo(item_id):
        conn = None
        cursor = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            # Змінено: Використання %s для плейсхолдерів в MySQL
            cursor.execute("DELETE FROM Todos WHERE Id = %s", (item_id,))
            conn.commit()
        except Error as ex: # Змінено тип винятку
            print(f"Database error: {ex}")
            return f"Database error: {ex}. Could not delete item.", 500
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
        return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)