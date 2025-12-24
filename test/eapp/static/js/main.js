/* 1. Hàm thêm vào giỏ hàng (Đã bỏ tham số student info) */
function addToCartSmart(id, name, price) {
    event.preventDefault();

    fetch('/api/carts', {
        method: 'post',
        body: JSON.stringify({
            "id": id,
            "name": name,
            "price": price
        }),
        headers: {
            'Content-Type': 'application/json'
        }
    }).then(function(res) {
        return res.json();
    }).then(function(data) {
        if (data.error) {
            alert(data.error); // VD: Lớp này đã có trong giỏ hàng
        } else {
            // Cập nhật icon giỏ hàng
            let counter = document.getElementsByClassName('cart-counter');
            for (let i = 0; i < counter.length; i++)
                counter[i].innerText = data.total_quantity;

            alert("Đã thêm lớp " + name + " vào giỏ hàng!");

            // Đóng Modal
            let openModal = document.querySelector('.modal.show');
            if (openModal) {
                let modalInstance = bootstrap.Modal.getInstance(openModal);
                if (modalInstance) modalInstance.hide();
            }
        }
    }).catch(function(err) {
        console.error(err);
    });
}

/* 2. Hàm xóa sản phẩm */
function deleteCart(id) {
    if (confirm("Bạn muốn xóa lớp này?") == true) {
        fetch('/api/carts/' + id, {
            method: 'delete',
            headers: {
                'Content-Type': 'application/json'
            }
        }).then(function(res) {
            return res.json();
        }).then(function(data) {
            // Reload trang để cập nhật lại bảng cho chuẩn
            location.reload();
        }).catch(function(err) {
            console.error(err);
        });
    }
}

/* 3. Hàm Thanh Toán */
function pay() {
    if (confirm("Xác nhận đăng ký các lớp học này cho TÀI KHOẢN CỦA BẠN?") == true) {
        fetch('/api/pay', {
            method: 'post',
            headers: {
                'Content-Type': 'application/json'
            }
        }).then(function(res) {
            return res.json();
        }).then(function(data) {
            if (data.status === 201) {
                alert("Đăng ký thành công! Chào mừng bạn.");
                window.location.href = "/"; // Về trang chủ
            } else {
                alert("LỖI: " + data.err_msg);
            }
        }).catch(function(err) {
            console.error(err);
            alert("Lỗi hệ thống.");
        });
    }
}