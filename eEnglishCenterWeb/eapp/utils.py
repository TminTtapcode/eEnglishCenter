import smtplib
from email.mime.text import MIMEText
from email.header import Header


# ... (Giữ nguyên hàm stats_cart cũ) ...

def send_payment_confirmation(user_email, user_name, cart):
    """
    Hàm gửi mail xác nhận đăng ký
    """
    # 1. CẤU HÌNH EMAIL CỦA BẠN
    sender_email = "oakceniki@gmail.com"  # <--- Thay email của bạn vào đây
    sender_password = "sgsl xyss mdjl jmcp"  # <--- Dán 16 ký tự App Password vào đây

    # 2. Tạo nội dung Email
    subject = "Xác nhận đăng ký khóa học - English Center"

    # Tạo danh sách các lớp đã đăng ký
    course_list_str = ""
    total_money = 0
    if cart:
        for c in cart.values():
            price = "{:,.0f}".format(c['price'])
            course_list_str += f"- Lớp: {c['name']} | Học phí: {price} VNĐ\n"
            total_money += c['price'] * c['quantity']

    body = f"""
    Xin chào {user_name},

    Cảm ơn bạn đã đăng ký khóa học tại English Center.
    Dưới đây là thông tin đăng ký của bạn:

    {course_list_str}
    --------------------------------------
    TỔNG CỘNG: {"{:,.0f}".format(total_money)} VNĐ

    Vui lòng đến trung tâm để nhận lịch học chi tiết.
    Trân trọng,
    English Center Team.
    """

    # 3. Thiết lập Email
    msg = MIMEText(body, 'plain', 'utf-8')
    msg['Subject'] = Header(subject, 'utf-8')
    msg['From'] = sender_email
    msg['To'] = user_email

    # 4. Gửi Mail (Sử dụng Gmail SMTP)
    try:
        # Kết nối tới server Gmail
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()  # Bật chế độ bảo mật
        server.login(sender_email, sender_password)

        # Gửi
        server.send_message(msg)
        print("✅ Đã gửi mail thành công cho:", user_email)
    except Exception as e:
        print(" Lỗi gửi mail:", str(e))
    finally:
        server.quit()


# Trong eapp/utils.py

def send_result_email(user_email, user_name, class_name, grade):
    """
    Gửi bảng điểm cuối khóa
    grade: Object Grade (chứa điểm thi)
    """
    sender_email = "email_cua_ban@gmail.com"  # <--- Thay email của bạn
    sender_password = "mat_khau_ung_dung"  # <--- Thay app password

    subject = f"KẾT QUẢ HỌC TẬP - Lớp {class_name}"

    status_color = "green" if grade.result == "Đạt" else "red"

    body = f"""
    Xin chào {user_name},

    Khóa học {class_name} đã chính thức khép lại.
    Dưới đây là bảng điểm chi tiết của bạn:

    --------------------------------------------------
    - Điểm chuyên cần: {grade.attendance}
    - Điểm giữa kỳ:    {grade.mid_term}
    - Điểm cuối kỳ:    {grade.final_term}
    --------------------------------------------------
    => ĐIỂM TRUNG BÌNH: {grade.average}
    => KẾT QUẢ: {grade.result}
    --------------------------------------------------

    {"Chúc mừng bạn đã hoàn thành khóa học!" if grade.result == "Đạt" else "Rất tiếc, bạn chưa đạt yêu cầu của khóa học này."}

    Trân trọng,
    English Center Team.
    """

    msg = MIMEText(body, 'plain', 'utf-8')
    msg['Subject'] = Header(subject, 'utf-8')
    msg['From'] = sender_email
    msg['To'] = user_email

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(sender_email, sender_password)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        print(f"Lỗi gửi mail cho {user_email}: {str(e)}")
        return False


def stats_cart(cart):
    total_quantity,total_amount=0,0

    if cart:
        for c in cart.values():
            total_quantity+=c['quantity']
            total_amount+=c['quantity']*c['price']
    return{
        "total_quantity":total_quantity,
        "total_amount":total_amount
    }


# eapp/utils.py

# eapp/utils.py

# eapp/utils.py

# eapp/utils.py
import smtplib
from email.mime.text import MIMEText
from email.header import Header


# ... (Các hàm gửi mail giữ nguyên) ...

def stats_cart(cart):
    total_quantity, total_amount = 0, 0
    if cart:
        for c in cart.values():
            total_quantity += c['quantity']
            total_amount += c['quantity'] * c['price']
    return {
        "total_quantity": total_quantity,
        "total_amount": total_amount
    }


def check_conflict(new_class_id, current_user_id, cart=None):
    """
    Kiểm tra xung đột toàn diện:
    1. Trùng Môn (Đã học môn này rồi -> Không đăng ký lại lớp khác cùng môn).
    2. Trùng Lịch (Trùng ngày giờ với lớp đang học hoặc lớp trong giỏ).
    """
    from eapp import db
    from eapp.Models import TimeSlot, Class, Grade

    # 1. Lấy thông tin Lớp mới và Ca học mới
    new_class = Class.query.get(new_class_id)
    if not new_class: return True, "Lớp học không tồn tại"

    new_slot = new_class.time_slot
    new_days_set = set([d.strip() for d in new_slot.days.split('-') if d.strip()])
    n_start = int(new_slot.start_time)
    n_end = int(new_slot.end_time)

    # Danh sách các lớp cần kiểm tra (Gồm lớp trong DB và lớp trong Cart)
    busy_list = []

    # A. Lấy từ Database (Các lớp ĐANG HỌC)
    if current_user_id:
        db_classes = db.session.query(Class) \
            .join(Grade) \
            .filter(Grade.student_id == current_user_id, Class.is_finished == False) \
            .all()
        for c in db_classes:
            busy_list.append({'class': c, 'source': 'Lớp đang học'})

    # B. Lấy từ Giỏ hàng (Các lớp ĐANG CHỌN)
    if cart:
        for item in cart.values():
            # item['id'] là ID của lớp
            cart_c = Class.query.get(int(item['id']))
            if cart_c and cart_c.id != new_class.id:  # Không so sánh với chính nó
                busy_list.append({'class': cart_c, 'source': 'Lớp trong giỏ'})

    # --- BẮT ĐẦU KIỂM TRA ---
    for item in busy_list:
        busy_class = item['class']
        source = item['source']

        # 1. KIỂM TRA TRÙNG KHÓA HỌC (Cùng Course ID)
        if busy_class.course_id == new_class.course_id:
            return True, f"Xung đột: Bạn đã đăng ký khóa '{busy_class.course.name}' ở lớp '{busy_class.name}' ({source}) rồi."

        # 2. KIỂM TRA TRÙNG LỊCH HỌC
        slot = busy_class.time_slot

        # a. Check trùng ngày
        old_days_set = set([d.strip() for d in slot.days.split('-') if d.strip()])
        common_days = new_days_set.intersection(old_days_set)

        if not common_days:
            continue  # Không trùng ngày -> Bỏ qua check giờ

        # b. Check trùng giờ (Giao nhau)
        o_start = int(slot.start_time)
        o_end = int(slot.end_time)

        # Công thức giao nhau: (Start A < End B) AND (Start B < End A)
        if (n_start < o_end) and (o_start < n_end):
            return True, f"Trùng lịch: Giờ học {new_slot.name} bị trùng với lớp '{busy_class.name}' ({source})."

    return False, None