echo "--- Cài thư viện ---"
pip install -r requirement.txt

echo "-- Tạo dữ liệu ---"
python eapp/Models.py

echo "-- Chạy ứng dụng ---"
python -m flash run eapp/index.py