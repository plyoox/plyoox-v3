FROM python:3.10 AS builder

WORKDIR /usr/app

RUN python -m venv /usr/app/venv
ENV PATH="/usr/app/venv/bin:$PATH"

COPY requirements.txt ./
RUN pip install -r requirements.txt

FROM python:3.10-alpine

WORKDIR /usr/app

COPY --from=builder /usr/app /usr/app
COPY ./src ./src

ENV PATH="/usr/app/venv/bin:$PATH"

CMD ["python", "src/launcher.py"]