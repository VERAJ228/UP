from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from decimal import Decimal
from flask_migrate import Migrate
from datetime import datetime
import pandas as pd
from flask import Response
from flask import jsonify
from flask import request, redirect, url_for
import qrcode
from io import BytesIO
from sqlalchemy import func
import base64

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:Piesos228@localhost/Uchebnaya_praktika'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
migrate = Migrate(app, db)

# Модели для базы данных
class Employee(db.Model):
    __tablename__ = 'employees'
    employee_id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(255), nullable=False)
    position = db.Column(db.String(255), nullable=False)
    store_id = db.Column(db.Integer, db.ForeignKey('stores.store_id'), nullable=False)
    store = db.relationship('Store', backref='employees')

class Product(db.Model):
    __tablename__ = 'products'
    product_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    brand = db.Column(db.String(255))
    category = db.Column(db.String(255))
    price = db.Column(db.Numeric(10, 2), nullable=False)
    purchase_price = db.Column(db.Numeric(10, 2), nullable=True)
    stock_quantity = db.Column(db.Integer, nullable=False)
    image = db.Column(db.LargeBinary)

    sale_items = db.relationship('SaleItem', backref='product_ref', lazy=True)

class Store(db.Model):
    __tablename__ = 'stores'
    store_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    address = db.Column(db.String(255), nullable=False)

class Sale(db.Model):
    __tablename__ = 'sales'
    sale_id = db.Column(db.Integer, primary_key=True)
    sale_date = db.Column(db.DateTime, default=db.func.current_timestamp())
    total = db.Column(db.Numeric(10, 2), nullable=False)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.employee_id'), nullable=False)
    store_id = db.Column(db.Integer, db.ForeignKey('stores.store_id'), nullable=False)
    employee = db.relationship('Employee', backref='sales')
    store = db.relationship('Store', backref='sales')

    sale_items = db.relationship('SaleItem', backref='sale_rel', lazy=True)

