from eapp import app, db
from eapp.Models import Course, User, Category, ReceiptDetails, Receipt, Class, Grade
import hashlib
import cloudinary.uploader
from flask_login import current_user
from sqlalchemy import func,case
from sqlalchemy.exc import IntegrityError
from datetime import datetime


# ... (Các hàm load_categories, load_courses, auth_user... giữ nguyên như cũ) ...
def load_categories():
    return Category.query.all()


def load_courses(cate_id=None, kw=None, page=1):
    query = Course.query
    if kw:
        query = query.filter(Course.name.contains(kw))
    if cate_id:
        query = query.filter(Course.category_id == cate_id)
    if page:
        page_size = app.config['PAGE_SIZE']
        start = (page - 1) * page_size
        query = query.slice(start, start + page_size)
    return query.all()


def count_courses():
    return Course.query.count()


def get_user_by_id(id):
    return User.query.get(id)


def auth_user(username, password):
    password = str(hashlib.md5(password.strip().encode('utf-8')).hexdigest())
    return User.query.filter(User.username == username.strip(),
                             User.password == password).first()


def add_user(name, username, password, avatar, email, phone):  # <--- Thêm tham số email, phone
    password = str(hashlib.md5(password.strip().encode('utf-8')).hexdigest())

    u = User(
        name=name.strip(),
        username=username.strip(),
        password=password,
        email=email.strip(),  # <--- Lưu email
        phone=phone.strip()  # <--- Lưu sdt
    )

    if avatar:
        try:
            res = cloudinary.uploader.upload(avatar)
            u.avatar = res.get('secure_url')
        except Exception as e:
            print("Lỗi upload ảnh:", e)
            # Có thể bỏ qua hoặc gán ảnh mặc định nếu upload lỗi

    db.session.add(u)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        raise Exception('Tên đăng nhập hoặc Email đã tồn tại!')


def count_course_by_cate():
    return db.session.query(Category.id, Category.name, func.count(Course.id)) \
        .join(Course, Course.category_id == Category.id, isouter=True) \
        .group_by(Category.id).all()


# --- CÁC HÀM XỬ LÝ NGHIỆP VỤ MỚI ---

def add_receipt(cart):
    if cart:
        try:
            r = Receipt(user=current_user, is_paid=True)
            db.session.add(r)

            for c in cart.values():
                class_id = int(c['id'])
                study_class = Class.query.get(class_id)

                if not study_class:
                    continue

                # 1. Kiểm tra sĩ số (Quan trọng: Trong thực tế cần Select For Update để lock)
                if study_class.current_students >= study_class.max_students:
                    raise Exception(f"Lớp {study_class.name} đã đủ sĩ số!")

                # 2. Kiểm tra: Học viên đã học lớp này chưa? (Tránh trùng lớp)
                existing_grade = Grade.query.filter(
                    Grade.student_id == current_user.id,
                    Grade.class_id == class_id
                ).first()
                if existing_grade:
                    raise Exception(f"Bạn đã có tên trong lớp {study_class.name} rồi!")

                # 3. Kiểm tra: Học viên đã học Khóa này ở lớp khác chưa? (Tránh trùng khóa)
                joined_course = db.session.query(Grade).join(Class) \
                    .filter(Grade.student_id == current_user.id,
                            Class.course_id == study_class.course_id).first()

                if joined_course:
                    raise Exception(
                        f"Bạn đã đăng ký khóa '{study_class.course.name}' rồi (Lớp: {joined_course.study_class.name}).")

                # Thêm chi tiết hóa đơn
                d = ReceiptDetails(receipt=r, class_id=class_id, quantity=1, price=study_class.course.price)
                db.session.add(d)

                # Ghi danh vào lớp (Tạo bảng điểm rỗng)
                g = Grade(student_id=current_user.id, class_id=class_id)
                db.session.add(g)
                db.session.flush()
                from eapp.Models import GradeScore
                for col in study_class.grade_columns:
                    # Tạo điểm 0 cho từng cột (Chuyên cần, GK, CK...)
                    initial_score = GradeScore(grade_id=g.id, grade_column_id=col.id, value=0)
                    db.session.add(initial_score)

            db.session.commit()
        except Exception as ex:
            db.session.rollback()
            raise ex  # Ném lỗi ra để Controller bắt và hiển thị


