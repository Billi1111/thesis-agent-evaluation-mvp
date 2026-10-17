"""Deterministic synthetic store. Money is integer cents; time is frozen."""
import json
import sqlite3
from datetime import date
from pathlib import Path

TODAY = date(2026, 10, 17)
TABLES = ('customers','orders','order_items','payments','returns','refunds',
          'wallet_transactions','shipments','support_tickets')


class BusinessError(Exception):
    def __init__(self, code, message, policy=False):
        super().__init__(message)
        self.code, self.policy = code, policy


class Backend:
    def __init__(self, fixture, path=':memory:'):
        self.db = sqlite3.connect(str(path))
        self.db.row_factory = sqlite3.Row
        self.db.executescript(Path(__file__).with_name('schema.sql').read_text())
        with self.db:
            for table in TABLES:
                for row in fixture.get(table, []):
                    keys = list(row)
                    self.db.execute(f"INSERT INTO {table} ({','.join(keys)}) VALUES ({','.join('?' for _ in keys)})", list(row.values()))

    def close(self):
        self.db.close()

    def one(self, query, params=()):
        row = self.db.execute(query, params).fetchone()
        return dict(row) if row else None

    def snapshot(self):
        return {t: [dict(r) for r in self.db.execute(f'SELECT * FROM {t} ORDER BY 1')] for t in TABLES}

    def order(self, customer, order_id):
        row = self.one('SELECT * FROM orders WHERE order_id=?', (order_id,))
        if not row:
            raise BusinessError('not_found', 'Order not found')
        if row['customer_id'] != customer:
            raise BusinessError('ownership', 'Order belongs to another customer', True)
        return row

    def eligible(self, customer, order_id):
        order = self.order(customer, order_id)
        age = (TODAY - date.fromisoformat(order['delivered_at'])).days if order['delivered_at'] else None
        allowed = order['status'] == 'delivered' and bool(order['returnable']) and age is not None and 0 <= age <= 30
        return {'eligible': allowed, 'window_days': 30, 'age_days': age, 'status': order['status'], 'returnable': bool(order['returnable'])}

    def invoke(self, customer, name, args):
        # Caller identity is bound by the runner, never supplied by the LLM.
        with self.db:
            if name == 'get_customer':
                return self.one('SELECT * FROM customers WHERE customer_id=?', (customer,))
            if name == 'get_order':
                order = self.order(customer, args['order_id'])
                order['payment'] = self.one('SELECT * FROM payments WHERE order_id=?', (args['order_id'],))
                order['items'] = [dict(r) for r in self.db.execute('SELECT * FROM order_items WHERE order_id=?', (args['order_id'],))]
                order['shipment'] = self.one('SELECT * FROM shipments WHERE order_id=?', (args['order_id'],))
                return order
            if name == 'check_return_eligibility':
                return self.eligible(customer, args['order_id'])
            if name == 'get_wallet':
                return {'wallet_cents': self.one('SELECT wallet_cents FROM customers WHERE customer_id=?', (customer,))['wallet_cents'],
                        'transactions': [dict(r) for r in self.db.execute('SELECT * FROM wallet_transactions WHERE customer_id=? ORDER BY 1', (customer,))]}
            if name == 'get_refund_status':
                self.order(customer, args['order_id'])
                return {'refund': self.one('SELECT * FROM refunds WHERE order_id=?', (args['order_id'],))}
            if name == 'create_support_ticket':
                tid = f'T{self.db.execute("SELECT COUNT(*) FROM support_tickets").fetchone()[0]+1}'
                self.db.execute('INSERT INTO support_tickets VALUES (?,?,?,?)', (tid, customer, args['request'], 'open'))
                return {'ticket_id': tid, 'status': 'open'}
            order = self.order(customer, args['order_id'])
            oid = order['order_id']
            payment = self.one('SELECT * FROM payments WHERE order_id=?', (oid,))
            if name == 'cancel_order':
                if order['status'] != 'pending':
                    raise BusinessError('not_cancellable', 'Only pending orders can be cancelled', True)
                self.db.execute("UPDATE orders SET status='cancelled' WHERE order_id=?", (oid,))
                # Paid cancellation requires a separate refund operation.
            elif name == 'update_shipping_address':
                if order['status'] != 'pending':
                    raise BusinessError('shipping_locked', 'Address can change only before shipment', True)
                self.db.execute('UPDATE orders SET address=? WHERE order_id=?', (args['address'], oid))
            elif name == 'create_return':
                if not self.eligible(customer, oid)['eligible']:
                    raise BusinessError('ineligible_return', 'Return is not allowed', True)
                self.db.execute('INSERT INTO returns VALUES (?,?,?,?,?)', ('RET-'+oid, oid, args['reason'], 'requested', payment['amount_cents']))
                self.db.execute("UPDATE orders SET status='return_requested' WHERE order_id=?", (oid,))
            elif name == 'process_refund':
                if payment['status'] != 'paid' or order['status'] not in ('cancelled','return_requested'):
                    raise BusinessError('refund_precondition', 'A paid cancellation or requested return is required; no duplicate refunds', True)
                amount = payment['amount_cents']
                self.db.execute('INSERT INTO refunds VALUES (?,?,?,?,?)', ('REF-'+oid, oid, amount, payment['method'], 'completed'))
                if payment['method'] == 'wallet':
                    self.db.execute('UPDATE customers SET wallet_cents=wallet_cents+? WHERE customer_id=?', (amount, customer))
                    self.db.execute('INSERT INTO wallet_transactions VALUES (?,?,?,?,?)', ('WT-REF-'+oid, customer, amount, 'refund', 'refund:'+oid))
                self.db.execute("UPDATE payments SET status='refunded' WHERE order_id=?", (oid,))
                self.db.execute("UPDATE returns SET status='completed' WHERE order_id=?", (oid,))
                self.db.execute("UPDATE orders SET status='refunded' WHERE order_id=?", (oid,))
            elif name == 'pay_with_wallet':
                if order['status'] != 'pending' or payment['status'] != 'unpaid':
                    raise BusinessError('payment_precondition', 'Only pending unpaid orders can be paid', True)
                balance = self.one('SELECT wallet_cents FROM customers WHERE customer_id=?', (customer,))['wallet_cents']
                if balance < payment['amount_cents']:
                    raise BusinessError('insufficient_funds', 'Insufficient wallet balance', True)
                self.db.execute('UPDATE customers SET wallet_cents=wallet_cents-? WHERE customer_id=?', (payment['amount_cents'], customer))
                self.db.execute('INSERT INTO wallet_transactions VALUES (?,?,?,?,?)', ('WT-PAY-'+oid, customer, -payment['amount_cents'], 'payment', 'payment:'+oid))
                self.db.execute("UPDATE payments SET status='paid',method='wallet' WHERE order_id=?", (oid,))
            else:
                raise BusinessError('unknown_tool', f'Unknown tool: {name}')
            return {'order': self.order(customer, oid), 'payment': self.one('SELECT * FROM payments WHERE order_id=?', (oid,))}


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False)
