import math

from flask import render_template, request, redirect,jsonify,session
from flask_login import login_user, logout_user,login_required,current_user
from eapp import app,dao,login, utils,db
from eapp.Models import Grade, Class,Course
from eapp.dao import add_user


@app.route('/')
def index():
    course = dao.load_courses(  cate_id=request.args.get('category_id'),
                                kw=request.args.get('kw'),
                                page=int(request.args.get('page',1)))
    return render_template('index.html',course=course,page=math.ceil(dao.count_courses()/app.config["PAGE_SIZE"]))
@app.route("/login")
def login_view():
    return render_template("login.html")

@app.route("/register")
def register_view():
    return render_template("register.html")
@app.route("/my-grades")
@login_required
def student_grades_view():
    grades = (db.session.query(Grade).join(Class).join(Course)
              .filter(Grade.student_id == current_user.id).all())

    return render_template("student_grades.html",grades=grades)
@app.route('/cart')
def cart_view():
    return render_template("cart.html")
@app.route('/profile')
@login_required
def profile():
    return render_template('profile.html')


@app.route('/profile/change-password', methods=['POST'])
@login_required
def change_password():
    old_pass = request.form.get('old_password')
    new_pass = request.form.get('new_password')
    confirm_pass = request.form.get('confirm_password')

    # Mã hóa mật khẩu cũ để kiểm tra
    old_pass_hash = hashlib.md5(old_pass.strip().encode('utf-8')).hexdigest()

    if old_pass_hash != current_user.password:
        return render_template('profile.html', msg="Mật khẩu hiện tại không đúng!", type="danger")

    if new_pass != confirm_pass:
        return render_template('profile.html', msg="Mật khẩu nhập lại không khớp!", type="danger")

    if len(new_pass) < 6:
        return render_template('profile.html', msg="Mật khẩu mới quá ngắn (tối thiểu 6 ký tự)!", type="warning")

    # Cập nhật mật khẩu mới
    new_pass_hash = hashlib.md5(new_pass.strip().encode('utf-8')).hexdigest()
    current_user.password = new_pass_hash
    db.session.commit()

    return render_template('profile.html', msg="Đổi mật khẩu thành công!", type="success")
@app.route('/api/carts/<id>',  methods=['put'])
def update_to_cart(id):
    cart= session.get('cart')
    if cart and id in cart:
        cart[id]["quantity"]= int(request.json.get("quantity"))
    session["cart"]=cart
    return jsonify(utils.stats_cart(cart))


from eapp.Models import Course  # Nhớ import Course


@app.route('/course/<int:course_id>')
def course_detail(course_id):
    # Lấy thông tin khóa học theo ID
    course = Course.query.get(course_id)

    if not course:
        return render_template('404.html')  # Hoặc redirect về trang chủ

    return render_template('course_detail.html', c=course)

@app.route('/api/carts/<id>',  methods=['delete'])
def delete_to_cart(id):
    cart= session.get('cart')
    if cart and id in cart:
        del cart[id]
    session["cart"]=cart
    return jsonify(utils.stats_cart(cart))


# Trong eapp/index.py

@app.route("/register", methods=["POST"])
def reginter_process():
    data = request.form
    password = data.get('password')
    confirm = data.get('confirm')

    if password != confirm:
        return render_template("register.html", err_msg="Mật khẩu không khớp!")

    try:
        # Gọi hàm add_user với đầy đủ thông tin
        dao.add_user(
            name=data.get('name'),
            username=data.get('username'),
            password=password,
            email=data.get('email'),  # <--- Lấy email từ form
            phone=data.get('phone'),  # <--- Lấy sdt từ form
            avatar=request.files.get('avatar')
        )
        return redirect("/login")
    except Exception as e:
        return render_template("register.html", err_msg=str(e))

@app.route("/logout")
def logout_process():
    logout_user()
    return redirect("/login")

# Trong eapp/index.py

@app.route('/login', methods=['post'])
def login_process():
    username = request.form.get('username')
    password = request.form.get('password')

    # Kiểm tra thông tin
    user = dao.auth_user(username=username, password=password)

    if user:
        # 1. Đăng nhập thành công
        login_user(user=user)

        # Chuyển hướng về trang trước đó hoặc trang chủ
        next_page = request.args.get("next")
        return redirect(next_page if next_page else '/')
    else:
        # 2. Đăng nhập thất bại
        # - Không redirect, mà render lại trang login
        # - Truyền kèm thông báo lỗi (err_msg)
        # - Truyền lại username để điền vào ô input
        return render_template('login.html',
                               err_msg='Tên đăng nhập hoặc mật khẩu không chính xác!',
                               username=username)  # Giữ lại username cũ
