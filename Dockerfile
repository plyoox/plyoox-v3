FROM python:3.10 AS builder

WORKDIR /usr/app

RUN python -m venv /usr/app/venv
ENV PATH="/usr/app/venv/bin:$PATH"

COPY requirements.txt ./
RUN pip install -r requirements.txt

FROM python:3.10-slim

WORKDIR /usr/app

RUN apt-get update -y && apt-get install -y git

COPY --from=builder /usr/app /usr/app
COPY ./src ./src
COPY .git .git

ENV PATH="/usr/app/venv/bin:$PATH"

CMD ["python", "src/launcher.py"]