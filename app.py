from flask import Flask, render_template, request, jsonify
import sqlite3
from datetime import datetime
import os

app = Flask(__name__)

# Database initialization
def init_db():
    conn = sqlite3.connect('budget.db')
    c = conn.cursor()
    
    # Income table
    c.execute('''CREATE TABLE IF NOT EXISTS income
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  amount REAL NOT NULL,
                  source TEXT,
                  date TEXT NOT NULL)''')
    
    # Commitments table
    c.execute('''CREATE TABLE IF NOT EXISTS commitments
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  name TEXT NOT NULL,
                  amount REAL NOT NULL,
                  frequency TEXT NOT NULL,
                  active INTEGER DEFAULT 1)''')
    
    # Investments table - Enhanced with tracking
    c.execute('''CREATE TABLE IF NOT EXISTS investments
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  name TEXT NOT NULL,
                  type TEXT NOT NULL,
                  amount_invested REAL NOT NULL,
                  current_value REAL DEFAULT 0,
                  buy_date TEXT NOT NULL,
                  sell_date TEXT,
                  status TEXT DEFAULT 'active',
                  notes TEXT)''')
    
    # Investment transactions table
    c.execute('''CREATE TABLE IF NOT EXISTS investment_transactions
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  investment_id INTEGER NOT NULL,
                  transaction_type TEXT NOT NULL,
                  amount REAL NOT NULL,
                  date TEXT NOT NULL,
                  notes TEXT,
                  FOREIGN KEY (investment_id) REFERENCES investments (id))''')
    
    # Spending table
    c.execute('''CREATE TABLE IF NOT EXISTS spending
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  category TEXT NOT NULL,
                  amount REAL NOT NULL,
                  description TEXT,
                  date TEXT NOT NULL)''')
    
    conn.commit()
    conn.close()

init_db()

@app.route('/')
def index():
    return render_template('index.html')

# Income endpoints
@app.route('/api/income', methods=['GET', 'POST'])
def income():
    conn = sqlite3.connect('budget.db')
    c = conn.cursor()
    
    if request.method == 'POST':
        data = request.json
        c.execute('INSERT INTO income (amount, source, date) VALUES (?, ?, ?)',
                  (data['amount'], data['source'], datetime.now().strftime('%Y-%m-%d')))
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    
    c.execute('SELECT * FROM income ORDER BY date DESC')
    income_data = [{'id': row[0], 'amount': row[1], 'source': row[2], 'date': row[3]} 
                   for row in c.fetchall()]
    conn.close()
    return jsonify(income_data)

# Commitments endpoints
@app.route('/api/commitments', methods=['GET', 'POST'])
def commitments():
    conn = sqlite3.connect('budget.db')
    c = conn.cursor()
    
    if request.method == 'POST':
        data = request.json
        c.execute('INSERT INTO commitments (name, amount, frequency) VALUES (?, ?, ?)',
                  (data['name'], data['amount'], data['frequency']))
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    
    c.execute('SELECT * FROM commitments WHERE active = 1')
    commitments_data = [{'id': row[0], 'name': row[1], 'amount': row[2], 'frequency': row[3]} 
                        for row in c.fetchall()]
    conn.close()
    return jsonify(commitments_data)

