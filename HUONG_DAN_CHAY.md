# 🎵 HƯỚNG DẪN CHẠY API AUDIO (VieNeu-TTS) CHO SOUNDMATES

Đây là tài liệu hướng dẫn cụ thể cách khởi động Server xử lý âm thanh (từ Text kịch bản -> file Audio `.wav`) để phục vụ cho `ai-service` của bạn trả về `Success: true` và phát nhạc trên Website.

*Lưu ý: Bạn không cần dùng Docker Container `vineu-tts` nữa vì máy thiếu Card màn hình NVIDIA. Hệ thống này được code để chạy thẳng trên CPU của bạn mà vẫn rất nhẹ bằng File Python GGUF (Port 8008).*

---

### 🚀 CÁCH SỬ DỤNG NHANH NHẤT (dành cho Windows)

Mình đã tạo sẵn một file `.bat` chạy tự động cho bạn ngay trong thư mục này. Từ nay về sau hoặc khi mang source code sang máy mới, bạn chỉ việc:

1. Vào thư mục `Capstone\VieNeu-TTS`.
2. Truyền lệnh bằng Terminal hoặc tìm tệp: **`start_server.bat`**
3. **Double Click (nhấp đúp)** vào nó!

File `start_server.bat` sẽ thay bạn tự động:
- Kiểm tra xem máy đã tạo môi trường `venv` chưa (nếu mang qua máy mới, nó sẽ tự cài lại `pip install`).
- Tự động gõ lệnh kích hoạt `venv\Scripts\activate`.
- Mở Port `http://localhost:8008` để hứng API từ C# truyền sang.
*(Bạn hãy để nguyên cái cửa sổ chạy đen đen đó nhé. Lúc nào làm việc xong mới ấn dấu X tắt đi)*

---

### 💻 CÁCH CHẠY THỦ CÔNG BẰNG LỆNH CMD (Nếu bạn muốn gõ tay)

Bạn mở CMD (Command Prompt) hoặc PowerShell rồi dán lần lượt các câu thần chú sau:

```powershell
# B1: Di chuyển vào đúng thư mục con chứa Source Python
cd C:\Users\Admin\OneDrive\Desktop\Capstone\VieNeu-TTS

# B2: Kích hoạt môi trường Python ảo (để thư viện không dơ máy)
.\venv\Scripts\activate.bat
## (Nếu trên màn hình hiện chữ (venv) ở đầu dòng là thành công)

# B3: Gọi Python chạy Server Streamer (Cổng 8008)
python apps\web_stream.py
```
Khi bạn thấy hiện ra `🌍 Open http://localhost:8008 to test GGUF Streaming`, thì đó là lúc Backend C# của bạn sẵn sàng chọc vào để lấy Audio ra!

---

### ⚠️ BẢO TRÌ NẾU LỖI CHO LẬP TRÌNH VIÊN NHIỆM KỲ SAU

Giả sử sau này bạn đổi lại Server có máy gắn Card xịn (NVIDIA GPU), bạn muốn dùng lại Docker siêu tốc độ (cái mà gọi Port 23333). 
Thì bạn không cần chạy lệnh `python apps\web_stream.py` GGUF CPU này nữa. 
Lúc đó, bạn sẽ bật Docker bằng lệnh `docker run -d --gpus all pnnbao/vieneu-tts:serve ...` và chạy file API cầu nối `python apps\remote_stream.py` nhé! Cả 2 cách bản chất chỉ đổi máy chủ xử lý, nhưng API ném cho web (Port 8008) là giữ nguyên!