# eapp/dao.py

def stats_student_count_by_course(year=None, month=None):
    query = db.session.query(Course.name, func.count(ReceiptDetails.id)) \
        .join(Class, Class.course_id == Course.id) \
        .join(ReceiptDetails, ReceiptDetails.class_id == Class.id) \
        .join(Receipt, ReceiptDetails.receipt_id == Receipt.id) \
        .filter(Receipt.is_paid == True)

    # Nếu có chọn năm, thêm điều kiện lọc năm
    if year:
        query = query.filter(func.extract('year', Receipt.created_date) == year)

    # Nếu có chọn tháng, thêm điều kiện lọc tháng
    if month:
        query = query.filter(func.extract('month', Receipt.created_date) == month)

    return query.group_by(Course.name).all()


# eapp/dao.py

# ... (Giữ nguyên các import) ...

def stats_pass_rate_by_course(year=None, month=None):
    # Logic: Join bảng Grade -> Class -> Course
    query = db.session.query(
        Course.name,
        func.count(Grade.id).label('total'),
        func.sum(case((Grade.final_average >= 5.0, 1), else_=0)).label('passed')
    ) \
        .join(Class, Grade.class_id == Class.id) \
        .join(Course, Class.course_id == Course.id)

    # Lọc theo thời gian Lớp học bắt đầu (start_date)
    if year:
        query = query.filter(func.extract('year', Class.start_date) == year)

    if month:
        query = query.filter(func.extract('month', Class.start_date) == month)

    return query.group_by(Course.name).all()


# ... (Các hàm khác giữ nguyên) ...

def stats_revenue_style_course(kw=None):
    query = db.session.query(Course.id, Course.name, func.sum(ReceiptDetails.quantity * ReceiptDetails.price)) \
        .join(Class, Class.course_id == Course.id) \
        .join(ReceiptDetails, ReceiptDetails.class_id == Class.id) \
        .join(Receipt, ReceiptDetails.receipt_id == Receipt.id) \
        .filter(Receipt.is_paid == True)

    if kw:
        query = query.filter(Course.name.contains(kw))

    return query.group_by(Course.id).all()


def stats_revenue_style_time(time='month', year=datetime.now().year):
    return db.session.query(func.extract('month', Receipt.created_date),
                            func.sum(ReceiptDetails.quantity * ReceiptDetails.price)) \
        .join(ReceiptDetails, ReceiptDetails.receipt_id == Receipt.id) \
        .filter(func.extract('year', Receipt.created_date) == year) \
        .filter(Receipt.is_paid == True) \
        .group_by(func.extract('month', Receipt.created_date)).all()
def get_revenue_years():
    # Lấy ra các năm duy nhất từ bảng Receipt
    return db.session.query(func.extract('year', Receipt.created_date))\
        .filter(Receipt.is_paid == True)\
        .group_by(func.extract('year', Receipt.created_date))\
        .order_by(func.extract('year', Receipt.created_date).desc()).all()
def stats_revenue_style_time(year=datetime.now().year):
    return db.session.query(
            func.extract('month', Receipt.created_date),
            func.sum(ReceiptDetails.quantity * ReceiptDetails.price)
        )\
        .join(ReceiptDetails, ReceiptDetails.receipt_id == Receipt.id)\
        .filter(Receipt.is_paid == True)\
        .filter(func.extract('year', Receipt.created_date) == year)\
        .group_by(func.extract('month', Receipt.created_date))\
        .order_by(func.extract('month', Receipt.created_date)).all()