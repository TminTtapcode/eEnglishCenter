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
@app.route('/login', methods=['post'])
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


@app.route("/api/carts", methods=['post'])
def add_to_cart():
    # 1. Khởi tạo giỏ hàng
    cart = session.get('cart')
    if not cart:
        cart = {}

    # 2. Lấy dữ liệu từ Request
    data = request.json
    class_id = str(data.get('id'))
    student_name = data.get('student_name')
    student_phone = data.get('student_phone')

    # 3. Lấy thông tin lớp học từ DB để check lịch
    new_class = Class.query.get(class_id)
    if not new_class:
        return jsonify({'error': 'Lớp học không tồn tại!'}), 404

    # --- LOGIC KIỂM TRA MỚI ---

    # Check 1: Đã có trong giỏ chưa?
    if class_id in cart:
        return jsonify({'error': 'Lớp này đã có trong giỏ hàng!'}), 400

    # Check 2: Có trùng lịch với các lớp ĐANG HỌC không? (Chỉ check nếu đã đăng nhập)
    if current_user.is_authenticated:
        # Gọi hàm check_conflict từ utils.py
        is_conflict = utils.check_conflict(new_class.time_slot_id, current_user.id)
        if is_conflict:
            return jsonify({'error': f'TRÙNG LỊCH HỌC! Bạn bị vướng lịch vào khung giờ: {new_class.time_slot}'}), 400

    # --------------------------

    # 4. Thêm vào giỏ (nếu không trùng)
    cart[class_id] = {
        'id': class_id,
        'name': new_class.name,  # Lấy name chuẩn từ DB
        'price': new_class.course.price,
        'quantity': 1,
        'student_name': student_name,
        'student_phone': student_phone
    }

    session['cart'] = cart
    return jsonify(utils.stats_cart(cart))

@app.route('/api/pay',methods=['post'])
@login_required
def pay():
    try:
        dao.add_receipt(session.get('cart'))
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


@app.context_processor
def common_responeses():
    return {
        'categories': dao.load_categories(),
        'cart_stats': utils.stats_cart(session.get('cart'))
    }
if __name__ == '__main__':
    from eapp import admin
    app.run(debug=True)