class SaleItem(db.Model):
    __tablename__ = 'sale_items'
    sale_item_id = db.Column(db.Integer, primary_key=True)
    sale_id = db.Column(db.Integer, db.ForeignKey('sales.sale_id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.product_id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Numeric(10, 2), nullable=False)

    # Убираем конфликтующие backref
    sale = db.relationship('Sale', backref='sale_items_rel')
    product = db.relationship('Product', backref='product_ref')

class Order(db.Model):
    __tablename__ = 'orders'
    order_id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.customer_id'), nullable=False)
    total = db.Column(db.Numeric(10, 2), nullable=False)
    order_date = db.Column(db.DateTime, default=db.func.current_timestamp())
    customer = db.relationship('Customer', backref=db.backref('orders', lazy=True))

class OrderItem(db.Model):
    __tablename__ = 'order_items'
    order_item_id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.order_id'))
    product_id = db.Column(db.Integer, db.ForeignKey('products.product_id'))
    quantity = db.Column(db.Integer)
    order = db.relationship('Order', backref='order_items')
    product = db.relationship('Product', backref='order_items')

class InventoryCheck(db.Model):
    __tablename__ = 'inventory_checks'
    check_id = db.Column(db.Integer, primary_key=True)
    store_id = db.Column(db.Integer, db.ForeignKey('stores.store_id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.product_id'), nullable=False)
    accounted_quantity = db.Column(db.Integer, nullable=False)
    actual_quantity = db.Column(db.Integer, nullable=False)
    difference = db.Column(db.Integer)
    check_date = db.Column(db.DateTime, default=db.func.current_timestamp())
    store = db.relationship('Store', backref='inventory_checks')
    product = db.relationship('Product', backref='inventory_checks')

class InventoryMovement(db.Model):
    __tablename__ = 'inventory_movements'
    movement_id = db.Column(db.Integer, primary_key=True)
    from_store_id = db.Column(db.Integer, db.ForeignKey('stores.store_id'), nullable=False)  # Магазин-отправитель
    to_store_id = db.Column(db.Integer, db.ForeignKey('stores.store_id'), nullable=False)  # Магазин-получатель
    product_id = db.Column(db.Integer, db.ForeignKey('products.product_id'), nullable=False)
    movement_date = db.Column(db.DateTime, default=db.func.current_timestamp())
    from_store = db.relationship('Store', foreign_keys=[from_store_id])
    to_store = db.relationship('Store', foreign_keys=[to_store_id])
    product = db.relationship('Product', backref='inventory_movements')

class InventoryRestock(db.Model):
    __tablename__ = 'inventory_restock'
    restock_id = db.Column(db.Integer, primary_key=True)
    store_id = db.Column(db.Integer, db.ForeignKey('stores.store_id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.product_id'), nullable=False)
    min_quantity = db.Column(db.Integer, nullable=False)
    max_quantity = db.Column(db.Integer, nullable=False)
    current_quantity = db.Column(db.Integer, nullable=False)
    store = db.relationship('Store', backref=db.backref('restock', lazy=True))
    product = db.relationship('Product', backref=db.backref('restock', lazy=True))

class Discount(db.Model):
    __tablename__ = 'discounts'
    discount_id = db.Column(db.Integer, primary_key=True)
    min_purchase = db.Column(db.Numeric(10, 2), nullable=False)
    discount_percentage = db.Column(db.Numeric(5, 2), nullable=False)

    def __repr__(self):
        return f"<Discount(min_purchase={self.min_purchase}, discount_percentage={self.discount_percentage})>"

class Customer(db.Model):
    __tablename__ = 'customers'
    customer_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    contact_info = db.Column(db.String(255))

@app.route('/')
def index():
    products = Product.query.all()
    return render_template('index.html', products=products)

@app.route('/add_product', methods=['GET', 'POST'])
def add_product():
    if request.method == 'POST':
        name = request.form['name']
        brand = request.form['brand']
        category = request.form['category']
        price = request.form['price']
        purchase_price = request.form.get('purchase_price', 0.0)
        stock_quantity = request.form['stock_quantity']
        image = request.files['image'].read()

        new_product = Product(
            name=name,
            brand=brand,
            category=category,
            price=price,
            purchase_price=purchase_price,
            stock_quantity=stock_quantity,
            image=image
        )

        db.session.add(new_product)
        db.session.commit()
        return redirect(url_for('index'))
    return render_template('add_product.html')

@app.route('/sell_product', methods=['GET', 'POST'])
def sell_product():
    if request.method == 'POST':
        product_ids = request.form.getlist('product_id')
        quantities = request.form.getlist('quantity')
        customer_id = request.form['customer_id']
        sale_total = Decimal(0)
        sale_items = []
        customer = Customer.query.get(customer_id)
        total_purchase = sum([item.total for item in customer.purchases])

        discount = Discount.query.filter(Discount.min_purchase <= total_purchase).order_by(
            Discount.min_purchase.desc()).first()

        discount_percentage = discount.discount_percentage if discount else 0
        discount_amount = (sale_total * discount_percentage) / 100 if discount else 0
        sale_total -= discount_amount

        new_sale = Sale(total=sale_total, employee_id=1, store_id=1)
        db.session.add(new_sale)
        db.session.commit()

        for product_id, quantity in zip(product_ids, quantities):
            product = Product.query.get(product_id)
            product_quantity = int(quantity)

            item_total = product.price * product_quantity
            sale_total += item_total

            sale_item = SaleItem(sale_id=new_sale.sale_id, product_id=product_id,
                                 quantity=product_quantity, price=product.price)
            db.session.add(sale_item)
            product.stock_quantity -= product_quantity

        new_sale.total = sale_total
        db.session.commit()

        print(f"Sale ID: {new_sale.sale_id}, Total: {sale_total}")

        return redirect(url_for('index'))

    products = Product.query.all()
    return render_template('sell_product.html', products=products)

@app.route('/sales_report', methods=['GET', 'POST'])
def sales_report():
    if request.method == 'POST':
        start_date = request.form['start_date']
        end_date = request.form['end_date']
        start_date = datetime.strptime(start_date, '%Y-%m-%d')
        end_date = datetime.strptime(end_date, '%Y-%m-%d')
        sales = Sale.query.filter(Sale.sale_date >= start_date, Sale.sale_date <= end_date).all()
        return render_template('sales_report.html', sales=sales)
    return render_template('sales_report.html', sales=[])

@app.route('/edit_product/<int:product_id>', methods=['GET', 'POST'])
def edit_product(product_id):
    product = Product.query.get_or_404(product_id)
    if request.method == 'POST':
        product.name = request.form['name']
        product.brand = request.form['brand']
        product.category = request.form['category']
        product.price = request.form['price']
        product.purchase_price = request.form['purchase_price']
        product.stock_quantity = request.form['stock_quantity']
        if 'image' in request.files:
            product.image = request.files['image'].read()
        db.session.commit()
        return redirect(url_for('index'))  # Перенаправление на главную страницу
    return render_template('edit_product.html', product=product)

@app.route('/search_product', methods=['GET', 'POST'])
def search_product():
    if request.method == 'POST':
        search_term = request.form['search_term']
        products = Product.query.filter(Product.name.ilike(f'%{search_term}%')).all()
        return render_template('index.html', products=products)

    return render_template('search_product.html')

@app.route('/delete_product/<int:product_id>', methods=['GET'])
def delete_product(product_id):
    product = Product.query.get_or_404(product_id)
    db.session.delete(product)
    db.session.commit()
    return redirect(url_for('index'))

@app.route('/inventory_check', methods=['GET', 'POST'])
def inventory_check():
    if request.method == 'POST':
        store_id = request.form['store_id']
        product_id = request.form['product_id']
        accounted_quantity = int(request.form['accounted_quantity'])
        actual_quantity = int(request.form['actual_quantity'])
        difference = actual_quantity - accounted_quantity
        inventory_check = InventoryCheck(
            store_id=store_id,
            product_id=product_id,
            accounted_quantity=accounted_quantity,
            actual_quantity=actual_quantity,
            difference=difference
        )
        product = Product.query.get(product_id)
        product.stock_quantity = actual_quantity
        db.session.add(inventory_check)
        db.session.commit()
        return redirect(url_for('index'))
    stores = Store.query.all()
    products = Product.query.all()
    return render_template('inventory_check.html', stores=stores, products=products)

@app.route('/stock_report')
def stock_report():
    products = Product.query.all()
    stores = Store.query.all()
    return render_template('stock_report.html', products=products, stores=stores)

@app.route('/movement_report')
def movement_report():
    movements = InventoryMovement.query.all()  # Get all inventory movements
    return render_template('movement_report.html', movements=movements)

@app.route('/popular_products', methods=['GET', 'POST'])
def popular_products():
    if request.method == 'POST':
        start_date = request.form['start_date']
        end_date = request.form['end_date']

        # Преобразуем строки в datetime
        start_date = datetime.strptime(start_date, '%Y-%m-%d')
        end_date = datetime.strptime(end_date, '%Y-%m-%d')

        # Получаем все продажи в указанном периоде
        sales = db.session.query(
            Product.name,
            db.func.sum(SaleItem.quantity).label('total_quantity'),
            db.func.sum(SaleItem.quantity * SaleItem.price).label('total_sales')
        ).join(SaleItem).join(Sale).filter(Sale.sale_date >= start_date, Sale.sale_date <= end_date).group_by(Product.name).order_by(db.desc('total_quantity')).limit(10).all()

        return render_template('popular_products.html', popular_products=sales)

    return render_template('popular_products.html', popular_products=[])

@app.route('/sales_comparison', methods=['GET', 'POST'])
def sales_comparison():
    if request.method == 'POST':
        start_date_1 = request.form['start_date_1']
        end_date_1 = request.form['end_date_1']
        start_date_2 = request.form['start_date_2']
        end_date_2 = request.form['end_date_2']
        start_date_1 = datetime.strptime(start_date_1, '%Y-%m-%d')
        end_date_1 = datetime.strptime(end_date_1, '%Y-%m-%d')
        start_date_2 = datetime.strptime(start_date_2, '%Y-%m-%d')
        end_date_2 = datetime.strptime(end_date_2, '%Y-%m-%d')
        sales_period_1 = db.session.query(
            Product.name,
            db.func.sum(SaleItem.quantity).label('sales_period_1')
        ).join(SaleItem).join(Sale).filter(Sale.sale_date >= start_date_1, Sale.sale_date <= end_date_1).group_by(Product.name).all()
        sales_period_2 = db.session.query(
            Product.name,
            db.func.sum(SaleItem.quantity).label('sales_period_2')
        ).join(SaleItem).join(Sale).filter(Sale.sale_date >= start_date_2, Sale.sale_date <= end_date_2).group_by(Product.name).all()
        comparison = []
        for product_1 in sales_period_1:
            for product_2 in sales_period_2:
                if product_1.name == product_2.name:
                    change = product_2.sales_period_2 - product_1.sales_period_1
                    comparison.append({
                        'product_name': product_1.name,
                        'sales_period_1': product_1.sales_period_1,
                        'sales_period_2': product_2.sales_period_2,
                        'change': change
                    })
        return render_template('sales_comparison.html', comparisons=comparison)
    return render_template('sales_comparison.html', comparisons=[])

@app.route('/add_discount', methods=['GET', 'POST'])
def add_discount():
    if request.method == 'POST':
        min_purchase = request.form['min_purchase']
        discount_percentage = request.form['discount_percentage']
        new_discount = Discount(min_purchase=min_purchase, discount_percentage=discount_percentage)
        db.session.add(new_discount)
        db.session.commit()
        return redirect(url_for('index'))  # Перенаправление на главную страницу
    return render_template('add_discount.html')

@app.route('/import_price_list', methods=['GET', 'POST'])
def import_price_list():
    if request.method == 'POST':
        file = request.files['price_list']  # Получаем файл
        if file and file.filename.endswith('.csv'):
            df = pd.read_csv(file)
            for index, row in df.iterrows():
                # Проверяем, существует ли товар с таким именем
                product = Product.query.filter_by(name=row['name']).first()
                if not product:
                    # Если товар не найден, добавляем новый товар
                    product = Product(
                        name=row['name'],
                        brand=row['brand'],
                        category=row['category'],
                        price=row['price'],
                        stock_quantity=row['stock_quantity']
                    )
                    db.session.add(product)
            db.session.commit()
            return redirect(url_for('index'))  # Перенаправление на главную страницу
    return render_template('import_price_list.html')

@app.route('/export_products')
def export_products():
    products = Product.query.all()
    def generate():
        yield 'Product Code, Name, Price, Stock Quantity\n'
        for product in products:
            yield f'{product.product_id}, {product.name}, {product.price}, {product.stock_quantity}\n'
    return Response(generate(), mimetype='text/csv', headers={"Content-Disposition": "attachment;filename=products.csv"})

@app.route('/api/products', methods=['GET'])
def get_products():
    products = Product.query.all()
    product_list = [{"product_id": product.product_id, "name": product.name, "price": product.price, "stock_quantity": product.stock_quantity} for product in products]
    return jsonify(product_list)

@app.route('/products')
def products():
    page = request.args.get('page', 1, type=int)
    products = Product.query.paginate(page, 10, False)
    return render_template('products.html', products=products)

@app.route('/edit_order/<int:order_id>', methods=['GET', 'POST'])
def edit_order(order_id):
    order = Order.query.get_or_404(order_id)
    if request.method == 'POST':
        order.order_status = request.form['status']
        for item in order.order_items:
            quantity_key = f"quantity_{item.product_id}"
            if quantity_key in request.form:
                new_quantity = int(request.form[quantity_key])
                item.quantity = new_quantity
                db.session.commit()
        flash('Order updated successfully!')
        return redirect(url_for('index'))
    return render_template('edit_order.html', order=order)

@app.route('/export_products_csv')
def export_products_csv():
    products = Product.query.all()  # Получаем все товары из базы данных
    data = []
    for product in products:
        data.append({
            'name': product.name,
            'brand': product.brand,
            'category': product.category,
            'price': product.price,
            'stock_quantity': product.stock_quantity
        })
    df = pd.DataFrame(data)
    output = df.to_csv(index=False)

    return Response(
        output,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment;filename=products.csv"}
    )

@app.route('/api/products', methods=['GET'])
def api_products():
    products = Product.query.all()
    products_list = []
    for product in products:
        products_list.append({
            'product_id': product.product_id,
            'name': product.name,
            'brand': product.brand,
            'category': product.category,
            'price': str(product.price),
            'stock_quantity': product.stock_quantity
        })
    return jsonify(products_list)

@app.route('/api/stock', methods=['GET'])
def api_stock():
    stores = Store.query.all()  # Получаем все магазины
    stock_data = []
    for store in stores:
        store_data = {
            'store_id': store.store_id,
            'store_name': store.name,
            'stock': []
        }
        for product in Product.query.all():  # Для каждого товара
            stock_data.append({
                'product_name': product.name,
                'store_name': store.name,
                'quantity': product.stock_quantity
            })
    return jsonify(stock_data)

@app.route('/api/create_order', methods=['POST'])
def api_create_order():
    order_data = request.get_json()  # Получаем данные заказа в формате JSON

    customer = Customer.query.get(order_data['customer_id'])
    if not customer:
        return jsonify({"error": "Customer not found"}), 404

    new_order = Order(customer_id=order_data['customer_id'], total=0)  # Создаем новый заказ
    db.session.add(new_order)
    db.session.commit()

    total_price = 0
    for item in order_data['items']:
        product = Product.query.get(item['product_id'])
        if not product:
            return jsonify({"error": f"Product {item['product_id']} not found"}), 404

        item_total = product.price * item['quantity']
        total_price += item_total

        # Добавляем товары в заказ
        order_item = OrderItem(order_id=new_order.order_id, product_id=product.product_id,
                               quantity=item['quantity'], price=product.price)
        db.session.add(order_item)
        product.stock_quantity -= item['quantity']  # Обновляем количество товара на складе

    # Обновляем общую сумму заказа
    new_order.total = total_price
    db.session.commit()

    return jsonify({"message": "Order created successfully", "order_id": new_order.order_id}), 201

@app.route('/generate_labels')
def generate_labels():
    products = Product.query.all()
    labels = []
    for product in products:
        qr_code = generate_qr_code(product.product_id)
        labels.append({
            'product_name': product.name,
            'product_price': product.price,
            'qr_code': qr_code
        })
    return render_template('labels.html', labels=labels)

@app.route('/restock_inventory', methods=['GET', 'POST'])
def restock_inventory():
    if request.method == 'POST':
        product_id = request.form['product_id']
        quantity = request.form['quantity']
        product = Product.query.get(product_id)
        product.stock_quantity += int(quantity)
        db.session.commit()
        return redirect(url_for('index'))
    products = Product.query.all()
    return render_template('restock_inventory.html', products=products)

@app.route('/max_profit_products', methods=['GET', 'POST'])
def max_profit_products():
    if request.method == 'POST':
        start_date = request.form['start_date']
        end_date = request.form['end_date']
        start_date = datetime.strptime(start_date, '%Y-%m-%d')
        end_date = datetime.strptime(end_date, '%Y-%m-%d')
        products_profit = db.session.query(
            Product.name,
            func.sum(SaleItem.quantity).label('total_quantity'),
            func.sum((SaleItem.quantity * (Product.price - Product.purchase_price))).label('total_profit')
        ).join(SaleItem).join(Sale).filter(Sale.sale_date >= start_date, Sale.sale_date <= end_date).group_by(Product.name).order_by(func.sum(SaleItem.quantity * (Product.price - Product.purchase_price)).desc()).limit(10).all()

        return render_template('max_profit_products.html', products_profit=products_profit)

    return render_template('max_profit_products.html', products_profit=[])

# Функция для генерации QR-кода товара
def generate_qr_code(product_id):
    qr_data = f'Product ID: {product_id}'
    qr = qrcode.make(qr_data)

    img = BytesIO()
    qr.save(img, 'PNG')
    img.seek(0)

    # Конвертируем в base64 для передачи в шаблон
    img_base64 = base64.b64encode(img.getvalue()).decode('utf-8')
    return img_base64

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
