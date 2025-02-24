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
                let row = document.createElement("tr");
                row.innerHTML = `
                    <td>${log.id}</td>
                    <td>${log.time}</td>
                    <td>${log.people_count}</td>
                    <td><img src="/uploads/${log.image_name}" class="thumbnail" onclick="showImage('/uploads/${log.image_name}')"></td>
                    `;
                //tableBody.innerHTML += row;
                tableBody.appendChild(row);
            });
        })
        .catch(error => console.log('Lỗi khi tải logs: ', error));
}

// 🔥 Hàm hiển thị ảnh lớn khi click vào ảnh thu nhỏ
function showImage(imageSrc) {
    let modal = document.getElementById("imageModal");
    let modalImg = document.getElementById("fullImage");

    modal.style.display = "block";
    modalImg.src = imageSrc + "?t=" + new Date().getTime(); // Tránh cache

    let closeBtn = document.querySelector(".close");
    closeBtn.onclick = function () {
        modal.style.display = "none";
    };
    modal.onclick = function () {
        modal.style.display = "none";
    };
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
            document.getElementById('uploadedImage').src = `/uploads/${data.image_name}`; // Đường dẫn ảnh từ server
            document.getElementById('uploadedImage').style.display = 'block';
            updateImage();
            updateLogs(); // Cập nhật lại logs ngay lập tức
        } else {
            alert('Tải ảnh thất bại!');
        }
    })
    .catch(error => {
        console.error('Lỗi khi tải ảnh:', error);
    });
}

// Cập nhật dữ liệu biểu đồ mật độ từ database
function updateChart() {
    fetch('/density-hourly')
        .then(response => response.json())
        .then(data => {
            if (!data || data.length === 0) {
                console.log("Không có dữ liệu để vẽ biểu đồ.");
                return;
            }
            console.log("📊 Dữ liệu mật độ theo giờ:", data);

            // Tạo trục X với 24 giờ (00:00 - 23:00)
            let labels = [];
            let values = new Array(24).fill(0);  // Mặc định tất cả giờ có giá trị 0
            for (let i = 0; i < 24; i++) {
                let hour = i.toString().padStart(2, '0') + ":00"; // Định dạng HH:00
                labels.push(hour);
            }
            // Cập nhật dữ liệu từ server vào mảng values
            data.forEach(entry => {
                let hourIndex = parseInt(entry.hour); // Lấy giờ (0-23)
                values[hourIndex] = entry.people_count; // Gán số lượng người vào đúng giờ
            });
            densityChart.data.labels = labels;
            densityChart.data.datasets[0].data = values;
            densityChart.update();      // Cập nhật biểu đồ
        })
        .catch(error => console.error('❌ Lỗi khi lấy dữ liệu biểu đồ:', error));
}

// Khởi tạo biểu đồ Chart.js
let ctx = document.getElementById('densityChart').getContext('2d');
let densityChart = new Chart(ctx, {
    type: 'bar',   // Kiểu biểu đồ cột
    data: {
        labels: [],     // Ban đầu chưa có dữ liệu
        datasets: [{
            label: 'Mật độ người',
            data: [],
            borderColor: 'blue',
            backgroundColor: 'rgba(54, 162, 235, 0.5)',  // Màu xanh
            borderWidth: 1
        }]
    },
    options: {
        responsive: true,
        scales: {
            x: { title: { display: true, text: 'Thời gian' }},
            y: { title: { display: true, text: 'Số người' }, beginAtZero: true }
        }
    }
});

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
// Cập nhật biểu đồ mỗi 5 giây
setInterval(updateChart, 5000);
