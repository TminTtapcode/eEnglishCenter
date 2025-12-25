import smtplib
from email.mime.text import MIMEText
from email.header import Header
from eapp import db
from eapp.Models import Class, Grade


def send_payment_confirmation(user_email, user_name, cart):
    """
    Hàm gửi mail xác nhận đăng ký
    """
    sender_email = "oakceniki@gmail.com"
    sender_password = "sgsl xyss mdjl jmcp"


    subject = "Xác nhận đăng ký khóa học - English Center"

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

    msg = MIMEText(body, 'plain', 'utf-8')
    msg['Subject'] = Header(subject, 'utf-8')
    msg['From'] = sender_email
    msg['To'] = user_email

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()  # Bật chế độ bảo mật
        server.login(sender_email, sender_password)

        server.send_message(msg)
        print(" Đã gửi mail thành công cho:", user_email)
    except Exception as e:
        print(" Lỗi gửi mail:", str(e))
    finally:
        server.quit()



def send_result_email(user_email, user_name, class_name, grade):

    sender_email = "oakceniki@gmail.com"
    sender_password = "sgsl xyss mdjl jmcp"

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


    new_class = Class.query.get(new_class_id)
    if not new_class: return True, "Lớp học không tồn tại"

    new_slot = new_class.time_slot
    new_days_set = set([d.strip() for d in new_slot.days.split('-') if d.strip()])
    n_start = int(new_slot.start_time)
    n_end = int(new_slot.end_time)

    busy_list = []

    if current_user_id:
        db_classes = db.session.query(Class) \
            .join(Grade) \
            .filter(Grade.student_id == current_user_id, Class.is_finished == False) \
            .all()
        for c in db_classes:
            busy_list.append({'class': c, 'source': 'Lớp đang học'})

    if cart:
        for item in cart.values():
            cart_c = Class.query.get(int(item['id']))
            if cart_c and cart_c.id != new_class.id:  # Không so sánh với chính nó
                busy_list.append({'class': cart_c, 'source': 'Lớp trong giỏ'})

    for item in busy_list:
        busy_class = item['class']
        source = item['source']

        if busy_class.course_id == new_class.course_id:
            return True, f"Xung đột: Bạn đã đăng ký khóa '{busy_class.course.name}' ở lớp '{busy_class.name}' ({source}) rồi."

        slot = busy_class.time_slot

        old_days_set = set([d.strip() for d in slot.days.split('-') if d.strip()])
        common_days = new_days_set.intersection(old_days_set)

        if not common_days:
            continue


        o_start = int(slot.start_time)
        o_end = int(slot.end_time)

        if (n_start < o_end) and (o_start < n_end):
            return True, f"Trùng lịch: Giờ học {new_slot.name} bị trùng với lớp '{busy_class.name}' ({source})."

    return False, None