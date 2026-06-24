# ReconFlow

ReconFlow là một **Framework Tự động Thu thập và Tổng hợp Thông tin (Automated Recon Aggregation Framework)** được thiết kế dành cho các Bug Bounty hunter, pentester và nhà nghiên cứu bảo mật. Công cụ này tự động chạy hàng loạt các công cụ trinh sát (recon) phổ biến, thu thập kết quả, chuẩn hóa, loại bỏ trùng lặp và phân loại các endpoint tìm được nhằm cung cấp một bộ dữ liệu sạch và có khả năng hành động ngay lập tức cho các cuộc đánh giá bảo mật của bạn.

## Tính năng chính

- **Điều phối Công cụ Tự động**: Tích hợp và chạy mượt mà các công cụ tiêu chuẩn trong ngành:
  - `subfinder` để tìm kiếm subdomain
  - `httpx` để xác định các host đang hoạt động (alive hosts)
  - `katana` để cào dữ liệu (crawling/spidering) website siêu tốc
  - `feroxbuster` để brute-force thư mục và tệp tin
  - `arjun` để khám phá các tham số (parameter discovery) ẩn
- **Tổng hợp & Loại bỏ Trùng lặp Thông minh**: Gộp kết quả từ nhiều công cụ khác nhau và loại bỏ các endpoint bị trùng lặp một cách chính xác.
- **Chuẩn hóa Dữ liệu (Normalization)**: Đưa output đa dạng của các công cụ về một định dạng cấu trúc thống nhất.
- **Phân loại & Chấm điểm Rủi ro (Classification)**: Tự động phân tích các endpoint và gán điểm rủi ro dựa trên các dấu hiệu "đáng chú ý" (ví dụ: trang quản trị admin, API endpoint, file nhạy cảm...).
- **Giao diện Dòng lệnh (CLI)**: Dễ sử dụng, được xây dựng bằng `Typer` và `Rich` giúp hiển thị kết quả đẹp mắt trên terminal.
- **Phục hồi Tiến trình**: Khả năng resume (tiếp tục) từ các trạng thái trước đó hoặc bỏ qua các giai đoạn cụ thể.
- **Xuất Dữ liệu**: Xuất các phát hiện (findings) ra định dạng JSON để dễ dàng tích hợp với các hệ thống khác.

## Hướng dẫn cài đặt

### Yêu cầu hệ thống

Hãy đảm bảo bạn đã cài đặt Python 3.8+. Bạn cũng cần cài đặt các công cụ recon ngoại vi (`subfinder`, `httpx`, `katana`, `feroxbuster`, `arjun`) và đảm bảo chúng có thể thực thi được trong `$PATH` của hệ thống.

### Cài đặt

1. Clone repository:
   ```bash
   git clone <repository-url>
   cd web-recon-framework
   ```

2. Cài đặt các thư viện Python cần thiết:
   ```bash
   pip install -r requirements.txt
   ```

## Cách sử dụng

ReconFlow cung cấp giao diện dòng lệnh (CLI) cực kỳ trực quan.

### Chạy quy trình Recon đầy đủ

Để chạy toàn bộ quy trình lên một domain mục tiêu:

```bash
python main.py run -t example.com
```

**Các tùy chọn nâng cao:**
- `--resume`: Tiếp tục quy trình đã bị dừng hoặc lỗi trước đó.
- `--skip`: Bỏ qua một số bước nhất định (cách nhau bằng dấu phẩy). Hữu ích nếu bạn đã có sẵn dữ liệu subdomain.
  ```bash
  python main.py run -t example.com --skip subfinder,amass
  ```
- `-c`, `--config`: Sử dụng file cấu hình YAML tùy chỉnh.

### Xem kết quả

Để hiển thị kết quả đã tổng hợp và phân loại:

```bash
python main.py show -t example.com
```

**Lọc và định dạng Output:**
- `--min-score`: Lọc các endpoint có điểm rủi ro lớn hơn hoặc bằng giá trị chỉ định.
- `--format interesting`: Chỉ hiển thị các endpoint được đánh dấu là "đáng chú ý" (interesting) dưới dạng bảng.
- `--format json`: Xuất toàn bộ dữ liệu tổng hợp ở định dạng JSON gốc.

```bash
python main.py show -t example.com --format interesting --min-score 3
```

## 📁 Cấu trúc Dự án

- `adapters/tools/`: Các wrapper để tích hợp công cụ recon ngoại vi.
- `core/`: Các engine lõi xử lý (`orchestrator`, `aggregator`, `classifier`, `deduplicator`, `normalizer`, `exporter`).
- `models/`: Các data model Pydantic giúp quản lý dữ liệu có cấu trúc.
- `utils/`: Các hàm hỗ trợ và cấu hình logging.
- `config/`: Nơi chứa file cấu hình (ví dụ: `config.yaml`).

## ⚠️ Tuyên bố miễn trừ trách nhiệm

Công cụ này chỉ được tạo ra với mục đích nghiên cứu bảo mật hợp pháp và giáo dục. Vui lòng chỉ sử dụng ReconFlow lên những hệ thống mà bạn đã được cấp phép kiểm tra một cách rõ ràng.
