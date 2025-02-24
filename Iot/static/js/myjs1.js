function updateImage() {
    fetch('/processed-image')
        .then(response => response.json())
        .then(data => {
            console.log("Ảnh đã nhận diện mới nhất:", data.image_name); // Debug
            if (data.image_name !== "") {
                let imgElement = document.getElementById("latest-image");
                imgElement.src = "/uploads/" + data.image_name + "?t=" + new Date().getTime(); // Tránh cache
                document.getElementById("image-container").classList.remove("hidden");
            }
        })
        .catch(error => console.error('Lỗi khi tải ảnh đã nhận diện:', error));
}

function updateLogs() {
    fetch('/access_control')
        .then(response => response.json())
        .then(data => {
            console.log("📜 Dữ liệu logs nhận được:", data);  // Debug
            let tableBody = document.getElementById('log-table-body');
            tableBody.innerHTML = '';     // Xóa dữ liệu cũ

            data.forEach(log => {
                let row = `<tr>
                            <td>${log.id}</td>
                            <td>${log.time}</td>
                            <td>${log.people_count}</td>
                            </tr>`;
                tableBody.innerHTML += row;
            });
        })
        .catch(error => console.log('Lỗi khi tải logs: ', error));
}

// Khi chọn ảnh, hiển thị ảnh ngay lập tức trước khi tải lên
document.getElementById('uploadInput').addEventListener('change', function(event) {
    let file = event.target.files[0];
    if (file) {
        let imageUrl = URL.createObjectURL(file);
        document.getElementById('uploadedImage').src = imageUrl;
        document.getElementById('uploadedImage').style.display = 'block';
    }
});

function uploadImage() {
    let input = document.getElementById('uploadInput');
    if (input.files.length === 0) {
        alert('Vui lòng chọn ảnh!');
        return;
    }
    let file = input.files[0];
    let formData = new FormData();
    formData.append("file", file);

    fetch('/upload', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            alert('Tải ảnh thành công!');
            let imageUrl = `/uploads/${data.image_name}`; // Đường dẫn ảnh từ server
            document.getElementById('uploadedImage').src = imageUrl;
            document.getElementById('uploadedImage').style.display = 'block';
        } else {
            alert('Tải ảnh thất bại!');
        }
    })
    .catch(error => {
        console.error('Lỗi khi tải ảnh:', error);
    });
}

function resetDatabase() {
    if (confirm("Bạn có chắc chắn muốn xóa toàn bộ dữ liệu & reset ID?")) {
        fetch('/reset_database', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        })
        .then(response => response.json())
        .then(data => {
            alert(data.message);
            location.reload(); // Làm mới trang sau khi reset
        })
        .catch(error => console.error('Lỗi khi reset database:', error));
    }
}

// Cập nhật ảnh và log mỗi 5 giây
setInterval(updateImage, 5000);
setInterval(updateLogs, 5000);
