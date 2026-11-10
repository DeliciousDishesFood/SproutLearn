# 青芽 SproutLearn 后端镜像
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    TZ=Asia/Shanghai

WORKDIR /app

COPY requirements.txt ./

# 升级 pip 基础组件并配置阿里云 PyPI 镜像源，解决构建时拉包失败问题
RUN python -m pip install --upgrade pip setuptools wheel \
    && pip config set global.index-url https://mirrors.aliyun.com/pypi/simple/ \
    && pip config set install.trusted-host mirrors.aliyun.com \
    && pip install --no-cache-dir -r requirements.txt

# 只复制运行所需文件，避免把本地 .env / 测试缓存 / 上传文件带进镜像
COPY alembic.ini ./
COPY alembic ./alembic
COPY app ./app

RUN mkdir -p /data/uploads

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
