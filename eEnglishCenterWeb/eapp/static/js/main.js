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
            alert(data.error);
        } else {
           giỏ hàng
            let counter = document.getElementsByClassName('cart-counter');
            for (let i = 0; i < counter.length; i++)
                counter[i].innerText = data.total_quantity;

            alert("Đã thêm lớp " + name + " vào giỏ hàng!");


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
            location.reload();
        }).catch(function(err) {
            console.error(err);
        });
    }
}

function pay() {
    let method = document.querySelector('input[name="paymentMethod"]:checked').value;

    let msg = method === 'online'
        ? "Bạn chọn chuyển khoản. Hệ thống sẽ ghi nhận ĐÃ THANH TOÁN ngay lập tức?"
        : "Bạn chọn nộp tiền tại trung tâm. Đăng ký sẽ ở trạng thái CHỜ THANH TOÁN?";

    if (confirm(msg) == true) {
        fetch('/api/pay', {
            method: 'post',
            body: JSON.stringify({
                'payment_method': method
            }),
            headers: {
                'Content-Type': 'application/json'
            }
        }).then(function(res) {
            return res.json();
        }).then(function(data) {
            if (data.status === 201) {
                alert("Đăng ký thành công! Vui lòng kiểm tra email.");
                window.location.href = "/";
            } else {
                alert("LỖI: " + data.err_msg);
            }
        }).catch(function(err) {
            console.error(err);
        });
    }
}