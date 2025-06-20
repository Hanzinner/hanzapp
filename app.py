import os
from flask import Flask, render_template_string, request, redirect, url_for
import pyodbc

app = Flask(__name__)

DB_CONNECTION_STRING = os.environ.get("DB_CONNECTION_STRING")

if not DB_CONNECTION_STRING:
    print("ERROR: DB_CONNECTION_STRING environment variable is not set.")
    @app.route('/')
    def index_no_db():
        return "<h1>Помилка: DB_CONNECTION_STRING не встановлено. Перевірте конфігурацію App Service.</h1>"
else:
    def get_db_connection():
        conn = pyodbc.connect(DB_CONNECTION_STRING)
        return conn

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
            cursor.execute("""
                IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='Todos' and xtype='U')
                CREATE TABLE Todos (
                    Id INT IDENTITY(1,1) PRIMARY KEY,
                    Description NVARCHAR(255) NOT NULL
                )
            """)
            conn.commit()

            cursor.execute("SELECT Id, Description FROM Todos ORDER BY Id DESC")
            todos = cursor.fetchall()
        except pyodbc.Error as ex:
            sqlstate = ex.args[0]
            print(f"Database error: {sqlstate}")
            return f"Database error: {sqlstate}. Is DB_CONNECTION_STRING correct and DB accessible from App Service? Check App Service logs.", 500
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
            cursor.execute("INSERT INTO Todos (Description) VALUES (?)", item)
            conn.commit()
        except pyodbc.Error as ex:
            sqlstate = ex.args[0]
            print(f"Database error: {sqlstate}")
            return f"Database error: {sqlstate}. Could not add item.", 500
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
            cursor.execute("DELETE FROM Todos WHERE Id = ?", item_id)
            conn.commit()
        except pyodbc.Error as ex:
            sqlstate = ex.args[0]
            print(f"Database error: {sqlstate}")
            return f"Database error: {sqlstate}. Could not delete item.", 500
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
        return redirect(url_for('index'))