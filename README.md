\---

title: Dashboard Cổ Phiếu Việt Nam

emoji: 📊

colorFrom: blue

colorTo: green

sdk: docker

app\_port: 7860

pinned: false

license: mit

short\_description: Phân tích cổ phiếu VN với AI, ROE ngành, Markowitz

\---



\# 📊 Dashboard Cổ Phiếu Việt Nam



Ứng dụng web phân tích cổ phiếu Việt Nam với AI hỗ trợ.



\## ✨ Tính năng



\### 📈 Thị trường

\- Bảng giá realtime 1500+ mã (HOSE, HNX, UPCOM)

\- Screener với bộ lọc đa tiêu chí: ngành, P/E, ROE, sentiment, kỹ thuật

\- Watchlist theo dõi mã yêu thích



\### 📊 Phân tích

\- \*\*Định giá\*\*: Graham, P/E fair, P/B fair, DCF, chia thưởng

\- \*\*Dupont 3 \& 5 lớp\*\*: bóc tách nguồn gốc ROE

\- \*\*So sánh ROE toàn ngành\*\*: 50+ mã/ngành

\- \*\*Kế hoạch giao dịch\*\*: entry, target, stop, R:R

\- \*\*Chỉ số rủi ro\*\*: Beta, σ, Sharpe, CAGR, Max Drawdown



\### 🤖 AI \& Báo cáo

\- Báo cáo AI chuyên sâu (Groq - miễn phí)

\- Sentiment tin tức tiếng Việt (từ điển + rule-based)

\- Chấm điểm tổng hợp 4 nhóm: Kỹ thuật + Cơ bản + Định giá + Tin tức

\- So sánh 2 mã cùng ngành với biểu đồ chuẩn hóa

\- Scrape báo cáo CTCK từ nhiều nguồn



\### 💼 Quản trị danh mục

\- \*\*Tối ưu Markowitz\*\*: SLSQP + Monte Carlo 5000 danh mục

\- \*\*Max Sharpe\*\* \& \*\*GMV\*\* (Global Minimum Variance)

\- Ma trận hiệp phương sai + đường biên hiệu quả

\- Phân tích tương quan, beta danh mục, DR



\## 🛠️ Công nghệ



\- \*\*Backend\*\*: Python 3.12, Flask, pandas, numpy, scipy

\- \*\*Data\*\*: vnstock 5.x (KBS), Yahoo Finance (fallback)

\- \*\*AI\*\*: Groq (gpt-oss-120b)

\- \*\*Chart\*\*: matplotlib, mplfinance

\- \*\*Report\*\*: reportlab (PDF)

\- \*\*Deploy\*\*: Docker, Hugging Face Spaces



\## 📖 Hướng dẫn sử dụng



1\. Mở link Space

2\. \*\*Tab Cổ Phiếu\*\* — xem bảng giá, dùng Screener để lọc

3\. \*\*Tab Phân Tích Sâu\*\* — nhập mã (VD: FPT) → phân tích toàn diện

4\. \*\*Tab So Sánh\*\* — chọn 2 mã để so sánh

5\. \*\*Tab Danh Mục\*\* — nhập 2-12 mã + tỷ trọng → tối ưu Markowitz



\## ⚠️ Lưu ý



\- \*\*Cold start\*\*: Free tier ngủ sau 15 phút → lần vào đầu chậm \~30-50s

\- \*\*Rate limit VNStock\*\*: 60 req/phút (gói Cộng đồng)

\- \*\*Playwright\*\*: Tắt trên HF (chỉ chạy local) — tab "Báo cáo CTCK" có thể trống

\- \*\*API key Groq\*\*: Cần key miễn phí từ https://console.groq.com để dùng AI



\## 📄 License



MIT



\---

Made with ❤️ for Vietnamese stock investors

