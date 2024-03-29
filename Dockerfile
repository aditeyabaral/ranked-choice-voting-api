FROM python

RUN apt update -y
RUN apt upgrade -y
RUN apt install python3-pip -y && pip3 install --upgrade pip

COPY app/ app/
COPY README.md README.md
COPY .env .env
COPY requirements.txt requirements.txt
RUN pip3 install --no-deps -r requirements.txt

CMD ["python3", "app/app.py"]