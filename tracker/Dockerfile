FROM ubuntu:20.04

RUN apt-get update && apt-get install -y \
    python3.8 \
    python3-pip

COPY ./requirements.txt ./

RUN pip install -r requirements.txt

COPY ./app /app

ENTRYPOINT ["python3.8"]
CMD ["./app/main.py"]