@app.route('/api/commitments/<int:id>', methods=['DELETE'])
def delete_commitment(id):
    conn = sqlite3.connect('budget.db')
    c = conn.cursor()
    c.execute('UPDATE commitments SET active = 0 WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

# Enhanced Investments endpoints
@app.route('/api/investments', methods=['GET', 'POST'])
def investments():
    conn = sqlite3.connect('budget.db')
    c = conn.cursor()
    
    if request.method == 'POST':
        data = request.json
        c.execute('''INSERT INTO investments 
                     (name, type, amount_invested, current_value, buy_date, status, notes) 
                     VALUES (?, ?, ?, ?, ?, ?, ?)''',
                  (data['name'], '', data['amount_invested'], 
                   data['current_value'], datetime.now().strftime('%Y-%m-%d'),
                   'active', data.get('notes', '')))
        
        investment_id = c.lastrowid
        
        # Add initial buy transaction
        c.execute('''INSERT INTO investment_transactions 
                     (investment_id, transaction_type, amount, date, notes) 
                     VALUES (?, ?, ?, ?, ?)''',
                  (investment_id, 'buy', data['amount_invested'], 
                   datetime.now().strftime('%Y-%m-%d'), 'Initial investment'))
        
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    
    c.execute('''SELECT id, name, type, amount_invested, current_value, buy_date, 
                 sell_date, status, notes FROM investments ORDER BY buy_date DESC''')
    investments_data = []
    for row in c.fetchall():
        profit_loss = row[4] - row[3] if row[4] > 0 else 0
        profit_loss_percent = ((profit_loss / row[3]) * 100) if row[3] > 0 else 0
        
        investments_data.append({
            'id': row[0],
            'name': row[1],
            'type': row[2],
            'amount_invested': row[3],
            'current_value': row[4],
            'buy_date': row[5],
            'sell_date': row[6],
            'status': row[7],
            'notes': row[8],
            'profit_loss': profit_loss,
            'profit_loss_percent': profit_loss_percent
        })
    
    conn.close()
    return jsonify(investments_data)

@app.route('/api/investments/<int:id>', methods=['PUT', 'DELETE'])
def update_investment(id):
    conn = sqlite3.connect('budget.db')
    c = conn.cursor()
    
    if request.method == 'PUT':
        data = request.json
        c.execute('''UPDATE investments 
                     SET name = ?, amount_invested = ?, current_value = ?, notes = ? 
                     WHERE id = ?''',
                  (data['name'], data['amount_invested'], data['current_value'], 
                   data.get('notes', ''), id))
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    
    if request.method == 'DELETE':
        # Delete investment completely
        c.execute('DELETE FROM investment_transactions WHERE investment_id = ?', (id,))
        c.execute('DELETE FROM investments WHERE id = ?', (id,))
        conn.commit()
        conn.close()
        return jsonify({'success': True})

@app.route('/api/investments/<int:id>/transactions', methods=['GET', 'POST'])
def investment_transactions(id):
    conn = sqlite3.connect('budget.db')
    c = conn.cursor()
    
    if request.method == 'POST':
        data = request.json
        c.execute('''INSERT INTO investment_transactions 
                     (investment_id, transaction_type, amount, date, notes) 
                     VALUES (?, ?, ?, ?, ?)''',
                  (id, data['transaction_type'], data['amount'], 
                   datetime.now().strftime('%Y-%m-%d'), data.get('notes', '')))
        
        # Update investment amount if adding more
        if data['transaction_type'] == 'buy':
            c.execute('SELECT amount_invested FROM investments WHERE id = ?', (id,))
            current = c.fetchone()[0]
            c.execute('UPDATE investments SET amount_invested = ? WHERE id = ?',
                     (current + data['amount'], id))
        
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    
    c.execute('''SELECT id, transaction_type, amount, date, notes 
                 FROM investment_transactions 
                 WHERE investment_id = ? ORDER BY date DESC''', (id,))
    transactions = [{'id': row[0], 'type': row[1], 'amount': row[2], 
                    'date': row[3], 'notes': row[4]} for row in c.fetchall()]
    conn.close()
    return jsonify(transactions)

# Spending endpoints
@app.route('/api/spending', methods=['GET', 'POST'])
def spending():
    conn = sqlite3.connect('budget.db')
    c = conn.cursor()
    
    if request.method == 'POST':
        data = request.json
        c.execute('INSERT INTO spending (category, amount, description, date) VALUES (?, ?, ?, ?)',
                  (data['category'], data['amount'], data['description'], datetime.now().strftime('%Y-%m-%d')))
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    
    c.execute('SELECT * FROM spending ORDER BY date DESC')
    spending_data = [{'id': row[0], 'category': row[1], 'amount': row[2], 'description': row[3], 'date': row[4]} 
                    for row in c.fetchall()]
    conn.close()
    return jsonify(spending_data)

# Dashboard summary
@app.route('/api/summary')
def summary():
    conn = sqlite3.connect('budget.db')
    c = conn.cursor()
    
    c.execute('SELECT SUM(amount) FROM income')
    total_income = c.fetchone()[0] or 0
    
    c.execute('SELECT SUM(amount) FROM commitments WHERE active = 1')
    total_commitments = c.fetchone()[0] or 0
    
    c.execute('SELECT SUM(amount_invested) FROM investments WHERE status = "active"')
    total_investments = c.fetchone()[0] or 0
    
    c.execute('SELECT SUM(current_value) FROM investments WHERE status = "active"')
    total_current_value = c.fetchone()[0] or 0
    
    c.execute('SELECT SUM(amount) FROM spending')
    total_spending = c.fetchone()[0] or 0
    
    conn.close()
    
    balance = total_income - total_commitments - total_investments - total_spending
    investment_profit_loss = total_current_value - total_investments if total_investments > 0 else 0
    
    return jsonify({
        'total_income': total_income,
        'total_commitments': total_commitments,
        'total_investments': total_investments,
        'total_current_value': total_current_value,
        'investment_profit_loss': investment_profit_loss,
        'total_spending': total_spending,
        'balance': balance
    })

if __name__ == '__main__':
    app.run(debug=True)