@login.user_loader
def load_user(id):
    return dao.get_user_by_id(id)


# eapp/index.py

# eapp/index.py

@app.route("/api/carts", methods=['post'])
def add_to_cart():
    # 1. Khởi tạo giỏ hàng
    cart = session.get('cart')
    if not cart:
        cart = {}

    # 2. Lấy dữ liệu
    data = request.json
    class_id = str(data.get('id'))
    student_name = data.get('student_name')

    # 3. Lấy thông tin lớp
    new_class = Class.query.get(class_id)
    if not new_class:
        return jsonify({'error': 'Lớp học không tồn tại!'}), 404

    # Check 1: Đã có chính lớp này trong giỏ chưa?
    if class_id in cart:
        return jsonify({'error': 'Lớp này đã có trong giỏ hàng rồi!'}), 400

    # --- LOGIC KIỂM TRA MỚI (Đã sửa) ---
    user_id = current_user.id if current_user.is_authenticated else None

    # Truyền new_class.id thay vì time_slot_id
    is_conflict, msg = utils.check_conflict(new_class.id, user_id, cart)

    if is_conflict:
        return jsonify({'error': msg}), 400
        # -----------------------------------

    # 4. Thêm vào giỏ (Thành công)
    cart[class_id] = {
        'id': class_id,
        'name': new_class.name,
        'price': new_class.course.price,
        'quantity': 1,
        'student_name': student_name,
        'schedule': new_class.schedule  # <--- THÊM DÒNG NÀY (Lưu lịch học vào session)
    }

    session['cart'] = cart
    return jsonify(utils.stats_cart(cart))

@app.route('/api/pay',methods=['post'])
@login_required
def pay():
    try:
        data = request.json
        method = data.get('payment_method', 'online')  # Mặc định là online nếu không có
        dao.add_receipt(session.get('cart'), payment_method=method)
        current_cart = session.get('cart')
        if current_cart:
            utils.send_payment_confirmation(
                user_email=current_user.email,  # Email người nhận (Học viên)
                user_name=current_user.name,  # Tên học viên
                cart=current_cart  # Danh sách lớp học
            )
    except Exception as ex:
        print(ex)  # In lỗi ra terminal để debug
        return jsonify({"status": 500, 'err_msg': str(ex)})
    else:
        del session['cart']
        return jsonify({'status':201})


# eapp/index.py

@app.route('/api/cancel-receipt/<int:receipt_id>', methods=['POST'])
@login_required
def cancel_receipt(receipt_id):
    from eapp.Models import Receipt, ReceiptDetails, Grade

    # 1. Tìm hóa đơn
    r = Receipt.query.get(receipt_id)

    # 2. Kiểm tra quyền sở hữu (Phải đúng là hóa đơn của user đang đăng nhập)
    if not r or r.user_id != current_user.id:
        return jsonify({'status': 403, 'msg': 'Bạn không có quyền truy cập hóa đơn này!'})

    # 3. CHỐT CHẶN QUAN TRỌNG: Đã thanh toán thì KHÔNG ĐƯỢC HỦY
    if r.is_paid:
        return jsonify({'status': 400, 'msg': 'Hóa đơn đã thanh toán. Không thể hủy!'})

    try:
        # 4. Logic Xóa: Xóa bảng điểm (Grade) trước để nhả chỗ trong lớp
        # (Vì Receipt xóa sẽ kéo theo ReceiptDetails xóa, nhưng Grade thì không tự mất)
        details = ReceiptDetails.query.filter_by(receipt_id=r.id).all()
        for d in details:
            g = Grade.query.filter_by(student_id=current_user.id, class_id=d.class_id).first()
            if g:
                db.session.delete(g)

        # 5. Xóa hóa đơn
        db.session.delete(r)
        db.session.commit()

        return jsonify({'status': 200, 'msg': 'Đã hủy đăng ký thành công!'})

    except Exception as ex:
        db.session.rollback()
        return jsonify({'status': 500, 'msg': str(ex)})


# eapp/index.py

@app.route('/my-registrations')
@login_required
def my_registrations():
    # Lấy danh sách hóa đơn của user, sắp xếp mới nhất lên đầu
    from eapp.Models import Receipt
    receipts = Receipt.query.filter_by(user_id=current_user.id) \
        .order_by(Receipt.created_date.desc()).all()

    return render_template('my_registrations.html', receipts=receipts)
@app.context_processor
def common_responeses():
    return {
        'categories': dao.load_categories(),
        'cart_stats': utils.stats_cart(session.get('cart'))
    }
if __name__ == '__main__':
    from eapp import admin
    app.run(debug=True)