FROM python:3.10-slim

# 設定工作目錄
WORKDIR /app

# 複製所有檔案到容器中
COPY . /app

# 安裝依賴套件
RUN pip install --upgrade pip \
 && pip install -r requirements.txt

RUN pip install gradio==5.32.1

# 開放需要的埠口
EXPOSE 7861
EXPOSE 7861

# 執行應用程式
CMD ["python", "app.py"]
